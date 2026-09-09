import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "@/stores/auth";
import type { PermissionKey, UserResponse } from "@/lib/api/types";

function makeUser(permissions: string[]): UserResponse {
  return {
    id: "u-1",
    username: "ana",
    full_name: "Ana Analyst",
    email: "ana@verity.test",
    is_active: true,
    last_login_at: null,
    role: {
      id: "r-1",
      name: "Intelligence Analyst",
      description: null,
      permissions: permissions.map((key) => ({ id: "p-1", key: key as PermissionKey, description: null })),
    },
  };
}

const PERM = { alertsRead: "alerts:read", alertsReview: "alerts:review", alertsConvert: "alerts:convert" } as const;

describe("auth store", () => {
  beforeEach(() => {
    sessionStorage.clear();
    useAuthStore.getState().clearSession();
  });

  it("starts signed out", () => {
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().hasPermission(PERM.alertsRead)).toBe(false);
  });

  it("persists the session to sessionStorage under verity.session", () => {
    useAuthStore.getState().setSession("token-abc", makeUser([PERM.alertsRead]));
    const raw = sessionStorage.getItem("verity.session");
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw!) as { state: { token: string; user: UserResponse } };
    expect(parsed.state.token).toBe("token-abc");
    expect(parsed.state.user.username).toBe("ana");
  });

  it("hydrates a prior session on store creation", async () => {
    sessionStorage.setItem("verity.session", JSON.stringify({ state: { token: "token-old", user: makeUser([]) } }));
    await useAuthStore.persist.rehydrate();
    const state = useAuthStore.getState();
    expect(state.token).toBe("token-old");
    expect(state.user?.username).toBe("ana");
  });

  it("grants permissions only for the authenticated role", () => {
    useAuthStore.getState().setSession("t", makeUser([PERM.alertsReview]));
    const s = useAuthStore.getState();
    expect(s.hasPermission(PERM.alertsReview)).toBe(true);
    expect(s.hasPermission(PERM.alertsRead)).toBe(false);
    expect(s.hasPermission(PERM.alertsConvert)).toBe(false);
  });

  it("clears the session", () => {
    useAuthStore.getState().setSession("t", makeUser([PERM.alertsReview]));
    useAuthStore.getState().clearSession();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().hasPermission(PERM.alertsReview)).toBe(false);
  });
});