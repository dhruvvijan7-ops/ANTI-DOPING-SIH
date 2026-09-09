import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { api, buildQuery, ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth";

const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });

describe("buildQuery", () => {
  it("returns an empty string for no params", () => {
    expect(buildQuery()).toBe("");
  });

  it("skips nullish values", () => {
    expect(buildQuery({ a: "", b: null, c: undefined })).toBe("");
  });

  it("serialises arrays by repeating the key", () => {
    expect(buildQuery({ ids: ["1", "2"], x: 3 })).toBe("?ids=1&ids=2&x=3");
  });

  it("appends encoded key-value pairs", () => {
    expect(buildQuery({ limit: 10, role: "analyst", q: "a b" })).toBe("?limit=10&role=analyst&q=a+b");
  });
});

describe("api", () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("includes the bearer token and returns parsed JSON", async () => {
    useAuthStore.getState().setSession("tok123", { id: "u-1", username: "ana", role: { key: "X", name: "x", permissions: [] } } as never);
    vi.mocked(fetch).mockResolvedValue(json({ data: [1, 2, 3] }));
    const result = await api<{ data: number[] }>("/widgets");
    expect(result).toEqual({ data: [1, 2, 3] });
    const [url, init] = vi.mocked(fetch).mock.calls[0] as unknown as [string, RequestInit];
    expect(url.startsWith("/api/v1/widgets")).toBe(true);
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok123");
  });

  it("posts JSON bodies for mutations", async () => {
    vi.mocked(fetch).mockResolvedValue(json({ id: "inv-1" }));
    await api("/investigations", { method: "POST", body: { title: "Case" } });
    const [, init] = vi.mocked(fetch).mock.calls[0] as unknown as [unknown, RequestInit];
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ title: "Case" }));
  });

  it("maps the backend error envelope into ApiError", async () => {
    vi.mocked(fetch).mockResolvedValue(
      json({ error: { code: "ALERT_NOT_FOUND", message: "No such alert", request_id: "req-9" } }, 404),
    );
    const err = (await api("/alerts/xyz").catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.code).toBe("ALERT_NOT_FOUND");
    expect(err.requestId).toBe("req-9");
  });

  it("clears the session on a 401 response", async () => {
    useAuthStore.getState().setSession("expired", { id: "u-1", username: "ana", role: { key: "X", name: "x", permissions: [] } } as never);
    vi.mocked(fetch).mockResolvedValue(json({ error: { code: "UNAUTHORIZED", message: "tok expired" } }, 401));
    await expect(api("/alerts")).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("raises a friendly network error when fetch rejects", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("Failed to fetch"));
    const err = (await api("/alerts").catch((e) => e)) as ApiError;
    expect(err.status).toBe(0);
    expect(err.code).toBe("NETWORK_ERROR");
  });
});