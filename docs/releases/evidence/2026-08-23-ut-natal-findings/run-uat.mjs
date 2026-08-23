/**
 * T-0821-UT-5 evidence only. System Chrome. Does not change product code.
 */
import playwright from "/Volumes/Lexar/code/mingli_web/web/node_modules/@playwright/test/index.js";
const { chromium } = playwright;
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BASE = "http://106.14.10.235:18080";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const FORBIDDEN = [
  "bazi.pillar-roles-v1",
  "bazi.three-yuan-structure-v1",
  "bazi.element-flow-inventory-v1",
  "claim_unit_id",
  "finding_ref",
  "public_text",
  "claim_units",
];
const TARGET_TITLES = ["柱位职分", "三元结构", "五行流转盘点"];

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
    const headings = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].map((el) => ({
      tag: el.tagName,
      text: (el.textContent || "").trim().replace(/\s+/g, " "),
    }));
    const buttons = [...document.querySelectorAll("button,a")].map((el) =>
      (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 80),
    );
    return {
      url: location.href,
      title: document.title,
      headings,
      buttons: buttons.filter(Boolean).slice(0, 60),
      text: (document.body?.innerText || "").replace(/\n{3,}/g, "\n\n"),
    };
  });
}

async function shot(page, file) {
  ensureDir(path.dirname(file));
  await page.screenshot({ path: file, fullPage: false });
}

async function pickSelect(page, label, needle) {
  const loc = page.getByLabel(label);
  await loc.waitFor({ timeout: 10000 });
  await page.waitForFunction(
    ({ label, needle }) => {
      const el = document.querySelector(`select[aria-label="${label}"]`);
      if (!el) return false;
      return [...el.options].some((o) => o.value === needle || (o.textContent || "").includes(needle));
    },
    { label, needle },
    { timeout: 15000 },
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

async function waitNatal(page, timeout = 60000) {
  const start = Date.now();
  let last = await dump(page);
  while (Date.now() - start < timeout) {
    last = await dump(page);
    const t = last.text || "";
    const busy = /正在准备免费盘面|正在排盘|正在生成|准备解读|服务端正在处理/.test(t);
    const chart =
      /庚辰/.test(t) && /丙戌/.test(t) && (/日主|日柱|己土/.test(t) || /己酉/.test(t));
    if (chart && !busy) return last;
    await page.waitForTimeout(800);
  }
  last.timedOut = true;
  return last;
}

async function scrollShots(page, dir, prefix) {
  const texts = [];
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(250);
  await shot(page, path.join(dir, `${prefix}-natal-top.png`));
  const height = await page.evaluate(() => document.body.scrollHeight);
  const viewport = await page.viewportSize();
  const step = viewport?.height ? Math.floor(viewport.height * 0.7) : 640;
  let y = 0;
  let i = 0;
  while (y < height + 20 && i < 16) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(220);
    await shot(page, path.join(dir, `${prefix}-scroll-${String(i).padStart(2, "0")}.png`));
    const d = await dump(page);
    texts.push(`--- scroll ${i} y=${y} ---\n${d.text}`);
    y += step;
    i += 1;
  }
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(250);
  await shot(page, path.join(dir, `${prefix}-bottom.png`));
  const full = await dump(page);
  fs.writeFileSync(path.join(dir, `${prefix}-full-text.txt`), visibleText(full.text));
  fs.writeFileSync(path.join(dir, `${prefix}-headings.json`), JSON.stringify(full.headings, null, 2));
  fs.writeFileSync(path.join(dir, `${prefix}-scroll-text.txt`), visibleText(texts.join("\n\n")));
  return full;
}

function analyze(full) {
  const text = full.text || "";
  const titleHits = TARGET_TITLES.filter((t) => text.includes(t));
  const headingHits = (full.headings || [])
    .map((h) => h.text)
    .filter((t) => TARGET_TITLES.some((x) => t.includes(x)));
  const forbiddenHits = FORBIDDEN.filter((k) => text.includes(k));
  const snake = [...text.matchAll(/\b[a-z]+_[a-z0-9_]+\b/g)].map((m) => m[0]);
  const dottedIds = [...text.matchAll(/\bbazi\.[a-z0-9.-]+\b/g)].map((m) => m[0]);
  const gufa = /命中古法|古法命中|原文/.test(text);
  const deepClosed = /测试期未开放|当前没有可购买的命盘深读|完整深度解读待接入/.test(text);
  const chartIdx = text.search(/年柱|四柱|庚辰/);
  const judgeIdx = text.search(/判断|深读|报告与追问|命中古法/);
  const firstFindingIdx = TARGET_TITLES.map((t) => text.indexOf(t)).filter((n) => n >= 0);
  const findingPos = firstFindingIdx.length ? Math.min(...firstFindingIdx) : -1;
  return {
    titleHits,
    headingHits,
    forbiddenHits,
    snake: [...new Set(snake)].slice(0, 20),
    dottedIds: [...new Set(dottedIds)],
    gufa,
    deepClosed,
    chartIdx,
    judgeIdx,
    findingPos,
    afterChartBeforeJudge:
      findingPos >= 0 && (chartIdx < 0 || chartIdx < findingPos) && (judgeIdx < 0 || findingPos < judgeIdx),
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
  await page.goto(`${BASE}/bazi`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(800);
  const entry = await dump(page);
  fs.writeFileSync(path.join(dir, "00-entry-text.txt"), visibleText(entry.text));
  await shot(page, path.join(dir, "00-entry.png"));
  await fillBazi(page);
  await page.waitForTimeout(300);
  const filled = await dump(page);
  fs.writeFileSync(path.join(dir, "01-filled-text.txt"), visibleText(filled.text));
  await shot(page, path.join(dir, "01-filled.png"));
  const submit = page.getByRole("button", { name: /立即排盘/ });
  await submit.click();
  await page.waitForTimeout(400);
  await shot(page, path.join(dir, "02-after-click.png"));
  const natal = await waitNatal(page, 50000);
  fs.writeFileSync(path.join(dir, "03-natal-wait-text.txt"), visibleText(natal.text));
  const full = await scrollShots(page, dir, "04");
  const analysis = analyze(full);
  analysis.entryUrl = entry.url;
  analysis.natalUrl = natal.url;
  analysis.timedOut = Boolean(natal.timedOut);
  fs.writeFileSync(path.join(dir, "result.json"), JSON.stringify(analysis, null, 2));
  await ctx.close();
  return analysis;
}

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: false,
  args: ["--disable-blink-features=AutomationControlled"],
});
const out = {};
try {
  out["1440"] = await runViewport(browser, 1440, 900, "1440");
  out["360"] = await runViewport(browser, 360, 800, "360");
} finally {
  await browser.close();
}
fs.writeFileSync(path.join(ROOT, "summary.json"), JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
