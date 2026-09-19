import re

import orjson

import app.sensitive as sensitive
from app.sensitive import scan_audit_log, scan_compiled, scan_text


def compiled():
    return [
        ({"id": 1, "name": "phone"}, re.compile(r"(?<!\w)1[3-9]\d{9}(?!\w)")),
        ({"id": 2, "name": "jwt"}, re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9._\-]{10,}")),
    ]


def test_scan_compiled():
    hits = scan_compiled("call 13812345678 or 13987654321", compiled())
    assert hits == [{"rule_id": 1, "rule_name": "phone", "count": 2}]
    assert scan_compiled("clean text", compiled()) == []
    assert scan_compiled("", compiled()) == []


def test_scan_text_uses_cache():
    sensitive._compiled_cache = compiled()
    assert scan_text("token eyJabcdefghijk.abcdefghijkl") == [
        {"rule_id": 2, "rule_name": "jwt", "count": 1},
    ]
    sensitive._compiled_cache = None
    assert scan_text("13812345678") == []


def test_scan_audit_log_aggregates():
    sensitive._compiled_cache = compiled()
    tool_calls = orjson.dumps([
        {"type": "tool_use", "tool_name": "Bash", "tool_use_id": "t1",
         "input": "echo 13812345678"},
        {"type": "tool_result", "tool_use_id": "t1",
         "content": "13812345678 13712345678"},
    ]).decode()
    hits = orjson.loads(scan_audit_log("contact 13612345678", tool_calls))
    assert hits == [{"rule_id": 1, "rule_name": "phone", "count": 4}]
    assert orjson.loads(scan_audit_log("", "[]")) == []
    assert orjson.loads(scan_audit_log("ok", "not-json")) == []
