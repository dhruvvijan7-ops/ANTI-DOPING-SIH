import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export { PageLoading, Spinner, Skeleton, SkeletonRows } from "@/components/ui/spinner";

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-ink-200 bg-ink-50/40 px-6 py-12 text-center",
        className,
      )}
    >
      {icon ? <div className="text-ink-400">{icon}</div> : null}
      <p className="text-sm font-medium text-ink-800">{title}</p>
      {description ? <p className="max-w-md text-sm text-ink-500">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        {eyebrow ? <p className="text-xs font-medium uppercase tracking-wider text-ink-500">{eyebrow}</p> : null}
        <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink-950">{title}</h1>
        {description ? <p className="mt-1 max-w-2xl text-sm text-ink-600">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: ReactNode;
  onRetry?: () => void;
}) {
  return (
    <div className="flex min-h-[30vh] flex-col items-center justify-center gap-2 rounded-lg border border-red-100 bg-red-50/50 px-6 py-10 text-center">
      <p className="text-sm font-semibold text-red-900">{title}</p>
      <p className="max-w-md text-sm text-red-700">{message ?? "The request could not be completed."}</p>
      {onRetry ? (
        <button
          className="mt-2 inline-flex h-8 items-center rounded-md px-3 text-sm font-medium text-red-900 ring-1 ring-inset ring-red-200 hover:bg-red-100"
          onClick={onRetry}
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}