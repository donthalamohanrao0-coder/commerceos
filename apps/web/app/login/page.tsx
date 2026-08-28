"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button, Card, Field } from "@/components/ui";
import { useAuth } from "@/lib/auth";

function LoginInner() {
  const { session, loading, signIn, signUp } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/chat";

  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (session && !loading) router.replace(next);
  }, [session, loading, next, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === "sign-in") {
        await signIn(email, password);
        router.replace(next);
      } else {
        await signUp(email, password);
        setNotice("Account created. You can sign in now.");
        setMode("sign-in");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <div className="co-fade-up mb-8 flex items-center gap-3">
        <div
          className="flex size-9 items-center justify-center rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-fg)] shadow-[var(--shadow-md)]"
          aria-hidden="true"
        >
          ✦
        </div>
        <div>
          <p className="text-lg font-semibold tracking-tight">CommerceOS</p>
          <p className="text-sm text-[var(--color-fg-muted)]">
            AI-native commerce. Every money action explainable, bounded and gated.
          </p>
        </div>
      </div>

      <Card elevated className="co-fade-up p-6">
        <h1 className="text-base font-semibold">
          {mode === "sign-in" ? "Sign in" : "Create an account"}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-fg-muted)]">
          {mode === "sign-in"
            ? "Use your CommerceOS credentials."
            : "New accounts get access to the demo merchant workspace."}
        </p>

        <form onSubmit={onSubmit} className="mt-5 flex flex-col gap-4">
          <Field
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            label="Password"
            name="password"
            type="password"
            autoComplete={mode === "sign-in" ? "current-password" : "new-password"}
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && (
            <p role="alert" className="text-sm text-[var(--color-danger)]">
              {error}
            </p>
          )}
          {notice && <p className="text-sm text-[var(--color-success)]">{notice}</p>}

          <Button type="submit" loading={busy}>
            {mode === "sign-in" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(mode === "sign-in" ? "sign-up" : "sign-in");
            setError(null);
            setNotice(null);
          }}
          className="mt-4 text-sm text-[var(--color-info)] hover:underline"
        >
          {mode === "sign-in"
            ? "Need an account? Create one"
            : "Already have an account? Sign in"}
        </button>
      </Card>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginInner />
    </Suspense>
  );
}
