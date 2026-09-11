import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Osint from "@/pages/Osint";
import { useAuthStore } from "@/stores/auth";
import type { OsintConnectorList, OsintRecordList, OsintSourceList } from "@/lib/api/types";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const connectors: OsintConnectorList = {
  count: 2,
  connectors: [
    { connector_type: "web_doc", source_kind: "HTML", search_driven: false },
    { connector_type: "gdelt", source_kind: "API", search_driven: true },
  ],
};

const sources: OsintSourceList = {
  count: 1,
  limit: 100,
  offset: 0,
  sources: [
    {
      id: "src-1",
      source_id: "wada-rss",
      name: "WADA RSS",
      connector_type: "rss",
      url: "https://www.wada-ama.org/en/rss.xml",
      authority: "OFFICIAL",
      jurisdiction: "Global",
      enabled: true,
      poll_frequency_min: 60,
      rate_limit_per_min: 30,
      health: "ACTIVE",
      consecutive_failures: 0,
      last_success_at: "2026-09-10T08:00:00Z",
      last_failure_at: null,
      last_failure_reason: null,
      connector_kind: "rss",
    },
  ],
};

const records: OsintRecordList = {
  count: 1,
  limit: 100,
  offset: 0,
  records: [
    {
      id: "rec-1",
      source_id: "wada-rss",
      source: "WADA RSS",
      source_type: "rss",
      authority_level: "OFFICIAL",
      title: "WADA bans five athletes",
      publisher: "WADA",
      author: null,
      source_url: "https://wada-ama.org/news/5",
      canonical_url: "https://wada-ama.org/news/5",
      published_at: "2026-09-09T10:00:00Z",
      retrieved_at: "2026-09-09T11:00:00Z",
      content_hash: "aaa111",
      language: "en",
      jurisdiction: "Global",
      extraction_method: "parsed",
      is_duplicate: false,
      duplicate_reason: null,
      duplicate_of: null,
      syndication_group: null,
      terms_matched: true,
    },
  ],
};

const readPerms = [
  { key: "osint:read", name: "Read OSINT" },
  { key: "osint:collect", name: "Collect OSINT" },
  { key: "osint:admin", name: "Admin OSINT" },
  { key: "intelligence:create", name: "Create intel" },
];

function stubFetch(extraRoutes?: Record<string, unknown>) {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";

    if (url === "/api/v1/osint/connector-types") return json(connectors);
    if (url.startsWith("/api/v1/osint/sources?") || url === "/api/v1/osint/sources") return json(sources);
    if (url === "/api/v1/osint/sources/src-1/collect" && method === "POST") {
      return json({
        source_id: "wada-rss",
        source_name: "WADA RSS",
        health: "ACTIVE",
        ok: true,
        error: null,
        new_records: 2,
        duplicates: 0,
        mentions: 1,
        stored: [],
        requested_by: "u-1",
        requested_at: "2026-09-10T08:01:00Z",
      });
    }
    if (url === "/api/v1/osint/collect" && method === "POST") {
      return json({
        terms: "anti-doping",
        requested_by: "u-1",
        requested_at: "2026-09-10T08:02:00Z",
        sources_run: 1,
        results: [
          { source_id: "wada-rss", source_name: "WADA RSS", health: "ACTIVE", ok: true, error: null, new_records: 1, duplicates: 0, mentions: 0, stored: [] },
        ],
      });
    }
    if (url === "/api/v1/osint/sources/defaults" && method === "POST") return json({ ok: true, sources_total: 5, records_total: 0 });
    if (url.startsWith("/api/v1/osint/records?")) return json(records);
    if (url === "/api/v1/osint/records/rec-1") {
      return json({ ...records.records[0], content: "Article content", mentions: [], claims: [], promoted_reports: 0 });
    }
    if (url === "/api/v1/osint/records/rec-1/promote" && method === "POST") {
      return json({ ok: true, report_id: "rpt-1", osint_record_id: "rec-1", title: "WADA bans five athletes", source_id: "wada-rss" });
    }
    if (url === "/api/v1/osint/records/rec-1/claims" && method === "POST") {
      const body = JSON.parse(String(init?.body ?? "{}"));
      return json({
        id: "claim-1",
        record_id: "rec-1",
        subject_type: null,
        subject_id: null,
        subject_label: null,
        predicate: body.predicate,
        object_value: body.object_value,
        confidence: null,
        verification: "UNREVIEWED",
        notes: null,
        created_by: "u-1",
        created_at: "2026-09-10T08:03:00Z",
        reviewed_by: null,
        reviewed_at: null,
      });
    }
    if (url === "/api/v1/osint/claims/claim-1" && method === "PATCH") {
      return json({
        id: "claim-1",
        record_id: "rec-1",
        subject_type: null,
        subject_id: null,
        subject_label: null,
        predicate: "sanctioned_by",
        object_value: "ADRV",
        confidence: null,
        verification: "CORROBORATED",
        notes: null,
        created_by: "u-1",
        created_at: "2026-09-10T08:03:00Z",
        reviewed_by: "u-1",
        reviewed_at: "2026-09-10T08:04:00Z",
      });
    }
    if (extraRoutes?.[url]) return json(extraRoutes[url]);
    return json({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  }));
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Osint />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Osint page", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    vi.restoreAllMocks();
  });

  it("restricts access without the osint:read permission", () => {
    renderPage();
    expect(screen.getByText(/access restricted/i)).toBeInTheDocument();
    expect(screen.queryByText(/open source/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /register source/i })).not.toBeInTheDocument();
  });

  it("loads sources and records when permitted", async () => {
    useAuthStore.getState().setSession("tok", {
      id: "u-1",
      username: "ana",
      full_name: "Ana Analyst",
      email: "ana@verity.test",
      is_active: true,
      role: { key: "ANALYST", name: "Analyst", permissions: readPerms },
    } as never);
    stubFetch();

    renderPage();
    expect(await screen.findByText("WADA RSS")).toBeInTheDocument();
    expect(await screen.findByText("WADA bans five athletes")).toBeInTheDocument();
    expect(screen.getByText("WADA RSS")).toBeInTheDocument();
  });

  it("collects a source and shows the result", async () => {
    useAuthStore.getState().setSession("tok", {
      id: "u-1",
      username: "ana",
      full_name: "Ana Analyst",
      email: "ana@verity.test",
      is_active: true,
      role: { key: "ANALYST", name: "Analyst", permissions: readPerms },
    } as never);
    stubFetch();

    renderPage();
    await screen.findByText("WADA RSS");
    const btn = screen.getByRole("button", { name: /^Collect$/ });
    await userEvent.click(btn);

    await waitFor(() => {
      expect(vi.mocked(fetch)).toHaveBeenCalledWith(
        "/api/v1/osint/sources/src-1/collect",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("promotes a record to intelligence", async () => {
    useAuthStore.getState().setSession("tok", {
      id: "u-1",
      username: "ana",
      full_name: "Ana Analyst",
      email: "ana@verity.test",
      is_active: true,
      role: { key: "ANALYST", name: "Analyst", permissions: readPerms },
    } as never);
    stubFetch();

    renderPage();
    await screen.findByText("WADA bans five athletes");
    await userEvent.click(screen.getByText("WADA bans five athletes"));

    await screen.findByRole("button", { name: /promote to intelligence/i });
    await userEvent.click(screen.getByRole("button", { name: /promote to intelligence/i }));

    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(
        ([input, init]) => String(input).includes("/rec-1/promote") && init?.method === "POST",
      );
      expect(call).toBeTruthy();
      const body = JSON.parse(String((call![1] as RequestInit).body));
      expect(body).toEqual({});
    });
  });

  it("hides admin and collect actions when those permissions are absent", async () => {
    useAuthStore.getState().setSession("tok", {
      id: "u-2",
      username: "viewer",
      full_name: "View Only",
      email: "view@verity.test",
      is_active: true,
      role: { key: "VIEWER", name: "Viewer", permissions: [{ key: "osint:read", name: "Read OSINT" }] },
    } as never);
    stubFetch();

    renderPage();
    expect(await screen.findByText("WADA RSS")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /register source/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /seed default/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /collect$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /promote to intelligence/i })).not.toBeInTheDocument();
  });
});
