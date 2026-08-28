"use client";

import type { Session } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { api, ApiError } from "./api";
import { supabase } from "./supabase";
import type { Identity } from "./types";

interface AuthState {
  session: Session | null;
  identity: Identity | null;
  loading: boolean;
  error: string | null;
  reloadIdentity: () => void;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const loadIdentity = useCallback(async () => {
    const token = (await supabase.auth.getSession()).data.session?.access_token;
    if (!token || inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    setError(null);
    try {
      setIdentity(await api<Identity>("/me"));
    } catch (e) {
      setIdentity(null);
      setError(
        e instanceof ApiError ? e.friendlyMessage : "Could not load your workspace. Please retry.",
      );
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (!data.session) setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      if (!next) {
        setIdentity(null);
        setError(null);
        setLoading(false);
      }
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  // (Re)resolve the backend identity whenever the access token changes.
  useEffect(() => {
    if (session?.access_token) void loadIdentity();
  }, [session?.access_token, loadIdentity]);

  const signIn = useCallback(async (email: string, password: string) => {
    const { error: e } = await supabase.auth.signInWithPassword({ email, password });
    if (e) throw new Error(e.message);
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const { data, error: e } = await supabase.auth.signUp({ email, password });
    if (e) throw new Error(e.message);
    if (!data.session) {
      // Email confirmation is on for this project — surface it clearly.
      throw new Error("Check your inbox to confirm your email, then sign in.");
    }
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setIdentity(null);
    setError(null);
    router.push("/login");
  }, [router]);

  const value = useMemo<AuthState>(
    () => ({
      session,
      identity,
      loading,
      error,
      reloadIdentity: () => void loadIdentity(),
      signIn,
      signUp,
      signOut,
    }),
    [session, identity, loading, error, loadIdentity, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
