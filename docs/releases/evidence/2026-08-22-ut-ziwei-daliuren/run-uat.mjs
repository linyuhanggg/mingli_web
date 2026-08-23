/**
 * One-shot UAT for UAT-ZW-DL-WIRE. Evidence only. Does not change product code.
 */
import playwright from "/Volumes/Lexar/code/mingli_web/web/node_modules/@playwright/test/index.js";
const { chromium } = playwright;
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BASE = "http://106.14.10.235:18080";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const IDENTITY = {
  subject: "林宇航",
  gender: "男",
  year: "2000",
  month: "10",
  day: "18",
  hour: "05",
  minute: "10",
  location: "福建省莆田市涵江区",
};
const QUESTION = "林宇航近日工作变动是否顺利，只问这一件事。";
const EVENT_TIME = "2026-08-22T19:00";

const OLD_ZIWEI = ["十二宫与主星", "本命四化事实"];
const OLD_DALIUREN = ["大六壬结构事实", "有界应期候选"];
const FORBIDDEN_KEYS = [
  "calculated_strength_not_verdict",
  "facts_only",
  "schema_version",
  "core_facts",
  "view_model",
  "hard_verdict",
  "source_conditioned_patterns",
  "predicate_matched_not_verdict",
  "GAP-ZW",
  "GAP-DL",
];
const LUCK_WORDS = ["大吉", "大凶", "吉凶", "喜用", "忌神"];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function visibleTextFrom(text) {
  return String(text || "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function hits(text, needles) {
  return needles.filter((n) => text.includes(n));
}

async function dumpPage(page) {
  return page.evaluate(() => {
    const login = [...document.querySelectorAll("a,button")].some((el) =>
      /^\s*登录\s*$/.test(el.textContent || ""),
    );
    const captions = [...document.querySelectorAll("caption")].map((el) =>
      (el.textContent || "").trim(),
    );
    const tables = [...document.querySelectorAll("table")].map((el) => ({
      caption: (el.querySelector("caption")?.textContent || "").trim(),
      name: el.getAttribute("aria-label") || "",
    }));
    const regions = [...document.querySelectorAll("[role='region']")].map((el) =>
      (el.getAttribute("aria-label") || el.getAttribute("aria-labelledby") || "").trim(),
    );
    const alerts = [...document.querySelectorAll("[role='alert']")].map((el) =>
      (el.textContent || "").trim(),
    );
    const buttons = [...document.querySelectorAll("button")].map((el) =>
      (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 80),
    );
    const highlight = [...document.querySelectorAll("[data-highlight]")].map((el) => ({
      highlight: el.getAttribute("data-highlight"),
      label: (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 80),
    }));
    const voids = [...document.querySelectorAll("[data-void='true']")].length;
    return {
      url: location.href,
      pathname: location.pathname,
      title: document.title,
      loginLink: login,
      captions,
      tables,
      regions,
      alerts,
      buttons: buttons.filter(Boolean).slice(0, 40),
      highlight,
      voids,
      text: (document.body?.innerText || "").replace(/\n{3,}/g, "\n\n"),
    };
  });
}

async function screenshot(page, file) {
  ensureDir(path.dirname(file));
  await page.screenshot({ path: file, fullPage: false });
  await page.screenshot({
    path: file.replace(/\.png$/, "-full.png"),
    fullPage: true,
  });
}

async function fillNatal(page, productId) {
  await page.locator(`#${productId}-subject`).fill(IDENTITY.subject);
  const gender = page.getByRole("radio", { name: IDENTITY.gender, exact: true });
  if (await gender.count()) {
    await gender.click();
  } else {
    await page.getByRole("button", { name: IDENTITY.gender, exact: true }).click();
  }
  await page.getByLabel("出生年份").selectOption(IDENTITY.year);
  await page.getByLabel("出生月份").selectOption(IDENTITY.month);
  await page.getByLabel("出生日期").selectOption(IDENTITY.day);
  await page.getByLabel("出生小时").selectOption(IDENTITY.hour);
  await page.getByLabel("出生分钟").selectOption(IDENTITY.minute);
  const province = page.getByLabel("出生省份");
  if (await province.count()) {
    await page.waitForFunction(() => {
      const el = document.querySelector('select[aria-label="出生省份"]');
      return el && [...el.options].some((o) => o.value.includes("福建"));
    }, null, { timeout: 15000 });
    const provinceValue = await province.evaluate((el) => {
      const hit = [...el.options].find((o) => /福建/.test(o.value) || /福建/.test(o.textContent || ""));
      return hit ? hit.value : "";
    });
    await province.selectOption(provinceValue);
    const city = page.getByLabel("出生城市");
    await page.waitForFunction(() => {
      const el = document.querySelector('select[aria-label="出生城市"]');
      return el && [...el.options].some((o) => /莆田/.test(o.value) || /莆田/.test(o.textContent || ""));
    }, null, { timeout: 8000 });
    const cityValue = await city.evaluate((el) => {
      const hit = [...el.options].find((o) => /莆田/.test(o.value) || /莆田/.test(o.textContent || ""));
      return hit ? hit.value : "";
    });
    await city.selectOption(cityValue);
    const area = page.getByLabel("出生区县");
    await page.waitForFunction(() => {
      const el = document.querySelector('select[aria-label="出生区县"]');
      return el && [...el.options].some((o) => /涵江/.test(o.value) || /涵江/.test(o.textContent || ""));
    }, null, { timeout: 8000 });
    const areaValue = await area.evaluate((el) => {
      const hit = [...el.options].find((o) => /涵江/.test(o.value) || /涵江/.test(o.textContent || ""));
      return hit ? hit.value : "";
    });
    await area.selectOption(areaValue);
    return;
  }
  const switcher = page.getByRole("button", { name: "海外或找不到？直接输入" });
  if (await switcher.count()) await switcher.click();
  await page.getByLabel("出生地点").fill(IDENTITY.location);
}

async function fillEvent(page, productId, extra = async () => {}) {
  await page.locator(`#${productId}-issue`).fill(QUESTION);
  await extra();
  await page.locator(`#${productId}-event-time`).fill(EVENT_TIME);
  const tz = page.locator(`#${productId}-timezone`);
  if (await tz.count()) {
    await tz.fill("Asia/Shanghai");
  }
  await page.locator(`#${productId}-location`).fill(IDENTITY.location);
}

async function waitSettled(page, stayPath, timeout = 45000) {
  const start = Date.now();
  let last = await dumpPage(page);
  while (Date.now() - start < timeout) {
    last = await dumpPage(page);
    const t = last.text || "";
    const preparing = /准备解读|事实已就绪|正在生成|正在排盘|正在起课/.test(t);
    const chartish =
      /十二宫环盘|命宫|课传|本卦|互卦|变卦|四柱|日主|爻/.test(t) ||
      last.regions.some((r) => /环盘|课传|命盘|盘面/.test(r));
    const wall = /登录后继续|请先登录|验证码/.test(t) && /account\/history|\/auth\/login/.test(last.pathname);
    if (!preparing && (chartish || wall || last.pathname !== stayPath)) {
      return { ...last, waitedMs: Date.now() - start };
    }
    await page.waitForTimeout(800);
  }
  return { ...last, waitedMs: Date.now() - start, timedOut: true };
}

function analyzeZiwei(dump, stayPath) {
  const text = dump.text || "";
  const oldHits = hits(text, OLD_ZIWEI);
  const captionHits = (dump.captions || []).filter((c) => OLD_ZIWEI.includes(c));
  return {
    url: dump.url,
    pathname: dump.pathname,
    stayed: dump.pathname === stayPath,
    loginWall: /\/account\/history|\/auth\/login/.test(dump.pathname),
    loginLink: dump.loginLink,
    oldTable: oldHits.length > 0 || captionHits.length > 0,
    oldHits,
    captionHits,
    hasRing: /十二宫环盘|命宫/.test(text) || (dump.regions || []).some((r) => /十二宫|环盘/.test(r)),
    hasMing: /命宫/.test(text),
    deepClosed: /测试期未开放/.test(text),
    priceCard: /¥|￥|立即支付|去结账|价格/.test(text) && /深读|绑定当前/.test(text),
    forbiddenHits: hits(text, FORBIDDEN_KEYS),
    luckHits: hits(text, LUCK_WORDS),
    emptyBoard: !/命宫|十二宫/.test(text),
    captions: dump.captions,
    regions: dump.regions,
    alerts: dump.alerts,
    highlight: dump.highlight,
    waitedMs: dump.waitedMs,
    timedOut: dump.timedOut || false,
  };
}

function analyzeDaliuren(dump, stayPath) {
  const text = dump.text || "";
  const oldHits = hits(text, OLD_DALIUREN);
  const captionHits = (dump.captions || []).filter((c) =>
    ["四课", "三传", ...OLD_DALIUREN].includes(c),
  );
  const hasKeChuanRegion = (dump.regions || []).some((r) => r === "课传");
  const hasOldLessonCaption = (dump.captions || []).includes("四课") || (dump.captions || []).includes("三传");
  return {
    url: dump.url,
    pathname: dump.pathname,
    stayed: dump.pathname === stayPath,
    loginWall: /\/account\/history|\/auth\/login/.test(dump.pathname),
    loginLink: dump.loginLink,
    oldTable: oldHits.length > 0 || captionHits.length > 0,
    oldHits,
    captionHits,
    hasKeChuan: hasKeChuanRegion || /课传/.test(text),
    hasOldLessonCaption,
    timingTable: /有界应期候选/.test(text) || (dump.captions || []).includes("有界应期候选"),
    timingArea: /应期/.test(text),
    deepClosed: /测试期未开放/.test(text),
    priceCard: /¥|￥|立即支付|去结账/.test(text),
    forbiddenHits: hits(text, FORBIDDEN_KEYS),
    luckHits: hits(text, LUCK_WORDS),
    captions: dump.captions,
    regions: dump.regions,
    alerts: dump.alerts,
    waitedMs: dump.waitedMs,
    timedOut: dump.timedOut || false,
  };
}

function analyzeSmoke(dump, stayPath, kind) {
  const text = dump.text || "";
  const white = !text || text.length < 40;
  return {
    url: dump.url,
    pathname: dump.pathname,
    stayed: dump.pathname === stayPath || dump.pathname.startsWith(stayPath),
    loginWall: /\/account\/history|\/auth\/login/.test(dump.pathname) && /请先登录|登录后/.test(text),
    hasChart:
      kind === "bazi"
        ? /四柱|日主|年柱|月柱/.test(text)
        : kind === "liuyao"
          ? /爻|本卦|世|应/.test(text)
          : /本卦|互卦|变卦|体|用/.test(text),
    white,
    consoleErrors: dump.consoleErrors || [],
    waitedMs: dump.waitedMs,
    timedOut: dump.timedOut || false,
    textSample: text.slice(0, 800),
  };
}

async function withConsole(page, bucket) {
  page.on("console", (msg) => {
    if (msg.type() === "error") bucket.push(msg.text());
  });
  page.on("pageerror", (err) => bucket.push(String(err)));
}

async function runZiwei(browser, width, height) {
  const dir = path.join(ROOT, String(width));
  ensureDir(dir);
  const ctx = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    locale: "zh-CN",
  });
  const page = await ctx.newPage();
  const consoleErrors = [];
  await withConsole(page, consoleErrors);
  await page.goto(`${BASE}/ziwei`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(800);
  const entry = await dumpPage(page);
  fs.writeFileSync(path.join(dir, "ziwei-00-entry-text.txt"), visibleTextFrom(entry.text));
  await screenshot(page, path.join(dir, "ziwei-00-entry.png"));
  await fillNatal(page, "ziwei");
  await page.waitForTimeout(300);
  const filled = await dumpPage(page);
  fs.writeFileSync(path.join(dir, "ziwei-01-filled-text.txt"), visibleTextFrom(filled.text));
  await screenshot(page, path.join(dir, "ziwei-01-filled.png"));
  const submit = page.getByRole("button", { name: /立即排盘/ });
  await submit.click();
  await page.waitForTimeout(500);
  const afterClick = await dumpPage(page);
  await screenshot(page, path.join(dir, "ziwei-02-after-click.png"));
  const settled = await waitSettled(page, "/ziwei", 50000);
  settled.consoleErrors = consoleErrors;
  fs.writeFileSync(path.join(dir, "ziwei-03-settled-text.txt"), visibleTextFrom(settled.text));
  await screenshot(page, path.join(dir, "ziwei-03-settled.png"));

  let clickedPalace = null;
  if (!analyzeZiwei(settled, "/ziwei").oldTable) {
    const palace = page.locator("button[aria-label*='宫'], [data-branch], [data-palace]").first();
    if (await palace.count()) {
      await palace.click();
      await page.waitForTimeout(400);
      clickedPalace = await dumpPage(page);
      await screenshot(page, path.join(dir, "ziwei-04-palace-click.png"));
      fs.writeFileSync(
        path.join(dir, "ziwei-04-palace-text.txt"),
        visibleTextFrom(clickedPalace.text),
      );
    }
    // scroll for deep-read
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(400);
    const bottom = await dumpPage(page);
    await screenshot(page, path.join(dir, "ziwei-05-bottom.png"));
    fs.writeFileSync(path.join(dir, "ziwei-05-bottom-text.txt"), visibleTextFrom(bottom.text));
    settled.text = `${settled.text}\n${bottom.text}`;
    settled.captions = [...new Set([...(settled.captions || []), ...(bottom.captions || [])])];
    settled.regions = [...new Set([...(settled.regions || []), ...(bottom.regions || [])])];
  }

  const analysis = analyzeZiwei(settled, "/ziwei");
  analysis.consoleErrors = consoleErrors;
  analysis.entryLogin = entry.loginLink;
  analysis.afterClickUrl = afterClick.url;
  analysis.palaceClick = clickedPalace
    ? { highlight: clickedPalace.highlight, url: clickedPalace.url }
    : null;
  fs.writeFileSync(path.join(dir, "ziwei-result.json"), JSON.stringify(analysis, null, 2));
  await ctx.close();
  return analysis;
}

async function runDaliuren(browser, width, height) {
  const dir = path.join(ROOT, String(width));
  ensureDir(dir);
  const ctx = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    locale: "zh-CN",
  });
  const page = await ctx.newPage();
  const consoleErrors = [];
  await withConsole(page, consoleErrors);
  await page.goto(`${BASE}/daliuren`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(800);
  const entry = await dumpPage(page);
  fs.writeFileSync(path.join(dir, "daliuren-00-entry-text.txt"), visibleTextFrom(entry.text));
  await screenshot(page, path.join(dir, "daliuren-00-entry.png"));
  await fillEvent(page, "daliuren", async () => {
    await page.locator("#daliuren-focus").selectOption("progress");
  });
  await page.waitForTimeout(300);
  const filled = await dumpPage(page);
  fs.writeFileSync(path.join(dir, "daliuren-01-filled-text.txt"), visibleTextFrom(filled.text));
  await screenshot(page, path.join(dir, "daliuren-01-filled.png"));
  await page.getByRole("button", { name: /立即起课/ }).click();
  await page.waitForTimeout(500);
  const afterClick = await dumpPage(page);
  await screenshot(page, path.join(dir, "daliuren-02-after-click.png"));
  const settled = await waitSettled(page, "/daliuren", 50000);
  settled.consoleErrors = consoleErrors;
  fs.writeFileSync(path.join(dir, "daliuren-03-settled-text.txt"), visibleTextFrom(settled.text));
  await screenshot(page, path.join(dir, "daliuren-03-settled.png"));
  if (!analyzeDaliuren(settled, "/daliuren").oldTable) {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(400);
    const bottom = await dumpPage(page);
    await screenshot(page, path.join(dir, "daliuren-04-bottom.png"));
    fs.writeFileSync(path.join(dir, "daliuren-04-bottom-text.txt"), visibleTextFrom(bottom.text));
    settled.text = `${settled.text}\n${bottom.text}`;
    settled.captions = [...new Set([...(settled.captions || []), ...(bottom.captions || [])])];
    settled.regions = [...new Set([...(settled.regions || []), ...(bottom.regions || [])])];
  }
  const analysis = analyzeDaliuren(settled, "/daliuren");
  analysis.consoleErrors = consoleErrors;
  analysis.entryLogin = entry.loginLink;
  analysis.afterClickUrl = afterClick.url;
  fs.writeFileSync(path.join(dir, "daliuren-result.json"), JSON.stringify(analysis, null, 2));
  await ctx.close();
  return analysis;
}

async function runSmoke(browser, route, productId, fill, submitName, kind, width = 1440, height = 900) {
  const dir = path.join(ROOT, "smoke");
  ensureDir(dir);
  const ctx = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    locale: "zh-CN",
  });
  const page = await ctx.newPage();
  const consoleErrors = [];
  await withConsole(page, consoleErrors);
  await page.goto(`${BASE}${route}`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(600);
  await screenshot(page, path.join(dir, `${kind}-00-entry.png`));
  await fill(page, productId);
  await screenshot(page, path.join(dir, `${kind}-01-filled.png`));
  await page.getByRole("button", { name: submitName }).click();
  const settled = await waitSettled(page, route, 50000);
  settled.consoleErrors = consoleErrors;
  await screenshot(page, path.join(dir, `${kind}-02-settled.png`));
  fs.writeFileSync(path.join(dir, `${kind}-settled-text.txt`), visibleTextFrom(settled.text));
  const analysis = analyzeSmoke(settled, route, kind);
  analysis.consoleErrors = consoleErrors;
  fs.writeFileSync(path.join(dir, `${kind}-result.json`), JSON.stringify(analysis, null, 2));
  await ctx.close();
  return analysis;
}

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: true,
});

const out = {
  startedAt: new Date().toISOString(),
  entry: BASE,
  identity: "林宇航 / 男 / 2000-10-18 05:10 / 福建省莆田市涵江区",
};

try {
  const step = async (name, fn) => {
    try {
      out[name] = await fn();
    } catch (err) {
      out[name] = { error: String(err && err.stack ? err.stack : err) };
      out.errors = [...(out.errors || []), { name, error: out[name].error }];
    }
  };
  await step("ziwei1440", () => runZiwei(browser, 1440, 900));
  await step("daliuren1440", () => runDaliuren(browser, 1440, 900));
  await step("ziwei360", () => runZiwei(browser, 360, 800));
  await step("daliuren360", () => runDaliuren(browser, 360, 800));
  await step("bazi", () => runSmoke(browser, "/bazi", "bazi", fillNatal, /立即排盘/, "bazi"));
  await step("liuyao", () =>
    runSmoke(
      browser,
      "/liuyao",
      "liuyao",
      async (page) => {
        await page.locator("#liuyao-issue").fill(QUESTION);
        await page.locator("#liuyao-focus").selectOption("coins");
        await page.locator("#liuyao-event-time").fill(EVENT_TIME);
        await page.locator("#liuyao-timezone").fill("Asia/Shanghai");
        await page.locator("#liuyao-location").fill(IDENTITY.location);
      },
      /立即起卦|查看/,
      "liuyao",
    ),
  );
  await step("meihua", () =>
    runSmoke(
      browser,
      "/meihua",
      "meihua",
      async (page) => {
        await fillEvent(page, "meihua", async () => {
          await page.locator("#meihua-focus").selectOption("outcome");
        });
      },
      /立即起卦/,
      "meihua",
    ),
  );
} catch (err) {
  out.error = String(err && err.stack ? err.stack : err);
} finally {
  out.finishedAt = new Date().toISOString();
  fs.writeFileSync(path.join(ROOT, "raw-run.json"), JSON.stringify(out, null, 2));
  await browser.close();
}

console.log(JSON.stringify({
  error: out.error || null,
  ziwei1440: out.ziwei1440 && {
    url: out.ziwei1440.url,
    oldTable: out.ziwei1440.oldTable,
    hasRing: out.ziwei1440.hasRing,
    deepClosed: out.ziwei1440.deepClosed,
    loginWall: out.ziwei1440.loginWall,
  },
  daliuren1440: out.daliuren1440 && {
    url: out.daliuren1440.url,
    oldTable: out.daliuren1440.oldTable,
    hasKeChuan: out.daliuren1440.hasKeChuan,
    deepClosed: out.daliuren1440.deepClosed,
    loginWall: out.daliuren1440.loginWall,
  },
  ziwei360: out.ziwei360 && { url: out.ziwei360.url, oldTable: out.ziwei360.oldTable, emptyBoard: out.ziwei360.emptyBoard },
  daliuren360: out.daliuren360 && { url: out.daliuren360.url, oldTable: out.daliuren360.oldTable },
  bazi: out.bazi && { url: out.bazi.url, hasChart: out.bazi.hasChart, white: out.bazi.white },
  liuyao: out.liuyao && { url: out.liuyao.url, hasChart: out.liuyao.hasChart, white: out.liuyao.white },
  meihua: out.meihua && { url: out.meihua.url, hasChart: out.meihua.hasChart, white: out.meihua.white },
}, null, 2));
