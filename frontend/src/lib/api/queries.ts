import { useMutation, useQuery, useQueryClient, type QueryClient, type UseMutationOptions, type UseQueryOptions } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/auth";
import {
  aiApi,
  alertsApi,
  analysisApi,
  athletesApi,
  authApi,
  dashboardApi,
  evidenceApi,
  findingsApi,
  intelligenceApi,
  investigationsApi,
  notesApi,
  relationshipsApi,
  reportsApi,
  supportPersonsApi,
  tasksApi,
} from "@/lib/api/endpoints";
import type {
  AlertListParams,
  AnalysisRunParams,
  AssignmentBody,
  AthleteListParams,
  ConvertBody,
  EvidenceBody,
  EvidencePatchBody,
  FindingBody,
  FindingPatchBody,
  InvestigationCreateBody,
  InvestigationListParams,
  InvestigationPatchBody,
  NoteBody,
  ReportCreateBody,
  ReportPatchBody,
  RunCreate,
  SignalExplainBody,
  SupportPersonListParams,
  TaskBody,
  TaskPatchBody,
  IntelligenceParams,
} from "@/lib/api/types";

// --- Auth ---
export function useMeQuery(options?: UseQueryOptions<Awaited<ReturnType<typeof authApi.me>>>) {
  return useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    retry: false,
    staleTime: 5 * 60_000,
    ...options,
  });
}

export function useLogoutMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => authApi.logout().catch(() => undefined),
    onSuccess: () => qc.clear(),
    onSettled: () => useAuthStore.getState().clearSession(),
  });
}

// --- Dashboard ---
export function useDashboardQuery() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.get,
    staleTime: 30_000,
  });
}

// --- Alerts ---
export function useAlertsQuery(params?: AlertListParams) {
  return useQuery({
    queryKey: ["alerts", params],
    queryFn: () => alertsApi.list(params),
    staleTime: 20_000,
  });
}

export function useAlertDetailQuery(alertId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["alerts", alertId, "detail"],
    queryFn: () => alertsApi.detail(alertId!),
    enabled: Boolean(alertId) && enabled,
    retry: false,
    staleTime: 20_000,
  });
}

export interface TriageMutationContext {
  alertId: string;
  note?: string | null;
}

export function triageInvalidations(alertId?: string) {
  return [
    ["alerts"] as const,
    alertId ? (["alerts", alertId, "detail"] as const) : null,
    ["dashboard"] as const,
  ].filter(Boolean) as unknown as string[][];
}

export function useReviewAlertMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof alertsApi.review>>, unknown, TriageMutationContext>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, note }) => alertsApi.review(alertId, note ?? null),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, triageInvalidations(v.alertId));
    },
    ...opts,
  });
}

export function useDismissAlertMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof alertsApi.dismiss>>, unknown, TriageMutationContext>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, note }) => alertsApi.dismiss(alertId, note ?? null),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, triageInvalidations(v.alertId));
    },
    ...opts,
  });
}

export function useFalsePositiveAlertMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof alertsApi.falsePositive>>, unknown, TriageMutationContext>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, note }) => alertsApi.falsePositive(alertId, note ?? null),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, triageInvalidations(v.alertId));
    },
    ...opts,
  });
}

export function useEscalateAlertMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof alertsApi.escalate>>, unknown, TriageMutationContext>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, note }) => alertsApi.escalate(alertId, note ?? null),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, triageInvalidations(v.alertId));
    },
    ...opts,
  });
}

export function useConvertAlertMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof alertsApi.convert>>, unknown, { alertId: string; body: ConvertBody }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, body }) => alertsApi.convert(alertId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, triageInvalidations(v.alertId));
      void invalidateMany(qc, [["investigations"], ["dashboard"]]);
    },
    ...opts,
  });
}

function invalidateMany(qc: QueryClient, keys: string[][]) {
  return Promise.all(keys.map((k) => qc.invalidateQueries({ queryKey: k })));
}

// --- Analysis ---
export function useAnalysisRunsQuery(params?: AnalysisRunParams) {
  return useQuery({
    queryKey: ["analysis", "runs", params],
    queryFn: () => analysisApi.runs(params),
    staleTime: 20_000,
  });
}

export function useAnalysisRunDetailQuery(runId?: string) {
  return useQuery({
    queryKey: ["analysis", "runs", runId, "detail"],
    queryFn: () => analysisApi.detail(runId!),
    enabled: Boolean(runId),
    staleTime: 60_000,
  });
}

export function useStartAnalysisRunMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof analysisApi.startRun>>, unknown, RunCreate>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => analysisApi.startRun(body),
    onSuccess: () => {
      void invalidateMany(qc, [["analysis", "runs"], ["dashboard"]]);
    },
    ...opts,
  });
}

// --- Athletes ---
export function useAthletesQuery(params?: AthleteListParams) {
  return useQuery({
    queryKey: ["athletes", params],
    queryFn: () => athletesApi.list(params),
    staleTime: 30_000,
  });
}

export function useAthleteDetailQuery(athleteId?: string) {
  return useQuery({
    queryKey: ["athletes", athleteId],
    queryFn: () => athletesApi.detail(athleteId!),
    enabled: Boolean(athleteId),
    staleTime: 30_000,
  });
}

export function useAthleteTestsQuery(athleteId?: string) {
  return useQuery({
    queryKey: ["athletes", athleteId, "tests"],
    queryFn: () => athletesApi.tests(athleteId!),
    enabled: Boolean(athleteId),
  });
}

export function useAthleteAbpQuery(athleteId?: string) {
  return useQuery({
    queryKey: ["athletes", athleteId, "abp"],
    queryFn: () => athletesApi.abp(athleteId!),
    enabled: Boolean(athleteId),
  });
}

export function useAthleteWhereaboutsQuery(athleteId?: string) {
  return useQuery({
    queryKey: ["athletes", athleteId, "whereabouts"],
    queryFn: () => athletesApi.whereabouts(athleteId!),
    enabled: Boolean(athleteId),
  });
}

export function useAthleteTravelQuery(athleteId?: string) {
  return useQuery({
    queryKey: ["athletes", athleteId, "travel"],
    queryFn: () => athletesApi.travel(athleteId!),
    enabled: Boolean(athleteId),
  });
}

export function useAthleteEventsQuery(athleteId?: string) {
  return useQuery({
    queryKey: ["athletes", athleteId, "events"],
    queryFn: () => athletesApi.events(athleteId!),
    enabled: Boolean(athleteId),
  });
}

export function useAthleteIntelQuery(athleteId?: string) {
  return useQuery({
    queryKey: ["athletes", athleteId, "intelligence"],
    queryFn: () => athletesApi.intelligence(athleteId!),
    enabled: Boolean(athleteId),
  });
}

export function useAthleteRelationshipsQuery(athleteId?: string) {
  return useQuery({
    queryKey: ["athletes", athleteId, "relationships"],
    queryFn: () => athletesApi.relationships(athleteId!),
    enabled: Boolean(athleteId),
  });
}

// --- Support persons ---
export function useSupportPersonsQuery(params?: SupportPersonListParams) {
  return useQuery({
    queryKey: ["support-persons", params],
    queryFn: () => supportPersonsApi.list(params),
  });
}

// --- Intelligence ---
export function useIntelligenceQuery(params?: IntelligenceParams) {
  return useQuery({
    queryKey: ["intelligence", params],
    queryFn: () => intelligenceApi.list(params),
    staleTime: 20_000,
  });
}

export function useIntelDetailQuery(reportId?: string) {
  return useQuery({
    queryKey: ["intelligence", reportId],
    queryFn: () => intelligenceApi.detail(reportId!),
    enabled: Boolean(reportId),
    retry: false,
  });
}

// --- Relationships ---
export function useRelationshipsQuery(params?: Parameters<typeof relationshipsApi.list>[0]) {
  return useQuery({
    queryKey: ["relationships", params],
    queryFn: () => relationshipsApi.list(params),
  });
}

// --- Investigations ---
export function useInvestigationsQuery(params?: InvestigationListParams) {
  return useQuery({
    queryKey: ["investigations", params],
    queryFn: () => investigationsApi.list(params),
    staleTime: 20_000,
  });
}

export function useInvestigationOverviewQuery(id?: string) {
  return useQuery({
    queryKey: ["investigations", id],
    queryFn: () => investigationsApi.overview(id!),
    enabled: Boolean(id),
    staleTime: 20_000,
  });
}

export function useInvestigationTimelineQuery(id?: string) {
  return useQuery({
    queryKey: ["investigations", id, "timeline"],
    queryFn: () => investigationsApi.timeline(id!),
    enabled: Boolean(id),
  });
}

export function useInvestigationRelationshipsQuery(id?: string) {
  return useQuery({
    queryKey: ["investigations", id, "relationships"],
    queryFn: () => investigationsApi.relationships(id!),
    enabled: Boolean(id),
  });
}

export function useInvestigationAuditQuery(id?: string) {
  return useQuery({
    queryKey: ["investigations", id, "audit"],
    queryFn: () => investigationsApi.audit(id!),
    enabled: Boolean(id),
  });
}

export function useInvestigationIntelQuery(id?: string) {
  return useQuery({
    queryKey: ["investigations", id, "intelligence"],
    queryFn: () => investigationsApi.intelligence(id!),
    enabled: Boolean(id),
  });
}

export function useCreateInvestigationMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof investigationsApi.create>>, unknown, InvestigationCreateBody>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => investigationsApi.create(body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations"],
        ["alerts"],
        ["dashboard"],
        v.originating_alert_id ? ["alerts", v.originating_alert_id, "detail"] : [],
      ]);
    },
    ...opts,
  });
}

export function useUpdateInvestigationMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof investigationsApi.update>>, unknown, { id: string; body: InvestigationPatchBody }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }) => investigationsApi.update(id, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [["investigations"], ["investigations", v.id], ["dashboard"]]);
    },
    ...opts,
  });
}

export function useAssignInvestigationMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof investigationsApi.assign>>, unknown, { id: string; body: AssignmentBody }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }) => investigationsApi.assign(id, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations"],
        ["investigations", v.id],
        ["investigations", v.id, "audit"],
        ["dashboard"],
      ]);
    },
    ...opts,
  });
}

export function useCloseInvestigationMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof investigationsApi.close>>, unknown, { id: string }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id }) => investigationsApi.close(id),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [["investigations"], ["investigations", v.id], ["dashboard"]]);
    },
    ...opts,
  });
}

// --- Evidence ---
export function useEvidenceListQuery(investigationId?: string) {
  return useQuery({
    queryKey: ["investigations", investigationId, "evidence"],
    queryFn: () => evidenceApi.list(investigationId!),
    enabled: Boolean(investigationId),
    staleTime: 15_000,
  });
}

export function useEvidenceDetailQuery(investigationId?: string, evidenceId?: string, enabled = true) {
  return useQuery({
    queryKey: ["investigations", investigationId, "evidence", evidenceId],
    queryFn: () => evidenceApi.detail(investigationId!, evidenceId!),
    enabled: Boolean(investigationId && evidenceId) && enabled,
    retry: false,
    staleTime: 15_000,
  });
}

export function useEvidenceVersionsQuery(investigationId?: string, evidenceId?: string) {
  return useQuery({
    queryKey: ["investigations", investigationId, "evidence", evidenceId, "versions"],
    queryFn: () => evidenceApi.versions(investigationId!, evidenceId!),
    enabled: Boolean(investigationId && evidenceId),
    retry: false,
    staleTime: 30_000,
  });
}

export function useCreateEvidenceMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof evidenceApi.create>>, unknown, { investigationId: string; body: EvidenceBody }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, body }) => evidenceApi.create(investigationId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "evidence"],
        ["investigations", v.investigationId],
        ["investigations", v.investigationId, "findings"],
        ["investigations", v.investigationId, "reports"],
      ]);
    },
    ...opts,
  });
}

export function useUpdateEvidenceMutation(
  opts?: UseMutationOptions<Awaited<ReturnType<typeof evidenceApi.update>>, unknown, { investigationId: string; evidenceId: string; body: EvidencePatchBody }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, evidenceId, body }) => evidenceApi.update(investigationId, evidenceId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "evidence"],
        ["investigations", v.investigationId, "evidence", v.evidenceId],
        ["investigations", v.investigationId, "evidence", v.evidenceId, "versions"],
        ["investigations", v.investigationId, "reports"],
      ]);
    },
    ...opts,
  });
}

export function useDeleteEvidenceMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof evidenceApi.remove>>, unknown, { investigationId: string; evidenceId: string }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, evidenceId }) => evidenceApi.remove(investigationId, evidenceId),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "evidence"],
        ["investigations", v.investigationId],
        ["investigations", v.investigationId, "findings"],
      ]);
    },
    ...opts,
  });
}

// --- Tasks ---
export function useTasksQuery(investigationId?: string, status?: string) {
  return useQuery({
    queryKey: ["investigations", investigationId, "tasks", status],
    queryFn: () => tasksApi.list(investigationId!, status),
    enabled: Boolean(investigationId),
  });
}

export function useCreateTaskMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof tasksApi.create>>, unknown, { investigationId: string; body: TaskBody }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, body }) => tasksApi.create(investigationId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "tasks"],
        ["investigations", v.investigationId],
        ["investigations", v.investigationId, "audit"],
      ]);
    },
    ...opts,
  });
}

export function useUpdateTaskMutation(
  opts?: UseMutationOptions<Awaited<ReturnType<typeof tasksApi.update>>, unknown, { investigationId: string; taskId: string; body: TaskPatchBody }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, taskId, body }) => tasksApi.update(investigationId, taskId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "tasks"],
        ["investigations", v.investigationId, "audit"],
      ]);
    },
    ...opts,
  });
}

// --- Notes ---
export function useNotesQuery(investigationId?: string) {
  return useQuery({
    queryKey: ["investigations", investigationId, "notes"],
    queryFn: () => notesApi.list(investigationId!),
    enabled: Boolean(investigationId),
  });
}

export function useCreateNoteMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof notesApi.create>>, unknown, { investigationId: string; body: NoteBody }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, body }) => notesApi.create(investigationId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "notes"],
        ["investigations", v.investigationId],
        ["investigations", v.investigationId, "audit"],
      ]);
    },
    ...opts,
  });
}

// --- Findings ---
export function useFindingsQuery(investigationId?: string) {
  return useQuery({
    queryKey: ["investigations", investigationId, "findings"],
    queryFn: () => findingsApi.list(investigationId!),
    enabled: Boolean(investigationId),
  });
}

export function useCreateFindingMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof findingsApi.create>>, unknown, { investigationId: string; body: FindingBody }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, body }) => findingsApi.create(investigationId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "findings"],
        ["investigations", v.investigationId],
        ["investigations", v.investigationId, "audit"],
        ["investigations", v.investigationId, "reports"],
      ]);
    },
    ...opts,
  });
}

export function useUpdateFindingMutation(
  opts?: UseMutationOptions<Awaited<ReturnType<typeof findingsApi.update>>, unknown, { investigationId: string; findingId: string; body: FindingPatchBody }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, findingId, body }) => findingsApi.update(investigationId, findingId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "findings"],
        ["investigations", v.investigationId, "audit"],
        ["investigations", v.investigationId, "reports"],
      ]);
    },
    ...opts,
  });
}

export function useLinkFindingEvidenceMutation(
  opts?: UseMutationOptions<Awaited<ReturnType<typeof findingsApi.linkEvidence>>, unknown, { investigationId: string; findingId: string; evidenceId: string; validity: string }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, findingId, evidenceId, validity }) =>
      findingsApi.linkEvidence(investigationId, findingId, { evidence_id: evidenceId, validity }),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [["investigations", v.investigationId, "findings"]]);
    },
    ...opts,
  });
}

export function useUnlinkFindingEvidenceMutation(
  opts?: UseMutationOptions<Awaited<ReturnType<typeof findingsApi.unlinkEvidence>>, unknown, { investigationId: string; findingId: string; evidenceId: string }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, findingId, evidenceId }) =>
      findingsApi.unlinkEvidence(investigationId, findingId, evidenceId),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [["investigations", v.investigationId, "findings"]]);
    },
    ...opts,
  });
}

// --- Reports ---
export function useReportsQuery(investigationId?: string) {
  return useQuery({
    queryKey: ["investigations", investigationId, "reports"],
    queryFn: () => reportsApi.list(investigationId!),
    enabled: Boolean(investigationId),
  });
}

export function useCreateReportMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof reportsApi.create>>, unknown, { investigationId: string; body: ReportCreateBody }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, body }) => reportsApi.create(investigationId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "reports"],
        ["investigations", v.investigationId],
        ["investigations", v.investigationId, "audit"],
      ]);
    },
    ...opts,
  });
}

export function usePublishReportMutation(
  opts?: UseMutationOptions<Awaited<ReturnType<typeof reportsApi.publish>>, unknown, { investigationId: string; reportId: string }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, reportId }) => reportsApi.publish(investigationId, reportId),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [
        ["investigations", v.investigationId, "reports"],
        ["investigations", v.investigationId, "audit"],
      ]);
    },
    ...opts,
  });
}

export function useUpdateReportMutation(
  opts?: UseMutationOptions<Awaited<ReturnType<typeof reportsApi.update>>, unknown, { investigationId: string; reportId: string; body: ReportPatchBody }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ investigationId, reportId, body }) => reportsApi.update(investigationId, reportId, body),
    onSuccess: (_d, v) => {
      void invalidateMany(qc, [["investigations", v.investigationId, "reports"]]);
    },
    ...opts,
  });
}

// --- AI ---
export function useAiSummaryQuery(investigationId?: string, enabled = true) {
  return useQuery({
    queryKey: ["ai", investigationId, "summary"],
    queryFn: () => aiApi.summary(investigationId!),
    enabled: Boolean(investigationId) && enabled,
    staleTime: 60_000,
  });
}

export function useAiInformationGapsQuery(investigationId?: string, enabled = true) {
  return useQuery({
    queryKey: ["ai", investigationId, "gaps"],
    queryFn: () => aiApi.informationGaps(investigationId!),
    enabled: Boolean(investigationId) && enabled,
    staleTime: 60_000,
  });
}

export function useAiSignalExplanationMutation(opts?: UseMutationOptions<Awaited<ReturnType<typeof aiApi.signalExplanation>>, unknown, { investigationId: string; body?: SignalExplainBody }>) {
  return useMutation({
    mutationFn: ({ investigationId, body }) => aiApi.signalExplanation(investigationId, body),
    ...opts,
  });
}