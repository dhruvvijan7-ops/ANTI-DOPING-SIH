import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/endpoints";
import { useAuthStore } from "@/stores/auth";
import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

export default function Login() {
  const token = useAuthStore((s) => s.token);
  const setSession = useAuthStore((s) => s.setSession);
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const resetDone = searchParams.get("reset") === "1";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const login = useMutation({
    mutationFn: () => authApi.login({ username, password }),
    onSuccess: (data) => {
      setSession(data.access_token, data.user);
      const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";
      void navigate(from, { replace: true });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Unable to sign in. Please try again.");
    },
  });

  if (token) return <Navigate to="/dashboard" replace />;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError("Enter both username and password.");
      return;
    }
    login.mutate();
  };

  return (
    <AuthShell
      footer={
        <div className="rounded-md border border-ink-100 bg-white px-4 py-3 text-xs leading-relaxed text-ink-500">
          <p className="font-medium text-ink-700">About your session</p>
          <p className="mt-1">
            Your authentication token expires when you close the browser tab. For security reasons credentials are
            never stored on this device.
          </p>
        </div>
      }
    >
      <h1 className="text-xl font-semibold text-ink-950">Sign in</h1>
      <p className="mt-1 text-sm text-ink-600">
        Access to this platform is restricted to authorised personnel. Your activity is securely logged.
      </p>

      {resetDone ? (
        <p role="status" className="mt-5 rounded-md border border-signal-200 bg-signal-50 px-3 py-2 text-sm text-ink-800">
          Your password has been reset. Sign in with your new password.
        </p>
      ) : null}

      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <Field label="Username" id="username">
          <Input
            id="username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
        </Field>
        <Field label="Password" id="password">
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        <div className="flex justify-end text-sm">
          <Link to="/forgot-password" className="font-medium text-signal-700 hover:underline">
            Forgot password?
          </Link>
        </div>

        {error ? (
          <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        ) : null}

        <Button type="submit" className="w-full" size="lg" loading={login.isPending}>
          Sign in
        </Button>
      </form>

      <div className="mt-6 border-t border-ink-100 pt-5 text-center text-sm text-ink-600">
        New to VERITY?{" "}
        <Link to="/signup" className="font-medium text-ink-950 hover:underline">
          Create an account
        </Link>
      </div>
    </AuthShell>
  );
}