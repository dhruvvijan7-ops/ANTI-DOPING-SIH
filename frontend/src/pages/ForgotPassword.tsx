import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/endpoints";
import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const request = useMutation({
    mutationFn: () => authApi.forgotPassword({ identifier: identifier.trim() }),
    onSuccess: (data) => {
      setSubmitted(true);
      // Development builds echo a working token (the backend never echoes one in
      // production). Surface only useful UX, never a raw secret.
      setDevLink(data.dev_reset_token ? `/reset-password?token=${encodeURIComponent(data.dev_reset_token)}` : null);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Unable to process your request. Please try again.");
    },
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!identifier.trim()) {
      setError("Enter your username or registered email.");
      return;
    }
    request.mutate();
  };

  return (
    <AuthShell
      footer={
        <p className="text-center text-sm text-ink-500">
          Remembered it?{" "}
          <Link to="/login" className="font-medium text-ink-800 hover:underline">
            Back to sign in
          </Link>
        </p>
      }
    >
      <h1 className="text-xl font-semibold text-ink-950">Reset your password</h1>
      <p className="mt-1 text-sm text-ink-600">
        Enter your username or the email associated with your account.
      </p>

      {submitted ? (
        <div className="mt-6 space-y-4">
          <p role="status" className="rounded-md border border-ink-200 bg-white px-3 py-2 text-sm text-ink-700">
            If an account exists for that identifier, password reset instructions have been sent.
          </p>
          {devLink ? (
            <div className="rounded-md border border-dashed border-signal-300 bg-signal-50 px-3 py-2 text-xs leading-relaxed text-ink-700">
              <p className="font-medium text-signal-800">Development build — demo reset link</p>
              <p className="mt-1">
                This environment echoes a working reset link so the flow can be exercised without an email provider.{" "}
                <Link to={devLink} className="font-medium text-ink-900 underline">
                  Open reset page
                </Link>
                .
              </p>
            </div>
          ) : null}
          <Button type="button" variant="secondary" className="w-full" onClick={() => navigate("/login")}>
            Return to sign in
          </Button>
        </div>
      ) : (
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <Field label="Username or email" id="identifier">
            <Input
              id="identifier"
              name="identifier"
              autoComplete="username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              autoFocus
            />
          </Field>

          {error ? (
            <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </p>
          ) : null}

          <Button type="submit" className="w-full" size="lg" loading={request.isPending}>
            Send reset instructions
          </Button>
        </form>
      )}
    </AuthShell>
  );
}