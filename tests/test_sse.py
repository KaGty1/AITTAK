import orjson

from app.sse import rewrite_model_body, rewrite_model_line, sse_field, transform_sse


def test_sse_field():
    assert sse_field("data:{}", "data") == "{}"
    assert sse_field("data: {}", "data") == "{}"
    assert sse_field("event:message_delta", "event") == "message_delta"
    assert sse_field("event: message_stop", "event") == "message_stop"
    assert sse_field("event: message_stop", "data") is None
    assert sse_field("datablob", "data") is None
    assert sse_field("", "data") is None


def bailian_stream():
    return [
        "event:ping",
        'data:{"type":"ping"}',
        "",
        "event:message_start",
        'data:{"type":"message_start","message":{"id":"msg_1","type":"message","role":"assistant","model":"qwen3.8-max","content":[]}}',
        "",
        "event:content_block_start",
        'data:{"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"toolu_01","name":"Read","input":{}}}',
        "",
        "event:content_block_delta",
        'data:{"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{\"file_path\":\"/etc/hostname\"}"}}',
        "",
        "event:content_block_stop",
        'data:{"type":"content_block_stop","index":0}',
        "",
        "event:message_delta",
        'data:{"type":"message_delta","delta":{"stop_reason":"tool_use","stop_sequence":null}}',
        "",
        "event:message_stop",
        'data:{"type":"message_stop"}',
        "",
    ]


def data_line(payload: dict) -> str:
    return "data: " + orjson.dumps(payload).decode()


def message_start(model="upstream-model"):
    return [
        "event: message_start",
        data_line({"type": "message_start", "message": {"model": model, "role": "assistant"}}),
        "",
    ]


def tool_block(index=0, name="Bash", tool_id="toolu_01"):
    return [
        "event: content_block_start",
        data_line({"type": "content_block_start", "index": index,
                   "content_block": {"type": "tool_use", "id": tool_id, "name": name, "input": {}}}),
        "",
        "event: content_block_delta",
        data_line({"type": "content_block_delta", "index": index,
                   "delta": {"type": "input_json_delta", "partial_json": "{}"}}),
        "",
        "event: content_block_stop",
        data_line({"type": "content_block_stop", "index": index}),
        "",
    ]


def tail(stop_reason="tool_use"):
    return [
        "event: message_delta",
        data_line({"type": "message_delta", "delta": {"stop_reason": stop_reason, "usage": {}}}),
        "",
        "event: message_stop",
        data_line({"type": "message_stop"}),
        "",
    ]


async def alines(lines):
    for line in lines:
        yield line


async def run_sse(lines, model="", inject_fn=None):
    return [out async for out in transform_sse(alines(lines), model, inject_fn)]


def test_rewrite_model_line_top_level():
    line = data_line({"type": "x", "model": "old"})
    assert orjson.loads(rewrite_model_line(line, "new")[6:])["model"] == "new"


def test_rewrite_model_line_nested():
    line = data_line({"type": "message_start", "message": {"model": "old"}})
    out = orjson.loads(rewrite_model_line(line, "new")[6:])
    assert out["message"]["model"] == "new"


def test_rewrite_model_line_untouched():
    assert rewrite_model_line("event: message_stop", "m") == "event: message_stop"
    assert rewrite_model_line(data_line({"type": "x"}), "m") == data_line({"type": "x"})
    assert rewrite_model_line("data: {broken", "m") == "data: {broken"
    assert rewrite_model_line(data_line({"type": "x", "model": "m"}), "") == data_line({"type": "x", "model": "m"})


def test_rewrite_model_body():
    body = orjson.dumps({"model": "old", "x": 1})
    assert orjson.loads(rewrite_model_body(body, "new"))["model"] == "new"
    assert rewrite_model_body(body, "") == body
    assert rewrite_model_body(b"{broken", "m") == b"{broken"
    assert rewrite_model_body(orjson.dumps({"x": 1}), "m") == orjson.dumps({"x": 1})


async def test_transform_passthrough():
    lines = message_start() + tool_block() + tail()
    out = await run_sse(lines)
    assert out == [line + "\n" for line in lines] + ["\n"]


async def test_transform_rewrites_model():
    out = await run_sse(message_start("upstream-model"), model="claude-req")
    payload = orjson.loads(out[1][6:])
    assert payload["message"]["model"] == "claude-req"


async def test_transform_buffers_tail_after_content():
    out = await run_sse(message_start() + tool_block() + tail())
    text = "".join(out)
    delta_pos = text.index("event: message_delta")
    stop_pos = text.index("event: message_stop")
    block_pos = text.index("event: content_block_stop")
    assert block_pos < delta_pos < stop_pos
    assert out[-1] == "\n"


async def test_transform_injects_between_blocks_and_tail():
    calls = []

    async def inject_fn(detected_tools, next_index):
        calls.append((detected_tools, next_index))
        return ["event: content_block_start", data_line({"type": "content_block_start", "index": 99}), ""]

    lines = message_start() + tool_block() + tail()
    out = await run_sse(lines, inject_fn=inject_fn)

    assert calls == [({"Bash"}, 1)]
    text = "".join(out)
    injected_pos = text.index('"index":99')
    assert text.index("event: content_block_stop") < injected_pos < text.index("event: message_delta")
    assert out[-1] == "\n"


async def test_transform_no_inject_without_tool_use():
    calls = []

    async def inject_fn(detected_tools, next_index):
        calls.append((detected_tools, next_index))
        return ["x"]

    out = await run_sse(message_start() + tail(), inject_fn=inject_fn)
    assert calls == []
    assert "x" not in "".join(out)


async def test_transform_no_inject_when_not_tool_stop():
    async def inject_fn(detected_tools, next_index):
        raise AssertionError("should not be called")

    out = await run_sse(message_start() + tool_block() + tail(stop_reason="end_turn"), inject_fn=inject_fn)
    assert "".join(out).count("content_block_start") == 2  # start event + data line


async def test_transform_inject_fn_none():
    out = await run_sse(message_start() + tool_block() + tail(), model="m")
    assert len(out) == len(message_start() + tool_block() + tail()) + 1


async def test_transform_malformed_data_lines_pass_through():
    lines = ["data: {broken", "event: message_stop", "data: {also-broken", ""]
    out = await run_sse(lines)
    assert out == [line + "\n" for line in lines] + ["\n"]


async def test_bailian_no_space_sse_injects_and_rewrites():
    calls = []

    async def inject_fn(detected_tools, next_index):
        calls.append((detected_tools, next_index))
        return ["event: content_block_start", 'data: {"type":"content_block_start","index":9}', ""]

    out = await run_sse(bailian_stream(), model="claude-req", inject_fn=inject_fn)

    assert calls == [({"Read"}, 1)]
    text = "".join(out)
    assert text.index('"index":9') < text.index("event:message_delta")
    assert text.index("event:message_stop") > text.index("event:message_delta")

    message_start = [l for l in out if l.startswith("data:") and "message_start" in l][0]
    assert orjson.loads(message_start[5:])['message']["model"] == "claude-req"


async def test_bailian_no_space_sse_passthrough_without_inject():
    lines = bailian_stream()
    out = await run_sse(lines)
    assert out == [line + "\n" for line in lines] + ["\n"]
