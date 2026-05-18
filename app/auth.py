from fastapi import Request, HTTPException
from app.database import get_db
from app.config import ADMIN_PASSWORD


def _extract_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key", "").strip()


async def verify_api_key(request: Request) -> dict:
    """代理接口认证：验证客户端提供的 API Key。"""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key")

    db = get_db()
    row = await db.execute_fetchall(
        "SELECT id, name FROM api_keys WHERE key = ? AND is_active = 1",
        (token,),
    )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"id": row[0][0], "name": row[0][1]}


async def verify_admin(request: Request):
    """管理后台认证：验证管理员密码。"""
    token = _extract_token(request)
    if token != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
