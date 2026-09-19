from fastapi import APIRouter, Depends

from app.api.crud import json_body, partial_update
from app.database import get_db
from app.sensitive import refresh_rules

router = APIRouter()

_FIELDS = ["name", "category", "pattern", "description", "is_active"]


@router.get("/sensitive/rules")
async def list_sensitive_rules():
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, category, pattern, description, is_active, is_builtin, created_at "
        "FROM sensitive_rules ORDER BY id"
    )
    return {"items": [
        {
            "id": r[0], "name": r[1], "category": r[2], "pattern": r[3],
            "description": r[4], "is_active": bool(r[5]),
            "is_builtin": bool(r[6]), "created_at": r[7],
        }
        for r in rows
    ]}


@router.post("/sensitive/rules")
async def create_sensitive_rule(body: dict = Depends(json_body)):
    db = get_db()
    await db.execute(
        "INSERT INTO sensitive_rules (name, category, pattern, description) VALUES (?,?,?,?)",
        (body.get("name", ""), body.get("category", ""), body.get("pattern", ""), body.get("description", "")),
    )
    await db.commit()
    await refresh_rules()
    return {"ok": True}


@router.put("/sensitive/rules/{rule_id}")
async def update_sensitive_rule(rule_id: int, body: dict = Depends(json_body)):
    result = await partial_update("sensitive_rules", _FIELDS, body, rule_id)
    await refresh_rules()
    return result


@router.delete("/sensitive/rules/{rule_id}")
async def delete_sensitive_rule(rule_id: int):
    db = get_db()
    await db.execute("DELETE FROM sensitive_rules WHERE id = ?", (rule_id,))
    await db.commit()
    await refresh_rules()
    return {"ok": True}
