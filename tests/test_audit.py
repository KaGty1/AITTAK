import orjson

import app.inject as inject
from app.audit import AuditLog, build_inject_logs, extract_tool_calls, extract_user_prompt, is_new_log


def payload():
    return {
        "model": "claude-x",
        "messages": [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "toolu_old", "name": "Grep", "input": {"pattern": "x"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_old", "content": "old result"},
                {"type": "text", "text": "assistant said:"},
            ]},
            {"role": "assistant", "content": [
                {"type": "text", "text": "let me check"},
                {"type": "tool_use", "id": "toolu_new", "name": "Bash",
                 "input": {"command": "ls /etc"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_new",
                 "content": [{"type": "text", "text": "hosts\npasswd"}]},
                {"type": "tool_result", "tool_use_id": "toolu_old", "content": "ignored"},
            ]},
        ],
    }


def test_extract_user_prompt():
    assert extract_user_prompt(payload()) == "assistant said:"
    assert extract_user_prompt({"messages": [{"role": "user", "content": "plain"}]}) == "plain"
    assert extract_user_prompt({}) == ""
    only_results = {"messages": [{"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t", "content": "x"},
    ]}]}
    assert extract_user_prompt(only_results) == ""


def test_extract_tool_calls_latest_round_only():
    items = orjson.loads(extract_tool_calls(payload()))
    assert len(items) == 2
    assert items[0]["type"] == "tool_use"
    assert items[0]["tool_use_id"] == "toolu_new"
    assert orjson.loads(items[0]["input"]) == {"command": "ls /etc"}
    assert items[1] == {
        "type": "tool_result",
        "tool_use_id": "toolu_new",
        "content": "hosts\npasswd",
    }
    assert extract_tool_calls({}) == "[]"


def test_extract_tool_calls_truncates():
    data = {"messages": [
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t", "name": "Bash", "input": {"command": "x" * 200000}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t", "content": "y" * 200000},
        ]},
    ]}
    out = extract_tool_calls(data)
    assert len(out) > 102400
    assert out.endswith('..."truncated"]')


def test_build_inject_logs():
    inject._inject_id_map["inject-x"] = "probe"
    stripped = [{"tool_use_id": "inject-x", "content": "host-a", "tool_name": "Read"}]
    logs = build_inject_logs(stripped, "req-1", "1.2.3.4", "/v1/messages", {"id": 7, "name": "k1"})
    assert len(logs) == 1
    log = logs[0]
    assert log.user_prompt == "[probe] Read"
    assert log.endpoint == "/v1/messages [inject-result]"
    assert log.api_key_name == "k1" and log.request_id == "req-1" and log.client_ip == "1.2.3.4"
    assert log.status_code == 200
    calls = orjson.loads(log.tool_calls)
    assert calls[0]["tool_name"] == "Read"
    assert calls[1]["content"] == "host-a"
    assert inject._inject_id_map == {}


def test_is_new_log_dedup():
    def log(calls_json):
        return AuditLog(tool_calls=calls_json)

    empty = orjson.dumps([]).decode()
    assert is_new_log(log(empty), set())

    first = orjson.dumps([{"type": "tool_use", "tool_use_id": "t1"}]).decode()
    seen: set = set()
    assert is_new_log(log(first), seen)
    assert seen == {"t1"}
    assert not is_new_log(log(first), seen)

    mixed = orjson.dumps([
        {"type": "tool_use", "tool_use_id": "t1"},
        {"type": "tool_use", "tool_use_id": "t2"},
    ]).decode()
    assert is_new_log(log(mixed), seen)
    assert seen == {"t1", "t2"}
    assert is_new_log(log("broken"), set())
