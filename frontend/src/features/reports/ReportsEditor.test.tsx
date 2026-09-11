import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReportsEditor } from "@/features/reports";

const H = vi.hoisted(() => {
  const baseReport = {
    id: "rep-1",
    investigation_id: "inv-1",
    version: 1,
    title: "Investigation report",
    report_type: "MANUAL",
    status: "DRAFT",
    purpose: "Assess doping signals",
    outcome: null,
    sections: {},
    blocks: [] as never[],
    draft: null,
    draft_saved_at: null,
    published_at: null,
    created_by: "u-1",
    created_at: "2026-09-01T08:00:00Z",
    updated_at: "2026-09-01T08:00:00Z",
  };
  return {
    report: { ...baseReport },
    saveDocument: vi.fn(() => Promise.resolve({ ...baseReport })),
    updateReport: vi.fn(() => Promise.resolve({ ...baseReport, id: "rep-2", version: 2, status: "DRAFT" })),
    aiDraft: vi.fn(() => Promise.resolve({ ...baseReport, blocks: [{ id: "b-ai1", type: "paragraph", text: "AI draft intro", provenance: { kind: "ai", refs: [] } }] })),
    aiSection: vi.fn(() => Promise.resolve({
      section: "timeline",
      label: "Timeline summary",
      provider: "deterministic",
      blocks: [{ id: "b-ai2", type: "paragraph", text: "Timeline summary content", provenance: { kind: "ai", refs: [] } }],
    })),
    setType: vi.fn(),
    review: vi.fn(() => Promise.resolve({ ...baseReport, status: "IN_REVIEW" })),
    publish: vi.fn(() => Promise.resolve({ ...baseReport, status: "FINAL" })),
    archive: vi.fn(() => Promise.resolve({ ...baseReport, status: "ARCHIVED" })),
    overview: vi.fn(() => Promise.resolve({ investigation: { case_ref: "CASE-001", title: "Target case", status: "OPEN", priority: "HIGH" }, counts: {} })),
  };
});

vi.mock("@/lib/api/queries", () => ({
  useReportDetailQuery: () => ({ data: H.report, isLoading: false, isError: false, error: null, refetch: vi.fn() }),
  useSaveReportDocumentMutation: () => ({ mutateAsync: H.saveDocument, isPending: false }),
  useUpdateReportMutation: () => ({ mutateAsync: H.updateReport, isPending: false }),
  useAiDraftReportMutation: () => ({ mutateAsync: H.aiDraft, isPending: false }),
  useAiSectionReportMutation: () => ({ mutateAsync: H.aiSection, isPending: false }),
  useSetReportTypeMutation: () => ({ mutate: H.setType, isPending: false }),
  useReviewReportMutation: () => ({ mutateAsync: H.review, isPending: false }),
  usePublishReportMutation: () => ({ mutateAsync: H.publish, isPending: false }),
  useArchiveReportMutation: () => ({ mutateAsync: H.archive, isPending: false }),
  useInvestigationOverviewQuery: () => ({ data: { investigation: { case_ref: "CASE-001", title: "Target case", status: "OPEN", priority: "HIGH" }, counts: {} }, isLoading: false }),
  useInvestigationTimelineQuery: () => ({
    data: {
      count: 1,
      timeline: [{ record_id: "t-1", event_type: "OBSERVATION", occurred_at: "2026-09-01T00:00:00Z", source: "Field", related_entity: "Target", relevance: "HIGH", origin: "MANUAL", summary: "Met with coach" }],
    },
    isLoading: false,
  }),
  useEvidenceListQuery: () => ({ data: { items: [] }, isLoading: false }),
  useFindingsQuery: () => ({ data: { items: [] }, isLoading: false }),
  useInvestigationRelationshipsQuery: () => ({ data: { relationships: [] }, isLoading: false }),
}));

function renderEditor() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/investigations/inv-1/reports/rep-1/edit"]}>
        <ReportsEditor investigationId="inv-1" reportId="rep-1" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ReportsEditor", () => {
  beforeEach(() => {
    vi.setSystemTime(new Date("2026-09-10T12:00:00Z"));
    H.report.status = "DRAFT";
    H.report.blocks = [];
    H.report.draft = null;
    H.report.report_type = "MANUAL";
    H.saveDocument.mockReset();
    H.updateReport.mockReset();
    H.aiDraft.mockReset();
    H.aiSection.mockReset();
    H.review.mockReset();
    H.publish.mockReset();
    H.archive.mockReset();
    H.setType.mockReset();
    H.saveDocument.mockImplementation(() => Promise.resolve({ ...H.report }));
    H.updateReport.mockImplementation(() => Promise.resolve({ ...H.report, id: "rep-2", version: 2, status: "DRAFT" }));
    H.aiDraft.mockImplementation(() => Promise.resolve({ ...H.report, blocks: [{ id: "b-ai1", type: "paragraph", text: "AI draft intro", provenance: { kind: "ai", refs: [] } }] }));
    H.aiSection.mockImplementation(() => Promise.resolve({
      section: "timeline",
      label: "Timeline summary",
      provider: "deterministic",
      blocks: [{ id: "b-ai2", type: "paragraph", text: "Timeline summary content", provenance: { kind: "ai", refs: [] } }],
    }));
  });

  it("shows the blank-page empty state for an empty draft", () => {
    renderEditor();
    expect(screen.getByText(/This report is blank/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Report title")).toHaveValue("Investigation report");
  });

  it("adds blocks from the toolbar and types content into the page", async () => {
    const user = userEvent.setup();
    renderEditor();
    await user.click(screen.getByTitle("Heading"));
    const heading = screen.getByPlaceholderText("Heading");
    await user.type(heading, "Executive summary");
    expect(heading).toHaveValue("Executive summary");
    expect(screen.getByText("Block: heading")).toBeInTheDocument();
  });

  it("labels a human block with H provenance", async () => {
    const user = userEvent.setup();
    renderEditor();
    await user.click(screen.getByTitle("Heading"));
    const heading = screen.getByPlaceholderText("Heading");
    await user.type(heading, "Findings");
    // H badge renders for human-authored blocks.
    const badge = screen.getByTitle("Human authored");
    expect(badge).toHaveTextContent("H");
  });

  it("inserts case data from the timeline sidebar", async () => {
    const user = userEvent.setup();
    renderEditor();
    await user.click(screen.getByRole("button", { name: /timeline/i }));
    const item = screen.getByRole("button", { name: /Met with coach/ });
    await user.click(item);
    expect(screen.getByDisplayValue(/Met with coach/)).toBeInTheDocument();
  });

  it("persists the document on Save without autosave", async () => {
    const user = userEvent.setup();
    renderEditor();
    await user.click(screen.getByTitle("Heading"));
    await user.type(screen.getByPlaceholderText("Heading"), "Draft title");
    await user.click(screen.getByRole("button", { name: /save/i }));
    await vi.waitFor(() => {
      expect(H.saveDocument).toHaveBeenCalledWith(
        expect.objectContaining({ investigationId: "inv-1", reportId: "rep-1", body: expect.objectContaining({ autosave: false }) }),
      );
    });
  });

  it("inserts an AI section with an AI provenance badge", async () => {
    const user = userEvent.setup();
    renderEditor();
    const combos = screen.getAllByRole("combobox");
    await user.selectOptions(combos[0] as HTMLSelectElement, "timeline");
    await vi.waitFor(() => {
      expect(screen.getByDisplayValue("Timeline summary content")).toBeInTheDocument();
    });
    const badge = screen.getByTitle("AI generated");
    expect(badge).toHaveTextContent("AI");
  });

  it("regenerates the whole document as an AI draft via the AI draft button", async () => {
    const user = userEvent.setup();
    renderEditor();
    await user.click(screen.getByRole("button", { name: /ai draft/i }));
    await vi.waitFor(() => {
      expect(screen.getByDisplayValue("AI draft intro")).toBeInTheDocument();
    });
  });

  it("locks the editor for a published report and offers a new version", async () => {
    const user = userEvent.setup();
    H.report.status = "FINAL";
    renderEditor();
    expect(screen.getByText(/locked for editing/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Report title")).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /create new version/i }));
    await vi.waitFor(() => {
      expect(H.updateReport).toHaveBeenCalled();
    });
  });
});