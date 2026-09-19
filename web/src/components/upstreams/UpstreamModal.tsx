import { useState } from "react";
import { toast } from "sonner";

import { api } from "../../lib/api.ts";
import type { Upstream, UpstreamInput } from "../../lib/types.ts";
import { Button } from "../ui/Button.tsx";
import { Field, inputCls, monoInputCls } from "../ui/Field.tsx";
import { Modal } from "../ui/Modal.tsx";

const PLATFORMS = ["claude", "openai"] as const;

export function UpstreamModal({
  existing,
  onClose,
  onSaved,
}: {
  existing?: Upstream | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(existing?.name ?? "");
  const [platform, setPlatform] = useState<string>(existing?.platform ?? "claude");
  const [baseUrl, setBaseUrl] = useState(existing?.base_url ?? "");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!name.trim() || busy) return;
    setBusy(true);
    try {
      if (existing) {
        const body: Partial<UpstreamInput> = {
          name: name.trim(),
          platform,
          base_url: baseUrl.trim(),
        };
        if (apiKey.trim()) body.api_key = apiKey.trim();
        await api.updateUpstream(existing.id, body);
        toast.success("上游已更新");
      } else {
        await api.createUpstream({ name: name.trim(), platform, base_url: baseUrl.trim(), api_key: apiKey.trim() });
        toast.success("上游已添加");
      }
      onSaved();
      onClose();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title={existing ? "编辑上游" : "添加上游"}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>取消</Button>
          <Button variant="primary" onClick={save} disabled={busy}>
            保存
          </Button>
        </>
      }
    >
      <Field label="名称">
        <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder="例如：Claude 官方" />
      </Field>
      <Field label="平台">
        <select value={platform} onChange={(e) => setPlatform(e.target.value)} className={inputCls}>
          {PLATFORMS.map((p) => (
            <option key={p} value={p}>
              {p === "claude" ? "Claude（/v1/messages）" : "OpenAI 兼容（/v1/chat/completions）"}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Base URL">
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          className={monoInputCls}
          placeholder="https://api.anthropic.com"
        />
      </Field>
      <Field label={existing ? "API Key（留空不修改）" : "API Key"}>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className={monoInputCls}
          placeholder="sk-…"
        />
      </Field>
    </Modal>
  );
}
