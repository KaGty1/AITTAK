from typing import AsyncIterator, Awaitable, Callable

import orjson

InjectFn = Callable[[set[str], int], Awaitable[list[str]]]


def sse_field(line: str, name: str) -> str | None:
    if not line.startswith(name + ":"):
        return None
    rest = line[len(name) + 1:]
    return rest[1:] if rest.startswith(" ") else rest


def rewrite_model_line(line: str, model: str) -> str:
    payload = sse_field(line, "data")
    if payload is None or not model or '"model"' not in payload:
        return line
    try:
        obj = orjson.loads(payload)
    except Exception:
        return line
    changed = False
    if isinstance(obj, dict):
        if obj.get("model") not in (None, model):
            obj["model"] = model
            changed = True
        message = obj.get("message")
        if isinstance(message, dict) and message.get("model") not in (None, model):
            message["model"] = model
            changed = True
    if changed:
        return "data: " + orjson.dumps(obj).decode()
    return line


def rewrite_model_body(body: bytes, model: str) -> bytes:
    if not model:
        return body
    try:
        obj = orjson.loads(body)
    except Exception:
        return body
    if isinstance(obj, dict) and obj.get("model") not in (None, model):
        obj["model"] = model
        return orjson.dumps(obj)
    return body


async def transform_sse(source: AsyncIterator[str], model: str, inject_fn: InjectFn | None = None):
    detected_tools: set[str] = set()
    max_index = 0
    pending: list[str] = []
    passthrough = True

    async for line in source:
        line = rewrite_model_line(line, model)
        payload = sse_field(line, "data")
        if payload is not None:
            try:
                obj = orjson.loads(payload)
                if obj.get("type") == "content_block_start":
                    max_index = max(max_index, obj.get("index", 0))
                    block = obj.get("content_block", {})
                    if block.get("type") == "tool_use":
                        detected_tools.add(block.get("name", ""))
                if obj.get("type") == "message_delta":
                    passthrough = False
                    delta = obj.get("delta", {})
                    if (delta.get("stop_reason") == "tool_use"
                            and detected_tools and inject_fn):
                        for injected in await inject_fn(detected_tools, max_index + 1):
                            yield injected + "\n"
            except Exception:
                pass
        if sse_field(line, "event") in ("message_delta", "message_stop"):
            passthrough = False
        if passthrough:
            yield line + "\n"
        else:
            pending.append(line)

    for line in pending:
        yield line + "\n"
    yield "\n"
