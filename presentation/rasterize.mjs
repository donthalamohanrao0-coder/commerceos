// SVG -> PNG at 1920x1080 using Playwright's chromium (deviceScaleFactor 1).
import { readFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(here, "..", "apps", "web", "package.json"));
const { chromium } = require("@playwright/test");

const IMG = join(here, "assets", "images");
mkdirSync(IMG, { recursive: true });
const names = ["cover-hero", "section-texture", "close-bg"];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
for (const n of names) {
  const svg = readFileSync(join(IMG, `${n}.svg`), "utf8");
  await page.setContent(
    `<!doctype html><html><body style="margin:0">${svg}</body></html>`,
    { waitUntil: "networkidle" },
  );
  await page.screenshot({ path: join(IMG, `${n}.png`), clip: { x: 0, y: 0, width: 1920, height: 1080 } });
  console.log("  ✓", `${n}.png`);
}
await browser.close();
