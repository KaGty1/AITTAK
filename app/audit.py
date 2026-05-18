import asyncio
import time
import orjson
from dataclasses import dataclass, field
from fastapi import Request
from app.database import get_db
from app.config import MAX_BODY_SIZE, LOG_RETENTION_DAYS
from app.sensitive import load_rules, scan_audit_log

_queue: asyncio.Queue | None = None
_stop_event = asyncio.Event()


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


def _extract_user_prompt(data: dict, platform: str) -> str:
    """Extract the user's actual text input, ignoring system prompts and tool results."""
    messages = data.get("messages", [])

    # Walk backwards to find the latest user text message
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # User message with blocks: pick text blocks, skip tool_result blocks
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif block.get("type") in ("tool_result",):
                        continue  # skip tool results, not the user's prompt
            if texts:
                return "\n".join(texts)
    return ""


def _extract_tool_calls(data: dict, platform: str) -> str:
    """Extract tool_use and tool_result from the LATEST round only.

    Only captures the last assistant message's tool_use blocks and the
    corresponding tool_result blocks from the last user message.
    This prevents historical tool calls from accumulating in each audit record.
    """
    items = []
    messages = data.get("messages", [])

    # Find the last assistant message with tool_use blocks
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
            break  # Only take the last assistant message with tools

    if not last_assistant_tools:
        return "[]"

    items.extend(last_assistant_tools)
    tool_ids = {t["tool_use_id"] for t in last_assistant_tools}

    # Find corresponding tool_result in the last user message
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
                    parts = []
                    for rb in result_content:
                        if isinstance(rb, dict) and rb.get("type") == "text":
                            parts.append(rb.get("text", ""))
                    result_content = "\n".join(parts)
                items.append({
                    "type": "tool_result",
                    "tool_use_id": block.get("tool_use_id", ""),
                    "content": str(result_content),
                })
        break  # Only check the last user message

    result = orjson.dumps(items).decode()
    if len(result) > MAX_BODY_SIZE:
        result = result[:MAX_BODY_SIZE] + '..."truncated"]'
    return result


def extract_audit(
    body: bytes,
    request: Request,
    api_key_info: dict,
    platform: str,
    upstream_id: int = 0,
) -> AuditLog:
    try:
        data = orjson.loads(body)
    except Exception:
        data = {}

    return AuditLog(
        request_id=request.headers.get("x-request-id", ""),
        api_key_id=api_key_info.get("id", 0),
        api_key_name=api_key_info.get("name", ""),
        client_ip=request.client.host if request.client else "",
        endpoint=request.url.path,
        model=data.get("model", ""),
        upstream_id=upstream_id,
        user_prompt=_extract_user_prompt(data, platform),
        tool_calls=_extract_tool_calls(data, platform),
    )


async def submit_audit(log: AuditLog):
    if _queue is not None:
        try:
            _queue.put_nowait(log)
        except asyncio.QueueFull:
            pass


async def start_audit_writer():
    global _queue
    _queue = asyncio.Queue(maxsize=4096)

    last_cleanup = time.time()
    cleanup_interval = 3600
    # 去重：记录已写入的 tool_use_id，避免同一工具调用被多轮请求重复记录
    seen_tool_ids: set[str] = set()
    SEEN_MAX_SIZE = 10000  # 防止内存无限增长

    while not _stop_event.is_set():
        batch: list[AuditLog] = []
        try:
            item = await asyncio.wait_for(_queue.get(), timeout=0.2)
            batch.append(item)
            while len(batch) < 32:
                try:
                    batch.append(_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
        except asyncio.TimeoutError:
            pass

        if batch:
            try:
                # Load rules on first use or after refresh
                import app.sensitive as _sens
                if _sens._compiled_cache is None:
                    await load_rules()
                # Scan each log for sensitive info
                for l in batch:
                    l.sensitive_hits = scan_audit_log(l.user_prompt, l.tool_calls)

                # 去重：提取本条日志中的 tool_use_id，跳过已记录的
                deduped_batch = []
                for l in batch:
                    try:
                        tc_items = orjson.loads(l.tool_calls)
                    except Exception:
                        tc_items = []
                    current_ids = {t.get("tool_use_id") for t in tc_items
                                   if isinstance(t, dict) and t.get("type") == "tool_use" and t.get("tool_use_id")}

                    if not current_ids:
                        # 没有工具调用的记录（纯 prompt）直接保留
                        deduped_batch.append(l)
                    elif current_ids - seen_tool_ids:
                        # 有新的 tool_use_id，保留并记录
                        seen_tool_ids.update(current_ids)
                        deduped_batch.append(l)
                    # else: 全部 tool_use_id 都已记录过，跳过

                # 防止 seen 集合无限增长
                if len(seen_tool_ids) > SEEN_MAX_SIZE:
                    # 保留最近一半
                    seen_tool_ids = set(list(seen_tool_ids)[SEEN_MAX_SIZE // 2:])

                if deduped_batch:
                    db = get_db()
                    await db.executemany(
                        """INSERT INTO audit_logs
                           (request_id, api_key_id, api_key_name, client_ip,
                            endpoint, model, upstream_id, user_prompt,
                            tool_calls, sensitive_hits, status_code, duration_ms)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        [
                            (
                                l.request_id, l.api_key_id, l.api_key_name, l.client_ip,
                                l.endpoint, l.model, l.upstream_id, l.user_prompt,
                                l.tool_calls, l.sensitive_hits, l.status_code, l.duration_ms,
                            )
                            for l in deduped_batch
                        ],
                    )
                    await db.commit()
            except Exception:
                pass

        now = time.time()
        if now - last_cleanup > cleanup_interval:
            last_cleanup = now
            try:
                db = get_db()
                await db.execute(
                    "DELETE FROM audit_logs WHERE created_at_ts < unixepoch() - ? * 86400",
                    (LOG_RETENTION_DAYS,),
                )
                await db.commit()
            except Exception:
                pass


async def stop_audit_writer():
    _stop_event.set()
