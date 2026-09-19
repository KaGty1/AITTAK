import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { CreateKeyModal } from "../components/keys/CreateKeyModal.tsx";
import { Button } from "../components/ui/Button.tsx";
import { ConfirmDialog } from "../components/ui/ConfirmDialog.tsx";
import { DataTable, type Column } from "../components/ui/DataTable.tsx";
import { PageHead } from "../components/ui/PageHead.tsx";
import { RowActions } from "../components/ui/RowActions.tsx";
import { StatusDot } from "../components/ui/StatusDot.tsx";
import { api } from "../lib/api.ts";
import { usePoll } from "../lib/hooks.ts";
import type { ApiKey } from "../lib/types.ts";

export function KeysPage() {
  const { data, refresh } = usePoll(api.listKeys, 10000);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<ApiKey | null>(null);

  const rows = data ?? [];

  const toggle = async (k: ApiKey) => {
    try {
      await api.updateKey(k.id, { is_active: !k.is_active });
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const remove = async (k: ApiKey) => {
    try {
      await api.deleteKey(k.id);
      toast.success("Key 已删除");
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const columns: Column<ApiKey>[] = [
    { key: "name", head: "名称", cell: (k) => k.name || "（未命名）" },
    {
      key: "key",
      head: "Key",
      cell: (k) => <span className="font-mono text-xs text-muted">{k.key}</span>,
    },
    {
      key: "created_at",
      head: "创建时间",
      cell: (k) => <span className="text-xs text-faint">{k.created_at}</span>,
    },
    { key: "is_active", head: "状态", cell: (k) => <StatusDot on={k.is_active} /> },
    {
      key: "actions",
      head: "操作",
      cell: (k) => (
        <RowActions
          items={[
            { label: k.is_active ? "禁用" : "启用", onClick: () => toggle(k) },
            { label: "删除", onClick: () => setDeleting(k), danger: true },
          ]}
        />
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="API Key"
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus size={15} /> 创建 Key
          </Button>
        }
      />
      <DataTable columns={columns} rows={rows} rowKey={(k) => k.id} empty="暂无 API Key" />

      {creating && <CreateKeyModal onClose={() => setCreating(false)} onSaved={refresh} />}
      {deleting && (
        <ConfirmDialog
          title="删除 Key"
          message={`确认删除 Key「${deleting.name || "未命名"}」？使用该 Key 的客户端将立即无法访问。`}
          confirmLabel="删除"
          danger
          onClose={() => setDeleting(null)}
          onConfirm={() => remove(deleting)}
        />
      )}
    </div>
  );
}
