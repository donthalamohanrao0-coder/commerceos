import { AuthGuard } from "@/components/navigation/AuthGuard";
import { TopBar } from "@/components/navigation/TopBar";

export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <TopBar />
      {children}
    </AuthGuard>
  );
}
