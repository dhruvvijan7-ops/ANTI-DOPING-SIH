import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Imports from "@/pages/Imports";
import { useAuthStore } from "@/stores/auth";
import type { DataImportItem, ImportRowsPage, ImportList } from "@/lib/api/types";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const IMPORT_ID = "a59f8f1e-0000-4000-8000-000000000001";

const detail: DataImportItem = {
  id: IMPORT_ID,
  name: "Lab dispatch",
  target: "INTELLIGENCE",
  source_kind: "FILE",
  format: "CSV",
  source_filename: "dispatch.csv",
  file_hash: "abcd1234efgh5678",
  file_size: 486,
  sheet_name: null,
  columns: ["Title", "Report Date", "Athlete ID", "Category"],
  sheets: [],
  structure: "TABULAR",
  status: "VALIDATED",
  progress: 100,
  column_mapping: {
    Title: "title",
    "Report Date": "report_date",
    "Athlete ID": "athlete_ref",
    Category: "info_category",
  },
  mappable_fields: [
    "title",
    "report_date",
    "description",
    "reliability",
    "information_quality",
    "info_category",
    "confidentiality",
    "athlete_ref",
    "athlete_name",
    "external_ref",
    "source_ref",
  ],
  inferred_types: { Title: "text", "Report Date": "date", "Athlete ID": "text", Category: "text" },
  summary: { total: 2, ready: 1, review: 0, duplicates: 0, invalid: 1, imported: 0, rejected: 0 },
  error_message: null,
  created_at: "2026-09-01T08:00:00Z",
  validated_at: "2026-09-01T08:05:00Z",
  committed_at: null,
  canceled_at: null,
  created_by: "u-1",
};

const rowsPage: ImportRowsPage = {
  count: 2,
  limit: 100,
  offset: 0,
  import_id: IMPORT_ID,
  rows: [
    {
      row_number: 1,
      status: "READY",
      original: { Title: "Sighting at lab", "Report Date": "2026-08-01", "Athlete ID": "ATH-0012", Category: "DOPING" },
      normalized: { title: "Sighting at lab", report_date: "2026-08-01", subject_ref: "ATH-0012", info_category: "DOPING" },
      errors: [],
      warnings: [],
      dedupe_key: "k1",
      entity_match: { subject_type: "athlete", subject_id: "ath-0012", label: "Athlete 0012", method: "EXACT_REF" },
      report_id: null,
    },
    {
      row_number: 2,
      status: "INVALID",
      original: { Title: "", "Report Date": "nope", "Athlete ID": "ATH-0999", Category: "DOPING" },
      normalized: { title: "", report_date: null, subject_ref: "ATH-0999", info_category: "DOPING" },
      errors: ["title is required."],
      warnings: [],
      dedupe_key: null,
      entity_match: null,
      report_id: null,
    },
  ],
};

const list: ImportList = { count: 1, limit: 100, offset: 0, imports: [detail] };

const perms = [
  { key: "imports:read", name: "Read imports" },
  { key: "imports:create", name: "Create imports" },
  { key: "imports:commit", name: "Commit imports" },
];

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (method === "POST" && url === "/api/v1/imports/upload") {
      return json(detail);
    }
    if (method === "POST" && url === `/api/v1/imports/${IMPORT_ID}/mapping`) {
      return json(detail);
    }
    if (method === "POST" && url === `/api/v1/imports/${IMPORT_ID}/commit`) {
      return json({ ...detail, status: "COMMITTED", committed_at: "2026-09-01T09:00:00Z" });
    }
    if (url === `/api/v1/imports/${IMPORT_ID}/rows?limit=100`) {
      return json(rowsPage);
    }
    if (url === `/api/v1/imports/${IMPORT_ID}`) {
      return json(detail);
    }
    if (url === "/api/v1/imports?limit=100") {
      return json(list);
    }
    return json({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  }));
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Imports />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Imports page", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    vi.restoreAllMocks();
  });

  it("restricts access without the imports:read permission", () => {
    renderPage();
    expect(screen.getByText(/access restricted/i)).toBeInTheDocument();
    expect(screen.queryByText(/new import/i)).not.toBeInTheDocument();
  });

  it("lists imports and opens the workspace for a selected import", async () => {
    useAuthStore.getState().setSession("tok", {
      id: "u-1",
      username: "ana",
      full_name: "Ana Analyst",
      email: "ana@verity.test",
      is_active: true,
      role: { key: "INTELLIGENCE_ANALYST", name: "Intelligence Analyst", permissions: perms },
    } as never);
    stubFetch();

    renderPage();
    expect(await screen.findByText("Lab dispatch")).toBeInTheDocument();

    const item = screen.getByRole("button", { name: /Lab dispatch/i });
    await userEvent.click(item);

    expect(await screen.findByText(/column mapping & validation/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /apply mapping & validate/i })).toBeInTheDocument();
    expect(await screen.findByText(/sighting at lab/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /commit selected rows/i })).toBeInTheDocument();
  });

  it("commits the selected import", async () => {
    useAuthStore.getState().setSession("tok", {
      id: "u-1",
      username: "ana",
      full_name: "Ana Analyst",
      email: "ana@verity.test",
      is_active: true,
      role: { key: "INTELLIGENCE_ANALYST", name: "Intelligence Analyst", permissions: perms },
    } as never);
    stubFetch();

    renderPage();
    await screen.findByText("Lab dispatch");
    await userEvent.click(screen.getByRole("button", { name: /Lab dispatch/i }));
    await screen.findByRole("button", { name: /commit selected rows/i });

    await userEvent.click(screen.getByRole("button", { name: /commit selected rows/i }));

    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(
        ([input, init]) => String(input).includes("/commit") && init?.method === "POST",
      );
      expect(call).toBeTruthy();
      const body = JSON.parse(String((call![1] as RequestInit).body));
      expect(body.include_statuses).toEqual(["READY"]);
    });
  });

  it("uploads through the multipart upload endpoint", async () => {
    useAuthStore.getState().setSession("tok", {
      id: "u-1",
      username: "ana",
      full_name: "Ana Analyst",
      email: "ana@verity.test",
      is_active: true,
      role: { key: "INTELLIGENCE_ANALYST", name: "Intelligence Analyst", permissions: perms },
    } as never);
    stubFetch();

    renderPage();

    const file = new File(["title,report_date\nT,2026-01-01"], "dispatch.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/data file/i), file);
    await userEvent.click(screen.getByRole("button", { name: /upload & parse/i }));

    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(([input]) => String(input).includes("/upload"));
      expect(call).toBeTruthy();
      expect(call![1]?.method).toBe("POST");
      expect(call![1]?.body).toBeInstanceOf(FormData);
    });
  });
});