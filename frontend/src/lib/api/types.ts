// ---------------------------------------------------------------------------
// VERITY frontend — typed API contract.
// Captured from the live backend OpenAPI spec and response probes. The backend
// validates every rule; this file only describes what it returns and sends.
// ---------------------------------------------------------------------------

export type IsoString = string;
export type Uuid = string;

// --- Generic error envelope -------------------------------------------------
export interface ApiEnvelope {
  error: {
    code: string;
    message: string;
    request_id: string;
  };
}

export interface ApiValidationDetail {
  loc: Array<string | number>;
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

// --- Auth / users -----------------------------------------------------------
export const PERMISSION_KEYS = [
  "alerts:convert",
  "alerts:dismiss",
  "alerts:read",
  "alerts:review",
  "analysis:read",
  "analysis:run",
  "athletes:read",
  "audit:read",
  "configuration:manage",
  "evidence:create",
  "evidence:modify",
  "intelligence:create",
  "intelligence:modify",
  "intelligence:read",
  "investigations:assign",
  "investigations:create",
  "investigations:modify",
"investigations:read",
  "models:manage",
  "osint:admin",
  "osint:collect",
  "osint:read",
  "reports:generate",
  "reports:read",
  "resources:read",
  "roles:manage",
  "rules:configure",
  "sources:manage",
  "users:manage",
] as const;

export type PermissionKey = (typeof PERMISSION_KEYS)[number];

export const ROLE_KEYS = ["ADMINISTRATOR", "INTELLIGENCE_ANALYST", "INVESTIGATOR", "VIEWER"] as const;
export type RoleKey = (typeof ROLE_KEYS)[number];

export interface PermissionResponse {
  id: Uuid;
  key: PermissionKey;
  description: string | null;
}

export interface RoleResponse {
  id: Uuid;
  name: string;
  description: string | null;
  permissions: PermissionResponse[];
}

export interface UserResponse {
  id: Uuid;
  username: string;
  email: string | null;
  full_name: string | null;
  is_active: boolean;
  last_login_at: IsoString | null;
  role: RoleResponse;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email?: string | null;
  full_name?: string | null;
  password: string;
}

export interface ForgotPasswordRequest {
  identifier: string;
}

export interface ForgotPasswordResponse {
  message: string;
  dev_reset_token: string | null;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface MessageResponse {
  message: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

// --- Shared enumerations ----------------------------------------------------
export type PriorityLevel = "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH" | "CRITICAL";
export type SubjectType = "ATHLETE" | "SUPPORT_PERSON";
export type InvestigationStatus = "OPEN" | "CLOSED" | "ARCHIVED";
export type TaskStatus = "OPEN" | "IN_PROGRESS" | "DONE" | "CANCELLED";
export type AlertStatus =
  | "NEW"
  | "REVIEWED"
  | "DISMISSED"
  | "FALSE_POSITIVE"
  | "ESCALATED"
  | "CONVERTED";
export type SensitivityLevel = "ROUTINE" | "SENSITIVE" | "HIGHLY_SENSITIVE" | "RESTRICTED";
export type EvidenceType = "DOCUMENT" | "TEST" | "SCREENSHOT" | "STATEMENT" | "OTHER";
export type FindingEvidenceValidity = "SUPPORTING" | "CONTRADICTING" | "REVIEW";
export type ReportStatus = "DRAFT" | "IN_REVIEW" | "FINAL" | "SUPERSEDED" | "ARCHIVED";
export type ReportType = "MANUAL" | "AI_ASSISTED" | "HYBRID";
export type BlockProvenanceKind = "human" | "ai" | "ai_edited";

export interface BlockProvenance {
  kind: BlockProvenanceKind;
  refs: Array<{ entity_type?: string; entity_id?: string; label?: string }>;
}

export interface DocumentBlock {
  id: string;
  type: "paragraph" | "heading" | "list" | "table" | "quote" | "page_break";
  text?: string | null;
  attrs?: Record<string, unknown>;
  items?: string[];
  head?: string[];
  rows?: string[][];
  provenance?: BlockProvenance;
}
export type AnalysisRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
export type SignalType = "RULE" | "ANOMALY" | "TEMPORAL" | "CROSS_SOURCE" | "NETWORK";
export type SeverityLevel = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
export type CorrelationType = "TEMPORAL" | "CROSS_SOURCE";

// --- Dashboard ---------------------------------------------------------------
export interface DashboardAlertSummary {
  id: Uuid;
  alert_ref: string;
  analysis_run_id: Uuid;
  subject_type: SubjectType;
  subject_id: Uuid;
  score: number;
  priority_level: PriorityLevel;
  title: string;
  status: AlertStatus | string;
  investigation_id: Uuid | null;
  triaged_at: IsoString | null;
  created_at: IsoString;
}

export interface DashboardRecentInvestigation {
  id: Uuid;
  case_ref: string;
  title: string;
  status: InvestigationStatus | string;
  priority: PriorityLevel | string;
  subject_type: SubjectType;
  subject_id: Uuid;
  assigned_to: Uuid | null;
  assigned_to_name: string | null;
  created_by: Uuid;
  created_at: IsoString;
  updated_at: IsoString;
}

export interface DashboardIntelItem {
  id: Uuid;
  title: string;
  report_date: string;
  ingestion_date: IsoString;
  status: string;
  info_category: string;
  subject_type: SubjectType;
  subject_id: Uuid;
  subject_name: string;
}

export interface Dashboard {
  generated_at: IsoString;
  alerts: {
    total: number;
    by_status: Record<string, number>;
    priority_distribution: Record<string, number>;
    recent: DashboardAlertSummary[];
  };
  investigations: {
    total: number;
    open: number;
    by_status: Record<string, number>;
    recent: DashboardRecentInvestigation[];
  };
  intelligence: {
    reports_total: number;
    new_reports: number;
    recent: DashboardIntelItem[];
  };
  analysis: {
    runs_total: number;
    recent: AnalysisRunSummary[];
  };
  entities: {
    athletes_total: number;
    intelligence_sources_total: number;
  };
}

// --- Analysis ----------------------------------------------------------------
export interface AnalysisRunSummary {
  run_id: Uuid;
  started_at: IsoString;
  finished_at: IsoString | null;
  status: AnalysisRunStatus | string;
  model: string;
  model_version: string;
  rule_version: number;
  feature_version: number;
  result_count: number;
  error: string | null;
}

export interface AnalysisRunConfig {
  temporal_window_days: number;
  cross_source_window_days: number;
  rule_version: number;
  feature_version: number;
  alert_threshold: PriorityLevel | string;
  recent_window_days: number;
  isolation_forest: {
    n_estimators: number;
    contamination: number;
    random_state: number;
    model_version: string;
  };
}

export interface AnalysisRunDetail extends AnalysisRunSummary {
  config: AnalysisRunConfig;
  result_counts: {
    features: number;
    rules: number;
    anomalies: number;
    correlations: number;
    network: number;
    priority: number;
  };
}

export interface RunCreate {
  subject_ids?: Uuid[];
  alert_threshold?: PriorityLevel | string;
  temporal_window_days?: number;
  cross_source_window_days?: number;
}

export interface SignalFeature {
  subject_id: Uuid;
  feature_id: string;
  feature_version: number;
  value: number;
  source_fields: Record<string, unknown>;
}

export interface RuleResult {
  id: Uuid;
  subject_id: Uuid;
  rule_id: string;
  rule_version: number;
  name: string;
  severity: SeverityLevel;
  weight: number;
  triggered: boolean;
  detail: Record<string, unknown>;
  expression: string;
}

export interface AnomalyContribution {
  contribution: number;
  std_value: number;
  value: number;
}

export interface AnomalyResult {
  id: Uuid;
  subject_id: Uuid;
  raw_score: number;
  normalized_score: number;
  is_anomaly: boolean;
  contributions: Record<string, AnomalyContribution>;
  model_version: string;
  feature_version: number;
}

export interface CorrelationResult {
  id: Uuid;
  subject_id: Uuid;
  correlation_type: CorrelationType | string;
  window_days: number;
  score: number;
  signal_count: number;
  category_count: number;
  signal_ids: Uuid[];
  description: string;
}

export interface NetworkResult {
  id: Uuid;
  subject_id: Uuid;
  degree: number;
  weighted_degree: number;
  relationship_diversity: number;
  connected_priority_count: number;
  score: number;
  detail: {
    neighbors: string[];
    connected_high_priority: string[];
    high_priority_threshold: number;
  };
}

export interface PriorityComponents {
  rule_score: number;
  anomaly_score: number;
  cross_source_score: number;
  temporal_score: number;
  network_score: number;
  source_quality_score: number;
  weights: {
    rule: number;
    anomaly: number;
    correlation: number;
    temporal: number;
    network: number;
    source_quality: number;
  };
}

export interface PriorityResult {
  id: Uuid;
  subject_id: Uuid;
  overall_score: number;
  priority_level: PriorityLevel | string;
  rule_score: number;
  anomaly_score: number;
  correlation_score: number;
  temporal_score: number;
  network_score: number;
  source_quality_score: number;
  explanation: string;
  components: PriorityComponents;
}

// --- Alerts ------------------------------------------------------------------
export interface AlertList {
  count: number;
  alerts: DashboardAlertSummary[];
}

export interface AlertSignal {
  id: Uuid;
  signal_type: SignalType | string;
  signal_id: Uuid;
  contributed: boolean;
  result: RuleResult | AnomalyResult | CorrelationResult | NetworkResult;
}

export interface AlertDetail {
  alert: DashboardAlertSummary;
  priority: PriorityResult;
  signals: AlertSignal[];
  features: SignalFeature[];
  traceable_chain: string[];
}

export interface TriageNoteBody {
  note?: string | null;
}

export interface ConvertBody {
  priority?: PriorityLevel | string;
  assigned_to?: Uuid | null;
  title?: string;
  note?: string | null;
}

export interface ConvertResponse {
  alert: DashboardAlertSummary;
  investigation: {
    id: Uuid;
    case_ref: string;
    title: string;
    status: InvestigationStatus | string;
    priority: PriorityLevel | string;
  };
}

// --- Investigations ----------------------------------------------------------
export interface InvestigationSummary {
  id: Uuid;
  case_ref: string;
  title: string;
  status: InvestigationStatus | string;
  priority: PriorityLevel | string;
  subject_type: SubjectType;
  subject_id: Uuid;
  originating_alert_id: Uuid | null;
  assigned_to: Uuid | null;
  assigned_to_name: string | null;
  created_by: Uuid;
  created_at: IsoString;
  updated_at: IsoString;
}

export interface InvestigationList {
  count: number;
  investigations: InvestigationSummary[];
}

export interface InvestigationOriginatingAlert {
  alert_id: Uuid;
  alert_ref: string;
  priority_level: PriorityLevel | string;
  score: number;
  created_at: IsoString;
}

export interface InvestigationOverview {
  investigation: InvestigationSummary;
  subject_label: string;
  originating_alert: InvestigationOriginatingAlert | null;
  counts: {
    alerts: number;
    evidence: number;
    tasks: number;
    notes: number;
    findings: number;
    reports: number;
  };
}

export interface InvestigationCreateBody {
  title: string;
  description?: string | null;
  priority?: PriorityLevel | string;
  subject_type: SubjectType | string;
  subject_id: Uuid;
  originating_alert_id?: Uuid | null;
  assigned_to?: Uuid | null;
}

export interface InvestigationPatchBody {
  title?: string;
  description?: string | null;
  priority?: PriorityLevel | string;
}

export interface AssignmentBody {
  assigned_to?: Uuid | null;
  note?: string | null;
}

export interface TimelineEvent {
  event_type: string;
  occurred_at: IsoString;
  source: string;
  related_entity: string;
  relevance: string;
  record_id: Uuid;
  origin: string;
  summary: string;
}

export interface InvestigationTimeline {
  count: number;
  timeline: TimelineEvent[];
}

export type TimelineEventType =
  | "MANUAL"
  | "MEETING"
  | "INTERVIEW"
  | "SEARCH"
  | "OBSERVATION"
  | "COMMUNICATION"
  | "LAB_RESULT"
  | "OTHER";

export interface TimelineEntryBody {
  occurred_at: IsoString | string;
  event_type?: TimelineEventType | string | null;
  summary: string;
  source?: string | null;
}

// --- Evidence -----------------------------------------------------------------
export interface EvidenceIntegrity {
  algorithm: string;
  canonical_form: string;
  value: string;
  verified: boolean;
}

export interface EvidenceItem {
  id: Uuid;
  investigation_id: Uuid;
  title: string;
  description: string | null;
  evidence_type: EvidenceType | string;
  source: string | null;
  classification: string;
  sensitivity: SensitivityLevel | string;
  version: number;
  item_date: string | null;
  relationship_to_case: string | null;
  integrity: EvidenceIntegrity;
  deleted: boolean;
  deleted_at: IsoString | null;
}

export interface EvidenceList {
  count: number;
  evidence: EvidenceItem[];
}

export interface EvidenceBody {
  title: string;
  description?: string | null;
  evidence_type: EvidenceType | string;
  source?: string | null;
  classification?: string | null;
  sensitivity?: SensitivityLevel | string;
  item_date?: string | null;
  relationship_to_case?: string | null;
}

export interface EvidencePatchBody extends EvidenceBody {
  change_reason?: string;
}

export interface EvidenceVersion {
  version: number;
  title: string;
  description: string;
  evidence_type: EvidenceType | string;
  source: string;
  classification: string;
  sensitivity: SensitivityLevel | string;
  sha256: string;
  item_date: string | null;
  relationship_to_case: string | null;
  changed_by: Uuid;
  changed_by_name: string;
  change_reason: string;
  created_at: IsoString;
}

export interface EvidenceVersions {
  evidence_id: Uuid;
  current_version: number;
  count: number;
  versions: EvidenceVersion[];
}

// --- Tasks --------------------------------------------------------------------
export interface TaskItem {
  id: Uuid;
  investigation_id: Uuid;
  title: string;
  description: string | null;
  assigned_to: Uuid | null;
  assigned_to_name: string | null;
  status: TaskStatus | string;
  due_date: string | null;
  created_by: Uuid;
  created_at: IsoString;
  updated_at: IsoString;
}

export interface TaskList {
  count: number;
  tasks: TaskItem[];
}

export interface TaskBody {
  title: string;
  description?: string | null;
  assigned_to?: Uuid | null;
  status?: TaskStatus | string;
  due_date?: string | null;
}

export interface TaskPatchBody {
  title?: string;
  description?: string | null;
  assigned_to?: Uuid | null;
  status?: TaskStatus | string;
  due_date?: string | null;
}

// --- Notes --------------------------------------------------------------------
export interface NoteItem {
  id: Uuid;
  investigation_id: Uuid;
  author_id: Uuid;
  author: string;
  content: string;
  created_at: IsoString;
  updated_at: IsoString;
}

export interface NoteList {
  count: number;
  notes: NoteItem[];
}

export interface NoteBody {
  content: string;
}

// --- Findings -----------------------------------------------------------------
export interface FindingEvidenceLink {
  link_id: Uuid;
  evidence_id: Uuid;
  validity: FindingEvidenceValidity | string;
  created_by: Uuid;
  created_at: IsoString;
}

export interface FindingItem {
  id: Uuid;
  investigation_id: Uuid;
  title: string;
  statement: string;
  supporting_evidence: string | null;
  assessment: string | null;
  confident: boolean;
  author_id: Uuid;
  author: string;
  evidence_links: FindingEvidenceLink[];
  created_at: IsoString;
  updated_at: IsoString;
}

export interface FindingList {
  count: number;
  findings: FindingItem[];
}

export interface FindingBody {
  title: string;
  statement: string;
  supporting_evidence?: string | null;
  assessment?: string | null;
  confident: boolean;
}

export interface FindingPatchBody {
  title?: string;
  statement?: string;
  supporting_evidence?: string | null;
  assessment?: string | null;
  confident?: boolean;
}

export interface FindingEvidenceLinkBody {
  evidence_id: Uuid;
  validity: FindingEvidenceValidity | string;
}

// --- Relationships graph --------------------------------------------------------
export interface RelationshipGraphNode {
  id: Uuid;
  label: string;
  kind: string;
  is_subject: boolean;
}

export interface RelationshipGraphEdge {
  id: Uuid;
  source: Uuid;
  target: Uuid;
  label: string;
  data: {
    relationship_type: string;
    confidence: number;
    start_date: string | null;
    end_date: string | null;
    source: string | null;
    relationship_id: Uuid;
  };
}

export interface RelationshipGraph {
  node_count: number;
  edge_count: number;
  nodes: RelationshipGraphNode[];
  edges: RelationshipGraphEdge[];
  note: string;
}

// --- Audit ----------------------------------------------------------------------
export interface AuditEvent {
  id: Uuid;
  action: string;
  entity_type: string;
  entity_id: Uuid;
  actor: string;
  actor_id: Uuid;
  metadata: Record<string, unknown>;
  timestamp: IsoString;
}

export interface AuditList {
  count: number;
  audit: AuditEvent[];
}

// --- Reports --------------------------------------------------------------------
export interface ReportAuditMetadata {
  version: number;
  recorded_audit_events: number;
  notes_count: number;
  tasks_count: number;
}

export interface ReportSections {
  case_metadata: {
    case_ref: string;
    title: string;
    status: InvestigationStatus | string;
    priority: PriorityLevel | string;
    subject: string;
    originating_alert: unknown;
  };
  purpose: string;
  intelligence: unknown[];
  analytical_signals: unknown[];
  timeline: string[];
  relationships: unknown[];
  evidence: string[];
  findings: string[];
  unresolved_questions: string[];
  outcome: string;
  audit_metadata: ReportAuditMetadata;
}

export interface ReportItem {
  id: Uuid;
  investigation_id: Uuid;
  version: number;
  title: string;
  report_type: ReportType | string;
  status: ReportStatus | string;
  purpose: string | null;
  outcome: string | null;
  sections: ReportSections;
  blocks: DocumentBlock[];
  draft?: DocumentBlock[];
  draft_saved_at?: string | null;
  published_at?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportList {
  count: number;
  reports: ReportItem[];
}

export interface ReportCreateBody {
  title?: string | null;
  purpose?: string | null;
  outcome?: string | null;
  unresolved_questions?: string[] | null;
  report_type?: ReportType | null;
}

export interface ReportPatchBody {
  title?: string;
  purpose?: string | null;
  outcome?: string | null;
  unresolved_questions?: string[] | null;
}

export interface ReportDocumentBody {
  blocks: DocumentBlock[];
  title?: string | null;
  autosave?: boolean;
}

// --- AI -------------------------------------------------------------------------
export interface AiClaim {
  claim_type: string;
  statement: string;
}

export interface AiResponse {
  provider: string;
  operation: string;
  grounded: boolean;
  disclaimer: string;
  content: AiClaim[];
  draft?: ReportSections;
}

export interface SignalExplainBody {
  signal_type?: string;
}

export interface AiSectionResponse {
  section: string;
  label: string;
  provider: string;
  blocks: DocumentBlock[];
}

// --- Intelligence ----------------------------------------------------------------
export interface IntelListItem {
  id: Uuid;
  external_ref: string | null;
  title: string;
  description: string | null;
  report_date: string;
  ingestion_date: IsoString;
  status: string;
  info_category: string;
  reliability: string;
  information_quality: string;
  confidentiality: string;
  is_duplicate: boolean;
  subject_type: SubjectType;
  subject_id: Uuid;
}

export interface IntelligenceList {
  count: number;
  limit: number;
  offset: number;
  reports: IntelListItem[];
}

export interface IntelligenceSource {
  source_id: Uuid;
  source_type: string;
  reliability_default: string;
  confidentiality: string;
  name: string | null;
  is_active: boolean;
}

export interface IntelligenceSourceOption extends IntelligenceSource {
  external_ref: string | null;
}

export interface IntelligenceSourceList {
  count: number;
  limit: number;
  offset: number;
  sources: IntelligenceSourceOption[];
}

export interface IntelCreateBody {
  source_id: Uuid;
  title: string;
  description?: string | null;
  subject_type?: string | null;
  subject_id?: Uuid | null;
  report_date?: string | null;
  reliability?: string | null;
  information_quality?: string | null;
  confidentiality?: string | null;
  status?: string | null;
  info_category?: string | null;
}

export interface IntelDetail extends IntelListItem {
  subject_name: string;
  source: IntelligenceSource;
}

export interface IntelligenceParams {
  subject_id?: Uuid;
  subject_type?: SubjectType | string;
  info_category?: string;
  status?: string;
  source_type?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

// --- Athletes --------------------------------------------------------------------
export interface TeamRef {
  id: Uuid;
  name: string;
}

export interface AthleteSummary {
  id: Uuid;
  external_ref: string;
  full_name: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  nationality: string;
  sport: string;
  discipline: string;
  gender: string;
  status: string;
  team: TeamRef | null;
  created_at: IsoString;
}

export interface AthleteList {
  count: number;
  limit: number;
  offset: number;
  athletes: AthleteSummary[];
}

export interface AthleteDetail extends AthleteSummary {
  counts: Record<string, number>;
}

export interface TestRecord {
  id: Uuid;
  test_date: string;
  test_type: string;
  location: string;
  result_classification: string;
  laboratory_ref: string | null;
}

export interface BiologicalObservation {
  id: Uuid;
  observation_date: string;
  marker: string;
  value: number;
  unit: string;
  baseline_deviation: number;
}

export interface WhereaboutEvent {
  id: Uuid;
  event_date: string;
  event_type: string;
  expected_location: string;
  observed_location: string | null;
  status: string;
}

export interface TravelEvent {
  id: Uuid;
  event_date: string;
  origin: string;
  destination: string;
  event_type: string;
}

export interface TimelineMarker {
  date: string;
  kind: string;
  label: string;
  id: Uuid;
}

export interface AthleteIntelItem {
  id: Uuid;
  title: string;
  report_date: string;
  ingestion_date: IsoString;
  status: string;
  info_category: string;
  reliability: string;
  confidentiality: string;
}

// --- Support persons ---------------------------------------------------------------
export interface SupportPersonSummary {
  id: Uuid;
  name: string;
  external_ref: string;
  support_role: string;
  organization: string;
  organization_id: Uuid;
  country: string;
  status: string;
  created_at: IsoString;
}

export interface SupportPersonList {
  count: number;
  limit: number;
  offset: number;
  support_persons: SupportPersonSummary[];
}

// --- Relationships ------------------------------------------------------------------
export type RelationshipEntityType =
  | "ATHLETE"
  | "SUPPORT_PERSON"
  | "TEAM"
  | "ORGANIZATION"
  | "PROVIDER"
  | "SUPPLEMENT"
  | "EVENT"
  | "COMPETITION"
  | "LOCATION"
  | "SOURCE";

export type GraphRole =
  | "ATHLETE" | "COACH" | "TRAINER" | "MEDICAL_PROFESSIONAL" | "MANAGER"
  | "AGENT" | "SUPPLIER" | "FEDERATION_OFFICIAL" | "TEAM" | "PROVIDER"
  | "EVENT" | "SOURCE" | "LOCATION" | "ORGANIZATION";

export interface NodeFeature {
  id: Uuid;
  entity_type: string;
  entity_id: Uuid;
  graph_role: string | null;
  verification: string | null;
  notes: string | null;
  position_x: number | null;
  position_y: number | null;
  created_at: IsoString;
}

export interface NodeFeaturesResponse {
  count: number;
  features: NodeFeature[];
}

export interface RoleListResponse {
  count: number;
  roles: string[];
}

export interface NodeDetail {
  id: Uuid;
  entity_type: string;
  name: string;
  external_ref: string | null;
  graph_role: string | null;
  verification: string | null;
  degree: number;
  relationships: Array<{
    id: Uuid;
    relationship_type: string;
    other_entity_type: string;
    other_entity_id: Uuid;
    other_name: string;
    confidence: number | null;
  }>;
  intel_count: number;
  investigation_count: number;
}

export interface RelationshipDetail {
  id: Uuid;
  relationship_type: string;
  from_entity_type: string;
  from_entity_id: Uuid;
  from_name: string | null;
  from_role: string | null;
  to_entity_type: string;
  to_entity_id: Uuid;
  to_name: string | null;
  to_role: string | null;
  start_date: string | null;
  end_date: string | null;
  confidence: number | null;
  frequency: string | null;
  notes: string | null;
  verification: string;
  status: string;
  deleted: boolean;
  source_id: Uuid | null;
  metadata: Record<string, unknown> | null;
  provenance: {
    source: { id: Uuid; name: string; source_type: string; reliability_default: string } | null;
    created_by_actor: { id: Uuid; name: string } | null;
    created_at: string | null;
  } | null;
  related_intel: { count: number; titles: string[] };
  related_timeline: { count: number };
  related_investigations: Array<{ id: Uuid; case_ref: string; title: string; status: string }>;
  created_at: IsoString;
  updated_at: IsoString;
}

export interface RelationshipDetailList {
  count: number;
  relationships: RelationshipDetail[];
}

export interface NodeCreateBody {
  entity_type: string;
  name: string;
  external_ref?: string;
  graph_role?: string;
  sport?: string;
  country?: string;
  city?: string;
  event_type?: string;
  start_date?: string;
  end_date?: string;
  location?: string;
  level?: string;
  source_type?: string;
  reliability?: string;
}

export interface RelationshipUpdateBody {
  relationship_type?: string;
  confidence?: number;
  start_date?: string | null;
  end_date?: string | null;
  frequency?: string;
  notes?: string;
  verification?: string;
  source_id?: string;
}

export interface NodeUpdateBody {
  graph_role?: string;
  verification?: string;
  notes?: string;
}

export interface RelationshipItem {
  id: Uuid;
  relationship_type: string;
  from_entity_type: SubjectType;
  from_entity_id: Uuid;
  from_name: string;
  to_entity_type: SubjectType;
  to_entity_id: Uuid;
  to_name: string;
  start_date: string | null;
  end_date: string | null;
  confidence: number;
  metadata: Record<string, unknown> | null;
  status: string;
  created_at: IsoString;
}

export interface RelationshipTypeSummary {
  name: string;
  description: string | null;
}

export interface RelationshipTypeList {
  count: number;
  types: RelationshipTypeSummary[];
}

export interface RelationshipCreateBody {
  from_entity_type: RelationshipEntityType | SubjectType | string;
  from_entity_id: Uuid;
  to_entity_type: RelationshipEntityType | SubjectType | string;
  to_entity_id: Uuid;
  relationship_type: string;
  start_date?: string | null;
  end_date?: string | null;
  confidence?: number | null;
  source_id?: Uuid | null;
  frequency?: string;
  notes?: string;
  verification?: string;
}

export interface SubjectOption {
  id: Uuid;
  label: string;
  external_ref: string | null;
}

export interface SubjectOptionsList {
  entity_type: string;
  count: number;
  options: SubjectOption[];
}

export interface RelationshipList {
  count: number;
  limit: number;
  offset: number;
  relationships: RelationshipItem[];
}

export interface RelationshipParams {
  entity_type?: SubjectType | string;
  entity_id?: Uuid;
  relationship_type?: string;
  verification?: string;
  confidence_min?: number;
  include_deleted?: boolean;
  limit?: number;
  offset?: number;
}

export interface AlertListParams {
  run_id?: Uuid;
  subject_id?: Uuid;
  status?: string | null;
}

export interface InvestigationListParams {
  status?: string | null;
  subject_id?: Uuid;
  assigned_to?: Uuid;
}

export interface AthleteListParams {
  q?: string;
  sport?: string;
  nationality?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface SupportPersonListParams {
  q?: string;
  support_role?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface AnalysisRunParams {
  limit?: number;
  status?: string | null;
}

// --- Import gate (checkpoint 1005) ------------------------------------------
export type ImportStatus =
  | "" | "UPLOADED" | "PARSED" | "VALIDATED" | "COMMITTED" | "PARTIAL" | "FAILED" | "CANCELED";

export type ImportRowStatus =
  | "READY" | "REVIEW" | "DUPLICATE" | "INVALID" | "IMPORTED" | "REJECTED";

export interface ImportEntityMatch {
  subject_type: string;
  subject_id: string;
  label: string;
  method: "EXACT_REF" | "EXACT_NAME";
}

export interface ImportSummary {
  total: number;
  ready: number;
  review: number;
  duplicates: number;
  invalid: number;
  imported: number;
  rejected: number;
  parsing_warnings?: string[];
}

export interface DataImportItem {
  id: Uuid;
  name: string;
  target: string;
  source_kind: "FILE" | "PASTE";
  format: string;
  source_filename: string | null;
  file_hash: string | null;
  file_size: number;
  sheet_name: string | null;
  columns: string[];
  sheets: string[];
  structure: string;
  status: ImportStatus;
  progress: number;
  column_mapping: Record<string, string>;
  mappable_fields: string[];
  inferred_types: Record<string, string>;
  summary: ImportSummary;
  error_message: string | null;
  created_at: string | null;
  validated_at: string | null;
  committed_at: string | null;
  canceled_at: string | null;
  created_by: Uuid | null;
  preview?: ImportRowItem[];
}

export interface ImportRowItem {
  row_number: number;
  status: ImportRowStatus;
  original: Record<string, unknown>;
  normalized: Record<string, unknown>;
  errors: string[];
  warnings: string[];
  dedupe_key: string | null;
  entity_match: ImportEntityMatch | null;
  report_id: Uuid | null;
}

export interface ImportListParams {
  status?: ImportStatus;
  q?: string;
  own_only?: boolean;
  limit?: number;
  offset?: number;
}

export interface ImportList {
  count: number;
  limit: number;
  offset: number;
  imports: DataImportItem[];
}

export interface ImportRowsPage {
  count: number;
  limit: number;
  offset: number;
  import_id: Uuid;
  rows: ImportRowItem[];
}

export interface PasteImportRequest {
  name: string;
  content: string;
}

// --- OSINT gate (checkpoint 1006) ------------------------------------------
export type OsintHealth = "ACTIVE" | "DEGRADED" | "FAILED" | "RATE_LIMITED" | "DISABLED";
export type OsintAuthority =
  | "OFFICIAL" | "PUBLIC_NEWS" | "PUBLIC_SOCIAL" | "ARCHIVAL" | "COMMERCIAL";
export type OsintClaimVerification =
  | "UNREVIEWED" | "REVIEWED" | "CORROBORATED" | "DISPUTED" | "REJECTED" | "PROMOTED_TO_EVIDENCE";

export interface OsintConnectorInfo {
  connector_type: string;
  source_kind: string | null;
  search_driven: boolean;
}

export interface OsintConnectorList {
  count: number;
  connectors: OsintConnectorInfo[];
}

export interface OsintSourceItem {
  id: string;
  source_id: string;
  name: string;
  connector_type: string;
  url: string;
  authority: OsintAuthority | string;
  jurisdiction: string | null;
  enabled: boolean;
  poll_frequency_min: number | null;
  rate_limit_per_min: number;
  health: OsintHealth | string;
  consecutive_failures: number;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_failure_reason: string | null;
  connector_kind: string | null;
}

export interface OsintSourceList {
  count: number;
  limit: number;
  offset: number;
  sources: OsintSourceItem[];
}

export interface OsintSourceHealth {
  source_id: string;
  source_ref: string;
  health: OsintHealth | string;
  consecutive_failures: number;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_failure_reason: string | null;
  enabled: boolean;
}

export interface OsintSourceCreateBody {
  source_id: string;
  name: string;
  connector_type: string;
  url: string;
  authority?: OsintAuthority | string;
  jurisdiction?: string | null;
  enabled?: boolean;
  poll_frequency_min?: number | null;
  rate_limit_per_min?: number;
  extra_config?: Record<string, unknown> | null;
}

export interface OsintSourcePatchBody {
  name?: string;
  url?: string;
  authority?: OsintAuthority | string;
  jurisdiction?: string | null;
  enabled?: boolean;
  poll_frequency_min?: number | null;
  rate_limit_per_min?: number;
  extra_config?: Record<string, unknown> | null;
}

export interface OsintMention {
  id: string;
  subject_type: string;
  subject_id: string;
  subject_label: string;
  match_kind: "EXACT" | "CONTAINS";
}

export interface OsintClaimItem {
  id: string;
  record_id: string | null;
  subject_type: string | null;
  subject_id: string | null;
  subject_label: string | null;
  predicate: string;
  object_value: string;
  confidence: number | null;
  verification: OsintClaimVerification | string;
  notes: string | null;
  created_by: string | null;
  created_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface OsintRecordItem {
  id: string;
  source_id: string;
  source: string;
  source_type: string;
  authority_level: OsintAuthority | string;
  title: string;
  publisher: string | null;
  author: string | null;
  source_url: string | null;
  canonical_url: string | null;
  published_at: string | null;
  retrieved_at: string;
  content_hash: string | null;
  language: string | null;
  jurisdiction: string | null;
  extraction_method: string;
  is_duplicate: boolean;
  duplicate_reason: string | null;
  duplicate_of: string | null;
  syndication_group: string | null;
  terms_matched: boolean;
}

export interface OsintRecordList {
  count: number;
  limit: number;
  offset: number;
  records: OsintRecordItem[];
}

export type OsintRecordDetail = Omit<OsintRecordItem, "source"> & {
  source: OsintSourceItem;
  content: string | null;
  mentions: OsintMention[];
  claims: OsintClaimItem[];
  promoted_reports: number;
};

export interface OsintDedupeCluster {
  record_id: string;
  syndication_group: string | null;
  member_count: number;
  independent_sources: number;
  publishers: string[];
  members: OsintRecordItem[];
}

export interface OsintCollectSummary {
  source_id: string;
  source_name: string;
  health: OsintHealth | string;
  ok: boolean;
  error: string | null;
  new_records: number;
  duplicates: number;
  mentions: number;
  stored: Array<{ id: string; title: string; duplicate: boolean; reason: string | null }>;
  elapsed_ms?: number;
}

export interface OsintCollectResponse extends OsintCollectSummary {
  requested_by: string;
  requested_at: string;
}

export interface OsintTargetedResponse {
  terms: string;
  requested_by: string;
  requested_at: string;
  sources_run: number;
  results: OsintCollectSummary[];
}

export interface OsintCollectBody {
  terms?: string | null;
  days?: number | null;
  max_records?: number;
}

export interface OsintTargetedBody {
  terms: string;
  days?: number | null;
  max_records?: number;
  source_ids?: string[] | null;
}

export interface OsintRecordParams {
  source_id?: string;
  q?: string;
  authority?: string;
  date_from?: string;
  date_to?: string;
  include_duplicates?: boolean;
  limit?: number;
  offset?: number;
}

export interface OsintPromoteBody {
  subject_type?: string | null;
  subject_id?: string | null;
  confidence?: number | null;
}

export interface OsintPromoteResponse {
  ok: boolean;
  report_id: string;
  osint_record_id: string;
  title: string;
  source_id: string;
}

export interface OsintClaimCreateBody {
  subject_type?: string | null;
  subject_id?: string | null;
  subject_label?: string | null;
  predicate: string;
  object_value: string;
  confidence?: number | null;
  notes?: string | null;
}

export interface OsintClaimReviewBody {
  verification: OsintClaimVerification | string;
  notes?: string | null;
  confidence?: number | null;
}
