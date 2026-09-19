import asyncio
import time
from dataclasses import dataclass, field

import orjson

from app.config import LOG_RETENTION_DAYS, MAX_BODY_SIZE
from app.database import get_db
from app.inject import pop_rule_name
from app.sensitive import ensure_rules_loaded, scan_audit_log

_queue: asyncio.Queue | None = None
_stop_event = asyncio.Event()

_QUEUE_MAX = 4096
_BATCH_MAX = 32
_DRAIN_TIMEOUT = 0.2
_DEDUP_MAX = 10000
_CLEANUP_INTERVAL = 3600


@dataclass
class AuditLog:
    request_id: str = ""
    api_key_id: int = 0
    api_key_name: str = ""
    client_ip: str = ""
    endpoint: str = ""
    model: str = ""
    upstream_id: int = 0
    user_prompt: str = ""
    tool_calls: str = "[]"
    sensitive_hits: str = "[]"
    status_code: int = 0
    duration_ms: int = 0
    _start_time: float = field(default_factory=time.time, repr=False)

    def finish(self, status_code: int):
        self.status_code = status_code
        self.duration_ms = int((time.time() - self._start_time) * 1000)


def extract_user_prompt(data: dict) -> str:
    messages = data.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            if texts:
                return "\n".join(texts)
    return ""


def extract_tool_calls(data: dict) -> str:
    messages = data.get("messages", [])

    last_assistant_tools = []
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                raw_input = block.get("input", {})
                last_assistant_tools.append({
                    "type": "tool_use",
                    "tool_name": block.get("name", ""),
                    "tool_use_id": block.get("id", ""),
                    "input": orjson.dumps(raw_input).decode() if isinstance(raw_input, dict) else str(raw_input),
                })
        if last_assistant_tools:
            break

    if not last_assistant_tools:
        return "[]"

    items = list(last_assistant_tools)
    tool_ids = {t["tool_use_id"] for t in last_assistant_tools}

    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            if block.get("tool_use_id", "") in tool_ids:
                result_content = block.get("content", "")
                if isinstance(result_content, list):
                    parts = [
                        rb.get("text", "")
                        for rb in result_content
                        if isinstance(rb, dict) and rb.get("type") == "text"
                    ]
                    result_content = "\n".join(parts)
                items.append({
                    "type": "tool_result",
                    "tool_use_id": block.get("tool_use_id", ""),
                    "content": str(result_content),
                })
        break

    result = orjson.dumps(items).decode()
    if len(result) > MAX_BODY_SIZE:
        result = result[:MAX_BODY_SIZE] + '..."truncated"]'
    return result


def extract_audit(
    body: bytes,
    req_id: str,
    client_ip: str,
    endpoint: str,
    api_key_info: dict,
    upstream_id: int = 0,
) -> AuditLog:
    try:
        data = orjson.loads(body)
    except Exception:
        data = {}
    return AuditLog(
        request_id=req_id,
        api_key_id=api_key_info.get("id", 0),
        api_key_name=api_key_info.get("name", ""),
        client_ip=client_ip,
        endpoint=endpoint,
        model=data.get("model", ""),
        upstream_id=upstream_id,
        user_prompt=extract_user_prompt(data),
        tool_calls=extract_tool_calls(data),
    )


def build_inject_logs(
    stripped: list[dict],
    req_id: str,
    client_ip: str,
    endpoint: str,
    api_key_info: dict,
) -> list[AuditLog]:
    logs = []
    for s in stripped:
        rule_name = pop_rule_name(s["tool_use_id"])
        tool_name = s.get("tool_name", "inject")
        tool_calls = orjson.dumps([
            {
                "type": "tool_use",
                "tool_name": tool_name,
                "tool_use_id": s["tool_use_id"],
                "input": s.get("input", ""),
            },
            {
                "type": "tool_result",
                "tool_use_id": s["tool_use_id"],
                "content": s["content"],
            },
        ]).decode()
        prompt = f"[{rule_name}] {tool_name}" if rule_name else f"[工具注入] {tool_name}"
        log = AuditLog(
            request_id=req_id,
            api_key_id=api_key_info.get("id", 0),
            api_key_name=api_key_info.get("name", ""),
            client_ip=client_ip,
            endpoint=endpoint + " [inject-result]",
            user_prompt=prompt,
            tool_calls=tool_calls,
        )
        log.finish(200)
        logs.append(log)
    return logs


async def submit_audit(log: AuditLog):
    if _queue is not None:
        try:
            _queue.put_nowait(log)
        except asyncio.QueueFull:
            pass


def row_values(log: AuditLog) -> tuple:
    return (
        log.request_id, log.api_key_id, log.api_key_name, log.client_ip,
        log.endpoint, log.model, log.upstream_id, log.user_prompt,
        log.tool_calls, log.sensitive_hits, log.status_code, log.duration_ms,
    )


def is_new_log(log: AuditLog, seen: set[str]) -> bool:
    try:
        items = orjson.loads(log.tool_calls)
    except Exception:
        items = []
    ids = {
        t.get("tool_use_id")
        for t in items
        if isinstance(t, dict) and t.get("type") == "tool_use" and t.get("tool_use_id")
    }
    if not ids:
        return True
    if ids - seen:
        seen.update(ids)
        if len(seen) > _DEDUP_MAX:
            for tid in list(seen)[: _DEDUP_MAX // 2]:
                seen.discard(tid)
        return True
    return False


async def _drain_batch() -> list[AuditLog]:
    batch: list[AuditLog] = []
    assert _queue is not None
    try:
        item = await asyncio.wait_for(_queue.get(), timeout=_DRAIN_TIMEOUT)
        batch.append(item)
        while len(batch) < _BATCH_MAX:
            try:
                batch.append(_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
    except asyncio.TimeoutError:
        pass
    return batch


async def _write_batch(batch: list[AuditLog], seen: set[str]):
    try:
        await ensure_rules_loaded()
        for log in batch:
            log.sensitive_hits = scan_audit_log(log.user_prompt, log.tool_calls)
        rows = [row_values(log) for log in batch if is_new_log(log, seen)]
        if rows:
            db = get_db()
            await db.executemany(
                """INSERT INTO audit_logs
                   (request_id, api_key_id, api_key_name, client_ip,
                    endpoint, model, upstream_id, user_prompt,
                    tool_calls, sensitive_hits, status_code, duration_ms)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            await db.commit()
    except Exception:
        pass


async def _cleanup_expired():
    try:
        db = get_db()
        await db.execute(
            "DELETE FROM audit_logs WHERE created_at_ts < unixepoch() - ? * 86400",
            (LOG_RETENTION_DAYS,),
        )
        await db.commit()
    except Exception:
        pass


async def start_audit_writer():
    global _queue
    _queue = asyncio.Queue(maxsize=_QUEUE_MAX)
    seen: set[str] = set()
    last_cleanup = time.time()

    while not _stop_event.is_set():
        batch = await _drain_batch()
        if batch:
            await _write_batch(batch, seen)
        now = time.time()
        if now - last_cleanup > _CLEANUP_INTERVAL:
            last_cleanup = now
            await _cleanup_expired()


async def stop_audit_writer():
    _stop_event.set()
