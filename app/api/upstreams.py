from fastapi import APIRouter, Depends

from app.api.crud import json_body, partial_update
from app.database import get_db

router = APIRouter()

_FIELDS = ["name", "platform", "base_url", "api_key", "is_active"]


@router.get("/upstreams")
async def list_upstreams():
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, platform, base_url, api_key, is_active, created_at FROM upstream_configs ORDER BY id"
    )
    return {"items": [
        {
            "id": r[0],
            "name": r[1],
            "platform": r[2],
            "base_url": r[3],
            "api_key": r[4][:8] + "..." if len(r[4]) > 8 else r[4],
            "is_active": bool(r[5]),
            "created_at": r[6],
        }
        for r in rows
    ]}


@router.post("/upstreams")
async def create_upstream(body: dict = Depends(json_body)):
    db = get_db()
    await db.execute(
        "INSERT INTO upstream_configs (name, platform, base_url, api_key) VALUES (?,?,?,?)",
        (body["name"], body["platform"], body["base_url"], body["api_key"]),
    )
    await db.commit()
    return {"ok": True}


@router.put("/upstreams/{upstream_id}")
async def update_upstream(upstream_id: int, body: dict = Depends(json_body)):
    return await partial_update("upstream_configs", _FIELDS, body, upstream_id)


@router.delete("/upstreams/{upstream_id}")
async def delete_upstream(upstream_id: int):
    db = get_db()
    await db.execute("DELETE FROM upstream_configs WHERE id = ?", (upstream_id,))
    await db.commit()
    return {"ok": True}
