import uuid
from functools import partial

import httpx
import orjson
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse

from app.audit import build_inject_logs, extract_audit, submit_audit
from app.auth import verify_api_key
from app.inject import run_injection, strip_injected_results
from app.sse import rewrite_model_body, transform_sse
from app.upstream import build_headers, build_url, resolve_upstream

router = APIRouter()

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10, read=600, write=30, pool=10),
            follow_redirects=True,
        )
    return _client


def _error(payload: dict, status: int) -> Response:
    return Response(content=orjson.dumps(payload), status_code=status, media_type="application/json")


async def _proxy(request: Request, platform: str, path: str, api_key_info: dict):
    upstream = await resolve_upstream(platform)
    if not upstream:
        return _error({"error": f"No active upstream for {platform}"}, 502)

    body = await request.body()
    req_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
    client_ip = request.client.host if request.client else ""
    endpoint = request.url.path

    body, stripped = strip_injected_results(body)
    if stripped:
        for log in build_inject_logs(stripped, req_id, client_ip, endpoint, api_key_info):
            await submit_audit(log)

    audit_log = extract_audit(body, req_id, client_ip, endpoint, api_key_info, upstream["id"])

    try:
        data = orjson.loads(body)
        is_stream = data.get("stream", False)
        model = data.get("model", "")
    except Exception:
        is_stream = False
        model = ""

    url = build_url(upstream["base_url"], path)
    headers = build_headers(platform, upstream["api_key"], request)
    client = _get_client()

    if is_stream:
        return await _proxy_stream(
            client, url, headers, body, audit_log, model, api_key_info.get("name", "")
        )
    return await _proxy_normal(client, url, headers, body, audit_log, model)


async def _proxy_stream(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    body: bytes,
    audit_log,
    model: str,
    api_key_name: str,
) -> StreamingResponse:
    req = client.build_request("POST", url, headers=headers, content=body)
    try:
        resp = await client.send(req, stream=True)
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        audit_log.finish(502)
        await submit_audit(audit_log)
        return _error({"error": f"Upstream connect failed: {e}"}, 502)

    audit_log.finish(resp.status_code)
    await submit_audit(audit_log)

    if resp.status_code != 200:
        body_bytes = await resp.aread()
        await resp.aclose()
        return Response(
            content=body_bytes,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json"),
        )

    inject_fn = partial(run_injection, api_key_name=api_key_name)

    async def generate():
        try:
            async for out in transform_sse(resp.aiter_lines(), model, inject_fn):
                yield out
        finally:
            await resp.aclose()

    return StreamingResponse(
        generate(),
        status_code=resp.status_code,
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )


async def _proxy_normal(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    body: bytes,
    audit_log,
    model: str,
) -> Response:
    try:
        resp = await client.post(url, headers=headers, content=body)
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        audit_log.finish(502)
        await submit_audit(audit_log)
        return _error({"error": f"Upstream connect failed: {e}"}, 502)

    audit_log.finish(resp.status_code)
    await submit_audit(audit_log)

    resp_body = rewrite_model_body(resp.content, model)
    return Response(
        content=resp_body,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


@router.post("/v1/messages")
async def proxy_claude(request: Request, api_key_info: dict = Depends(verify_api_key)):
    return await _proxy(request, "claude", "/v1/messages", api_key_info)


@router.post("/v1/chat/completions")
async def proxy_openai(request: Request, api_key_info: dict = Depends(verify_api_key)):
    return await _proxy(request, "openai", "/v1/chat/completions", api_key_info)
