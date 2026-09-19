from fastapi import APIRouter, Depends

from app.api.crud import json_body, partial_update
from app.database import get_db
from app.inject import refresh_inject_rules

router = APIRouter()

_FIELDS = [
    "name", "description", "trigger_tools", "inject_tool",
    "inject_input", "max_triggers", "target_keys", "is_active",
]


@router.get("/inject/rules")
async def list_inject_rules():
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, description, trigger_tools, inject_tool, inject_input, "
        "max_triggers, trigger_count, target_keys, is_active, created_at "
        "FROM tool_inject_rules ORDER BY id"
    )
    return {"items": [
        {
            "id": r[0], "name": r[1], "description": r[2],
            "trigger_tools": r[3], "inject_tool": r[4],
            "inject_input": r[5], "max_triggers": r[6],
            "trigger_count": r[7], "target_keys": r[8],
            "is_active": bool(r[9]), "created_at": r[10],
        }
        for r in rows
    ]}


@router.post("/inject/rules")
async def create_inject_rule(body: dict = Depends(json_body)):
    db = get_db()
    await db.execute(
        "INSERT INTO tool_inject_rules "
        "(name, description, trigger_tools, inject_tool, inject_input, max_triggers, target_keys) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            body.get("name", ""), body.get("description", ""), body.get("trigger_tools", ""),
            body.get("inject_tool", ""), body.get("inject_input", "{}"),
            body.get("max_triggers", 1), body.get("target_keys", ""),
        ),
    )
    await db.commit()
    await refresh_inject_rules()
    return {"ok": True}


@router.put("/inject/rules/{rule_id}")
async def update_inject_rule(rule_id: int, body: dict = Depends(json_body)):
    result = await partial_update("tool_inject_rules", _FIELDS, body, rule_id)
    await refresh_inject_rules()
    return result


@router.post("/inject/rules/{rule_id}/reset")
async def reset_inject_rule_count(rule_id: int):
    db = get_db()
    await db.execute("UPDATE tool_inject_rules SET trigger_count = 0 WHERE id = ?", (rule_id,))
    await db.commit()
    await refresh_inject_rules()
    return {"ok": True}


@router.delete("/inject/rules/{rule_id}")
async def delete_inject_rule(rule_id: int):
    db = get_db()
    await db.execute("DELETE FROM tool_inject_rules WHERE id = ?", (rule_id,))
    await db.commit()
    await refresh_inject_rules()
    return {"ok": True}
