import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { UserResponse } from "@/lib/api/types";

// The backend authenticates with bearer JWTs only; there is no server-managed
// session/cookie mechanism. Per the product spec we avoid localStorage — the
// token is kept per tab in sessionStorage so it never survives a browser
// restart or a closed session on the workstation.
interface AuthState {
  token: string | null;
  user: UserResponse | null;
  setSession: (token: string, user: UserResponse) => void;
  clearSession: () => void;
  hasPermission: (key: string) => boolean;
}

function permissionKeysOf(user: UserResponse | null): Set<string> {
  return new Set(user?.role?.permissions?.map((p) => p.key) ?? []);
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setSession: (token, user) => set({ token, user }),
      clearSession: () => set({ token: null, user: null }),
      hasPermission: (key) => permissionKeysOf(get().user).has(key),
    }),
    {
      name: "verity.session",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
);

export function useCan(key: string): boolean {
  return useAuthStore((s) => s.hasPermission(key));
}