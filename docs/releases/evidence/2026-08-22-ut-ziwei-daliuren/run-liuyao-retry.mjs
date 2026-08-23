import playwright from "/Volumes/Lexar/code/mingli_web/web/node_modules/@playwright/test/index.js";
const { chromium } = playwright;
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(ROOT, "smoke");
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "zh-CN" });
const page = await ctx.newPage();
await page.goto("http://106.14.10.235:18080/liuyao", { waitUntil: "domcontentloaded", timeout: 45000 });
await page.waitForTimeout(600);
await page.locator("#liuyao-issue").fill("林宇航近日工作变动是否顺利，只问这一件事。");
await page.locator("#liuyao-focus").selectOption("coins");
await page.locator("#liuyao-event-time").fill("2026-08-22T19:00");
await page.locator("#liuyao-timezone").fill("Asia/Shanghai");
await page.locator("#liuyao-location").fill("福建省莆田市涵江区");
const names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"];
for (const name of names) {
  const box = page.locator("fieldset", { hasText: name }).locator("select").first();
  if (await box.count()) {
    const opts = await box.locator("option").allTextContents();
    const hit = opts.find((t) => /少阳/.test(t));
    if (hit) await box.selectOption({ label: hit });
  }
}
await page.getByRole("button", { name: /立即起卦/ }).click();
const start = Date.now();
let last = {};
while (Date.now() - start < 60000) {
  last = await page.evaluate(() => ({ url: location.href, pathname: location.pathname, text: document.body?.innerText || "" }));
  const t = last.text;
  if (/需要登录|登录后才能查看历史/.test(t)) break;
  if (/服务暂时不可用/.test(t)) break;
  if (/爻塔|世爻/.test(t) && /纳甲|六亲/.test(t)) break;
  if (/正在生成盘面|正在准备/.test(t)) {
    await page.waitForTimeout(1200);
    continue;
  }
  await page.waitForTimeout(800);
}
last.waitedMs = Date.now() - start;
await page.screenshot({ path: path.join(dir, "liuyao-05-retry.png"), fullPage: false });
await page.screenshot({ path: path.join(dir, "liuyao-05-retry-full.png"), fullPage: true });
fs.writeFileSync(path.join(dir, "liuyao-retry-text.txt"), last.text || "");
const t = last.text || "";
const result = {
  url: last.url,
  pathname: last.pathname,
  stayed: last.pathname === "/liuyao",
  loginWall: /需要登录/.test(t),
  unavailable: /服务暂时不可用/.test(t),
  hasChart: /爻塔|世爻/.test(t) && /纳甲|六亲/.test(t),
  generating: /正在生成盘面/.test(t),
  waitedMs: last.waitedMs,
};
fs.writeFileSync(path.join(dir, "liuyao-retry.json"), JSON.stringify(result, null, 2));
await browser.close();
console.log(JSON.stringify(result, null, 2));
