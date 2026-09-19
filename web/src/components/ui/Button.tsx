import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils.ts";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-ink/90",
  secondary: "bg-surface border border-line-strong text-ink hover:bg-paper",
  ghost: "text-muted hover:text-ink hover:bg-line/60",
  danger: "text-danger border border-danger/30 hover:bg-danger/5",
};

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg font-medium transition disabled:opacity-40 disabled:pointer-events-none",
        size === "sm" ? "px-2.5 py-1 text-[13px]" : "px-3.5 py-1.5 text-sm",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}
