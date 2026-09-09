import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-paper-50 p-6 text-center">
      <p className="text-5xl font-semibold text-ink-300">404</p>
      <h1 className="text-lg font-semibold text-ink-950">This page could not be found</h1>
      <p className="max-w-md text-sm text-ink-600">
        The address may have changed or the link may be outdated. Your session and data are safe.
      </p>
      <div className="mt-2 flex gap-2">
        <Link to="/dashboard">
          <Button variant="primary">Go to dashboard</Button>
        </Link>
        <Link to="/">
          <Button variant="outline">Back to overview</Button>
        </Link>
      </div>
    </div>
  );
}