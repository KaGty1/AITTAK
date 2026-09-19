import { useState } from "react";
import { toast } from "sonner";

import { api } from "../../lib/api.ts";
import type { SensitiveRule, SensitiveRuleInput } from "../../lib/types.ts";
import { Button } from "../ui/Button.tsx";
import { Field, inputCls, monoInputCls } from "../ui/Field.tsx";
import { Modal } from "../ui/Modal.tsx";

export function SensitiveRuleModal({
  existing,
  onClose,
  onSaved,
}: {
  existing?: SensitiveRule | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(existing?.name ?? "");
  const [category, setCategory] = useState(existing?.category ?? "");
  const [pattern, setPattern] = useState(existing?.pattern ?? "");
  const [description, setDescription] = useState(existing?.description ?? "");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!name.trim() || !pattern.trim() || busy) return;
    try {
      new RegExp(pattern);
    } catch (e) {
      toast.error(`正则无效：${(e as Error).message}`);
      return;
    }
    setBusy(true);
    const payload: SensitiveRuleInput = {
      name: name.trim(),
      category: category.trim(),
      pattern,
      description: description.trim(),
    };
    try {
      if (existing) {
        await api.updateSensitiveRule(existing.id, payload);
        toast.success("规则已更新");
      } else {
        await api.createSensitiveRule(payload);
        toast.success("规则已创建");
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
      title={existing ? "编辑规则" : "添加规则"}
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
      <Field label="规则名称">
        <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder="例如：手机号" />
      </Field>
      <Field label="分类">
        <input value={category} onChange={(e) => setCategory(e.target.value)} className={inputCls} placeholder="例如：个人信息" />
      </Field>
      <Field label="正则表达式">
        <input
          value={pattern}
          onChange={(e) => setPattern(e.target.value)}
          className={monoInputCls}
          placeholder="1[3-9]\d{9}"
          spellCheck={false}
        />
      </Field>
      <Field label="描述（可选）">
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className={inputCls}
          placeholder="规则用途说明"
        />
      </Field>
    </Modal>
  );
}
