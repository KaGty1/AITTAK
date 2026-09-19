from fastapi import Request

from app.database import get_db


async def resolve_upstream(platform: str) -> dict | None:
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, base_url, api_key FROM upstream_configs WHERE platform = ? AND is_active = 1 LIMIT 1",
        (platform,),
    )
    if not rows:
        return None
    return {"id": rows[0][0], "base_url": rows[0][1], "api_key": rows[0][2]}


def build_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def build_headers(platform: str, api_key: str, request: Request) -> dict:
    headers = {"content-type": "application/json"}
    if platform == "claude":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        beta = request.headers.get("anthropic-beta")
        if beta:
            headers["anthropic-beta"] = beta
    else:
        headers["authorization"] = f"Bearer {api_key}"
    return headers
