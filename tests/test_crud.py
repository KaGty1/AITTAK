import orjson
from starlette.requests import Request

from app.api.crud import json_body, partial_update


def make_request(payload: bytes) -> Request:
    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    return Request({"type": "http", "method": "POST", "headers": []}, receive)


async def test_json_body():
    req = make_request(orjson.dumps({"a": 1}))
    assert await json_body(req) == {"a": 1}
    assert await json_body(make_request(b"broken")) == {}
    assert await json_body(make_request(b"[1,2]")) == {}


async def test_partial_update(db):
    await db.execute(
        "INSERT INTO upstream_configs (name, platform, base_url, api_key) VALUES ('u1', 'claude', 'http://x', 'k')"
    )
    await db.commit()

    result = await partial_update(
        "upstream_configs",
        ["name", "platform", "base_url", "api_key", "is_active"],
        {"name": "u2", "is_active": False, "ignored": "x"},
        1,
    )
    assert result == {"ok": True}
    rows = await db.execute_fetchall("SELECT name, is_active FROM upstream_configs")
    assert tuple(rows[0]) == ("u2", 0)

    result = await partial_update("upstream_configs", ["name"], {}, 1)
    assert result == {"ok": False, "error": "No fields to update"}


async def test_seeded_sensitive_rules(db):
    rows = await db.execute_fetchall("SELECT COUNT(*) FROM sensitive_rules")
    assert rows[0][0] == 15


async def test_main_app_imports():
    from app.main import app
    assert app.title == "AITTAK"
    assert any(r.path == "/v1/messages" for r in app.routes)
    assert any(r.path == "/admin/api/audit/logs" for r in app.routes)
