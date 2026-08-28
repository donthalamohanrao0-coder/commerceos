"use client";

import { config } from "./config";
import { supabase } from "./supabase";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  /** A message safe to show a user — never a raw provider/stack string. */
  get friendlyMessage(): string {
    if (this.status === 401) return "Your session has expired. Please sign in again.";
    if (this.status === 403) return "You don't have permission to do that.";
    if (this.status === 404) return "We couldn't find that.";
    if (this.status === 429) return "Too many requests — give it a moment and try again.";
    if (this.status >= 500) return "Something went wrong on our side. Please try again.";
    return this.message || "Request failed.";
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(await authHeader()),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "NETWORK", "Could not reach the server. Check your connection.");
  }

  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const err = (payload as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(
      response.status,
      err?.code ?? "ERROR",
      err?.message ?? `HTTP ${response.status}`,
    );
  }

  return ((payload as { data?: T } | null)?.data ?? (payload as T)) as T;
}

/** Authenticated multipart POST (file uploads). The browser sets the boundary,
 * so we must NOT send a Content-Type header. Same envelope unwrap as `api`. */
export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      method: "POST",
      headers: { ...(await authHeader()) },
      body: form,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "NETWORK", "Could not reach the server. Check your connection.");
  }

  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    const detail =
      (payload as { detail?: string; error?: { message?: string } } | null) ?? null;
    throw new ApiError(
      response.status,
      "UPLOAD",
      detail?.error?.message ?? detail?.detail ?? `HTTP ${response.status}`,
    );
  }
  return ((payload as { data?: T } | null)?.data ?? (payload as T)) as T;
}

/** Authenticated POST that returns the raw streaming `Response` (for SSE). */
export async function apiStream(path: string, body: unknown): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(await authHeader()) },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "NETWORK", "Could not reach the server. Check your connection.");
  }
  if (!response.ok || !response.body) {
    throw new ApiError(response.status || 0, "STREAM", `HTTP ${response.status}`);
  }
  return response;
}
