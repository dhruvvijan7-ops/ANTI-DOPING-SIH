import { cn } from "@/lib/utils";

export interface TabItem<T extends string> {
  key: T;
  label: string;
  count?: number;
  leading?: React.ReactNode;
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  className,
}: {
  tabs: Array<TabItem<T>>;
  value: T;
  onChange: (key: T) => void;
  className?: string;
}) {
  const current = tabs.find((t) => t.key === value) ?? tabs[0];
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-1 border-b border-ink-100",
        className,
      )}
      role="tablist"
      aria-label="Sections"
    >
      {tabs.map((tab) => {
        const selected = tab.key === current?.key;
        return (
          <button
            key={tab.key}
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(tab.key)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-t-md border-b-2 px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-600",
              selected
                ? "border-signal-600 text-ink-950"
                : "border-transparent text-ink-500 hover:border-ink-200 hover:text-ink-800",
            )}
          >
            {tab.leading}
            {tab.label}
            {tab.count !== undefined ? (
              <span
                className={cn(
                  "rounded-full px-1.5 text-xs tabular-nums",
                  selected ? "bg-signal-100 text-signal-800" : "bg-ink-100 text-ink-600",
                )}
              >
                {tab.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}