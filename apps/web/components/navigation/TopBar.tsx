"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

import { Button } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const links = [
  { href: "/chat", label: "Shop" },
  { href: "/console", label: "Merchant console" },
];

export function TopBar() {
  const pathname = usePathname();
  const { identity, signOut } = useAuth();

  return (
    <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-bg)]/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href="/chat" className="text-sm font-semibold tracking-tight">
            CommerceOS
          </Link>
          <nav className="hidden items-center gap-1 sm:flex">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={clsx(
                  "rounded-[var(--radius-control)] px-3 py-1.5 text-sm transition-colors",
                  pathname.startsWith(l.href)
                    ? "bg-[var(--color-surface-muted)] text-[var(--color-fg)]"
                    : "text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]",
                )}
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {identity && (
            <span className="hidden text-xs text-[var(--color-fg-muted)] sm:inline">
              {identity.merchant.business_name} · {identity.user.email}
            </span>
          )}
          <Button variant="ghost" onClick={signOut} className="px-2 py-1 text-xs">
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
