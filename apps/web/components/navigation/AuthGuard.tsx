"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

/** Blocks a subtree until a Supabase session + backend identity are resolved.
 *  If the identity call fails (e.g. the API is unreachable) it shows a recoverable
 *  error instead of spinning forever. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { session, identity, loading, error, reloadIdentity, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !session) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, session, router, pathname]);

  if (loading || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="size-6 text-[var(--color-fg-muted)]" />
      </div>
    );
  }

  if (!identity) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <div
          role="alert"
          className="flex max-w-sm flex-col items-center gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-center"
        >
          <p className="text-sm font-semibold">We couldn&apos;t load your workspace</p>
          <p className="text-sm text-[var(--color-fg-muted)]">
            {error ?? "The service is not responding. Check your connection and try again."}
          </p>
          <div className="mt-1 flex gap-2">
            <Button variant="secondary" onClick={signOut}>
              Sign out
            </Button>
            <Button onClick={reloadIdentity}>Try again</Button>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
