import { cn } from "@/lib/utils";
import { clamp } from "@/lib/utils";

export function ProgressBar({
  value,
  className,
  barClassName,
  min = 0,
  max = 100,
  height = "h-1.5",
}: {
  value: number;
  className?: string;
  barClassName?: string;
  min?: number;
  max?: number;
  height?: string;
}) {
  const pct = max > min ? clamp(((value - min) / (max - min)) * 100, 0, 100) : 0;
  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn("w-full overflow-hidden rounded-full bg-ink-100", height, className)}
    >
      <div
        className={cn("h-full rounded-full transition-[width] duration-300", barClassName ?? "bg-signal-600")}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function ScoreRing({
  value,
  level,
  size = 52,
}: {
  value: number;
  level?: string;
  size?: number;
}) {
  const stroke = 4.5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = clamp(value, 0, 100);
  const color =
    pct >= 85 ? "#dc2626" : pct >= 70 ? "#d97706" : pct >= 50 ? "#0284c7" : "#94a3b8";
  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${level ?? "Priority"} ${Math.round(pct)} out of 100`}
    >
      <svg width={size} height={size} aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * c} ${c}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className="absolute text-sm font-semibold tabular-nums text-ink-900">
        {Math.round(pct)}
      </span>
    </div>
  );
}