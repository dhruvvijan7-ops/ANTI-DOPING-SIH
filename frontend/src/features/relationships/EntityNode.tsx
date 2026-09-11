import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

interface EntityNodeData {
  label: string;
  kind: string;
  entityId: string;
  isSubject: boolean;
  color: string;
}

export const EntityNode = memo(function EntityNode({ data }: NodeProps) {
  const d = data as unknown as EntityNodeData;
  const radius = d.isSubject ? 32 : 22;
  return (
    <div className="relative flex flex-col items-center">
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-none !w-0 !h-0" />
      <svg width={radius * 2 + 12} height={radius * 2 + 12}>
        <circle
          cx={radius + 6}
          cy={radius + 6}
          r={radius}
          fill={d.color}
          stroke={d.isSubject ? "#fbbf24" : "#fff"}
          strokeWidth={d.isSubject ? 3 : 2}
          opacity={d.isSubject ? 1 : 0.9}
        />
        <text
          x={radius + 6}
          y={radius + 6 + 5}
          textAnchor="middle"
          fill="white"
          fontSize={d.isSubject ? 16 : 12}
          fontWeight="600"
        >
          {d.label.slice(0, d.isSubject ? 2 : 1).toUpperCase()}
        </text>
      </svg>
      <span
        className={`mt-1 max-w-[120px] truncate text-center ${
          d.isSubject ? "text-xs font-semibold text-ink-900" : "text-[10px] text-ink-600"
        }`}
        title={d.label}
      >
        {d.label.length > 20 ? `${d.label.slice(0, 19)}…` : d.label}
      </span>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-none !w-0 !h-0" />
    </div>
  );
});
