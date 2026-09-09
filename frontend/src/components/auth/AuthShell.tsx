import type { ReactNode } from "react";
import { Link } from "react-router-dom";

/** Shared layout for the public authentication pages (login, signup, forgot,
 * reset). A lightweight enter animation keeps transitions between auth screens
 * subtle without slowing navigation. */
export function AuthShell({
  children,
  footer,
}: {
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-paper-50">
      <header className="flex items-center justify-between border-b border-ink-100 bg-white px-6 py-4">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-ink-950 text-sm font-bold text-paper-50">V</div>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-ink-950">VERITY</p>
            <p className="text-xs text-ink-500">Anti-Doping Intelligence & Investigations</p>
          </div>
        </Link>
        <Link to="/" className="text-sm font-medium text-ink-700 hover:underline">
          Back to overview
        </Link>
      </header>

      <div className="auth-enter flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {children}
          {footer ? <div className="mt-6">{footer}</div> : null}
        </div>
      </div>
    </div>
  );
}