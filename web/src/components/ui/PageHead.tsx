import type { ReactNode } from "react";

export function PageHead({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex items-center justify-between">
      <h1 className="font-display text-2xl font-semibold tracking-tight">{title}</h1>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
