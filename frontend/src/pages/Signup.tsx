import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/endpoints";
import { useAuthStore } from "@/stores/auth";
import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

export default function Signup() {
  const token = useAuthStore((s) => s.token);
  const setSession = useAuthStore((s) => s.setSession);
  const navigate = useNavigate();
  const location = useLocation();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  const register = useMutation({
    mutationFn: () =>
      authApi.register({
        username: username.trim(),
        email: email.trim() ? email.trim() : null,
        full_name: fullName.trim() ? fullName.trim() : null,
        password,
      }),
    onSuccess: (data) => {
      setSession(data.access_token, data.user);
      const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";
      void navigate(from, { replace: true });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to create your account. Please try again.");
      }
    },
  });

  if (token) return <Navigate to="/dashboard" replace />;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const name = username.trim();
    if (name.length < 3) {
      setError("Choose a username of at least 3 characters (letters, numbers, . _ -).");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    register.mutate();
  };

  return (
    <AuthShell
      footer={
        <div className="rounded-md border border-ink-100 bg-white px-4 py-3 text-xs leading-relaxed text-ink-500">
          <p className="font-medium text-ink-700">Role on creation</p>
          <p className="mt-1">
            New accounts start with read-only VIEWER access. An administrator can later assign analyst or
            investigator capabilities. Registration and subsequent logins are securely audited.
          </p>
        </div>
      }
    >
      <h1 className="text-xl font-semibold text-ink-950">Create an account</h1>
      <p className="mt-1 text-sm text-ink-600">
        Registering signs you into VERITY immediately with read-only viewer access.
      </p>

      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <Field label="Full name" id="full-name" hint="Optional.">
          <Input
            id="full-name"
            name="fullName"
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </Field>
        <Field label="Work email" id="email" hint="Optional. Also accepted by the reset flow.">
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field label="Username" id="username">
          <Input
            id="username"
            name="username"
            autoComplete="username"
            minLength={3}
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
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        <Field label="Confirm password" id="confirm-password">
          <Input
            id="confirm-password"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
        </Field>

        {error ? (
          <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        ) : null}

        <Button type="submit" className="w-full" size="lg" loading={register.isPending}>
          Create account
        </Button>
      </form>

      <div className="mt-6 border-t border-ink-100 pt-5 text-center text-sm text-ink-600">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-ink-950 hover:underline">
          Sign in
        </Link>
      </div>
    </AuthShell>
  );
}