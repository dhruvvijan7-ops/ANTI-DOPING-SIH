// Typed endpoint functions. One-to-one with the backend contract.
import { api } from "@/lib/api/client";
import type {
  AiResponse,
  AlertDetail,
  AlertList,
  AlertListParams,
  AlertStatus,
  AnalysisRunDetail,
  AnalysisRunParams,
  AnalysisRunSummary,
  AnomalyResult,
  AssignmentBody,
  AthleteDetail,
  AthleteIntelItem,
  AthleteList,
  AthleteListParams,
  AuditList,
  BiologicalObservation,
  ConvertBody,
  CorrelationResult,
  Dashboard,
  EvidenceBody,
  EvidenceItem,
  EvidenceList,
  EvidencePatchBody,
  EvidenceVersions,
  FindingBody,
  FindingEvidenceLinkBody,
  FindingItem,
  FindingList,
  FindingPatchBody,
  IntelDetail,
  IntelListItem,
  IntelligenceList,
  IntelligenceParams,
  InvestigationCreateBody,
  InvestigationList,
  InvestigationListParams,
  InvestigationOverview,
  InvestigationPatchBody,
  InvestigationStatus,
  InvestigationSummary,
  InvestigationTimeline,
  LoginRequest,
  MessageResponse,
  NetworkResult,
  NoteBody,
  NoteItem,
  NoteList,
  PermissionResponse,
  PriorityResult,
  RegisterRequest,
  RelationshipGraph,
  RelationshipItem,
  RelationshipList,
  RelationshipParams,
  ReportCreateBody,
  ReportItem,
  ReportList,
  ReportPatchBody,
  ReportSections,
  RoleResponse,
  RuleResult,
  RunCreate,
  SignalExplainBody,
  SignalFeature,
  SupportPersonList,
  SupportPersonListParams,
  SupportPersonSummary,
  TaskBody,
  TaskItem,
  TaskList,
  TaskPatchBody,
  TestRecord,
  TimelineMarker,
  TokenResponse,
  TravelEvent,
  UserResponse,
  WhereaboutEvent,
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  ResetPasswordRequest,
} from "@/lib/api/types";

export const authApi = {
  login: (body: LoginRequest) => api<TokenResponse>("/auth/login", { method: "POST", body }),
  me: () => api<UserResponse>("/auth/me"),
  logout: () => api<{ message: string }>("/auth/logout", { method: "POST" }),
  register: (body: RegisterRequest) => api<TokenResponse>("/auth/register", { method: "POST", body }),
  forgotPassword: (body: ForgotPasswordRequest) =>
    api<ForgotPasswordResponse>("/auth/forgot-password", { method: "POST", body }),
  resetPassword: (body: ResetPasswordRequest) =>
    api<MessageResponse>("/auth/reset-password", { method: "POST", body }),
};

export const usersApi = {
  list: () => api<UserResponse[]>("/users"),
  roles: () => api<RoleResponse[]>("/users/roles"),
  permissions: () => api<PermissionResponse[]>("/users/permissions"),
};

export const dashboardApi = {
  get: () => api<Dashboard>("/dashboard"),
};

export const analysisApi = {
  startRun: (body: RunCreate) =>
    api<AnalysisRunSummary & { started_at: string }>("/analysis/runs", { method: "POST", body }),
  runs: (params?: AnalysisRunParams) =>
    api<{ count: number; runs: AnalysisRunSummary[] }>("/analysis/runs", { params }),
  detail: (runId: string) =>
    api<AnalysisRunDetail>(`/analysis/runs/${runId}`),
  features: (runId: string, subjectId?: string) =>
    api<{ count: number; features: SignalFeature[] }>(`/analysis/runs/${runId}/features`, {
      params: subjectId ? { subject_id: subjectId } : undefined,
    }),
  rules: (runId: string, opts?: { subjectId?: string; onlyTriggered?: boolean }) =>
    api<{ count: number; rules: RuleResult[] }>(`/analysis/runs/${runId}/rules`, {
      params: {
        subject_id: opts?.subjectId,
        only_triggered: opts?.onlyTriggered ?? false,
      },
    }),
  anomalies: (runId: string, subjectId?: string) =>
    api<{ count: number; anomalies: AnomalyResult[] }>(`/analysis/runs/${runId}/anomalies`, {
      params: subjectId ? { subject_id: subjectId } : undefined,
    }),
  correlations: (runId: string, opts?: { correlationType?: string; subjectId?: string }) =>
    api<{ count: number; correlations: CorrelationResult[] }>(`/analysis/runs/${runId}/correlations`, {
      params: {
        correlation_type: opts?.correlationType,
        subject_id: opts?.subjectId,
      },
    }),
  network: (runId: string, subjectId?: string) =>
    api<{ count: number; network: NetworkResult[] }>(`/analysis/runs/${runId}/network`, {
      params: subjectId ? { subject_id: subjectId } : undefined,
    }),
  priority: (runId: string, minLevel?: string) =>
    api<{ count: number; priority: PriorityResult[] }>(`/analysis/runs/${runId}/priority`, {
      params: minLevel ? { min_level: minLevel } : undefined,
    }),
  subjectResults: (subjectId: string, runId?: string) =>
    api<{ results: Array<Record<string, unknown>> }>(`/analysis/subjects/${subjectId}/results`, {
      params: runId ? { run_id: runId } : undefined,
    }),
};

export const alertsApi = {
  list: (params?: AlertListParams) => api<AlertList>("/alerts", { params }),
  detail: (alertId: string) => api<AlertDetail>(`/alerts/${alertId}`),
  updateStatus: (alertId: string, status: AlertStatus | string) =>
    api<DashboardAlertLite>(`/alerts/${alertId}/status`, { method: "PATCH", body: { status } }),
  review: (alertId: string, note?: string | null) =>
    api<DashboardAlertLite>(`/alerts/${alertId}/review`, { method: "POST", body: { note } }),
  dismiss: (alertId: string, note?: string | null) =>
    api<DashboardAlertLite>(`/alerts/${alertId}/dismiss`, { method: "POST", body: { note } }),
  falsePositive: (alertId: string, note?: string | null) =>
    api<DashboardAlertLite>(`/alerts/${alertId}/false-positive`, { method: "POST", body: { note } }),
  escalate: (alertId: string, note?: string | null) =>
    api<DashboardAlertLite>(`/alerts/${alertId}/escalate`, { method: "POST", body: { note } }),
  convert: (alertId: string, body: ConvertBody = {}) =>
    api<{ alert: DashboardAlertLite; investigation: { id: string; case_ref: string; title: string; status: InvestigationStatus | string; priority: string } }>(
      `/alerts/${alertId}/convert`,
      { method: "POST", body },
    ),
};

// Convenience alias: the alert summary shape used across alert routes.
export interface DashboardAlertLite {
  id: string;
  alert_ref: string;
  analysis_run_id: string;
  subject_type: string;
  subject_id: string;
  score: number;
  priority_level: string;
  title: string;
  status: AlertStatus | string;
  investigation_id: string | null;
  triaged_at: string | null;
  created_at: string;
}

export const investigationsApi = {
  list: (params?: InvestigationListParams) =>
    api<InvestigationList>("/investigations", { params }),
  create: (body: InvestigationCreateBody) =>
    api<InvestigationSummary>("/investigations", { method: "POST", body }),
  overview: (id: string) => api<InvestigationOverview>(`/investigations/${id}`),
  update: (id: string, body: InvestigationPatchBody) =>
    api<InvestigationSummary>(`/investigations/${id}`, { method: "PATCH", body }),
  assign: (id: string, body: AssignmentBody) =>
    api<InvestigationSummary>(`/investigations/${id}/assign`, { method: "POST", body }),
  close: (id: string) => api<InvestigationSummary>(`/investigations/${id}/close`, { method: "POST" }),
  intelligence: (id: string) =>
    api<{ count: number; intelligence: IntelListItem[] }>(`/investigations/${id}/intelligence`),
  timeline: (id: string) => api<InvestigationTimeline>(`/investigations/${id}/timeline`),
  relationships: (id: string, relTypes?: string[]) =>
    api<RelationshipGraph>(`/investigations/${id}/relationships`, {
      params: relTypes?.length ? { rel_type: relTypes } : undefined,
    }),
  audit: (id: string) => api<AuditList>(`/investigations/${id}/audit`),
};

export const evidenceApi = {
  list: (investigationId: string) =>
    api<EvidenceList>(`/investigations/${investigationId}/evidence`),
  create: (investigationId: string, body: EvidenceBody) =>
    api<EvidenceItem>(`/investigations/${investigationId}/evidence`, { method: "POST", body }),
  detail: (investigationId: string, evidenceId: string) =>
    api<{ evidence: EvidenceItem }>(`/investigations/${investigationId}/evidence/${evidenceId}`),
  update: (investigationId: string, evidenceId: string, body: EvidencePatchBody) =>
    api<EvidenceItem>(`/investigations/${investigationId}/evidence/${evidenceId}`, {
      method: "PATCH",
      body,
    }),
  remove: (investigationId: string, evidenceId: string) =>
    api<{ message: string }>(`/investigations/${investigationId}/evidence/${evidenceId}`, {
      method: "DELETE",
    }),
  versions: (investigationId: string, evidenceId: string) =>
    api<EvidenceVersions>(`/investigations/${investigationId}/evidence/${evidenceId}/versions`),
};

export const tasksApi = {
  list: (investigationId: string, status?: string) =>
    api<TaskList>(`/investigations/${investigationId}/tasks`, {
      params: status ? { status } : undefined,
    }),
  create: (investigationId: string, body: TaskBody) =>
    api<TaskItem>(`/investigations/${investigationId}/tasks`, { method: "POST", body }),
  update: (investigationId: string, taskId: string, body: TaskPatchBody) =>
    api<TaskItem>(`/investigations/${investigationId}/tasks/${taskId}`, { method: "PATCH", body }),
};

export const notesApi = {
  list: (investigationId: string) => api<NoteList>(`/investigations/${investigationId}/notes`),
  create: (investigationId: string, body: NoteBody) =>
    api<NoteItem>(`/investigations/${investigationId}/notes`, { method: "POST", body }),
  update: (investigationId: string, noteId: string, body: NoteBody) =>
    api<NoteItem>(`/investigations/${investigationId}/notes/${noteId}`, { method: "PATCH", body }),
};

export const findingsApi = {
  list: (investigationId: string) => api<FindingList>(`/investigations/${investigationId}/findings`),
  create: (investigationId: string, body: FindingBody) =>
    api<FindingItem>(`/investigations/${investigationId}/findings`, { method: "POST", body }),
  update: (investigationId: string, findingId: string, body: FindingPatchBody) =>
    api<FindingItem>(`/investigations/${investigationId}/findings/${findingId}`, { method: "PATCH", body }),
  linkEvidence: (investigationId: string, findingId: string, body: FindingEvidenceLinkBody) =>
    api<FindingItem>(`/investigations/${investigationId}/findings/${findingId}/evidence`, {
      method: "POST",
      body,
    }),
  unlinkEvidence: (investigationId: string, findingId: string, evidenceId: string) =>
    api<FindingItem>(
      `/investigations/${investigationId}/findings/${findingId}/evidence/${evidenceId}`,
      { method: "DELETE" },
    ),
};

export const reportsApi = {
  list: (investigationId: string) => api<ReportList>(`/investigations/${investigationId}/reports`),
  create: (investigationId: string, body: ReportCreateBody = {}) =>
    api<ReportItem>(`/investigations/${investigationId}/reports`, { method: "POST", body }),
  detail: (investigationId: string, reportId: string) =>
    api<ReportItem>(`/investigations/${investigationId}/reports/${reportId}`),
  update: (investigationId: string, reportId: string, body: ReportPatchBody) =>
    api<ReportItem>(`/investigations/${investigationId}/reports/${reportId}`, {
      method: "PATCH",
      body,
    }),
  publish: (investigationId: string, reportId: string) =>
    api<ReportItem>(`/investigations/${investigationId}/reports/${reportId}/publish`, {
      method: "POST",
    }),
};

export const aiApi = {
  summary: (investigationId: string) =>
    api<AiResponse>(`/investigations/${investigationId}/ai/summary`, { method: "POST" }),
  timelineSummary: (investigationId: string) =>
    api<AiResponse>(`/investigations/${investigationId}/ai/timeline-summary`, { method: "POST" }),
  signalExplanation: (investigationId: string, body?: SignalExplainBody) =>
    api<AiResponse>(`/investigations/${investigationId}/ai/signal-explanation`, {
      method: "POST",
      body,
    }),
  informationGaps: (investigationId: string) =>
    api<AiResponse>(`/investigations/${investigationId}/ai/information-gaps`, { method: "POST" }),
  questions: (investigationId: string) =>
    api<AiResponse>(`/investigations/${investigationId}/ai/questions`, { method: "POST" }),
  reportDraft: (investigationId: string, body: ReportCreateBody = {}) =>
    api<AiResponse & { draft: ReportSections }>(`/investigations/${investigationId}/ai/report-draft`, {
      method: "POST",
      body,
    }),
};

export const intelligenceApi = {
  list: (params?: IntelligenceParams) => api<IntelligenceList>("/intelligence/reports", { params }),
  detail: (reportId: string) => api<IntelDetail>(`/intelligence/reports/${reportId}`),
};

export const relationshipsApi = {
  list: (params?: RelationshipParams) => api<RelationshipList>("/relationships", { params }),
  detail: (relationshipId: string) => api<RelationshipItem>(`/relationships/${relationshipId}`),
};

export const athletesApi = {
  list: (params?: AthleteListParams) => api<AthleteList>("/athletes", { params }),
  detail: (athleteId: string) => api<AthleteDetail>(`/athletes/${athleteId}`),
  tests: (athleteId: string) =>
    api<{ count: number; tests: TestRecord[] }>(`/athletes/${athleteId}/tests`),
  abp: (athleteId: string, marker?: string) =>
    api<{ count: number; observations: BiologicalObservation[] }>(`/athletes/${athleteId}/abp`, {
      params: marker ? { marker } : undefined,
    }),
  whereabouts: (athleteId: string) =>
    api<{ count: number; whereabouts: WhereaboutEvent[] }>(`/athletes/${athleteId}/whereabouts`),
  travel: (athleteId: string) =>
    api<{ count: number; travel: TravelEvent[] }>(`/athletes/${athleteId}/travel`),
  events: (athleteId: string) =>
    api<{ count: number; timeline: TimelineMarker[] }>(`/athletes/${athleteId}/events`),
  intelligence: (athleteId: string) =>
    api<{ count: number; reports: AthleteIntelItem[] }>(`/athletes/${athleteId}/intelligence`),
  relationships: (athleteId: string) =>
    api<{ count: number; relationships: RelationshipItem[] }>(`/athletes/${athleteId}/relationships`),
};

export const supportPersonsApi = {
  list: (params?: SupportPersonListParams) =>
    api<SupportPersonList>("/support-persons", { params }),
  detail: (personId: string) =>
    api<SupportPersonSummary & { counts: Record<string, number> }>(`/support-persons/${personId}`),
  relationships: (personId: string) =>
    api<{ count: number; relationships: RelationshipItem[] }>(`/support-persons/${personId}/relationships`),
  intelligence: (personId: string) =>
    api<{ count: number; reports: AthleteIntelItem[] }>(`/support-persons/${personId}/intelligence`),
};