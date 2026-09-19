import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { InjectRuleModal } from "../components/inject/InjectRuleModal.tsx";
import { splitList } from "../components/inject/templates.ts";
import { Button } from "../components/ui/Button.tsx";
import { ConfirmDialog } from "../components/ui/ConfirmDialog.tsx";
import { DataTable, type Column } from "../components/ui/DataTable.tsx";
import { PageHead } from "../components/ui/PageHead.tsx";
import { RowActions } from "../components/ui/RowActions.tsx";
import { StatusDot } from "../components/ui/StatusDot.tsx";
import { Tag } from "../components/ui/Tag.tsx";
import { api } from "../lib/api.ts";
import { usePoll } from "../lib/hooks.ts";
import type { InjectRule } from "../lib/types.ts";

export function InjectPage() {
  const { data, refresh } = usePoll(api.listInjectRules, 5000);
  const { data: keys } = usePoll(api.listKeys, 30000);
  const [editing, setEditing] = useState<InjectRule | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<InjectRule | null>(null);

  const rows = data ?? [];

  const toggle = async (r: InjectRule) => {
    try {
      await api.updateInjectRule(r.id, { is_active: !r.is_active });
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const reset = async (r: InjectRule) => {
    try {
      await api.resetInjectRule(r.id);
      toast.success("计数已重置");
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const remove = async (r: InjectRule) => {
    try {
      await api.deleteInjectRule(r.id);
      toast.success("规则已删除");
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const columns: Column<InjectRule>[] = [
    { key: "name", head: "名称", cell: (r) => r.name },
    {
      key: "trigger_tools",
      head: "触发工具",
      cell: (r) => {
        const tools = splitList(r.trigger_tools);
        return tools.length ? (
          <span className="flex flex-wrap gap-1">
            {tools.map((t) => (
              <Tag key={t} tone="mono">
                {t}
              </Tag>
            ))}
          </span>
        ) : (
          <span className="text-xs text-faint">任意</span>
        );
      },
    },
    {
      key: "inject_tool",
      head: "注入工具",
      cell: (r) => <span className="font-mono text-xs text-muted">{r.inject_tool}</span>,
    },
    {
      key: "triggers",
      head: "触发次数",
      cell: (r) => (
        <span className={`text-xs ${r.trigger_count >= r.max_triggers ? "text-faint" : "text-muted"}`}>
          {r.trigger_count} / {r.max_triggers}
        </span>
      ),
    },
    {
      key: "target_keys",
      head: "目标 Key",
      cell: (r) => {
        const ks = splitList(r.target_keys);
        return ks.length ? (
          <span className="flex flex-wrap gap-1">
            {ks.map((k) => (
              <Tag key={k}>{k}</Tag>
            ))}
          </span>
        ) : (
          <span className="text-xs text-faint">全部</span>
        );
      },
    },
    { key: "is_active", head: "状态", cell: (r) => <StatusDot on={r.is_active} /> },
    {
      key: "actions",
      head: "操作",
      cell: (r) => (
        <RowActions
          items={[
            { label: "编辑", onClick: () => setEditing(r) },
            { label: r.is_active ? "禁用" : "启用", onClick: () => toggle(r) },
            { label: "重置计数", onClick: () => reset(r) },
            { label: "删除", onClick: () => setDeleting(r), danger: true },
          ]}
        />
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="工具注入"
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus size={15} /> 添加规则
          </Button>
        }
      />
      <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} empty="暂无注入规则" />

      {creating && <InjectRuleModal keys={keys ?? []} onClose={() => setCreating(false)} onSaved={refresh} />}
      {editing && (
        <InjectRuleModal existing={editing} keys={keys ?? []} onClose={() => setEditing(null)} onSaved={refresh} />
      )}
      {deleting && (
        <ConfirmDialog
          title="删除注入规则"
          message={`确认删除规则「${deleting.name}」？`}
          confirmLabel="删除"
          danger
          onClose={() => setDeleting(null)}
          onConfirm={() => remove(deleting)}
        />
      )}
    </div>
  );
}
