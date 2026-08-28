"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui";

const AnalyticsPage = dynamic(
  () => import("@/features/console/Analytics").then((m) => m.AnalyticsPage),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-4">
        <Skeleton className="h-8 w-40" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-60 w-full" />
          ))}
        </div>
      </div>
    ),
  },
);

export default function Page() {
  return <AnalyticsPage />;
}
