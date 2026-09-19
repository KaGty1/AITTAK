import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

import { cn } from "../../lib/utils.ts";

export function Modal({
  title,
  onClose,
  children,
  footer,
  size = "md",
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  size?: "md" | "lg" | "xl";
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/20 p-4" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "w-full rounded-xl border border-line bg-surface p-5 shadow-pop",
          size === "md" ? "max-w-md" : size === "lg" ? "max-w-2xl" : "max-w-3xl",
        )}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="text-faint transition hover:text-ink" aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        {children}
        {footer && <div className="mt-5 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}
