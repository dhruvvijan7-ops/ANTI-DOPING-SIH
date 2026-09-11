import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/auth";
import { RelationshipGraphView } from "@/features/relationships/RelationshipGraph";

const H = vi.hoisted(() => ({
  updatePosition: vi.fn(),
  nodeDetail: null as null | unknown,
  edgeDetail: null as null | unknown,
}));

vi.mock("@/lib/api/queries", () => ({
  useUpdateNodePositionMutation: () => ({ mutate: H.updatePosition, isPending: false }),
  useNodeDetailQuery: () => ({ data: H.nodeDetail, isLoading: false, isError: false }),
  useRelationshipDetailQuery: () => ({ data: H.edgeDetail, isLoading: false, isError: false }),
}));

vi.mock("@xyflow/react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@xyflow/react")>();
  return {
    ...actual,
    ReactFlow: ({ children }: { children: React.ReactNode }) =>
      <div data-testid="react-flow">{children}</div>,
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
    Handle: () => null,
  };
});

const graph = {
  node_count: 2,
  edge_count: 1,
  nodes: [
    { id: "A-1", label: "Alice A", kind: "ATHLETE", is_subject: true },
    { id: "B-1", label: "Bob B", kind: "ATHLETE", is_subject: false },
  ],
  edges: [
    {
      id: "e-1",
      source: "A-1",
      target: "B-1",
      label: "TRAINING_PARTNER",
      data: { relationship_type: "TRAINING_PARTNER", confidence: 0.8, start_date: null, end_date: null, source: null, relationship_id: "r-1" },
    },
  ],
  note: "Closed network shown.",
};

describe("Relationship graph — React Flow view", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    H.updatePosition.mockReset();
    H.nodeDetail = null;
    H.edgeDetail = null;
  });

  function renderGraph() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={qc}>
        <RelationshipGraphView graph={graph} />
      </QueryClientProvider>,
    );
  }

  it("renders the interactive canvas", async () => {
    renderGraph();
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
  });

  it("does not crash when the graph is empty", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RelationshipGraphView graph={{ node_count: 1, edge_count: 0, nodes: [], edges: [], note: "" }} />
      </QueryClientProvider>,
    );
    expect(screen.queryByTestId("react-flow")).not.toBeInTheDocument();
  });
});