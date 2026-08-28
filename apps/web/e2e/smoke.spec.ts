import { expect, test, type Page } from "@playwright/test";

const EMAIL = process.env.E2E_EMAIL ?? "e2e@commerceos.test";
const PASSWORD = process.env.E2E_PASSWORD ?? "E2e-pass-12345";

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /^sign in$/i }).click();
  await page.waitForURL("**/chat", { timeout: 30_000 });
  // Wait for the backend identity to resolve (the TopBar shows the merchant name).
  await expect(page.getByText(/NovaTech/i)).toBeVisible({ timeout: 30_000 });
}

test.describe("customer chat", () => {
  // Drives a real LLM, so we send explicit prompts and re-nudge if a step's
  // affordance hasn't appeared yet, rather than assuming exact phrasing.
  async function waitTurn(page: Page) {
    const status = page.getByRole("status"); // the "Thinking…" indicator
    await status.waitFor({ state: "visible", timeout: 10_000 }).catch(() => {});
    await expect(status).toBeHidden({ timeout: 90_000 });
  }

  async function send(page: Page, text: string) {
    await page.getByLabel(/message the shopping assistant/i).fill(text);
    await page.getByRole("button", { name: /send message/i }).click();
    await waitTurn(page);
  }

  async function waitOrNudge(page: Page, locator: ReturnType<Page["getByRole"]>, nudge: string) {
    for (let i = 0; i < 3; i++) {
      if (await locator.first().isVisible().catch(() => false)) return;
      await send(page, nudge);
    }
    await expect(locator.first()).toBeVisible({ timeout: 45_000 });
  }

  test("discover → add to cart → approve → real Razorpay Checkout opens", async ({ page }) => {
    await signIn(page);
    await expect(page.getByRole("heading", { name: /what are you shopping for/i })).toBeVisible();

    const newConv = page.getByRole("button", { name: /new conversation/i });
    if (await newConv.isVisible().catch(() => false)) await newConv.click();

    await send(page, "Show me the NovaBook Pro 14 laptop");
    await waitOrNudge(
      page,
      page.getByRole("button", { name: /add to cart/i }),
      "List your laptops with prices",
    );
    await page.getByRole("button", { name: /add to cart/i }).first().click();
    await waitTurn(page);

    await waitOrNudge(
      page,
      page.getByRole("button", { name: /confirm & pay/i }),
      "Check out and pay for the NovaBook Pro 14 now",
    );

    // The high-trust gate: nothing charged until this click.
    await expect(page.getByText(/requires your confirmation/i)).toBeVisible();
    await page.getByRole("button", { name: /confirm & pay/i }).click();

    // Approval creates a Razorpay order and the real Checkout window opens.
    // (Completing a test card inside Razorpay's iframe is out of scope for CI.)
    await expect(page.getByText(/complete your payment/i)).toBeVisible({ timeout: 60_000 });
    await expect(page.locator("iframe[src*='razorpay']")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("button", { name: /^pay ₹/i })).toBeVisible();
  });
});

test.describe("merchant console", () => {
  test("overview, activity trace and AI-buyer key issuance", async ({ page }) => {
    await signIn(page);
    await page.goto("/console");

    await expect(page.getByRole("heading", { name: /overview/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/^Revenue$/)).toBeVisible();
    await expect(page.getByRole("heading", { name: /^audit trail$/i })).toBeVisible();

    // analytics is its own page — charts render there (lazy-loaded)
    await page.goto("/console/analytics");
    await expect(page.getByRole("heading", { name: /^analytics$/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.locator(".recharts-surface").first()).toBeVisible({ timeout: 30_000 });

    await page.goto("/console/activity");
    await expect(page.getByRole("heading", { name: /agent activity/i })).toBeVisible({
      timeout: 30_000,
    });
    // sessions are grouped by time bucket
    await expect(
      page.getByRole("heading", { name: /today|yesterday|earlier this week|this month/i }).first(),
    ).toBeVisible({ timeout: 20_000 });
    const firstSession = page.locator("button", { hasText: /tool call/i }).first();
    if (await firstSession.isVisible().catch(() => false)) {
      await firstSession.click();
      await expect(page.getByRole("dialog", { name: /agent session trace/i })).toBeVisible();
      await page.getByRole("button", { name: /^close$/i }).click();
    }

    await page.goto("/console/knowledge");
    await expect(page.getByRole("heading", { name: /knowledge base/i })).toBeVisible({
      timeout: 30_000,
    });
    // the grounding corpus lists its indexed documents
    await expect(page.locator("tbody tr").first()).toBeVisible({ timeout: 20_000 });
    // retrieval preview runs the real semantic search
    await page.getByPlaceholder(/how long does delivery take/i).fill("what is the return window");
    await page.getByRole("button", { name: /run retrieval/i }).click();
    await expect(page.getByText(/returns policy/i).first()).toBeVisible({ timeout: 30_000 });

    await page.goto("/console/ai-buyers");
    await expect(page.getByRole("heading", { name: /ai buyers/i })).toBeVisible({ timeout: 30_000 });
    await page.getByLabel("Label").fill(`e2e-${Date.now()}`);
    await page.getByRole("button", { name: /generate key/i }).click();

    // The one-time reveal card — scope the key assertion to it (list rows also start with ack_).
    const revealCard = page.locator("div", { hasText: /only time the full key is shown/i }).last();
    await expect(revealCard).toBeVisible({ timeout: 15_000 });
    await expect(revealCard.locator("code")).toHaveText(/^ack_live_/);
  });

  test("commerce dashboard pages load real data", async ({ page }) => {
    await signIn(page);

    for (const [route, heading] of [
      ["products", /products/i],
      ["orders", /orders/i],
      ["customers", /customers/i],
      ["payments", /payments/i],
      ["campaigns", /campaigns/i],
    ] as const) {
      await page.goto(`/console/${route}`);
      await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible({
        timeout: 30_000,
      });
      await expect(page.locator("tbody tr").first()).toBeVisible({ timeout: 20_000 });
    }

    await page.goto("/console/settings");
    await expect(page.getByRole("heading", { name: /policy limits/i })).toBeVisible({
      timeout: 30_000,
    });
  });

  test("product CRUD: add, edit price, archive", async ({ page }) => {
    await signIn(page);
    await page.goto("/console/products");
    await expect(page.locator("tbody tr").first()).toBeVisible({ timeout: 30_000 });

    const name = `E2E Cable ${Date.now()}`;
    await page.getByRole("button", { name: /add product/i }).first().click();
    const addDialog = page.getByRole("dialog", { name: /add product/i });
    await addDialog.getByLabel("Name").fill(name);
    await addDialog.getByLabel("Price (₹)").fill("499");
    await addDialog.getByRole("button", { name: /^add product$/i }).click();

    const row = page.locator("tbody tr", { hasText: name });
    await expect(row).toBeVisible({ timeout: 15_000 });

    await row.getByRole("button", { name: /edit/i }).click();
    const editDialog = page.getByRole("dialog", { name: /edit product/i });
    await editDialog.getByLabel("Price (₹)").fill("299");
    await editDialog.getByRole("button", { name: /save changes/i }).click();
    await expect(row.getByText("₹299")).toBeVisible({ timeout: 15_000 });

    page.once("dialog", (d) => d.accept());
    await row.getByRole("button", { name: /archive/i }).click();
    await expect(row).toHaveCount(0, { timeout: 15_000 });
    await page.getByLabel(/show archived/i).check();
    await expect(page.locator("tbody tr", { hasText: name })).toBeVisible({ timeout: 10_000 });
  });
});
