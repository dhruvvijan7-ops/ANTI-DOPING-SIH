import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/auth";
import { NodeDetailPanel } from "@/features/relationships/NodeDetailPanel";
import { EdgeDetailPanel } from "@/features/relationships/EdgeDetailPanel";

const H = vi.hoisted(() => ({
  deleteMutate: vi.fn(),
}));

vi.mock("@/lib/api/queries", () => ({
  useDeleteRelationshipMutation: () => ({
    mutate: H.deleteMutate,
    isPending: false,
  }),
}));

const nodeDetail = {
  id: "A-1",
  entity_type: "ATHLETE",
  name: "Alice A",
  external_ref: "ATH-1",
  graph_role: "ATHLETE",
  verification: "UNVERIFIED",
  degree: 1,
  relationships: [{ id: "r-1", relationship_type: "TRAINING_PARTNER", other_entity_type: "ATHLETE", other_entity_id: "B-1", other_name: "Bob B", confidence: 0.8 }],
  intel_count: 2,
  investigation_count: 1,
};

const edgeDetail = {
  id: "r-1",
  relationship_type: "TRAINING_PARTNER",
  from_entity_type: "ATHLETE",
  from_entity_id: "A-1",
  from_name: "Alice A",
  from_role: "ATHLETE",
  to_entity_type: "ATHLETE",
  to_entity_id: "B-1",
  to_name: "Bob B",
  to_role: null,
  start_date: null,
  end_date: null,
  confidence: 0.8,
  frequency: "WEEKLY",
  notes: "Trained together",
  verification: "VERIFIED",
  status: "ACTIVE",
  deleted: false,
  source_id: null,
  metadata: null,
  provenance: {
    source: null,
    created_by_actor: { id: "u-1", name: "Pers Analyst" },
    created_at: "2026-09-01T08:00:00Z",
  },
  related_intel: { count: 1, titles: ["Intel report"] },
  related_timeline: { count: 0 },
  related_investigations: [],
  created_at: "2026-09-01T08:00:00Z",
  updated_at: "2026-09-01T08:00:00Z",
};

describe("Node detail panel", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
  });

  function renderPanel() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={qc}>
        <NodeDetailPanel entityType="ATHLETE" entityId="A-1" detail={nodeDetail} onClose={vi.fn()} />
      </QueryClientProvider>,
    );
  }

  it("shows entity metadata and degree", () => {
    renderPanel();
    expect(screen.getByText("Entity Detail")).toBeInTheDocument();
    expect(screen.getByText("Alice A")).toBeInTheDocument();
    expect(screen.getByText("Connections: 1")).toBeInTheDocument();
    expect(screen.getByText("Intelligence reports: 2")).toBeInTheDocument();
    expect(screen.getByText("Investigations: 1")).toBeInTheDocument();
    expect(screen.getByText(/TRAINING_PARTNER/)).toBeInTheDocument();
  });
});

describe("Edge detail panel", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    H.deleteMutate.mockReset();
  });

  function session(permissions: string[]) {
    useAuthStore.getState().setSession("tok", {
      id: "u-1",
      username: "pers",
      full_name: "Pers Analyst",
      email: "pers@verity.test",
      is_active: true,
      role: { key: "INVESTIGATOR", name: "Investigator", permissions: permissions.map((key) => ({ id: "p-1", key, description: null })) },
    } as never);
  }

  function renderPanel() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={qc}>
        <EdgeDetailPanel detail={edgeDetail} onClose={vi.fn()} />
      </QueryClientProvider>,
    );
  }

  it("shows relationship metadata and provenance", () => {
    session(["investigations:modify"]);
    renderPanel();
    expect(screen.getByText("Relationship Detail")).toBeInTheDocument();
    expect(screen.getByText("TRAINING_PARTNER")).toBeInTheDocument();
    expect(screen.getByText(/Confidence:/)).toBeInTheDocument();
    expect(screen.getByText("Trained together")).toBeInTheDocument();
    expect(screen.getByText(/Pers Analyst/)).toBeInTheDocument();
  });

  it("offers soft-delete for a modifier", async () => {
    session(["investigations:modify"]);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: /delete relationship/i }));
    expect(H.deleteMutate).toHaveBeenCalledWith("r-1");
    confirmSpy.mockRestore();
  });

  it("hides delete for a read-only user", () => {
    session(["investigations:read"]);
    renderPanel();
    expect(screen.queryByRole("button", { name: /delete relationship/i })).not.toBeInTheDocument();
  });
});