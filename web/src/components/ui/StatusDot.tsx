import { cn } from "../../lib/utils.ts";

export function StatusDot({ on, onLabel = "启用", offLabel = "禁用" }: { on: boolean; onLabel?: string; offLabel?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted">
      <span className={cn("h-2 w-2 rounded-full", on ? "bg-ok" : "bg-line-strong")} />
      {on ? onLabel : offLabel}
    </span>
  );
}

export function StatusCode({ code }: { code: number }) {
  const ok = code >= 200 && code < 400;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted">
      <span className={cn("h-1.5 w-1.5 rounded-full", ok ? "bg-ok" : "bg-danger")} />
      {code}
    </span>
  );
}
