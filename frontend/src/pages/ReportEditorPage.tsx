import { useParams } from "react-router-dom";
import { ReportsEditor } from "@/features/reports";

export default function ReportEditorPage() {
  const { investigationId, reportId } = useParams();
  if (!investigationId || !reportId) return <p className="p-6 text-sm text-ink-500">Missing report parameters.</p>;
  return <ReportsEditor investigationId={investigationId} reportId={reportId} />;
}