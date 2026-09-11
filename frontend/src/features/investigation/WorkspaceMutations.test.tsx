import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { InvTimeline } from "@/features/investigation/InvTimeline";
import { InvIntelligence } from "@/features/investigation/InvIntelligence";
import { InvRelationships } from "@/features/investigation/InvRelationships";
import { useAuthStore } from "@/stores/auth";

// Module-level mutable data + spies the mocked hooks serve to the components.
const H = vi.hoisted(() => ({
  timelineList: null as null | { count: number; timeline: Array<{ event_type: string; occurred_at: string; source: string; related_entity: string; relevance: string; record_id: string; origin: string; summary: string }> },
  timelineMutate: vi.fn(),
  intelList: null as null | { count: number; intelligence: Array<{ id: string; title: string; info_category: string; report_date: string | null; status: string }> },
  sourcesList: null as null | { count: number; limit: number; offset: number; sources: Array<{ source_id: string; source_type: string; reliability_default: string; confidentiality: string; name: string | null; is_active: boolean; external_ref: string | null }> },
  overview: null as null | unknown,
  intelMutate: vi.fn(),
  relGraph: null as null | { node_count: number; edge_count: number; nodes: unknown[]; edges: unknown[]; note: string },
  relTypes: null as null | { count: number; types: Array<{ name: string; description: string | null }> },
  subjectOptions: null as null | { entity_type: string; count: number; options: Array<{ id: string; label: string; external_ref: string | null }> },
  relMutate: vi.fn(),
  relSources: null as null | { count: number; limit: number; offset: number; sources: Array<{ source_id: string; source_type: string; reliability_default: string; confidentiality: string; name: string | null; is_active: boolean; external_ref: string | null }> },
}));

vi.mock("@/lib/api/queries", () => ({
  useInvestigationTimelineQuery: () => ({ data: H.timelineList, isLoading: false, isError: false, refetch: vi.fn() }),
  useCreateTimelineEntryMutation: () => ({ mutate: H.timelineMutate, isPending: false }),
  useInvestigationIntelQuery: () => ({ data: H.intelList, isLoading: false, isError: false, refetch: vi.fn() }),
  useIntelligenceSourcesQuery: () => ({ data: H.sourcesList, isLoading: false, isError: false }),
  useInvestigationOverviewQuery: () => ({ data: H.overview, isLoading: false, isError: false, refetch: vi.fn() }),
  useCreateIntelligenceMutation: () => ({ mutate: H.intelMutate, isPending: false }),
  useInvestigationRelationshipsQuery: () => ({ data: H.relGraph, isLoading: false, isError: false, refetch: vi.fn() }),
  useRelationshipTypesQuery: () => ({ data: H.relTypes, isLoading: false, isError: false }),
  useSubjectOptionsQuery: () => ({ data: H.subjectOptions, isLoading: false, isError: false }),
  useCreateRelationshipMutation: () => ({ mutate: H.relMutate, isPending: false }),
  useUpdateNodePositionMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useNodeDetailQuery: () => ({ data: undefined, isLoading: false, isError: false }),
  useRelationshipDetailQuery: () => ({ data: undefined, isLoading: false, isError: false }),
}));

const PERMS = (keys: string[]) =>
  keys.map((key) => ({ id: "p-1", key, description: null }));

function session(permissions: string[]) {
  useAuthStore.getState().setSession("tok", {
    id: "u-1",
    username: "pers",
    full_name: "Pers Analyst",
    email: "pers@verity.test",
    is_active: true,
    role: { key: "INTELLIGENCE_ANALYST", name: "Intelligence Analyst", permissions: PERMS(permissions) },
  } as never);
}

const overview = {
  investigation: {
    id: "case-1",
    case_ref: "INV-2026-0001",
    title: "Alice A review",
    status: "OPEN",
    priority: "HIGH",
    subject_type: "ATHLETE",
    subject_id: "ath-1",
    originating_alert_id: null,
    assigned_to: null,
    assigned_to_name: null,
    created_by: "u-1",
    created_at: "2026-09-01T08:00:00Z",
    updated_at: "2026-09-01T08:00:00Z",
  },
  subject_label: "Alice A",
  originating_alert: null,
  counts: { alerts: 0, evidence: 0, tasks: 0, notes: 0, findings: 0, reports: 0 },
};

describe("Workspace mutations — timeline", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    H.timelineMutate.mockReset();
    H.timelineList = null;
  });

  function renderTimeline() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <InvTimeline id="case-1" />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("submits a manual entry through the mounted create hook", async () => {
    H.timelineList = {
      count: 1,
      timeline: [{ event_type: "MEETING", occurred_at: "2026-09-02T10:00:00Z", source: "CASE WORK", related_entity: "ath-1", relevance: "CONTEXT", record_id: "e-1", origin: "timeline_events", summary: "Initial interview with coach" }],
    };
    session(["investigations:modify"]);
    renderTimeline();

    expect(await screen.findByText(/initial interview with coach/i)).toBeInTheDocument();
    expect(screen.getByText("Manual entry")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /add entry/i }));
    await userEvent.type(screen.getByLabelText(/summary/i), "Follow-up DNA sample logged");
    const [, submitTimeline] = screen.getAllByRole("button", { name: /add entry/i });
    await userEvent.click(submitTimeline!);

    await waitFor(() => {
      expect(H.timelineMutate).toHaveBeenCalledTimes(1);
    });
    const [args] = H.timelineMutate.mock.calls[0] as [{ investigationId: string; body: { summary: string; event_type: string; source: string | null; occurred_at: string } }];
    expect(args.investigationId).toBe("case-1");
    expect(args.body.summary).toBe("Follow-up DNA sample logged");
    expect(args.body.event_type).toBe("MANUAL");
    expect(args.body.source).toBeNull();
    expect(args.body.occurred_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("hides the add-entry button for a read-only user", async () => {
    H.timelineList = { count: 0, timeline: [] };
    session(["investigations:read"]);
    renderTimeline();
    await screen.findByText(/no timeline events/i);
    expect(screen.queryByRole("button", { name: /add entry/i })).not.toBeInTheDocument();
  });
});

describe("Workspace mutations — intelligence", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    H.intelMutate.mockReset();
    H.intelList = null;
    H.sourcesList = null;
    H.overview = null;
  });

  function renderIntel() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <InvIntelligence id="case-1" />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("submits a manual intelligence record linked to the case subject", async () => {
    H.intelList = { count: 0, intelligence: [] };
    H.sourcesList = {
      count: 1,
      limit: 200,
      offset: 0,
      sources: [{ source_id: "src-1", source_type: "OSINT", reliability_default: "B", confidentiality: "OPEN", name: "Source One", is_active: true, external_ref: "SRC-1" }],
    };
    H.overview = overview;
    session(["intelligence:create"]);
    renderIntel();

    await userEvent.click(await screen.findByRole("button", { name: /add intelligence/i }));
    await userEvent.selectOptions(screen.getByLabelText(/^source/i), "src-1");
    await userEvent.type(screen.getByLabelText(/title/i), "Reported in-person admission");
    await userEvent.click(screen.getByRole("button", { name: /record intelligence/i }));

    await waitFor(() => {
      expect(H.intelMutate).toHaveBeenCalledTimes(1);
    });
    const [args] = H.intelMutate.mock.calls[0] as [{ source_id: string; title: string; subject_type: string; subject_id: string; info_category: string; status: string; confidentiality: string; reliability: string | null; report_date: string | null; description: string | null }];
    expect(args.source_id).toBe("src-1");
    expect(args.title).toBe("Reported in-person admission");
    expect(args.subject_type).toBe("ATHLETE");
    expect(args.subject_id).toBe("ath-1");
    expect(args.info_category).toBe("SOURCE_OBSERVATION");
    expect(args.status).toBe("NEW");
    expect(args.confidentiality).toBe("INTERNAL");
  });

  it("requires a source selection", async () => {
    H.intelList = { count: 0, intelligence: [] };
    H.sourcesList = {
      count: 1,
      limit: 200,
      offset: 0,
      sources: [{ source_id: "src-1", source_type: "OSINT", reliability_default: "B", confidentiality: "OPEN", name: "Source One", is_active: true, external_ref: "SRC-1" }],
    };
    H.overview = overview;
    session(["intelligence:create"]);
    renderIntel();

    await userEvent.click(await screen.findByRole("button", { name: /add intelligence/i }));
    await userEvent.type(screen.getByLabelText(/title/i), "Unlinked report");
    await userEvent.click(screen.getByRole("button", { name: /record intelligence/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(H.intelMutate).not.toHaveBeenCalled();
  });

  it("hides the add-intelligence button for a read-only user", async () => {
    H.intelList = { count: 0, intelligence: [] };
    session(["investigations:read"]);
    renderIntel();
    await screen.findByText(/no intelligence linked/i);
    expect(screen.queryByRole("button", { name: /add intelligence/i })).not.toBeInTheDocument();
  });
});

describe("Workspace mutations — relationships", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    H.relMutate.mockReset();
    H.relGraph = null;
    H.relTypes = null;
    H.subjectOptions = null;
    H.relSources = null;
    H.overview = null;
  });

  function renderRel() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <InvRelationships id="case-1" />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("submits a relationship anchored on the case subject", async () => {
    H.relGraph = { node_count: 1, edge_count: 0, nodes: [], edges: [], note: "Closed network shown." };
    H.relTypes = { count: 1, types: [{ name: "COACH_ATHLETE", description: "Coach-athlete pairing" }] };
    H.subjectOptions = {
      entity_type: "ATHLETE",
      count: 2,
      options: [
        { id: "ath-2", label: "Bob B", external_ref: "ATH-2" },
        { id: "ath-1", label: "Alice A", external_ref: "ATH-1" },
      ],
    };
    H.relSources = { count: 0, limit: 200, offset: 0, sources: [] };
    H.overview = overview;
    session(["investigations:modify"]);
    renderRel();

    await userEvent.click(await screen.findByRole("button", { name: /add relationship/i }));
    await userEvent.selectOptions(screen.getByLabelText(/relationship type/i), "COACH_ATHLETE");
    await userEvent.selectOptions(screen.getByLabelText(/select entity/i), "ath-2");
    await userEvent.click(screen.getByRole("button", { name: /record relationship/i }));

    await waitFor(() => {
      expect(H.relMutate).toHaveBeenCalledTimes(1);
    });
    const [args] = H.relMutate.mock.calls[0] as [{ from_entity_type: string; from_entity_id: string; to_entity_type: string; to_entity_id: string; relationship_type: string; confidence: number; start_date: string | null; end_date: string | null; source_id: string | null }];
    expect(args.from_entity_type).toBe("ATHLETE");
    expect(args.from_entity_id).toBe("ath-1");
    expect(args.to_entity_type).toBe("ATHLETE");
    expect(args.to_entity_id).toBe("ath-2");
    expect(args.relationship_type).toBe("COACH_ATHLETE");
    expect(args.confidence).toBe(0.9);
    expect(args.source_id).toBeNull();
  });

  it("rejects relating the case subject to itself", async () => {
    H.relGraph = { node_count: 1, edge_count: 0, nodes: [], edges: [], note: "" };
    H.relTypes = { count: 1, types: [{ name: "COACH_ATHLETE", description: "Coach-athlete pairing" }] };
    H.subjectOptions = {
      entity_type: "ATHLETE",
      count: 1,
      options: [{ id: "ath-1", label: "Alice A", external_ref: "ATH-1" }],
    };
    H.relSources = { count: 0, limit: 200, offset: 0, sources: [] };
    H.overview = overview;
    session(["investigations:modify"]);
    renderRel();

    await userEvent.click(await screen.findByRole("button", { name: /add relationship/i }));
    await userEvent.selectOptions(screen.getByLabelText(/relationship type/i), "COACH_ATHLETE");
    await userEvent.click(screen.getByRole("button", { name: /record relationship/i }));

    // Self-relation is prevented client-side: no target selected -> validation error.
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(H.relMutate).not.toHaveBeenCalled();
  });
});