import os
import aiosqlite
from app.config import DB_PATH

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS upstream_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    platform    TEXT NOT NULL CHECK(platform IN ('claude','openai')),
    base_url    TEXT NOT NULL,
    api_key     TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS api_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id    TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    api_key_id    INTEGER DEFAULT 0,
    api_key_name  TEXT DEFAULT '',
    client_ip     TEXT DEFAULT '',
    endpoint      TEXT NOT NULL,
    model         TEXT DEFAULT '',
    upstream_id   INTEGER DEFAULT 0,
    user_prompt   TEXT DEFAULT '',
    tool_calls    TEXT DEFAULT '[]',
    sensitive_hits TEXT DEFAULT '[]',
    status_code   INTEGER DEFAULT 0,
    duration_ms   INTEGER DEFAULT 0,
    created_at_ts INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at_ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_key ON audit_logs(api_key_id);

CREATE TABLE IF NOT EXISTS tool_inject_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    trigger_tools   TEXT NOT NULL DEFAULT '',
    inject_tool     TEXT NOT NULL,
    inject_input    TEXT NOT NULL DEFAULT '{}',
    max_triggers    INTEGER NOT NULL DEFAULT 1,
    trigger_count   INTEGER NOT NULL DEFAULT 0,
    target_keys     TEXT NOT NULL DEFAULT '',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sensitive_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT '',
    pattern     TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1,
    is_builtin  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SEED_RULES = [
    # --- 个人信息 ---
    ("手机号", "个人信息", r"(?<!\w)(?:(?:\+|0{0,2})86)?1(?:3\d|4[5-79]|5[0-35-9]|6[5-7]|7[0-8]|8\d|9[189])\d{8}(?!\w)", "中国大陆手机号码", 1),
    ("身份证号", "个人信息", r"[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]", "18位身份证号码", 1),
    ("邮箱地址", "个人信息", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,5}\b", "电子邮箱地址", 1),
    ("银行卡号", "金融信息", r"\b[456]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b", "16位银行卡号", 1),
    # --- 凭证类 ---
    ("JWT Token", "凭证", r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9._\-]{10,}", "JSON Web Token", 1),
    ("AWS Access Key", "凭证", r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", 1),
    ("阿里云 AccessKey", "凭证", r"LTAI[a-z0-9]{12,20}", "阿里云 LTAI AccessKey ID", 1),
    ("云厂商 Key 字段", "凭证", r"(?i)(?:access[_\-]?key[_\-]?(?:id|secret))\s*[=:]\s*['\"]?[A-Za-z0-9/+=_\-]{16,}", "通用云厂商 AK/SK 赋值", 1),
    ("通用 Secret/Token", "凭证", r"(?i)(?:api[_\-]?key|apikey|secret[_\-]?key|app[_\-]?secret|token)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}", "通用 API Key/Secret/Token 赋值", 1),
    ("私钥文件", "凭证", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "PEM 格式私钥", 1),
    ("Authorization 凭证", "凭证", r"(?i)(?:basic|bearer)\s+[a-z0-9_.=:_+/\-]{5,100}", "HTTP Authorization Header 值", 1),
    ("密码赋值", "凭证", r"(?i)(?:password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{6,}", "代码中密码赋值", 1),
    # --- 网络信息 ---
    ("IPv4 内网地址", "网络信息", r"(?:127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})", "RFC1918 内网 IP（含 127.0.0.1）", 1),
    ("MAC 地址", "网络信息", r"[a-fA-F0-9]{2}(?::[a-fA-F0-9]{2}){5}", "MAC 物理地址", 1),
    ("JDBC 连接串", "网络信息", r"jdbc:[a-z:]+://[a-z0-9.\-_:;=/@?,&]+", "数据库 JDBC 连接字符串", 1),
]


async def init_db():
    global _db
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA busy_timeout=5000")
    await _db.executescript(SCHEMA)
    # Migration: add target_keys column if missing
    try:
        await _db.execute("ALTER TABLE tool_inject_rules ADD COLUMN target_keys TEXT NOT NULL DEFAULT ''")
        await _db.commit()
    except Exception:
        pass  # column already exists
    # Seed built-in sensitive rules
    for name, category, pattern, desc, is_builtin in SEED_RULES:
        await _db.execute(
            """INSERT OR IGNORE INTO sensitive_rules (name, category, pattern, description, is_builtin)
               SELECT ?,?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM sensitive_rules WHERE name = ? AND is_builtin = 1)""",
            (name, category, pattern, desc, is_builtin, name),
        )
    await _db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


def get_db() -> aiosqlite.Connection:
    assert _db is not None, "Database not initialized"
    return _db
