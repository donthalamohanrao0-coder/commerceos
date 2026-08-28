import { defineConfig, devices } from "@playwright/test";

/**
 * E2E against a real running stack: FastAPI on :8000 + this app on :3000 +
 * the live Supabase project. Set E2E_EMAIL / E2E_PASSWORD to a confirmed
 * Supabase user (see e2e/README.md).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
