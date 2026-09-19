import type { ReactNode } from "react";
import { cn } from "../../lib/utils.ts";

export interface Column<T> {
  key: string;
  head: ReactNode;
  cell: (row: T) => ReactNode;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty = "暂无数据",
  selectable = false,
  selectedIds = new Set<number>(),
  onToggleRow,
  onToggleAll,
  onRowClick,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => number;
  empty?: string;
  selectable?: boolean;
  selectedIds?: Set<number>;
  onToggleRow?: (id: number) => void;
  onToggleAll?: (select: boolean) => void;
  onRowClick?: (row: T) => void;
}) {
  const allSelected = rows.length > 0 && rows.every((r) => selectedIds.has(rowKey(r)));

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line bg-paper/60">
            {selectable && (
              <th className="w-9 px-4 py-2.5">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={() => onToggleAll?.(!allSelected)}
                  className="rounded border-line-strong"
                  aria-label="全选"
                />
              </th>
            )}
            {columns.map((c) => (
              <th key={c.key} className={cn("px-4 py-2.5 text-left text-xs font-medium text-muted", c.className)}>
                {c.head}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length + (selectable ? 1 : 0)} className="px-4 py-12 text-center text-sm text-faint">
                {empty}
              </td>
            </tr>
          ) : (
            rows.map((row) => {
              const id = rowKey(row);
              const selected = selectedIds.has(id);
              return (
                <tr
                  key={id}
                  className={cn(
                    "border-b border-line last:border-0 hover:bg-paper/70",
                    onRowClick && "cursor-pointer",
                  )}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                >
                  {selectable && (
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => onToggleRow?.(id)}
                        className="rounded border-line-strong"
                        aria-label="选择"
                      />
                    </td>
                  )}
                  {columns.map((c) => (
                    <td key={c.key} className={cn("px-4 py-3", c.className)}>
                      {c.cell(row)}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
