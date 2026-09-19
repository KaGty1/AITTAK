import orjson
from fastapi import APIRouter, Depends, Query, Response

from app.api.crud import json_body
from app.database import get_db

router = APIRouter()

_LIST_SQL = """SELECT id, request_id, created_at, api_key_id, api_key_name, client_ip,
                      endpoint, model, upstream_id, user_prompt, tool_calls,
                      sensitive_hits, status_code, duration_ms"""


@router.get("/audit/logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    api_key_name: str | None = None,
    model: str | None = None,
    keyword: str | None = None,
    sensitive_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
):
    where, params = [], []
    if api_key_name:
        where.append("api_key_name = ?")
        params.append(api_key_name)
    if model:
        where.append("model = ?")
        params.append(model)
    if keyword:
        where.append("(user_prompt LIKE ? OR tool_calls LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw])
    if sensitive_type:
        where.append("sensitive_hits LIKE ?")
        params.append(f'%"rule_name":"{sensitive_type}"%')
    if start_time:
        where.append("created_at >= ?")
        params.append(start_time)
    if end_time:
        where.append("created_at <= ?")
        params.append(end_time)

    where_sql = " AND ".join(where) if where else "1=1"
    db = get_db()
    count_rows = await db.execute_fetchall(
        f"SELECT COUNT(*) FROM audit_logs WHERE {where_sql}", params
    )
    total = count_rows[0][0] if count_rows else 0

    offset = (page - 1) * page_size
    rows = await db.execute_fetchall(
        f"{_LIST_SQL} FROM audit_logs WHERE {where_sql} "
        f"ORDER BY created_at_ts DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    )

    items = []
    for r in rows:
        try:
            calls = orjson.loads(r[10])
            tool_summary = ", ".join(dict.fromkeys(
                t.get("tool_name", "")
                for t in calls
                if isinstance(t, dict) and t.get("type") == "tool_use" and t.get("tool_name")
            ))
        except Exception:
            tool_summary = ""
        try:
            sensitive_hits = orjson.loads(r[11])
        except Exception:
            sensitive_hits = []
        items.append({
            "id": r[0], "request_id": r[1], "created_at": r[2],
            "api_key_id": r[3], "api_key_name": r[4], "client_ip": r[5],
            "endpoint": r[6], "model": r[7], "upstream_id": r[8],
            "user_prompt": r[9], "tool_summary": tool_summary,
            "sensitive_hits": sensitive_hits,
            "status_code": r[12], "duration_ms": r[13],
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/audit/logs/delete")
async def batch_delete_audit_logs(body: dict = Depends(json_body)):
    ids = body.get("ids", [])
    if not ids or not isinstance(ids, list):
        return {"ok": False, "error": "No ids provided"}
    db = get_db()
    placeholders = ",".join("?" for _ in ids)
    await db.execute(f"DELETE FROM audit_logs WHERE id IN ({placeholders})", ids)
    await db.commit()
    return {"ok": True, "deleted": len(ids)}


@router.delete("/audit/logs")
async def clear_all_audit_logs():
    db = get_db()
    await db.execute("DELETE FROM audit_logs")
    await db.commit()
    return {"ok": True}


@router.get("/audit/logs/{log_id}")
async def get_audit_log(log_id: int):
    db = get_db()
    rows = await db.execute_fetchall(
        f"{_LIST_SQL} FROM audit_logs WHERE id = ?", (log_id,)
    )
    if not rows:
        return Response(
            content=orjson.dumps({"error": "Not found"}),
            status_code=404,
            media_type="application/json",
        )
    r = rows[0]
    try:
        calls = orjson.loads(r[10])
    except Exception:
        calls = []
    try:
        sensitive_hits = orjson.loads(r[11])
    except Exception:
        sensitive_hits = []

    results = {
        t.get("tool_use_id"): t.get("content", "")
        for t in calls
        if isinstance(t, dict) and t.get("type") == "tool_result"
    }
    paired = [
        {
            "tool_name": t.get("tool_name", ""),
            "tool_use_id": t.get("tool_use_id", ""),
            "input": t.get("input", ""),
            "result": results.get(t.get("tool_use_id", ""), ""),
        }
        for t in calls
        if isinstance(t, dict) and t.get("type") == "tool_use"
    ]

    return {
        "id": r[0], "request_id": r[1], "created_at": r[2],
        "api_key_id": r[3], "api_key_name": r[4], "client_ip": r[5],
        "endpoint": r[6], "model": r[7], "upstream_id": r[8],
        "user_prompt": r[9], "tool_calls": paired,
        "sensitive_hits": sensitive_hits,
        "status_code": r[12], "duration_ms": r[13],
    }
