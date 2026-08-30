// Re-capture just the activity-trace shot with a proper wait for the drawer content.
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(here, "..", "apps", "web", "package.json"));
const { chromium } = require("@playwright/test");

const BASE = process.env.E2E_BASE_URL ?? "https://commerceos-sand.vercel.app";
const OUT = join(here, "assets", "screenshots");

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(45_000);

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.getByLabel("Email").fill(process.env.E2E_EMAIL);
await page.getByLabel("Password").fill(process.env.E2E_PASSWORD);
await page.getByRole("button", { name: /^sign in$/i }).click();
await page.waitForURL("**/chat", { timeout: 60_000 });
await page.getByText(/NovaTech/i).first().waitFor({ timeout: 60_000 });

await page.goto(`${BASE}/console/activity`, { waitUntil: "networkidle" });
await page.waitForTimeout(2500);
// Open a session with a rich trace (more tool calls). Pick the "10 tool calls" row if present.
const rich = page.getByRole("button", { name: /10 tool calls/i }).first();
const target = (await rich.isVisible().catch(() => false))
  ? rich
  : page.getByRole("button", { name: /tool call/i }).first();
await target.click();
const dialog = page.getByRole("dialog", { name: /agent session trace/i });
await dialog.waitFor({ timeout: 20_000 });
// Wait for the tool-trace heading to render (spinner gone).
await page.getByRole("heading", { name: /tool trace/i }).waitFor({ timeout: 30_000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: join(OUT, "console-activity-trace.png") });
console.log("  ✓ console-activity-trace re-captured");

await b.close();
