import secrets

from fastapi import APIRouter, Depends

from app.api.crud import json_body, partial_update
from app.database import get_db

router = APIRouter()

_FIELDS = ["name", "is_active"]


@router.get("/keys")
async def list_keys():
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, key, name, is_active, created_at FROM api_keys ORDER BY id"
    )
    return {"items": [
        {
            "id": r[0],
            "key": r[1][:12] + "..." + r[1][-4:] if len(r[1]) > 16 else r[1],
            "name": r[2],
            "is_active": bool(r[3]),
            "created_at": r[4],
        }
        for r in rows
    ]}


@router.post("/keys")
async def create_key(body: dict = Depends(json_body)):
    key = "sk-proxy-" + secrets.token_hex(24)
    db = get_db()
    await db.execute("INSERT INTO api_keys (key, name) VALUES (?,?)", (key, body.get("name", "")))
    await db.commit()
    return {"ok": True, "key": key}


@router.put("/keys/{key_id}")
async def update_key(key_id: int, body: dict = Depends(json_body)):
    return await partial_update("api_keys", _FIELDS, body, key_id)


@router.delete("/keys/{key_id}")
async def delete_key(key_id: int):
    db = get_db()
    await db.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    await db.commit()
    return {"ok": True}
