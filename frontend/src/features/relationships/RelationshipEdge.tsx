import { memo } from "react";
import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/react";

interface EdgeData {
  confidence: number;
  relationshipType: string;
  relationshipId: string;
  startDate: string | null;
  endDate: string | null;
  label: string;
}

export const RelationshipEdge = memo(function RelationshipEdge(props: EdgeProps) {
  const d = (props.data ?? {}) as unknown as EdgeData;
  const confidence = d.confidence ?? 1;
  const strokeWidth = 1 + confidence * 2;
  const strokeOpacity = 0.4 + confidence * 0.6;
  const strokeColor = confidence >= 0.7 ? "#14b8a6" : confidence >= 0.4 ? "#f59e0b" : "#ef4444";

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
  });

  return (
    <>
      <BaseEdge
        path={edgePath}
        style={{
          stroke: strokeColor,
          strokeWidth,
          strokeOpacity,
        }}
        markerEnd={props.markerEnd}
      />
      {props.label ? (
        <foreignObject x={labelX - 60} y={labelY - 14} width={120} height={28} className="pointer-events-none">
          <div className="flex h-full items-center justify-center">
            <span className="rounded bg-white/90 px-1.5 py-0.5 text-[9px] font-medium text-ink-600 shadow-sm">
              {props.label}
            </span>
          </div>
        </foreignObject>
      ) : null}
    </>
  );
});
