import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { SensitiveRuleModal } from "../components/settings/SensitiveRuleModal.tsx";
import { Button } from "../components/ui/Button.tsx";
import { ConfirmDialog } from "../components/ui/ConfirmDialog.tsx";
import { DataTable, type Column } from "../components/ui/DataTable.tsx";
import { PageHead } from "../components/ui/PageHead.tsx";
import { RowActions } from "../components/ui/RowActions.tsx";
import { StatusDot } from "../components/ui/StatusDot.tsx";
import { Tag } from "../components/ui/Tag.tsx";
import { api } from "../lib/api.ts";
import { usePoll } from "../lib/hooks.ts";
import type { SensitiveRule } from "../lib/types.ts";

export function SettingsPage() {
  const { data, refresh } = usePoll(api.listSensitiveRules, 15000);
  const [editing, setEditing] = useState<SensitiveRule | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<SensitiveRule | null>(null);

  const rows = data ?? [];

  const toggle = async (r: SensitiveRule) => {
    try {
      await api.updateSensitiveRule(r.id, { is_active: !r.is_active });
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const remove = async (r: SensitiveRule) => {
    try {
      await api.deleteSensitiveRule(r.id);
      toast.success("规则已删除");
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const columns: Column<SensitiveRule>[] = [
    { key: "name", head: "名称", cell: (r) => r.name },
    {
      key: "category",
      head: "分类",
      cell: (r) => (r.category ? <Tag>{r.category}</Tag> : <span className="text-xs text-faint">—</span>),
    },
    {
      key: "pattern",
      head: "正则表达式",
      className: "max-w-[220px]",
      cell: (r) => (
        <span className="block truncate font-mono text-xs text-muted" title={r.pattern}>
          {r.pattern}
        </span>
      ),
    },
    {
      key: "description",
      head: "描述",
      cell: (r) => <span className="text-xs text-muted">{r.description || "—"}</span>,
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
            { label: "删除", onClick: () => setDeleting(r), danger: true },
          ]}
        />
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="敏感规则"
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus size={15} /> 添加规则
          </Button>
        }
      />
      <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} empty="暂无敏感规则" />

      {creating && <SensitiveRuleModal onClose={() => setCreating(false)} onSaved={refresh} />}
      {editing && <SensitiveRuleModal existing={editing} onClose={() => setEditing(null)} onSaved={refresh} />}
      {deleting && (
        <ConfirmDialog
          title="删除规则"
          message={`确认删除敏感规则「${deleting.name}」？历史命中记录将保留。`}
          confirmLabel="删除"
          danger
          onClose={() => setDeleting(null)}
          onConfirm={() => remove(deleting)}
        />
      )}
    </div>
  );
}
