// Canonical permission keys (mirrored from the backend's 26 permissions).
export const PERMISSIONS = {
  alertsRead: "alerts:read",
  alertsReview: "alerts:review",
  alertsDismiss: "alerts:dismiss",
  alertsFalsePositive: "alerts:dismiss",
  alertsEscalate: "alerts:review",
  alertsConvert: "alerts:convert",
  analysisRead: "analysis:read",
  analysisRun: "analysis:run",
  athletesRead: "athletes:read",
  auditRead: "audit:read",
  evidenceCreate: "evidence:create",
  evidenceModify: "evidence:modify",
  intelligenceRead: "intelligence:read",
  intelligenceCreate: "intelligence:create",
  intelligenceModify: "intelligence:modify",
  investigationsRead: "investigations:read",
  investigationsCreate: "investigations:create",
  investigationsModify: "investigations:modify",
  investigationsAssign: "investigations:assign",
  reportsRead: "reports:read",
  reportsGenerate: "reports:generate",
  usersManage: "users:manage",
} as const;

export const DROP_PERMISSIONS = {
  intelligenceRead: "intelligence:read",
  alertsRead: "alerts:read",
  athletesRead: "athletes:read",
  investigationsRead: "investigations:read",
  reportsRead: "reports:read",
  auditRead: "audit:read",
  usersManage: "users:manage",
} as const;

export type PermissionKey = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];