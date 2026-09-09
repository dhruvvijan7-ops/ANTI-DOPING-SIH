import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/endpoints";
import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const reset = useMutation({
    mutationFn: () => authApi.resetPassword({ token, new_password: password }),
    onSuccess: () => setSuccess(true),
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Unable to reset your password. Please try again.");
    },
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    reset.mutate();
  };

  const content = success ? (
    <div className="mt-6 space-y-4">
      <p role="status" className="rounded-md border border-signal-200 bg-signal-50 px-3 py-2 text-sm text-ink-800">
        Your password has been reset. You can now sign in with your new password.
      </p>
        <Link
            to="/login?reset=1"
            className="inline-flex h-11 w-full items-center justify-center rounded-md bg-signal-700 px-5 text-sm font-medium text-white transition-colors hover:bg-signal-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-600 focus-visible:ring-offset-1"
          >
            Go to sign in
          </Link>
    </div>
  ) : !token ? (
    <div className="mt-6 space-y-4">
      <p className="text-sm leading-relaxed text-ink-600">
        This page sets a new password using a one-time link. The link appears to be missing or incomplete.
      </p>
      <Link
        to="/forgot-password"
        className="inline-flex h-9 w-full items-center justify-center rounded-md border border-ink-200 bg-white px-3.5 text-sm font-medium text-ink-800 transition-colors hover:border-ink-300 hover:bg-ink-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-400 focus-visible:ring-offset-1"
      >
        Request a new reset link
      </Link>
    </div>
  ) : (
    <form className="mt-6 space-y-4" onSubmit={onSubmit}>
      <Field label="New password" id="new-password">
        <Input
          id="new-password"
          name="newPassword"
          type="password"
          autoComplete="new-password"
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoFocus
        />
      </Field>
      <Field label="Confirm new password" id="confirm-password">
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

      <Button type="submit" className="w-full" size="lg" loading={reset.isPending}>
        Set new password
      </Button>
    </form>
  );

  return (
    <AuthShell
      footer={
        <p className="text-center text-sm text-ink-500">
          <Link to="/login" className="font-medium text-ink-800 hover:underline">
            Back to sign in
          </Link>
        </p>
      }
    >
      <h1 className="text-xl font-semibold text-ink-950">Set a new password</h1>
      <p className="mt-1 text-sm text-ink-600">
        Choose a strong password of at least 8 characters. The reset link works once and expires quickly.
      </p>
      {content}
    </AuthShell>
  );
}