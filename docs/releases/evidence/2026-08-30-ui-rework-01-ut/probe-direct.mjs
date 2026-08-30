/**
 * Open known prepared reading URL and check if chart renders (guest may 401).
 */
import pw from "/Users/sync/code/mingli_web/web/node_modules/playwright/index.js";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = pw;
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BASE = "http://106.14.10.235:18080";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const dir = path.join(ROOT, "probe-direct");
fs.mkdirSync(dir, { recursive: true });

async function pickSelect(page, label, needle) {
  const loc = page.getByLabel(label);
  await loc.waitFor({ timeout: 15000 });
  await page.waitForFunction(
    ({ label, needle }) => {
      const el = document.querySelector(`select[aria-label="${label}"]`);
      if (!el) return false;
      return [...el.options].some((o) => o.value === needle || (o.textContent || "").includes(needle));
    },
    { label, needle },
    { timeout: 20000 },
  );
  const value = await loc.evaluate((el, needle) => {
    const hit = [...el.options].find(
      (o) => o.value === needle || o.textContent?.trim() === needle || (o.textContent || "").includes(needle),
    );
    return hit ? hit.value : "";
  }, needle);
  await loc.selectOption(value);
}

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "zh-CN" });
const page = await ctx.newPage();
const net = [];
page.on("response", async (res) => {
  const url = res.url();
  if (!/api\/v1\/(readings|guest|profiles)/.test(url)) return;
  let body = "";
  try { body = (await res.text()).slice(0, 1200); } catch {}
  net.push({ status: res.status(), url, body });
});

// Submit once, capture reading+profile ids from preview, then force navigate with query
await page.goto(`${BASE}/bazi`, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(600);
await page.getByLabel("受测对象").fill("林宇航");
await page.getByRole("radio", { name: "男", exact: true }).click();
await pickSelect(page, "出生年份", "2000");
await pickSelect(page, "出生月份", "10");
await pickSelect(page, "出生日期", "18");
await pickSelect(page, "出生小时", "05");
await pickSelect(page, "出生分钟", "10");
await pickSelect(page, "出生省份", "福建");
await pickSelect(page, "出生城市", "莆田");
await pickSelect(page, "出生区县", "涵江");
await page.getByRole("button", { name: /立即排盘/ }).click();

// wait for preview response
let preview = null;
for (let i = 0; i < 30; i++) {
  preview = net.find((n) => n.url.includes("/readings/preview") && n.status === 201);
  if (preview) break;
  await page.waitForTimeout(200);
}
const parsed = preview ? JSON.parse(preview.body) : null;
const reading = parsed?.reading_version_id;
const profile = parsed?.profile_version_id;
const afterPreviewUrl = page.url();
await page.waitForTimeout(1500);
const stuckText = await page.evaluate(() => (document.body?.innerText || "").slice(0, 800));
await page.screenshot({ path: path.join(dir, "01-stuck.png") });

let afterNav = null;
if (reading && profile) {
  const target = `${BASE}/bazi?reading=${reading}&profile=${profile}`;
  await page.goto(target, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  afterNav = await page.evaluate(() => ({
    url: location.href,
    text: (document.body?.innerText || "").slice(0, 2000),
    hasChart: /庚辰|己酉|日主|年柱|八字命盘/.test(document.body?.innerText || ""),
    busy: /正在准备免费盘面|正在处理/.test(document.body?.innerText || ""),
  }));
  await page.screenshot({ path: path.join(dir, "02-direct-url.png"), fullPage: false });
  await page.screenshot({ path: path.join(dir, "02-direct-url-full.png"), fullPage: true });
}

const out = {
  previewStatus: parsed?.status,
  result_available: parsed?.result_available,
  poll_required: parsed?.poll_required,
  pillars: parsed?.view_model?.pillars,
  afterPreviewUrl,
  stuckSnippet: stuckText,
  afterNav,
  netBrief: net.map((n) => ({ status: n.status, url: n.url })),
};
fs.writeFileSync(path.join(dir, "out.json"), JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
await browser.close();
