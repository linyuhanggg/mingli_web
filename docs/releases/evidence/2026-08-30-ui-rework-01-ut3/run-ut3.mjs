/**
 * UI-REWORK-01 / UT3 evidence runner.
 *
 * This runner is intentionally synthetic and privacy-safe:
 * - it uses the repository-approved 1994-04-30 synthetic fixture date;
 * - it creates a fresh unauthenticated browser context;
 * - it never reads, stores, or prints response bodies, cookies, or session state;
 * - text evidence stores assertions only, never arbitrary page text.
 */
import pw from "/Users/sync/code/mingli_web/web/node_modules/playwright/index.js";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = pw;
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BASE = "http://106.14.10.235:18080";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const RELEASE = "ui-rework-01-ut3-synthetic-20260831";
const SENTINEL = "SYNTHETIC-UT3-20260831";
const INPUT = Object.freeze({
  subject: "合成访客 UT3",
  date: "1994-04-30",
  time: "12:00",
  location: "Synthetic Test Location",
  timezone: "Asia/Shanghai",
  calendar: "公历",
  gender: "男",
});

const FORBIDDEN_INTERNAL = [
  "month_command",
  "ten_gods",
  "day_master",
  "raw_json",
  "view_model",
  "runtime_status",
  "poll_required",
  "result_available",
];
const SNAKE_LEAK_HINTS = ["month_command", "ten_gods", "day_master", "view_model", "runtime_status"];
const QUEUE_NARRATIVE = /排队|队列中|预计等待|稍后通知|任务已创建|离开页面后任务仍会继续|服务端正在处理|正在准备免费盘面/;
const CHART_TEXT = /免费盘面已就绪|日主|日柱|年柱|月柱|时柱|八字命盘|四柱/;
const RESULT_TEXT = /日主|日柱/;

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeJson(file, value) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function pathOnly(rawUrl) {
  try {
    return new URL(rawUrl).pathname;
  } catch {
    return "<invalid-url>";
  }
}

function pageSnapshotForEvidence(snapshot, phase) {
  const text = snapshot.text || "";
  const internalHits = FORBIDDEN_INTERNAL.filter((item) => text.includes(item));
  const snake = [...text.matchAll(/\b[a-z]+_[a-z0-9_]+\b/g)].map((match) => match[0]);
  const snakeLeaks = [...new Set(snake)].filter((item) => SNAKE_LEAK_HINTS.some((hint) => item.includes(hint)));
  return {
    schemaVersion: 1,
    sentinel: SENTINEL,
    phase,
    path: pathOnly(snapshot.url),
    bodyTextPersisted: false,
    bodyTextLength: text.length,
    hasSyntheticSubject: text.includes(INPUT.subject),
    hasChartText: CHART_TEXT.test(text),
    queueNarrative: QUEUE_NARRATIVE.test(text),
    forbiddenInternalHits: internalHits.length,
    snakeLeakHits: snakeLeaks.length,
    overflowX: Boolean(snapshot.overflowX),
  };
}

async function dump(page) {
  return page.evaluate(() => ({
    url: location.href,
    text: document.body?.innerText || "",
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
  }));
}

async function shot(page, file, fullPage = false) {
  ensureDir(path.dirname(file));
  await page.screenshot({ path: file, fullPage });
}

async function selectValue(page, label, value) {
  const control = page.getByLabel(label).first();
  await control.waitFor({ state: "visible", timeout: 10000 });
  await control.selectOption(value);
}

async function fillBazi(page) {
  await page.getByLabel("受测对象").fill(INPUT.subject);
  await page.locator('input[type="radio"][value="male"]').check();

  const [year, month, day] = INPUT.date.split("-");
  await selectValue(page, "出生年份", year);
  await selectValue(page, "出生月份", month);
  await selectValue(page, "出生日期", day);
  const [hour, minute] = INPUT.time.split(":");
  await selectValue(page, "出生小时", hour);
  await selectValue(page, "出生分钟", minute);

  const manualSwitch = page.getByRole("button", { name: "海外或找不到？直接输入", exact: true });
  if (await manualSwitch.count()) await manualSwitch.click();
  await page.getByLabel("出生地点").fill(INPUT.location);

  const timezone = page.getByLabel("出生时区");
  if (await timezone.count() && await timezone.first().isVisible()) await timezone.first().fill(INPUT.timezone);
}

async function waitNatal(page, timeout = 30000) {
  const started = Date.now();
  let last = await dump(page);
  let sawQueueMs = null;
  while (Date.now() - started < timeout) {
    last = await dump(page);
    if (QUEUE_NARRATIVE.test(last.text || "")) sawQueueMs ??= Date.now() - started;
    if (RESULT_TEXT.test(last.text || "") && /年柱|月柱|时柱|四柱|八字命盘/.test(last.text || "") && !QUEUE_NARRATIVE.test(last.text || "")) {
      return {
        ...last,
        timedOut: false,
        elapsedMs: Date.now() - started,
        sawQueueMs,
      };
    }
    await page.waitForTimeout(500);
  }
  return {
    ...last,
    timedOut: true,
    elapsedMs: Date.now() - started,
    sawQueueMs,
  };
}

async function measureFirstViewport(page) {
  return page.evaluate(() => {
    window.scrollTo(0, 0);
    const vh = window.innerHeight;
    const needles = ["日主", "日柱", "年柱", "月柱", "时柱", "四柱", "八字命盘", "免费盘面已就绪"];
    const hits = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const text = walker.currentNode.textContent || "";
      for (const needle of needles) {
        if (!text.includes(needle)) continue;
        const element = walker.currentNode.parentElement;
        if (!element) continue;
        const rect = element.getBoundingClientRect();
        if (rect.height <= 0) continue;
        hits.push({
          needle,
          top: Math.round(rect.top),
          inFirstViewport: rect.top >= -1 && rect.top < vh && rect.bottom > 1,
        });
      }
    }
    const chartHits = hits.filter((hit) => hit.inFirstViewport);
    const pillarHits = chartHits.filter((hit) => ["年柱", "月柱", "日柱", "时柱", "四柱"].includes(hit.needle));
    const dayMasterHits = chartHits.filter((hit) => ["日主", "日柱"].includes(hit.needle));
    return {
      vh,
      scrollY: window.scrollY,
      chartInFirstViewport: chartHits.length > 0,
      pillarsInFirstViewport: pillarHits.length > 0,
      dayMasterInFirstViewport: dayMasterHits.length > 0,
      hitCount: hits.length,
    };
  });
}

function checkF1(natal) {
  const text = natal.text || "";
  const fast = !natal.timedOut && natal.elapsedMs < 10000;
  const ready = RESULT_TEXT.test(text) && /年柱|月柱|时柱|四柱|八字命盘/.test(text);
  const chart = ready || CHART_TEXT.test(text);
  const queue = QUEUE_NARRATIVE.test(text);
  return {
    id: "F1",
    name: "free chart readiness",
    elapsedMs: natal.elapsedMs,
    timedOut: Boolean(natal.timedOut),
    sawQueueMs: natal.sawQueueMs,
    fast,
    ready,
    chart,
    queue,
    verdict: fast && ready && chart && !queue ? "PASS" : "FAIL",
  };
}

function checkF2(measure) {
  const pass = measure.chartInFirstViewport && (measure.pillarsInFirstViewport || measure.dayMasterInFirstViewport);
  return {
    id: "F2",
    name: "chart-first first viewport",
    chartInFirstViewport: measure.chartInFirstViewport,
    pillarsInFirstViewport: measure.pillarsInFirstViewport,
    dayMasterInFirstViewport: measure.dayMasterInFirstViewport,
    verdict: pass ? "PASS" : "FAIL",
  };
}

function checkF3(natalText) {
  const text = natalText || "";
  const internalHits = FORBIDDEN_INTERNAL.filter((item) => text.includes(item));
  const snake = [...text.matchAll(/\b[a-z]+_[a-z0-9_]+\b/g)].map((match) => match[0]);
  const snakeLeaks = [...new Set(snake)].filter((item) => SNAKE_LEAK_HINTS.some((hint) => item.includes(hint)));
  return {
    id: "F3",
    name: "no engineering field leak",
    forbiddenInternalHits: internalHits.length,
    snakeLeakHits: snakeLeaks.length,
    verdict: internalHits.length === 0 && snakeLeaks.length === 0 ? "PASS" : "FAIL",
  };
}

async function runViewport(browser, width, height, name) {
  const dir = path.join(ROOT, name);
  ensureDir(dir);
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, locale: "zh-CN" });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  const network = [];
  page.on("response", (response) => {
    try {
      const url = new URL(response.url());
      if (!/^\/api\/v\d+\/readings/.test(url.pathname)) return;
      network.push({ path: url.pathname, method: response.request().method(), status: response.status() });
    } catch {
      // Ignore non-URL responses; no response body is inspected.
    }
  });

  await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(500);
  const home = await dump(page);
  await shot(page, path.join(dir, "00-home-viewport.png"));
  fs.writeFileSync(path.join(dir, "00-home-text.txt"), `${JSON.stringify(pageSnapshotForEvidence(home, "home"), null, 2)}\n`, "utf8");

  await page.goto(`${BASE}/bazi`, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(500);
  await shot(page, path.join(dir, "01-bazi-entry.png"));
  await fillBazi(page);
  await page.waitForTimeout(250);
  const filled = await dump(page);
  await shot(page, path.join(dir, "02-bazi-filled.png"));
  fs.writeFileSync(path.join(dir, "02-bazi-filled-text.txt"), `${JSON.stringify(pageSnapshotForEvidence(filled, "filled"), null, 2)}\n`, "utf8");

  const started = Date.now();
  await page.getByRole("button", { name: /立即排盘/ }).click();
  await page.waitForTimeout(250);
  const afterClick = await dump(page);
  await shot(page, path.join(dir, "03-after-click.png"));
  fs.writeFileSync(path.join(dir, "03-after-click-text.txt"), `${JSON.stringify(pageSnapshotForEvidence(afterClick, "after-click"), null, 2)}\n`, "utf8");

  const natal = await waitNatal(page);
  const wallElapsedMs = Date.now() - started;
  fs.writeFileSync(path.join(dir, "04-natal-text.txt"), `${JSON.stringify(pageSnapshotForEvidence(natal, "natal"), null, 2)}\n`, "utf8");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(250);
  const measure = await measureFirstViewport(page);
  await shot(page, path.join(dir, "04-natal-top.png"));
  await shot(page, path.join(dir, "04-natal-full.png"), true);
  await shot(page, path.join(ROOT, `probe-${name}`, "top.png"));

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(250);
  await shot(page, path.join(dir, "05-natal-mid.png"));
  const shenshaY = await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      if (/神煞|五行盘点|判定过程/.test(walker.currentNode.textContent || "")) {
        const element = walker.currentNode.parentElement;
        if (!element) continue;
        const rect = element.getBoundingClientRect();
        return Math.max(0, Math.round(window.scrollY + rect.top - 120));
      }
    }
    return 0;
  });
  await page.evaluate((y) => window.scrollTo(0, y), shenshaY);
  await page.waitForTimeout(250);
  await shot(page, path.join(dir, "06-shensha-region.png"));

  const output = {
    schemaVersion: 1,
    sentinel: SENTINEL,
    release: RELEASE,
    viewport: { width, height, name },
    homePath: pathOnly(home.url),
    natalPath: pathOnly(natal.url),
    timedOut: Boolean(natal.timedOut),
    homeSpot: /开始排八字|八字/.test(home.text || "") ? "PASS" : "FAIL",
    fillSpot: (filled.text || "").includes(INPUT.subject) ? "PASS" : "FAIL",
    inputIsSynthetic: true,
    measure,
    checks: { F1: checkF1({ ...natal, elapsedMs: natal.elapsedMs ?? wallElapsedMs }), F2: checkF2(measure), F3: checkF3(natal.text) },
    networkEntryCount: network.length,
    bodyCapture: "none",
    cookieCapture: "none",
  };
  writeJson(path.join(dir, "result.json"), output);
  return { output, network };
}

const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ["--disable-gpu"] });
const results = {};
try {
  for (const viewport of [
    { width: 1440, height: 900, name: "1440" },
    { width: 360, height: 800, name: "360" },
  ]) {
    console.error(`running ${viewport.name}`);
    results[viewport.name] = await runViewport(browser, viewport.width, viewport.height, viewport.name);
  }
} finally {
  await browser.close();
}

const outputs = Object.fromEntries(Object.entries(results).map(([name, value]) => [name, value.output]));
const allF1 = Object.values(outputs).every((value) => value.checks.F1.verdict === "PASS");
const allF2 = Object.values(outputs).every((value) => value.checks.F2.verdict === "PASS");
const allF3 = Object.values(outputs).every((value) => value.checks.F3.verdict === "PASS");
const allHome = Object.values(outputs).every((value) => value.homeSpot === "PASS");
const allFill = Object.values(outputs).every((value) => value.fillSpot === "PASS");
const allOverflowFree = Object.values(outputs).every((value) => !value.measure.overflowX);
const networkEntries = Object.values(results).flatMap((value) => value.network);

writeJson(path.join(ROOT, "network-capture.json"), {
  schemaVersion: 1,
  sentinel: SENTINEL,
  bodyCapture: "none",
  cookiesCaptured: false,
  storageStateCaptured: false,
  entries: networkEntries,
});
writeJson(path.join(ROOT, "probe-timing.json"), {
  schemaVersion: 1,
  sentinel: SENTINEL,
  release: RELEASE,
  viewports: Object.fromEntries(Object.entries(outputs).map(([name, value]) => [name, { elapsedMs: value.checks.F1.elapsedMs, timedOut: value.timedOut }])),
});
const summary = {
  schemaVersion: 1,
  sentinel: SENTINEL,
  release: RELEASE,
  inputProfile: "repository-approved synthetic fixture; no personal profile",
  bodyCapture: "none",
  cookiesCaptured: false,
  f1: allF1 ? "PASS" : "FAIL",
  f2: allF2 ? "PASS" : "FAIL",
  f3: allF3 ? "PASS" : "FAIL",
  home: allHome ? "PASS" : "FAIL",
  fill: allFill ? "PASS" : "FAIL",
  overflowX: allOverflowFree ? "PASS" : "FAIL",
  overall: allF1 && allF2 && allF3 && allHome && allFill && allOverflowFree ? "PASS" : "FAIL",
  viewports: outputs,
};
writeJson(path.join(ROOT, "summary.json"), summary);
fs.writeFileSync(
  path.join(ROOT, "VERDICT.md"),
  `## UI-REWORK-01 UT3 privacy-safe evidence\n\n- Sentinel: \`${SENTINEL}\`\n- Input: repository-approved synthetic fixture only; no personal profile or authenticated session\n- Browser: fresh context; response bodies, cookies, storage state, and full page text were not captured\n- Text evidence: assertion summaries only\n- Overall: **${summary.overall}**\n- F1 readiness: **${summary.f1}**\n- F2 first viewport: **${summary.f2}**\n- F3 no engineering leak: **${summary.f3}**\n`,
  "utf8",
);
fs.writeFileSync(
  path.join(ROOT, "run.log"),
  [
    `sentinel=${SENTINEL}`,
    "input_profile=repository-approved-synthetic",
    "body_capture=none",
    "cookie_capture=none",
    `overall=${summary.overall}`,
  ].join("\n") + "\n",
  "utf8",
);
console.log(JSON.stringify({ sentinel: SENTINEL, overall: summary.overall, f1: summary.f1, f2: summary.f2, f3: summary.f3 }, null, 2));
