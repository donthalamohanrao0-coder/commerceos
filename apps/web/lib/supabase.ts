"use client";

import { createClient } from "@supabase/supabase-js";

import { config } from "./config";

/**
 * Browser-side Supabase client. Only used for authentication (sign in / sign up /
 * session). All commerce data goes through the FastAPI backend, which
 * re-derives the merchant from the verified token — never from the client.
 */
export const supabase = createClient(config.supabaseUrl, config.supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
