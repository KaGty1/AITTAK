import re

import orjson

from app.database import get_db

_rules_cache: list[dict] | None = None
_compiled_cache: list[tuple[dict, re.Pattern]] | None = None


async def load_rules() -> list[dict]:
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
            pass
    return _rules_cache


async def refresh_rules() -> None:
    global _rules_cache, _compiled_cache
    _rules_cache = None
    _compiled_cache = None


async def ensure_rules_loaded() -> None:
    if _compiled_cache is None:
        await load_rules()


def scan_compiled(text: str, compiled: list[tuple[dict, re.Pattern]]) -> list[dict]:
    hits = []
    for rule, pattern in compiled:
        matches = pattern.findall(text)
        if matches:
            hits.append({"rule_id": rule["id"], "rule_name": rule["name"], "count": len(matches)})
    return hits


def scan_text(text: str) -> list[dict]:
    if not _compiled_cache or not text:
        return []
    return scan_compiled(text, _compiled_cache)


def scan_audit_log(user_prompt: str, tool_calls_json: str) -> str:
    texts = [user_prompt]
    try:
        items = orjson.loads(tool_calls_json)
        for item in items:
            if isinstance(item, dict):
                texts.append(str(item.get("input", "")) + " " + str(item.get("content", "")))
    except Exception:
        pass

    all_hits: dict[int, dict] = {}
    for text in texts:
        for hit in scan_text(text):
            key = hit["rule_id"]
            if key in all_hits:
                all_hits[key]["count"] += hit["count"]
            else:
                all_hits[key] = hit.copy()
    return orjson.dumps(list(all_hits.values())).decode() if all_hits else "[]"
