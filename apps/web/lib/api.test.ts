import { beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { api, ApiError } from "./api";
import { supabase } from "./supabase";

let fetchSpy: MockInstance;

function respond(status: number, body: unknown) {
  const text = typeof body === "string" ? body : JSON.stringify(body);
  fetchSpy.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(text),
  } as Response);
}

beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("unexpected fetch"));
  vi.mocked(supabase.auth.getSession).mockResolvedValue({
    data: { session: { access_token: "test-token" } },
    error: null,
  } as never);
});

describe("api()", () => {
  it("unwraps the { data, request_id } envelope", async () => {
    respond(200, { data: { hello: "world" }, request_id: "r1" });
    await expect(api("/thing")).resolves.toEqual({ hello: "world" });
  });

  it("falls back to the raw payload when there is no envelope", async () => {
    respond(200, { status: "ok" });
    await expect(api("/health")).resolves.toEqual({ status: "ok" });
  });

  it("attaches the bearer token and JSON body on POST", async () => {
    respond(200, { data: {} });
    await api("/agent/sessions", { method: "POST", body: { workflow: "shopping" } });

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit & { headers: Record<string, string> }];
    expect(url).toBe("http://api.test/api/v1/agent/sessions");
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer test-token");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ workflow: "shopping" }));
  });

  it("throws ApiError carrying the backend error code + status", async () => {
    respond(403, { error: { code: "PAYMENT_POLICY_DENIED", message: "exceeds limit" } });
    await expect(api("/pay")).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
      code: "PAYMENT_POLICY_DENIED",
      message: "exceeds limit",
    });
  });

  it("turns a network failure into a NETWORK ApiError, not an unhandled throw", async () => {
    fetchSpy.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(api("/x")).rejects.toMatchObject({ code: "NETWORK", status: 0 });
  });

  it("omits the Authorization header when signed out", async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValueOnce({
      data: { session: null },
      error: null,
    } as never);
    respond(200, { data: {} });

    await api("/me");
    const [, init] = fetchSpy.mock.calls[0] as [string, { headers: Record<string, string> }];
    expect(init.headers.Authorization).toBeUndefined();
  });
});

describe("ApiError.friendlyMessage", () => {
  it("maps status codes to safe, user-facing messages", () => {
    expect(new ApiError(401, "X", "raw").friendlyMessage).toMatch(/session has expired/i);
    expect(new ApiError(403, "X", "raw").friendlyMessage).toMatch(/permission/i);
    expect(new ApiError(429, "X", "raw").friendlyMessage).toMatch(/too many/i);
    expect(new ApiError(500, "X", "internal stack trace").friendlyMessage).toMatch(
      /something went wrong/i,
    );
  });
});
