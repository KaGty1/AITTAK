import { useEffect, useState } from "react";

import { api } from "../../lib/api.ts";
import type { AuditLogDetail } from "../../lib/types.ts";
import { fmtJson } from "../../lib/utils.ts";
import { Modal } from "../ui/Modal.tsx";
import { StatusCode } from "../ui/StatusDot.tsx";
import { Tag } from "../ui/Tag.tsx";

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="w-20 shrink-0 text-faint">{label}</span>
      <span className={`min-w-0 break-all text-ink ${mono ? "font-mono text-xs" : ""}`}>{value || "—"}</span>
    </div>
  );
}

function Pre({ text, mono = true }: { text: string; mono?: boolean }) {
  return (
    <pre
      className={`max-h-72 overflow-y-auto whitespace-pre-wrap break-all rounded-lg border border-line bg-paper/60 p-3 text-xs leading-relaxed text-muted ${
        mono ? "font-mono" : ""
      }`}
    >
      {text}
    </pre>
  );
}

export function LogDetailModal({ id, onClose }: { id: number; onClose: () => void }) {
  const [detail, setDetail] = useState<AuditLogDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    api
      .getLog(id)
      .then((d) => alive && setDetail(d))
      .catch((e) => alive && setError((e as Error).message));
    return () => {
      alive = false;
    };
  }, [id]);

  return (
    <Modal title="请求详情" onClose={onClose} size="xl">
      {error ? (
        <p className="text-sm text-danger">{error}</p>
      ) : !detail ? (
        <p className="text-sm text-faint">加载中…</p>
      ) : (
        <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-lg border border-line bg-paper/40 p-4">
            <Meta label="时间" value={detail.created_at} />
            <Meta label="名称" value={detail.api_key_name} />
            <Meta label="客户端 IP" value={detail.client_ip} mono />
            <Meta label="端点" value={detail.endpoint} mono />
            <Meta label="模型" value={detail.model} mono />
            <div className="flex gap-2 text-sm">
              <span className="w-20 shrink-0 text-faint">状态码</span>
              <StatusCode code={detail.status_code} />
              <span className="text-xs text-faint">{detail.duration_ms}ms</span>
            </div>
            <Meta label="请求 ID" value={detail.request_id} mono />
          </div>

          {detail.sensitive_hits?.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted">敏感信息命中</p>
              <div className="flex flex-wrap gap-1">
                {detail.sensitive_hits.map((h) => (
                  <Tag key={h.rule_name} tone="danger">
                    {h.rule_name} ×{h.count}
                  </Tag>
                ))}
              </div>
            </div>
          )}

          {detail.user_prompt && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted">用户 Prompt</p>
              <Pre text={detail.user_prompt} mono={false} />
            </div>
          )}

          {detail.tool_calls?.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted">工具调用</p>
              <div className="space-y-3">
                {detail.tool_calls.map((c) => (
                  <div key={c.tool_use_id} className="rounded-lg border border-line p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <Tag tone="mono">{c.tool_name}</Tag>
                      <span className="font-mono text-[11px] text-faint">{c.tool_use_id}</span>
                    </div>
                    {c.input && (
                      <div className="mb-2">
                        <p className="mb-1 text-[11px] text-faint">输入</p>
                        <Pre text={fmtJson(c.input)} />
                      </div>
                    )}
                    {c.result && (
                      <div>
                        <p className="mb-1 text-[11px] text-faint">结果</p>
                        <Pre text={c.result} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {!detail.user_prompt && !detail.tool_calls?.length && (
            <p className="text-sm text-faint">无 Prompt 与工具调用内容</p>
          )}
        </div>
      )}
    </Modal>
  );
}
