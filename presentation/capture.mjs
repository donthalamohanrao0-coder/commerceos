// Presentation screenshot capture — runs against the LIVE deployment.
// Usage:
//   E2E_EMAIL=... E2E_PASSWORD=... node presentation/capture.mjs
// Requires @playwright/test's chromium (installed for apps/web e2e).

// Playwright is installed under apps/web/node_modules — resolve it from there.
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(repoRoot, "apps", "web", "package.json"));
const { chromium } = require("@playwright/test");

const BASE = process.env.E2E_BASE_URL ?? "https://commerceos-sand.vercel.app";
const EMAIL = process.env.E2E_EMAIL;
const PASSWORD = process.env.E2E_PASSWORD;
if (!EMAIL || !PASSWORD) {
  console.error("Set E2E_EMAIL and E2E_PASSWORD");
  process.exit(1);
}

const OUT = join(dirname(fileURLToPath(import.meta.url)), "assets", "screenshots");
mkdirSync(OUT, { recursive: true });

const shot = async (page, name, opts = {}) => {
  const path = join(OUT, `${name}.png`);
  await page.screenshot({ path, fullPage: !!opts.fullPage });
  console.log("  ✓", name, opts.fullPage ? "(full)" : "");
};

const step = async (label, fn) => {
  process.stdout.write(`• ${label}\n`);
  try {
    await fn();
  } catch (err) {
    console.warn(`  ! ${label} failed: ${err.message}`);
  }
};

const run = async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(45_000);

  // 1. Login screen, logged out.
  await step("login screen", async () => {
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await page.waitForTimeout(800);
    await shot(page, "login");
  });

  // Sign in.
  await step("sign in", async () => {
    await page.getByLabel("Email").fill(EMAIL);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: /^sign in$/i }).click();
    await page.waitForURL("**/chat", { timeout: 60_000 });
    await page.getByText(/NovaTech/i).first().waitFor({ timeout: 60_000 });
    await page.waitForTimeout(1500);
  });

  // 2. Customer chat — a scripted short conversation.
  await step("customer chat", async () => {
    await page.goto(`${BASE}/chat`, { waitUntil: "networkidle" });
    const fresh = page.getByRole("button", { name: /new conversation/i });
    if (await fresh.isVisible().catch(() => false)) await fresh.click();
    const box = page.getByRole("textbox", { name: /message the shopping assistant/i });
    const send = page.getByRole("button", { name: /send message/i });
    const turn = async (text) => {
      await box.fill(text);
      await send.click();
      const status = page.getByRole("status");
      await status.waitFor({ state: "visible", timeout: 10_000 }).catch(() => {});
      await status.waitFor({ state: "hidden", timeout: 90_000 }).catch(() => {});
      await page.waitForTimeout(1200);
    };
    await turn("I need a laptop for coding under ₹90,000 — what do you recommend?");
    await shot(page, "customer-chat");
    // Try to progress to an add-to-cart / checkout affordance for a second shot.
    const addBtn = page.getByRole("button", { name: /add to cart/i });
    if (!(await addBtn.first().isVisible().catch(() => false))) {
      await turn("List your laptops with prices");
    }
    if (await addBtn.first().isVisible().catch(() => false)) {
      await addBtn.first().click();
      await page.waitForTimeout(1500);
      await turn("Yes, check out and pay for that");
      await shot(page, "customer-checkout");
    }
  });

  // 3. Console pages.
  const consolePages = [
    ["console-overview", "/console", { wait: 2500 }],
    ["console-analytics", "/console/analytics", { wait: 3500, fullPage: true }],
    ["console-activity", "/console/activity", { wait: 2500 }],
    ["console-approvals", "/console/approvals", { wait: 2000 }],
    ["console-ai-buyers", "/console/ai-buyers", { wait: 2000 }],
    ["console-campaigns", "/console/campaigns", { wait: 2000 }],
    ["console-orders", "/console/orders", { wait: 2500 }],
  ];
  for (const [name, route, opts] of consolePages) {
    await step(name, async () => {
      await page.goto(`${BASE}${route}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(opts.wait ?? 2000);
      await shot(page, name, { fullPage: opts.fullPage });
    });
  }

  // 4. Activity trace — open the first session drawer.
  await step("console activity trace", async () => {
    await page.goto(`${BASE}/console/activity`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const row = page.getByRole("button", { name: /tool call|msg/i }).first();
    await row.click({ timeout: 15_000 });
    await page.waitForTimeout(2500);
    await shot(page, "console-activity-trace");
  });

  // 5. Knowledge base — run a retrieval preview.
  await step("console knowledge", async () => {
    await page.goto(`${BASE}/console/knowledge`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const ta = page.locator("textarea").first();
    await ta.fill("What is the return window for a laptop, and is there a restocking fee?");
    await page.getByRole("button", { name: /run retrieval/i }).click();
    await page.waitForTimeout(4000);
    await shot(page, "console-knowledge", { fullPage: true });
  });

  await browser.close();
  console.log("\nDone →", OUT);
};

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
