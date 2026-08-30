"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";

const groups: { label: string; items: { href: string; label: string; exact?: boolean }[] }[] = [
  {
    label: "Overview",
    items: [
      { href: "/console", label: "Overview", exact: true },
      { href: "/console/analytics", label: "Analytics" },
    ],
  },
  {
    label: "Commerce",
    items: [
      { href: "/console/products", label: "Products" },
      { href: "/console/orders", label: "Orders" },
      { href: "/console/customers", label: "Customers" },
      { href: "/console/payments", label: "Payments" },
      { href: "/console/campaigns", label: "Campaigns" },
    ],
  },
  {
    label: "Agents",
    items: [
      { href: "/console/assistant", label: "Growth assistant" },
      { href: "/console/activity", label: "Agent activity" },
      { href: "/console/approvals", label: "Approvals" },
      { href: "/console/knowledge", label: "Knowledge base" },
      { href: "/console/ai-buyers", label: "AI buyers" },
    ],
  },
  {
    label: "Config",
    items: [{ href: "/console/settings", label: "Settings" }],
  },
];

export function ConsoleSidebar() {
  const pathname = usePathname();
  return (
    <aside className="shrink-0 border-b border-[var(--color-border)] md:w-52 md:border-b-0 md:border-r">
      <nav className="flex gap-4 overflow-x-auto p-3 md:flex-col md:gap-5 md:overflow-visible">
        {groups.map((group) => (
          <div key={group.label} className="flex shrink-0 gap-1 md:flex-col md:gap-0.5">
            <p className="hidden px-3 pb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-fg-muted)] md:block">
              {group.label}
            </p>
            {group.items.map((item) => {
              const active = item.exact
                ? pathname === item.href
                : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={clsx(
                    "whitespace-nowrap rounded-[var(--radius-control)] px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-[var(--color-surface-muted)] font-medium text-[var(--color-fg)]"
                      : "text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-fg)]",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
