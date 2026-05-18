import re
import orjson
from app.database import get_db

_rules_cache: list[dict] | None = None
_compiled_cache: list[tuple[dict, re.Pattern]] | None = None


async def load_rules() -> list[dict]:
    """从 DB 加载 active 规则并编译正则，结果缓存。"""
    global _rules_cache, _compiled_cache
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, pattern FROM sensitive_rules WHERE is_active = 1"
    )
    _rules_cache = [{"id": r[0], "name": r[1], "pattern": r[2]} for r in rows]
    _compiled_cache = []
    for rule in _rules_cache:
        try:
            _compiled_cache.append((rule, re.compile(rule["pattern"])))
        except re.error:
            pass  # skip invalid regex
    return _rules_cache


async def refresh_rules():
    """规则变更时调用，清除缓存使下次扫描重新加载。"""
    global _rules_cache, _compiled_cache
    _rules_cache = None
    _compiled_cache = None


def scan_text(text: str) -> list[dict]:
    """对文本执行所有 active 规则匹配，返回命中列表。"""
    if not _compiled_cache or not text:
        return []
    hits = []
    for rule, pattern in _compiled_cache:
        matches = pattern.findall(text)
        if matches:
            hits.append({"rule_id": rule["id"], "rule_name": rule["name"], "count": len(matches)})
    return hits


def scan_audit_log(user_prompt: str, tool_calls_json: str) -> str:
    """扫描 user_prompt + tool_calls 内容，返回 hits JSON 字符串。"""
    all_hits: dict[int, dict] = {}

    # 扫描 user_prompt
    for hit in scan_text(user_prompt):
        key = hit["rule_id"]
        if key in all_hits:
            all_hits[key]["count"] += hit["count"]
        else:
            all_hits[key] = hit.copy()

    # 解析 tool_calls JSON，扫描每个 input 和 content
    try:
        items = orjson.loads(tool_calls_json)
        for item in items:
            text = str(item.get("input", "")) + " " + str(item.get("content", ""))
            for hit in scan_text(text):
                key = hit["rule_id"]
                if key in all_hits:
                    all_hits[key]["count"] += hit["count"]
                else:
                    all_hits[key] = hit.copy()
    except Exception:
        pass

    return orjson.dumps(list(all_hits.values())).decode() if all_hits else "[]"
