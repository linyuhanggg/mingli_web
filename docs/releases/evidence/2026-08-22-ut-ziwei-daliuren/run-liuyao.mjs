import playwright from "/Volumes/Lexar/code/mingli_web/web/node_modules/@playwright/test/index.js";
const { chromium } = playwright;
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BASE = "http://106.14.10.235:18080";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const dir = path.join(ROOT, "smoke");

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "zh-CN" });
const page = await ctx.newPage();
const consoleErrors = [];
page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });
page.on("pageerror", (e) => consoleErrors.push(String(e)));

await page.goto(`${BASE}/liuyao`, { waitUntil: "domcontentloaded", timeout: 45000 });
await page.waitForTimeout(800);
await page.locator("#liuyao-issue").fill("林宇航近日工作变动是否顺利，只问这一件事。");
await page.locator("#liuyao-focus").selectOption("coins");
await page.locator("#liuyao-event-time").fill("2026-08-22T19:00");
await page.locator("#liuyao-timezone").fill("Asia/Shanghai");
await page.locator("#liuyao-location").fill("福建省莆田市涵江区");

const lineSelects = page.locator("select");
const n = await lineSelects.count();
for (let i = 0; i < n; i += 1) {
  const el = lineSelects.nth(i);
  const opts = await el.locator("option").allTextContents().catch(() => []);
  const hit = opts.find((t) => /少阳/.test(t));
  if (hit) await el.selectOption({ label: hit }).catch(() => {});
}
await page.getByRole("button", { name: /立即起卦/ }).click();

const start = Date.now();
let last = {};
while (Date.now() - start < 90000) {
  last = await page.evaluate(() => ({
    url: location.href,
    pathname: location.pathname,
    text: document.body?.innerText || "",
  }));
  const t = last.text;
  const generating = /正在生成盘面|正在准备|服务端正在处理/.test(t);
  const chart = /爻塔|世爻|应爻|本卦/.test(t) && /纳甲|六亲|动爻/.test(t);
  const wall = /需要登录|登录后才能查看历史/.test(t);
  const formStill = /立即起卦 · 查看本卦与变卦/.test(t) && !generating;
  if ((chart && !generating) || wall || (formStill && Date.now() - start > 8000 && !generating)) break;
  await page.waitForTimeout(1000);
}
last.waitedMs = Date.now() - start;
await page.screenshot({ path: path.join(dir, "liuyao-04-settled.png"), fullPage: false });
await page.screenshot({ path: path.join(dir, "liuyao-04-settled-full.png"), fullPage: true });
fs.writeFileSync(path.join(dir, "liuyao-final-text.txt"), last.text || "");
const t = last.text || "";
const result = {
  url: last.url,
  pathname: last.pathname,
  stayed: last.pathname === "/liuyao",
  loginWall: /需要登录|登录后才能查看历史/.test(t),
  generating: /正在生成盘面/.test(t),
  hasChart: /爻塔|世爻|应爻/.test(t) && !/立即起卦 · 查看本卦与变卦/.test(t),
  stillForm: /立即起卦 · 查看本卦与变卦/.test(t),
  white: !t.trim(),
  waitedMs: last.waitedMs,
  consoleErrors,
};
fs.writeFileSync(path.join(dir, "liuyao-result.json"), JSON.stringify(result, null, 2));
await browser.close();
console.log(JSON.stringify(result, null, 2));
