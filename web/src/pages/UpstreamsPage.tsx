import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { UpstreamModal } from "../components/upstreams/UpstreamModal.tsx";
import { Button } from "../components/ui/Button.tsx";
import { ConfirmDialog } from "../components/ui/ConfirmDialog.tsx";
import { DataTable, type Column } from "../components/ui/DataTable.tsx";
import { PageHead } from "../components/ui/PageHead.tsx";
import { RowActions } from "../components/ui/RowActions.tsx";
import { StatusDot } from "../components/ui/StatusDot.tsx";
import { Tag } from "../components/ui/Tag.tsx";
import { api } from "../lib/api.ts";
import { usePoll } from "../lib/hooks.ts";
import type { Upstream } from "../lib/types.ts";

export function UpstreamsPage() {
  const { data, refresh } = usePoll(api.listUpstreams, 10000);
  const [editing, setEditing] = useState<Upstream | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<Upstream | null>(null);

  const rows = data ?? [];

  const toggle = async (u: Upstream) => {
    try {
      await api.updateUpstream(u.id, { is_active: !u.is_active });
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const remove = async (u: Upstream) => {
    try {
      await api.deleteUpstream(u.id);
      toast.success("上游已删除");
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const columns: Column<Upstream>[] = [
    { key: "name", head: "名称", cell: (u) => u.name },
    { key: "platform", head: "平台", cell: (u) => <Tag tone="mono">{u.platform}</Tag> },
    {
      key: "base_url",
      head: "Base URL",
      cell: (u) => (
        <span className="font-mono text-xs text-muted" title={u.base_url}>
          {u.base_url || "—"}
        </span>
      ),
    },
    { key: "is_active", head: "状态", cell: (u) => <StatusDot on={u.is_active} /> },
    {
      key: "actions",
      head: "操作",
      cell: (u) => (
        <RowActions
          items={[
            { label: "编辑", onClick: () => setEditing(u) },
            { label: u.is_active ? "禁用" : "启用", onClick: () => toggle(u) },
            { label: "删除", onClick: () => setDeleting(u), danger: true },
          ]}
        />
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="上游配置"
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus size={15} /> 添加上游
          </Button>
        }
      />
      <DataTable columns={columns} rows={rows} rowKey={(u) => u.id} empty="暂无上游配置" />

      {creating && <UpstreamModal onClose={() => setCreating(false)} onSaved={refresh} />}
      {editing && <UpstreamModal existing={editing} onClose={() => setEditing(null)} onSaved={refresh} />}
      {deleting && (
        <ConfirmDialog
          title="删除上游"
          message={`确认删除上游「${deleting.name}」？相关请求将无法转发。`}
          confirmLabel="删除"
          danger
          onClose={() => setDeleting(null)}
          onConfirm={() => remove(deleting)}
        />
      )}
    </div>
  );
}
