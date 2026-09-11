import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Athletes from "@/pages/Athletes";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Athletes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Athletes page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.mocked(fetch).mockResolvedValue(json({ count: 0, limit: 200, offset: 0, athletes: [] }));
  });

  it("requests the first page at the server list cap", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/no athletes found/i)).toBeInTheDocument();
    });
    const url = vi.mocked(fetch).mock.calls[0]?.[0] as string;
    expect(url).toContain("/api/v1/athletes");
    expect(url).toContain("limit=200");
  });

  it("renders an empty state when there are no athletes", async () => {
    renderPage();
    expect(await screen.findByText(/no athletes found/i)).toBeInTheDocument();
  });

  it("surfaces the backend error message when the request fails", async () => {
    vi.mocked(fetch).mockResolvedValue(
      json({ error: { code: "INVALID_LIMIT", message: "limit must not exceed 200" } }, 422),
    );
    renderPage();
    expect(await screen.findByText(/could not load athletes/i)).toBeInTheDocument();
    expect(await screen.findByText(/limit must not exceed 200/i)).toBeInTheDocument();
  });
});