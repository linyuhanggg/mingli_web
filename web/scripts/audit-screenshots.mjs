// One-off visual-audit screenshot script (not part of the frozen e2e contract).
// Usage: node scripts/audit-screenshots.mjs [baseUrl]
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const base = process.argv[2] ?? "http://127.0.0.1:3000";
const outDir = new URL("../e2e/screenshots/audit-2026-08-14/", import.meta.url).pathname;
mkdirSync(outDir, { recursive: true });

const routes = [
  ["home", "/"],
  ["bazi-entry", "/bazi"],
  ["ziwei-entry", "/ziwei"],
  ["liuyao-entry", "/liuyao"],
  ["hecan", "/hecan"],
  ["daily", "/daily"],
  ["tools", "/tools"],
  ["library", "/library"],
  ["pricing", "/pricing"],
  ["about", "/about"],
  ["auth-login", "/auth/login"],
  ["account", "/account"],
  ["workbench-demo", "/workbench/demo"],
  ["ui-lab", "/_ui-lab"],
];

const viewports = [
  [360, 800],
  [768, 1024],
  [1024, 768],
  [1440, 900],
];

const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" });
const results = [];
for (const [w, h] of viewports) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  for (const [name, route] of routes) {
    const url = base + route;
    try {
      const resp = await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(400);
      const file = outDir + w + "/" + name + ".png";
      mkdirSync(outDir + w, { recursive: true });
      await page.screenshot({ path: file, fullPage: true });
      results.push({ viewport: w, name, route, status: resp && resp.status(), file });
      console.log("ok " + w + " " + name + " " + (resp && resp.status()));
    } catch (err) {
      results.push({ viewport: w, name, route, status: "ERR", error: String(err).slice(0, 200) });
      console.log("ERR " + w + " " + name + ": " + String(err).slice(0, 120));
    }
  }
  await page.close();
}
await browser.close();
console.log(JSON.stringify(results, null, 1));
