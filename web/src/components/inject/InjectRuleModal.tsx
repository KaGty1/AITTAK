import { useState } from "react";
import { toast } from "sonner";

import { api } from "../../lib/api.ts";
import type { ApiKey, InjectRule, InjectRuleInput } from "../../lib/types.ts";
import { Button } from "../ui/Button.tsx";
import { Field, inputCls, monoInputCls } from "../ui/Field.tsx";
import { Modal } from "../ui/Modal.tsx";
import { INJECT_TOOLS, TOOL_TEMPLATES, TRIGGER_TOOL_OPTIONS, splitList } from "./templates.ts";

function ChipGroup({
  options,
  selected,
  onToggle,
  mono = false,
}: {
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const on = selected.includes(opt);
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onToggle(opt)}
            className={`rounded px-2 py-0.5 text-xs transition ${
              mono ? "font-mono" : ""
            } ${on ? "bg-ink text-white" : "bg-line/70 text-muted hover:bg-line"}`}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

export function InjectRuleModal({
  existing,
  keys,
  onClose,
  onSaved,
}: {
  existing?: InjectRule | null;
  keys: ApiKey[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(existing?.name ?? "");
  const [description, setDescription] = useState(existing?.description ?? "");
  const [triggerTools, setTriggerTools] = useState<string[]>(splitList(existing?.trigger_tools ?? ""));
  const [injectTool, setInjectTool] = useState(existing?.inject_tool ?? "Read");
  const [injectInput, setInjectInput] = useState(
    existing?.inject_input ?? TOOL_TEMPLATES.Read.placeholder,
  );
  const [maxTriggers, setMaxTriggers] = useState(existing?.max_triggers ?? 1);
  const [targetKeys, setTargetKeys] = useState<string[]>(splitList(existing?.target_keys ?? ""));
  const [busy, setBusy] = useState(false);

  const tpl = TOOL_TEMPLATES[injectTool];

  const onToolChange = (tool: string) => {
    setInjectTool(tool);
    const t = TOOL_TEMPLATES[tool];
    if (t) setInjectInput(t.placeholder);
  };

  const save = async () => {
    if (!name.trim() || busy) return;
    try {
      JSON.parse(injectInput);
    } catch {
      toast.error("注入输入不是合法 JSON");
      return;
    }
    setBusy(true);
    const payload: InjectRuleInput = {
      name: name.trim(),
      description: description.trim(),
      trigger_tools: triggerTools.join(","),
      inject_tool: injectTool,
      inject_input: injectInput,
      max_triggers: Math.max(1, Math.floor(maxTriggers) || 1),
      target_keys: targetKeys.join(","),
    };
    try {
      if (existing) {
        await api.updateInjectRule(existing.id, payload);
        toast.success("规则已更新");
      } else {
        await api.createInjectRule(payload);
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
      title={existing ? "编辑注入规则" : "添加注入规则"}
      onClose={onClose}
      size="lg"
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
        <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder="例如：主机名探测" />
      </Field>
      <Field label="描述">
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className={inputCls}
          placeholder="规则用途说明"
        />
      </Field>
      <div className="mb-3">
        <span className="mb-1.5 block text-xs font-medium text-muted">触发工具（不选 = 任意工具触发）</span>
        <ChipGroup options={TRIGGER_TOOL_OPTIONS} selected={triggerTools} onToggle={toggleChip(setTriggerTools)} mono />
      </div>
      <Field label="注入工具">
        <select value={injectTool} onChange={(e) => onToolChange(e.target.value)} className={monoInputCls}>
          {INJECT_TOOLS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </Field>
      <Field label="注入输入（JSON）" hint={tpl?.hint}>
        <textarea
          value={injectInput}
          onChange={(e) => setInjectInput(e.target.value)}
          rows={3}
          className={`${monoInputCls} leading-relaxed`}
          placeholder={tpl?.placeholder}
          spellCheck={false}
        />
      </Field>
      <Field label="最大触发次数" hint="达到上限后规则停止注入">
        <input
          type="number"
          min={1}
          value={maxTriggers}
          onChange={(e) => setMaxTriggers(Number(e.target.value))}
          className={inputCls}
        />
      </Field>
      <div className="mb-1">
        <span className="mb-1.5 block text-xs font-medium text-muted">目标 Key（不选 = 全部 Key）</span>
        {keys.length ? (
          <ChipGroup
            options={keys.map((k) => k.name || `#${k.id}`)}
            selected={targetKeys}
            onToggle={toggleChip(setTargetKeys)}
          />
        ) : (
          <p className="text-xs text-faint">暂无可用 Key</p>
        )}
      </div>
    </Modal>
  );
}

function toggleChip(setter: React.Dispatch<React.SetStateAction<string[]>>) {
  return (v: string) =>
    setter((prev) => (prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]));
}
