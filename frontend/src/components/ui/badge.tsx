import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  children,
  tone,
}: {
  className?: string;
  children: ReactNode;
  tone?: "neutral" | "info" | "success" | "warn" | "danger";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-ink-100 text-ink-700 ring-ink-200",
    info: "bg-sky-50 text-sky-800 ring-sky-200",
    success: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    warn: "bg-amber-50 text-amber-800 ring-amber-200",
    danger: "bg-red-50 text-red-800 ring-red-200",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        tone ? tones[tone] : className,
        !tone && className,
      )}
    >
      {children}
    </span>
  );
}