/**
 * Probe: submit bazi once, capture network + longer wait.
 */
import pw from "/Users/sync/code/mingli_web/web/node_modules/playwright/index.js";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = pw;
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BASE = "http://106.14.10.235:18080";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const dir = path.join(ROOT, "probe");
fs.mkdirSync(dir, { recursive: true });
const GUEST_SESSION_PATH = /\/api\/v1\/guest-sessions(?:[\/?#]|$)/i;
const REDACTED_GUEST_SESSION_BODY = "[redacted guest-session response]";

function isGuestSessionResponse(url) {
  try {
    return GUEST_SESSION_PATH.test(new URL(url).pathname);
  } catch {
    return GUEST_SESSION_PATH.test(url);
  }
}

function stripResponseUrlQuery(url) {
  try {
    const parsed = new URL(url);
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return url;
  }
}

async function captureResponse(res, url) {
  if (isGuestSessionResponse(url)) {
    return {
      status: res.status(),
      url: stripResponseUrlQuery(url),
      body: REDACTED_GUEST_SESSION_BODY,
      bodyRedacted: true,
    };
  }

  let body = "";
  try {
    body = (await res.text()).slice(0, 800);
  } catch {}
  return { status: res.status(), url, body };
}

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

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--disable-blink-features=AutomationControlled"],
});
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "zh-CN" });
const page = await ctx.newPage();
const net = [];
const cons = [];
page.on("console", (msg) => cons.push({ type: msg.type(), text: msg.text() }));
page.on("response", async (res) => {
  const url = res.url();
  if (!/api\/v1|prepare|readings|bazi|health/.test(url)) return;
  net.push(await captureResponse(res, url));
});

await page.goto(`${BASE}/bazi`, { waitUntil: "domcontentloaded", timeout: 45000 });
await page.waitForTimeout(800);
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
await page.waitForTimeout(400);

const t0 = Date.now();
await page.getByRole("button", { name: /立即排盘/ }).click();

const samples = [];
for (let i = 0; i < 60; i++) {
  await page.waitForTimeout(1000);
  const snap = await page.evaluate(() => ({
    url: location.href,
    text: (document.body?.innerText || "").slice(0, 1200),
  }));
  samples.push({ sec: i + 1, url: snap.url, hasChart: /庚辰|己酉|日主|年柱/.test(snap.text), busy: /正在准备|正在处理|排队/.test(snap.text), head: snap.text.slice(0, 280) });
  if (samples.at(-1).hasChart && !samples.at(-1).busy) break;
}

await page.screenshot({ path: path.join(dir, "final.png"), fullPage: false });
const out = {
  elapsedMs: Date.now() - t0,
  net,
  cons: cons.filter((c) => c.type === "error" || /error|fail|prepare/i.test(c.text)).slice(0, 40),
  samples,
  finalUrl: page.url(),
  finalText: await page.evaluate(() => (document.body?.innerText || "").slice(0, 2500)),
};
fs.writeFileSync(path.join(dir, "probe.json"), JSON.stringify(out, null, 2));
console.log(JSON.stringify({ elapsedMs: out.elapsedMs, netCount: net.length, samples: samples.map((s) => ({ sec: s.sec, hasChart: s.hasChart, busy: s.busy, url: s.url })), cons: out.cons.slice(0, 10), net: net.map((n) => ({ status: n.status, url: n.url })) }, null, 2));
await browser.close();
