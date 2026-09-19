import { useState } from "react";
import { Radio, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { LogDetailModal } from "../components/monitor/LogDetailModal.tsx";
import { Button } from "../components/ui/Button.tsx";
import { ConfirmDialog } from "../components/ui/ConfirmDialog.tsx";
import { DataTable, type Column } from "../components/ui/DataTable.tsx";
import { PageHead } from "../components/ui/PageHead.tsx";
import { StatusCode } from "../components/ui/StatusDot.tsx";
import { Tag } from "../components/ui/Tag.tsx";
import { cn } from "../lib/utils.ts";
import { api } from "../lib/api.ts";
import { usePoll } from "../lib/hooks.ts";
import type { AuditLogItem } from "../lib/types.ts";

const PAGE_SIZE = 50;

interface Filters {
  keyword: string;
  api_key_name: string;
  sensitive_type: string;
}

const EMPTY_FILTERS: Filters = { keyword: "", api_key_name: "", sensitive_type: "" };

export function MonitorPage() {
  const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS);
  const [draft, setDraft] = useState<Filters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [live, setLive] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [detailId, setDetailId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const pollKey = JSON.stringify([applied, page]);
  const { data, refresh } = usePoll(
    () => api.listLogs({ ...applied, page, page_size: PAGE_SIZE }),
    3000,
    { key: pollKey, enabled: live },
  );
  const { data: keys } = usePoll(api.listKeys, 30000);
  const { data: sensitiveRules } = usePoll(api.listSensitiveRules, 60000);

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const applyFilters = (next: Partial<Filters>) => {
    const merged = { ...draft, ...next };
    setDraft(merged);
    setApplied(merged);
    setPage(1);
    setSelected(new Set());
  };

  const goPage = (p: number) => {
    setPage(Math.min(Math.max(1, p), totalPages));
    setSelected(new Set());
  };

  const toggleRow = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = (select: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      rows.forEach((r) => (select ? next.add(r.id) : next.delete(r.id)));
      return next;
    });
  };

  const batchDelete = async () => {
    const ids = [...selected];
    try {
      await api.deleteLogs(ids);
      toast.success(`已删除 ${ids.length} 条日志`);
      setSelected(new Set());
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const clearAll = async () => {
    try {
      await api.clearLogs();
      toast.success("日志已清空");
      setSelected(new Set());
      refresh();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const columns: Column<AuditLogItem>[] = [
    {
      key: "created_at",
      head: "时间",
      cell: (l) => <span className="whitespace-nowrap text-xs text-faint">{l.created_at}</span>,
    },
    {
      key: "api_key_name",
      head: "名称",
      cell: (l) => <span className="text-sm">{l.api_key_name || "—"}</span>,
    },
    {
      key: "client_ip",
      head: "IP",
      cell: (l) => <span className="font-mono text-xs text-muted">{l.client_ip}</span>,
    },
    {
      key: "user_prompt",
      head: "用户 Prompt",
      className: "max-w-[220px]",
      cell: (l) => (
        <span className="block truncate text-sm" title={l.user_prompt}>
          {l.user_prompt || "—"}
        </span>
      ),
    },
    {
      key: "tools",
      head: "工具调用",
      cell: (l) =>
        l.tool_summary ? (
          <span className="font-mono text-xs text-muted">{l.tool_summary}</span>
        ) : (
          <span className="text-xs text-faint">—</span>
        ),
    },
    {
      key: "sensitive",
      head: "敏感信息",
      cell: (l) =>
        l.sensitive_hits?.length ? (
          <span className="flex flex-wrap gap-1">
            {l.sensitive_hits.map((h) => (
              <Tag key={h.rule_name} tone="danger">
                {h.rule_name}
              </Tag>
            ))}
          </span>
        ) : (
          <span className="text-xs text-faint">—</span>
        ),
    },
    { key: "status", head: "状态", cell: (l) => <StatusCode code={l.status_code} /> },
    {
      key: "duration",
      head: "耗时",
      cell: (l) => <span className="text-xs text-faint">{l.duration_ms}ms</span>,
    },
  ];

  return (
    <div>
      <PageHead
        title="行为监控"
        actions={
          <>
            <Button variant={live ? "secondary" : "ghost"} onClick={() => setLive((v) => !v)}>
              <Radio size={14} className={live ? "text-ok" : ""} />
              {live ? "实时刷新中" : "实时刷新已暂停"}
            </Button>
            {selected.size > 0 && (
              <Button variant="danger" onClick={() => setConfirmDelete(true)}>
                <Trash2 size={14} /> 删除选中（{selected.size}）
              </Button>
            )}
            <Button variant="ghost" onClick={() => setConfirmClear(true)}>
              清空全部
            </Button>
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          value={draft.keyword}
          onChange={(e) => setDraft({ ...draft, keyword: e.target.value })}
          onKeyDown={(e) => e.key === "Enter" && applyFilters({})}
          placeholder="搜索 Prompt / 工具内容"
          className="h-8 w-56 rounded-lg border border-line-strong bg-surface px-3 text-sm outline-none transition focus:border-ink placeholder:text-faint"
        />
        <select
          value={draft.api_key_name}
          onChange={(e) => applyFilters({ api_key_name: e.target.value })}
          className="h-8 rounded-lg border border-line-strong bg-surface px-2 text-sm text-muted outline-none transition focus:border-ink"
        >
          <option value="">全部名称</option>
          {(keys ?? []).map((k) => (
            <option key={k.id} value={k.name}>
              {k.name || `#${k.id}`}
            </option>
          ))}
        </select>
        <select
          value={draft.sensitive_type}
          onChange={(e) => applyFilters({ sensitive_type: e.target.value })}
          className="h-8 rounded-lg border border-line-strong bg-surface px-2 text-sm text-muted outline-none transition focus:border-ink"
        >
          <option value="">全部敏感类型</option>
          {(sensitiveRules ?? []).map((r) => (
            <option key={r.id} value={r.name}>
              {r.name}
            </option>
          ))}
        </select>
        <Button size="sm" onClick={() => applyFilters({})}>
          查询
        </Button>
        {(applied.keyword || applied.api_key_name || applied.sensitive_type) && (
          <Button size="sm" variant="ghost" onClick={() => applyFilters(EMPTY_FILTERS)}>
            重置
          </Button>
        )}
        <div className="flex-1" />
        <span className="text-xs text-faint">
          共 {total} 条{applied.sensitive_type ? "（命中筛选）" : ""}
        </span>
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(l) => l.id}
        empty={pollHasFilter(applied) ? "无匹配记录" : "暂无数据，等待客户端请求"}
        selectable
        selectedIds={selected}
        onToggleRow={toggleRow}
        onToggleAll={toggleAll}
        onRowClick={(l) => setDetailId(l.id)}
      />

      <div className="mt-4 flex items-center justify-end gap-2 text-xs text-muted">
        <Button size="sm" onClick={() => goPage(page - 1)} disabled={page <= 1}>
          上一页
        </Button>
        <span className={cn("px-1")}>
          {page} / {totalPages}
        </span>
        <Button size="sm" onClick={() => goPage(page + 1)} disabled={page >= totalPages}>
          下一页
        </Button>
      </div>

      {detailId !== null && <LogDetailModal id={detailId} onClose={() => setDetailId(null)} />}
      {confirmDelete && (
        <ConfirmDialog
          title="删除日志"
          message={`确认删除选中的 ${selected.size} 条日志？`}
          confirmLabel="删除"
          danger
          onClose={() => setConfirmDelete(false)}
          onConfirm={batchDelete}
        />
      )}
      {confirmClear && (
        <ConfirmDialog
          title="清空日志"
          message="确认清空全部行为监控日志？此操作不可恢复。"
          confirmLabel="清空"
          danger
          onClose={() => setConfirmClear(false)}
          onConfirm={clearAll}
        />
      )}
    </div>
  );
}

function pollHasFilter(f: Filters): boolean {
  return !!(f.keyword || f.api_key_name || f.sensitive_type);
}
