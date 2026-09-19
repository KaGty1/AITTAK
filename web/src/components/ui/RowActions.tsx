export interface RowAction {
  label: string;
  onClick: () => void;
  danger?: boolean;
}

export function RowActions({ items }: { items: RowAction[] }) {
  return (
    <div className="flex gap-3 text-xs">
      {items.map((a) => (
        <button
          key={a.label}
          className={`transition ${a.danger ? "text-muted hover:text-danger" : "text-muted hover:text-ink"}`}
          onClick={a.onClick}
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
