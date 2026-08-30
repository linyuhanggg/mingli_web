/**
 * UI-REWORK-01-UT2 · F1 + §9.3 retest (REL2).
 * System Chrome. Evidence only. Does not change product code.
 */
import pw from "/Users/sync/code/mingli_web/web/node_modules/playwright/index.js";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = pw;

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BASE = "http://106.14.10.235:18080";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const RELEASE = "ui-rework-01-fe2-f1-20260830-184242-on-rework01";

const FORBIDDEN_INTERNAL = [
  "claim_unit_id",
  "finding_ref",
  "public_text",
  "claim_units",
  "bazi.pillar-roles-v1",
  "bazi.three-yuan-structure-v1",
  "request_id",
];

const QUEUE_NARRATIVE =
  /排队|队列中|预计等待|稍后通知|任务已创建|离开页面后任务仍会继续|服务端正在处理|正在准备免费盘面/;

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function visibleText(text) {
  return String(text || "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

async function dump(page) {
  return page.evaluate(() => {
    const headings = [...document.querySelectorAll("h1,h2,h3,h4")].map((el) => ({
      tag: el.tagName,
      text: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 120),
    }));
    const buttons = [...document.querySelectorAll("button,a")].map((el) =>
      (el.textContent || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 80),
    );
    return {
      url: location.href,
      title: document.title,
      headings,
      buttons: buttons.filter(Boolean).slice(0, 80),
      text: (document.body?.innerText || "").replace(/\n{3,}/g, "\n\n"),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      overflowX: document.documentElement.scrollWidth > window.innerWidth + 2,
      bg: getComputedStyle(document.body).backgroundColor,
      themeColor: document.querySelector('meta[name="theme-color"]')?.content || "",
    };
  });
}

async function shot(page, file, fullPage = false) {
  ensureDir(path.dirname(file));
  await page.screenshot({ path: file, fullPage });
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
  if (!value) throw new Error(`no option ${needle} in ${label}`);
  await loc.selectOption(value);
}

async function fillBazi(page) {
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
}

async function waitNatal(page, timeout = 20000) {
  const start = Date.now();
  let last = await dump(page);
  let sawQueueMs = 0;
  while (Date.now() - start < timeout) {
    last = await dump(page);
    const t = last.text || "";
    const busy = QUEUE_NARRATIVE.test(t);
    if (busy) sawQueueMs = Date.now() - start;
    // 林宇航 2000-10-18 05:10 → 庚辰 / 丙戌 / 己酉 / 丁卯
    const chart =
      (/庚辰/.test(t) || /丙戌/.test(t) || /己酉/.test(t) || /丁卯/.test(t)) &&
      (/日主|日柱|年柱|月柱|时柱|八字命盘|四柱/.test(t));
    if (chart && !busy) {
      last.elapsedMs = Date.now() - start;
      last.sawQueueMs = sawQueueMs;
      return last;
    }
    await page.waitForTimeout(250);
  }
  last.timedOut = true;
  last.elapsedMs = Date.now() - start;
  last.sawQueueMs = sawQueueMs;
  return last;
}

function checkResult93(d) {
  const text = d.text || "";
  const headings = (d.headings || []).map((h) => h.text);
  const pillarEarly =
    text.search(/年柱|月柱|日柱|时柱|庚辰|丙戌|己酉|日主/) >= 0 &&
    text.search(/年柱|月柱|日柱|时柱|庚辰|丙戌|己酉|日主/) < 2500;
  const payIdx = text.search(/购买|解锁|深读|付费/);
  const chartIdx = text.search(/八字命盘|年柱|日主|四柱/);
  const pendingCount = (text.match(/待接入/g) || []).length;
  const pendingFolded = /更多时间层/.test(text) || pendingCount <= 2;
  const internal = FORBIDDEN_INTERNAL.filter((k) => text.includes(k));
  const snake = [...text.matchAll(/\b[a-z]+_[a-z0-9_]{2,}\b/g)].map((m) => m[0]);
  const snakeFiltered = [...new Set(snake)].filter(
    (s) => !["aria_label", "data_testid"].includes(s) && !s.startsWith("http"),
  );
  const payOverChart = payIdx >= 0 && chartIdx >= 0 && payIdx < chartIdx;
  const hasPillars =
    /庚辰/.test(text) && /丙戌/.test(text) && /己酉/.test(text);
  const hasDayMaster = /日主/.test(text);
  return {
    id: "9.3",
    name: "结果页：四柱+日主主角 / 专业表在后 / 付费不压盘 / 待接入不刷屏 / 无内部字段",
    pillarEarly,
    hasPillars,
    hasDayMaster,
    chartIdx,
    payIdx,
    payOverChart,
    pendingCount,
    pendingFolded,
    headingsPreview: headings.slice(0, 12),
    internal,
    snakeFiltered: snakeFiltered.slice(0, 15),
    overflowX: d.overflowX,
    verdict:
      hasPillars &&
      hasDayMaster &&
      pillarEarly &&
      !payOverChart &&
      pendingFolded &&
      internal.length === 0
        ? "PASS"
        : "FAIL",
  };
}

function checkF1(elapsedMs, natal, afterClickText) {
  const natalText = natal.text || "";
  const stuckBusy = QUEUE_NARRATIVE.test(natalText);
  const afterBusy = QUEUE_NARRATIVE.test(afterClickText || "");
  // Brief flash during submit OK; final natal must not keep queue narrative
  const longStuck = Boolean(natal.timedOut) || (stuckBusy && (elapsedMs || 0) >= 8000);
  const fast = typeof elapsedMs === "number" && elapsedMs < 12000 && !natal.timedOut;
  const hasChart =
    (/庚辰|丙戌|己酉|丁卯/.test(natalText) && /日主|年柱|八字命盘|四柱/.test(natalText));
  const leavePageNarrative = /离开页面后任务仍会继续/.test(natalText + (afterClickText || ""));
  return {
    id: "F1",
    name: "秒出：四柱迅速上屏 / 无长时间准备盘面 / 无离开页面仍继续叙事",
    elapsedMs,
    timedOut: Boolean(natal.timedOut),
    sawQueueMs: natal.sawQueueMs || 0,
    stuckBusy,
    afterBusy,
    leavePageNarrative,
    longStuck,
    fast,
    hasChart,
    natalUrl: natal.url,
    verdict: fast && hasChart && !stuckBusy && !leavePageNarrative && !longStuck ? "PASS" : "FAIL",
  };
}

async function runViewport(browser, width, height, name) {
  const dir = path.join(ROOT, name);
  ensureDir(dir);
  const ctx = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    locale: "zh-CN",
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(45000);

  // Network probe on preview POST
  const apiHits = [];
  page.on("response", async (res) => {
    try {
      const u = res.url();
      if (!/\/api\/v1\/readings/.test(u)) return;
      const ct = res.headers()["content-type"] || "";
      let body = null;
      if (ct.includes("json")) {
        body = await res.json().catch(() => null);
      }
      apiHits.push({
        url: u,
        status: res.status(),
        method: res.request().method(),
        result_available: body?.result_available,
        poll_required: body?.poll_required,
        statusField: body?.status,
        hasViewModel: Boolean(body?.view_model || body?.document?.view_model),
      });
    } catch {
      /* ignore */
    }
  });

  // --- HOME (spot check, first round PASS) ---
  await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(700);
  const home = await dump(page);
  await shot(page, path.join(dir, "00-home-viewport.png"), false);
  fs.writeFileSync(path.join(dir, "00-home-text.txt"), visibleText(home.text));

  // --- BAZI INPUT ---
  await page.goto(`${BASE}/bazi`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(700);
  await shot(page, path.join(dir, "01-bazi-entry.png"), false);
  await fillBazi(page);
  await page.waitForTimeout(350);
  const filled = await dump(page);
  await shot(page, path.join(dir, "02-bazi-filled.png"), false);
  fs.writeFileSync(path.join(dir, "02-bazi-filled-text.txt"), visibleText(filled.text));

  // --- SUBMIT ---
  const t0 = Date.now();
  await page.getByRole("button", { name: /立即排盘/ }).click();
  await page.waitForTimeout(280);
  const afterClick = await dump(page);
  await shot(page, path.join(dir, "03-after-click.png"), false);
  fs.writeFileSync(path.join(dir, "03-after-click-text.txt"), visibleText(afterClick.text));

  const natal = await waitNatal(page, 20000);
  natal.elapsedMs = natal.elapsedMs ?? Date.now() - t0;
  const wallElapsed = Date.now() - t0;
  fs.writeFileSync(path.join(dir, "04-natal-text.txt"), visibleText(natal.text));
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await shot(page, path.join(dir, "04-natal-top.png"), false);
  await shot(page, path.join(dir, "04-natal-full.png"), true);

  // Scroll mid for professional table / pay placement
  await page.evaluate(() => window.scrollTo(0, Math.min(document.body.scrollHeight, 900)));
  await page.waitForTimeout(200);
  await shot(page, path.join(dir, "05-natal-mid.png"), false);

  const firstViewportChart = await page.evaluate(() => {
    window.scrollTo(0, 0);
    const vh = window.innerHeight;
    const needles = ["年柱", "日主", "八字命盘", "庚辰", "己酉", "丙戌", "丁卯"];
    const hits = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const t = walker.currentNode.textContent || "";
      for (const n of needles) {
        if (t.includes(n)) {
          const el = walker.currentNode.parentElement;
          if (!el) continue;
          const r = el.getBoundingClientRect();
          if (r.top >= 0 && r.top < vh && r.height > 0) hits.push({ n, top: Math.round(r.top) });
        }
      }
    }
    return hits.slice(0, 24);
  });

  // Re-scroll top and re-shot after measure
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(150);

  const resultCheck = checkResult93(natal);
  resultCheck.firstViewportChartHits = firstViewportChart;
  resultCheck.chartInFirstViewport = firstViewportChart.length > 0;
  if (!resultCheck.chartInFirstViewport) resultCheck.verdict = "FAIL";

  const f1 = checkF1(natal.elapsedMs ?? wallElapsed, natal, afterClick.text);
  f1.wallElapsedMs = wallElapsed;
  f1.apiHits = apiHits.slice(0, 12);

  const out = {
    viewport: { width, height, name },
    release: RELEASE,
    homeUrl: home.url,
    natalUrl: natal.url,
    timedOut: Boolean(natal.timedOut),
    checks: { F1: f1, "9.3": resultCheck },
  };
  fs.writeFileSync(path.join(dir, "result.json"), JSON.stringify(out, null, 2));
  await ctx.close();
  return out;
}

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--disable-blink-features=AutomationControlled"],
});

const summary = { release: RELEASE, base: BASE, at: new Date().toISOString(), viewports: {} };
try {
  for (const vp of [
    { w: 1440, h: 900, n: "1440" },
    { w: 360, h: 800, n: "360" },
  ]) {
    console.error(`running ${vp.n}...`);
    summary.viewports[vp.n] = await runViewport(browser, vp.w, vp.h, vp.n);
  }
} finally {
  await browser.close();
}

const f1All = Object.values(summary.viewports).every((v) => v.checks.F1.verdict === "PASS");
const r93All = Object.values(summary.viewports).every((v) => v.checks["9.3"].verdict === "PASS");
summary.overall = f1All && r93All ? "PASS" : "FAIL";
summary.f1 = f1All ? "PASS" : "FAIL";
summary.section93 = r93All ? "PASS" : "FAIL";

fs.writeFileSync(path.join(ROOT, "summary.json"), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
