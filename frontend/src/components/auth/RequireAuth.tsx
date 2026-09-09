import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { PageLoading } from "@/components/ui/spinner";

export function RequireAuth({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  if (token === "__HYDRATING__") {
    // sessionStorage rehydration is synchronous under zustand persist, so this
    // branch is a defensive guard for edge cases.
    return <PageLoading />;
  }
  return <>{children}</>;
}