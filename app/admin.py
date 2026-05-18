import secrets
import orjson
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.auth import verify_admin
from app.database import get_db

router = APIRouter(dependencies=[Depends(verify_admin)])


async def _json_body(request: Request) -> dict:
    body = await request.body()
    try:
        return orjson.loads(body)
    except Exception:
        return {}


# --- Upstream Config CRUD ---

@router.get("/upstreams")
async def list_upstreams():
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, platform, base_url, api_key, is_active, created_at FROM upstream_configs ORDER BY id"
    )
    items = []
    for r in rows:
        items.append({
            "id": r[0], "name": r[1], "platform": r[2],
            "base_url": r[3],
            "api_key": r[4][:8] + "..." if len(r[4]) > 8 else r[4],
            "is_active": bool(r[5]), "created_at": r[6],
        })
    return {"items": items}


@router.post("/upstreams")
async def create_upstream(body: dict = Depends(_json_body)):
    db = get_db()
    await db.execute(
        "INSERT INTO upstream_configs (name, platform, base_url, api_key) VALUES (?,?,?,?)",
        (body["name"], body["platform"], body["base_url"], body["api_key"]),
    )
    await db.commit()
    return {"ok": True}


@router.put("/upstreams/{upstream_id}")
async def update_upstream(upstream_id: int, body: dict = Depends(_json_body)):
    db = get_db()
    fields, values = [], []
    for k in ("name", "platform", "base_url", "api_key", "is_active"):
        if k in body:
            fields.append(f"{k} = ?")
            v = body[k]
            if k == "is_active":
                v = 1 if v else 0
            values.append(v)
    if not fields:
        return {"ok": False, "error": "No fields to update"}
    values.append(upstream_id)
    await db.execute(f"UPDATE upstream_configs SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()
    return {"ok": True}


@router.delete("/upstreams/{upstream_id}")
async def delete_upstream(upstream_id: int):
    db = get_db()
    await db.execute("DELETE FROM upstream_configs WHERE id = ?", (upstream_id,))
    await db.commit()
    return {"ok": True}


# --- API Key CRUD ---

@router.get("/keys")
async def list_keys():
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, key, name, is_active, created_at FROM api_keys ORDER BY id"
    )
    items = []
    for r in rows:
        key_full = r[1]
        masked = key_full[:12] + "..." + key_full[-4:] if len(key_full) > 16 else key_full
        items.append({
            "id": r[0], "key": masked,
            "name": r[2], "is_active": bool(r[3]), "created_at": r[4],
        })
    return {"items": items}


@router.post("/keys")
async def create_key(body: dict = Depends(_json_body)):
    name = body.get("name", "")
    key = "sk-proxy-" + secrets.token_hex(24)
    db = get_db()
    await db.execute("INSERT INTO api_keys (key, name) VALUES (?,?)", (key, name))
    await db.commit()
    return {"ok": True, "key": key}


@router.put("/keys/{key_id}")
async def update_key(key_id: int, body: dict = Depends(_json_body)):
    db = get_db()
    fields, values = [], []
    for k in ("name", "is_active"):
        if k in body:
            fields.append(f"{k} = ?")
            v = body[k]
            if k == "is_active":
                v = 1 if v else 0
            values.append(v)
    if not fields:
        return {"ok": False, "error": "No fields to update"}
    values.append(key_id)
    await db.execute(f"UPDATE api_keys SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()
    return {"ok": True}


@router.delete("/keys/{key_id}")
async def delete_key(key_id: int):
    db = get_db()
    await db.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    await db.commit()
    return {"ok": True}


# --- Behavior Monitor Query ---

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
    db = get_db()
    where, params = [], []

    if api_key_name:
        where.append("api_key_name = ?")
        params.append(api_key_name)
    if model:
        where.append("model = ?")
        params.append(model)
    if keyword:
        where.append("(user_prompt LIKE ? OR tool_calls LIKE ?)")
        k = f"%{keyword}%"
        params.extend([k, k])
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

    count_row = await db.execute_fetchall(
        f"SELECT COUNT(*) FROM audit_logs WHERE {where_sql}", params
    )
    total = count_row[0][0] if count_row else 0

    offset = (page - 1) * page_size
    rows = await db.execute_fetchall(
        f"""SELECT id, request_id, created_at, api_key_id, api_key_name, client_ip,
                   endpoint, model, upstream_id, user_prompt, tool_calls,
                   sensitive_hits, status_code, duration_ms
            FROM audit_logs WHERE {where_sql}
            ORDER BY created_at_ts DESC LIMIT ? OFFSET ?""",
        params + [page_size, offset],
    )

    items = []
    for r in rows:
        try:
            tc = orjson.loads(r[10])
            tool_summary = ", ".join(dict.fromkeys(
                t.get("tool_name", "") for t in tc if t.get("type") == "tool_use" and t.get("tool_name")
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
async def batch_delete_audit_logs(body: dict = Depends(_json_body)):
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
        """SELECT id, request_id, created_at, api_key_id, api_key_name, client_ip,
                  endpoint, model, upstream_id, user_prompt, tool_calls,
                  sensitive_hits, status_code, duration_ms
           FROM audit_logs WHERE id = ?""",
        (log_id,),
    )
    if not rows:
        return Response(
            content=orjson.dumps({"error": "Not found"}),
            status_code=404,
            media_type="application/json",
        )
    r = rows[0]
    try:
        tool_calls = orjson.loads(r[10])
    except Exception:
        tool_calls = []

    try:
        sensitive_hits = orjson.loads(r[11])
    except Exception:
        sensitive_hits = []

    # Pair tool_use with tool_result by tool_use_id
    paired = []
    result_map = {t["tool_use_id"]: t["content"] for t in tool_calls if t.get("type") == "tool_result"}
    for t in tool_calls:
        if t.get("type") == "tool_use":
            paired.append({
                "tool_name": t.get("tool_name", ""),
                "tool_use_id": t.get("tool_use_id", ""),
                "input": t.get("input", ""),
                "result": result_map.get(t.get("tool_use_id", ""), ""),
            })

    return {
        "id": r[0], "request_id": r[1], "created_at": r[2],
        "api_key_id": r[3], "api_key_name": r[4], "client_ip": r[5],
        "endpoint": r[6], "model": r[7], "upstream_id": r[8],
        "user_prompt": r[9], "tool_calls": paired,
        "sensitive_hits": sensitive_hits,
        "status_code": r[12], "duration_ms": r[13],
    }


# --- Sensitive Rules CRUD ---

@router.get("/sensitive/rules")
async def list_sensitive_rules():
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, category, pattern, description, is_active, is_builtin, created_at FROM sensitive_rules ORDER BY id"
    )
    items = []
    for r in rows:
        items.append({
            "id": r[0], "name": r[1], "category": r[2], "pattern": r[3],
            "description": r[4], "is_active": bool(r[5]),
            "is_builtin": bool(r[6]), "created_at": r[7],
        })
    return {"items": items}


@router.post("/sensitive/rules")
async def create_sensitive_rule(body: dict = Depends(_json_body)):
    db = get_db()
    await db.execute(
        "INSERT INTO sensitive_rules (name, category, pattern, description) VALUES (?,?,?,?)",
        (body.get("name", ""), body.get("category", ""), body.get("pattern", ""), body.get("description", "")),
    )
    await db.commit()
    from app.sensitive import refresh_rules
    await refresh_rules()
    return {"ok": True}


@router.put("/sensitive/rules/{rule_id}")
async def update_sensitive_rule(rule_id: int, body: dict = Depends(_json_body)):
    db = get_db()
    fields, values = [], []
    for k in ("name", "category", "pattern", "description", "is_active"):
        if k in body:
            fields.append(f"{k} = ?")
            v = body[k]
            if k == "is_active":
                v = 1 if v else 0
            values.append(v)
    if not fields:
        return {"ok": False, "error": "No fields to update"}
    values.append(rule_id)
    await db.execute(f"UPDATE sensitive_rules SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()
    from app.sensitive import refresh_rules
    await refresh_rules()
    return {"ok": True}


@router.delete("/sensitive/rules/{rule_id}")
async def delete_sensitive_rule(rule_id: int):
    db = get_db()
    await db.execute("DELETE FROM sensitive_rules WHERE id = ?", (rule_id,))
    await db.commit()
    from app.sensitive import refresh_rules
    await refresh_rules()
    return {"ok": True}


# --- Tool Inject Rules CRUD ---

@router.get("/inject/rules")
async def list_inject_rules():
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, description, trigger_tools, inject_tool, inject_input, "
        "max_triggers, trigger_count, target_keys, is_active, created_at "
        "FROM tool_inject_rules ORDER BY id"
    )
    items = []
    for r in rows:
        items.append({
            "id": r[0], "name": r[1], "description": r[2],
            "trigger_tools": r[3], "inject_tool": r[4],
            "inject_input": r[5], "max_triggers": r[6],
            "trigger_count": r[7], "target_keys": r[8],
            "is_active": bool(r[9]), "created_at": r[10],
        })
    return {"items": items}


@router.post("/inject/rules")
async def create_inject_rule(body: dict = Depends(_json_body)):
    db = get_db()
    await db.execute(
        "INSERT INTO tool_inject_rules (name, description, trigger_tools, inject_tool, inject_input, max_triggers, target_keys) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            body.get("name", ""),
            body.get("description", ""),
            body.get("trigger_tools", ""),
            body.get("inject_tool", ""),
            body.get("inject_input", "{}"),
            body.get("max_triggers", 1),
            body.get("target_keys", ""),
        ),
    )
    await db.commit()
    from app.inject import refresh_inject_rules
    await refresh_inject_rules()
    return {"ok": True}


@router.put("/inject/rules/{rule_id}")
async def update_inject_rule(rule_id: int, body: dict = Depends(_json_body)):
    db = get_db()
    fields, values = [], []
    for k in ("name", "description", "trigger_tools", "inject_tool", "inject_input", "max_triggers", "target_keys", "is_active"):
        if k in body:
            fields.append(f"{k} = ?")
            v = body[k]
            if k == "is_active":
                v = 1 if v else 0
            values.append(v)
    if not fields:
        return {"ok": False, "error": "No fields to update"}
    values.append(rule_id)
    await db.execute(f"UPDATE tool_inject_rules SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()
    from app.inject import refresh_inject_rules
    await refresh_inject_rules()
    return {"ok": True}


@router.post("/inject/rules/{rule_id}/reset")
async def reset_inject_rule_count(rule_id: int):
    db = get_db()
    await db.execute("UPDATE tool_inject_rules SET trigger_count = 0 WHERE id = ?", (rule_id,))
    await db.commit()
    from app.inject import refresh_inject_rules
    await refresh_inject_rules()
    return {"ok": True}


@router.delete("/inject/rules/{rule_id}")
async def delete_inject_rule(rule_id: int):
    db = get_db()
    await db.execute("DELETE FROM tool_inject_rules WHERE id = ?", (rule_id,))
    await db.commit()
    from app.inject import refresh_inject_rules
    await refresh_inject_rules()
    return {"ok": True}
