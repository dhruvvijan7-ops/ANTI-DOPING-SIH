import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TriagePanel } from "@/features/alerts/TriagePanel";
import type { DashboardAlertSummary } from "@/lib/api/types";
import { useAuthStore } from "@/stores/auth";

const convertSpy = vi.hoisted(() => ({
  mutate: vi.fn(),
  isPending: false,
  isIdle: true,
  isSuccess: false,
  error: null,
  data: undefined,
}));

vi.mock("@/lib/api/queries", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    useConvertAlertMutation: () => convertSpy,
    useDismissAlertMutation: () => convertSpy,
    useEscalateAlertMutation: () => convertSpy,
    useFalsePositiveAlertMutation: () => convertSpy,
    useReviewAlertMutation: () => convertSpy,
  };
});

const alert: DashboardAlertSummary = {
  id: "alert-1",
  alert_ref: "ALERT-2026-0001",
  analysis_run_id: "run-1",
  subject_type: "ATHLETE",
  subject_id: "athlete-1",
  score: 84.5,
  priority_level: "CRITICAL",
  title: "Elevated biomarkers for SYN-ATH-000",
  status: "NEW",
  investigation_id: null,
  triaged_at: null,
  created_at: "2026-09-01T08:00:00Z",
};

const fullPermissions = [
  { key: "alerts:read", name: "Read alerts" },
  { key: "alerts:review", name: "Review alerts" },
  { key: "alerts:dismiss", name: "Dismiss alerts" },
  { key: "alerts:convert", name: "Convert alerts" },
  { key: "investigations:assign", name: "Assign investigations" },
];

function renderPanel(userPermissions = fullPermissions, overrides: Partial<DashboardAlertSummary> = {}) {
  useAuthStore.getState().setSession("tok", {
    id: "u-1",
    username: "ana",
    full_name: "Ana Analyst",
    email: "ana@verity.test",
    is_active: true,
    role: { key: "INTELLIGENCE_ANALYST", name: "Intelligence Analyst", permissions: userPermissions },
  } as never);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <TriagePanel alert={{ ...alert, ...overrides }} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TriagePanel", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    convertSpy.mutate.mockReset();
  });

  it("shows triage actions for a reviewer with convert permission", () => {
    renderPanel();
    expect(screen.getByRole("button", { name: /mark reviewed/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /convert to investigation/i })).toBeInTheDocument();
  });

  it("hides actions the user is not permitted to perform", () => {
    renderPanel([{ key: "alerts:review", name: "Review alerts" }]);
    expect(screen.getByRole("button", { name: /mark reviewed/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /convert to investigation/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dismiss/i })).not.toBeInTheDocument();
  });

  it("links straight to an existing case when the alert was converted", () => {
    renderPanel(fullPermissions, { investigation_id: "inv-42" });
    expect(screen.getByRole("link", { name: /open linked case/i })).toHaveAttribute("href", "/investigations/inv-42");
    expect(screen.queryByRole("button", { name: /convert to investigation/i })).not.toBeInTheDocument();
  });

  it("submits the convert mutation with the chosen priority and cleaned title", async () => {
    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: /convert to investigation/i }));
    await userEvent.type(screen.getByLabelText(/title override/i), "SYN-ATH-000 review   ");
    await userEvent.selectOptions(screen.getByLabelText(/^priority/i), "HIGH");
    await userEvent.click(screen.getByRole("button", { name: /create investigation/i }));
    await waitFor(() => {
      expect(convertSpy.mutate).toHaveBeenCalledWith({
        alertId: "alert-1",
        body: {
          priority: "HIGH",
          title: "SYN-ATH-000 review",
          note: null,
          assigned_to: null,
        },
      });
    });
  });
});