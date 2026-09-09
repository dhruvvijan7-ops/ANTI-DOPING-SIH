// Display metadata for backend enumerations and state machines.
// Colors must never be the only signal: every badge also carries a label.

export const PRIORITY_META: Record<
  string,
  { label: string; badge: string; bar: string; rank: number }
> = {
  LOW: {
    label: "Low priority",
    badge: "bg-ink-100 text-ink-700 ring-ink-200",
    bar: "bg-ink-400",
    rank: 0,
  },
  MODERATE: {
    label: "Moderate priority",
    badge: "bg-sky-50 text-sky-800 ring-sky-200",
    bar: "bg-sky-500",
    rank: 1,
  },
  HIGH: {
    label: "High priority",
    badge: "bg-amber-50 text-amber-800 ring-amber-200",
    bar: "bg-amber-500",
    rank: 2,
  },
  VERY_HIGH: {
    label: "Very high priority",
    badge: "bg-orange-50 text-orange-800 ring-orange-200",
    bar: "bg-orange-500",
    rank: 3,
  },
  CRITICAL: {
    label: "Critical priority",
    badge: "bg-red-50 text-red-800 ring-red-200",
    bar: "bg-red-600",
    rank: 4,
  },
};

export const PRIORITY_ORDER = ["LOW", "MODERATE", "HIGH", "VERY_HIGH", "CRITICAL"];

export function priorityLabel(value: string | undefined): string {
  return PRIORITY_META[value ?? ""]?.label ?? value ?? "—";
}

export const INVESTIGATION_STATUS_META: Record<string, { label: string; badge: string }> = {
  OPEN: { label: "Open", badge: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  CLOSED: { label: "Closed", badge: "bg-ink-100 text-ink-600 ring-ink-200" },
  ARCHIVED: { label: "Archived", badge: "bg-ink-50 text-ink-500 ring-ink-200" },
};

export const TASK_STATUS_META: Record<string, { label: string; badge: string }> = {
  OPEN: { label: "Open", badge: "bg-ink-100 text-ink-700 ring-ink-200" },
  IN_PROGRESS: {
    label: "In progress",
    badge: "bg-sky-50 text-sky-800 ring-sky-200",
  },
  DONE: { label: "Done", badge: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  CANCELLED: { label: "Cancelled", badge: "bg-ink-100 text-ink-500 ring-ink-200" },
};

export const ALERT_STATUS_META: Record<string, { label: string; badge: string }> = {
  NEW: { label: "New", badge: "bg-amber-50 text-amber-800 ring-amber-200" },
  REVIEWED: { label: "Reviewed", badge: "bg-sky-50 text-sky-800 ring-sky-200" },
  DISMISSED: { label: "Dismissed", badge: "bg-ink-100 text-ink-600 ring-ink-200" },
  FALSE_POSITIVE: { label: "False positive", badge: "bg-ink-100 text-ink-600 ring-ink-200" },
  ESCALATED: { label: "Escalated", badge: "bg-orange-50 text-orange-800 ring-orange-200" },
  CONVERTED: { label: "Converted to case", badge: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
};

export const SENSITIVITY_META: Record<string, { label: string; badge: string }> = {
  ROUTINE: { label: "Routine", badge: "bg-ink-100 text-ink-700 ring-ink-200" },
  SENSITIVE: { label: "Sensitive", badge: "bg-sky-50 text-sky-800 ring-sky-200" },
  HIGHLY_SENSITIVE: {
    label: "Highly sensitive",
    badge: "bg-amber-50 text-amber-800 ring-amber-200",
  },
  RESTRICTED: { label: "Restricted", badge: "bg-red-50 text-red-800 ring-red-200" },
};

export const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  DOCUMENT: "Document",
  TEST: "Test / laboratory",
  SCREENSHOT: "Screenshot / capture",
  STATEMENT: "Witness statement",
  OTHER: "Other",
};

export const SIGNAL_TYPE_LABELS: Record<string, string> = {
  RULE: "Rule-based signal",
  ANOMALY: "Anomaly detection",
  TEMPORAL: "Temporal correlation",
  CROSS_SOURCE: "Cross-source correlation",
  NETWORK: "Network context",
};

export const SIGNAL_TYPE_ORDER = ["RULE", "ANOMALY", "TEMPORAL", "CROSS_SOURCE", "NETWORK"];

export const VALIDITY_META: Record<string, { label: string; badge: string }> = {
  SUPPORTING: { label: "Supporting", badge: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  CONTRADICTING: { label: "Contradicting", badge: "bg-red-50 text-red-800 ring-red-200" },
  REVIEW: { label: "Under review", badge: "bg-ink-100 text-ink-700 ring-ink-200" },
};

export const REPORT_STATUS_META: Record<string, { label: string; badge: string }> = {
  DRAFT: { label: "Draft", badge: "bg-ink-100 text-ink-700 ring-ink-200" },
  FINAL: { label: "Final", badge: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  SUPERSEDED: { label: "Superseded", badge: "bg-ink-100 text-ink-500 ring-ink-200" },
};

export const RUN_STATUS_META: Record<string, { label: string; badge: string }> = {
  PENDING: { label: "Pending", badge: "bg-ink-100 text-ink-700 ring-ink-200" },
  RUNNING: { label: "Running", badge: "bg-sky-50 text-sky-800 ring-sky-200" },
  COMPLETED: { label: "Completed", badge: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  FAILED: { label: "Failed", badge: "bg-red-50 text-red-800 ring-red-200" },
  CANCELLED: { label: "Cancelled", badge: "bg-ink-100 text-ink-500 ring-ink-200" },
};

export const SEVERITY_META: Record<string, { label: string; badge: string }> = {
  LOW: { label: "Low severity", badge: "bg-ink-100 text-ink-700 ring-ink-200" },
  MODERATE: { label: "Moderate severity", badge: "bg-sky-50 text-sky-800 ring-sky-200" },
  HIGH: { label: "High severity", badge: "bg-amber-50 text-amber-800 ring-amber-200" },
  CRITICAL: { label: "Critical severity", badge: "bg-red-50 text-red-800 ring-red-200" },
};

export const INFO_CATEGORY_LABELS: Record<string, string> = {
  SUSPECTED_SUBSTANCE_EXPOSURE: "Suspected substance exposure",
  ADMISSION: "Admission or disclosure",
  WITNESS_ACCOUNT: "Witness account",
  TRAVEL_ANOMALY: "Travel anomaly",
  MEDICAL_EXCEPTION: "Therapeutic use / medical record",
  SOURCE_OBSERVATION: "Source observation",
};

export function infoCategoryLabel(value: string | undefined): string {
  return INFO_CATEGORY_LABELS[value ?? ""] ?? value ?? "—";
}

export function reliabilityLabel(value: string | undefined): string {
  // Backend supplies a reliability level string (e.g. A/B/C/1/2/3…). Pass through.
  return value ?? "—";
}

export type SeverityGlyph = { label: string };

export const DEFAULT_PAGE_TITLE = "VERITY — Anti-Doping Intelligence & Investigations Platform";