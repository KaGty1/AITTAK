import secrets

from fastapi import HTTPException, Request

from app.config import ADMIN_PASSWORD
from app.database import get_db


def _extract_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key", "").strip()


async def verify_api_key(request: Request) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key")
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name FROM api_keys WHERE key = ? AND is_active = 1",
        (token,),
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"id": rows[0][0], "name": rows[0][1]}


async def verify_admin(request: Request) -> None:
    token = _extract_token(request)
    if not token or not secrets.compare_digest(token, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Unauthorized")
