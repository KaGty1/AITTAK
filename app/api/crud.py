import orjson
from fastapi import Request

from app.database import get_db


async def json_body(request: Request) -> dict:
    body = await request.body()
    try:
        value = orjson.loads(body)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


async def partial_update(table: str, fields: list[str], body: dict, row_id: int) -> dict:
    sets, values = [], []
    for name in fields:
        if name not in body:
            continue
        value = body[name]
        if name == "is_active":
            value = 1 if value else 0
        sets.append(f"{name} = ?")
        values.append(value)
    if not sets:
        return {"ok": False, "error": "No fields to update"}
    values.append(row_id)
    db = get_db()
    await db.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?", values)
    await db.commit()
    return {"ok": True}
