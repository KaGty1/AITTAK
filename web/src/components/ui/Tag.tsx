import type { ReactNode } from "react";
import { cn } from "../../lib/utils.ts";

type Tone = "line" | "danger" | "ok" | "mono";

const TONES: Record<Tone, string> = {
  line: "bg-line/70 text-muted",
  danger: "bg-danger/10 text-danger",
  ok: "bg-ok/10 text-ok",
  mono: "bg-line/70 text-muted font-mono",
};

export function Tag({ tone = "line", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={cn("inline-block rounded px-1.5 py-0.5 text-xs leading-5", TONES[tone])}>
      {children}
    </span>
  );
}
