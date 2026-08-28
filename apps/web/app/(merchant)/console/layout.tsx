import { AuthGuard } from "@/components/navigation/AuthGuard";
import { ConsoleSidebar } from "@/components/navigation/ConsoleSidebar";
import { TopBar } from "@/components/navigation/TopBar";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <TopBar />
      <div className="mx-auto flex max-w-6xl flex-col md:flex-row">
        <ConsoleSidebar />
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-6">{children}</main>
      </div>
    </AuthGuard>
  );
}
