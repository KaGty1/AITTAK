import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api.ts";
import { Button } from "../ui/Button.tsx";
import { Field, inputCls } from "../ui/Field.tsx";
import { Modal } from "../ui/Modal.tsx";

export function CreateKeyModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState("");
  const [createdKey, setCreatedKey] = useState("");
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const r = await api.createKey(name.trim());
      setCreatedKey(r.key);
      onSaved();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(createdKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (createdKey) {
    return (
      <Modal
        title="Key 已创建"
        onClose={onClose}
        footer={<Button variant="primary" onClick={onClose}>完成</Button>}
      >
        <p className="mb-2 text-xs text-faint">完整 Key 仅显示这一次，请立即保存：</p>
        <div className="flex items-center gap-2 rounded-lg border border-ok/30 bg-ok/5 p-3">
          <code className="flex-1 break-all font-mono text-xs text-ok">{createdKey}</code>
          <Button size="sm" onClick={copy} aria-label="复制">
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </Button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      title="创建 API Key"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>取消</Button>
          <Button variant="primary" onClick={create} disabled={busy}>
            创建
          </Button>
        </>
      }
    >
      <Field label="名称" hint="名称用于审计日志归属与注入规则定向">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputCls}
          placeholder="例如：blue-team-01"
        />
      </Field>
    </Modal>
  );
}
