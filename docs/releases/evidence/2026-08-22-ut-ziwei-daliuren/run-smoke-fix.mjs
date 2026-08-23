import playwright from "/Volumes/Lexar/code/mingli_web/web/node_modules/@playwright/test/index.js";
const { chromium } = playwright;
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BASE = "http://106.14.10.235:18080";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const QUESTION = "林宇航近日工作变动是否顺利，只问这一件事。";
const EVENT_TIME = "2026-08-22T19:00";
const LOCATION = "福建省莆田市涵江区";

async function dump(page) {
  return page.evaluate(() => ({
    url: location.href,
    pathname: location.pathname,
    title: document.title,
    text: (document.body?.innerText || "").replace(/\n{3,}/g, "\n\n"),
  }));
}

async function shot(page, file) {
  await page.screenshot({ path: file, fullPage: false });
  await page.screenshot({ path: file.replace(/\.png$/, "-full.png"), fullPage: true });
}

async function waitChart(page, pred, timeout = 90000) {
  const start = Date.now();
  let last = await dump(page);
  while (Date.now() - start < timeout) {
    last = await dump(page);
    if (pred(last)) return { ...last, waitedMs: Date.now() - start };
    await page.waitForTimeout(1000);
  }
  return { ...last, waitedMs: Date.now() - start, timedOut: true };
}

async function fillNatal(page, productId) {
  await page.locator(`#${productId}-subject`).fill("林宇航");
  await page.getByRole("radio", { name: "男", exact: true }).click();
  await page.getByLabel("出生年份").selectOption("2000");
  await page.getByLabel("出生月份").selectOption("10");
  await page.getByLabel("出生日期").selectOption("18");
  await page.getByLabel("出生小时").selectOption("05");
  await page.getByLabel("出生分钟").selectOption("10");
  await page.waitForFunction(() => {
    const el = document.querySelector('select[aria-label="出生省份"]');
    return el && [...el.options].some((o) => /福建/.test(o.value) || /福建/.test(o.textContent || ""));
  }, null, { timeout: 15000 });
  const province = page.getByLabel("出生省份");
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
}

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const dir = path.join(ROOT, "smoke");
const out = {};

try {
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "zh-CN" });
    const page = await ctx.newPage();
    const consoleErrors = [];
    page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });
    page.on("pageerror", (e) => consoleErrors.push(String(e)));
    await page.goto(`${BASE}/bazi`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(800);
    await fillNatal(page, "bazi");
    await page.getByRole("button", { name: /立即排盘/ }).click();
    const settled = await waitChart(page, (d) => {
      const t = d.text || "";
      const preparing = /正在准备免费盘面|服务端正在处理确定性盘面/.test(t);
      const chart = /日主|年柱|月柱|四柱盘|甲戌|戊辰/.test(t) && !preparing;
      return chart || /白屏|出错|不可用/.test(t);
    });
    await shot(page, path.join(dir, "bazi-03-waited.png"));
    fs.writeFileSync(path.join(dir, "bazi-waited-text.txt"), settled.text || "");
    out.bazi = {
      url: settled.url,
      pathname: settled.pathname,
      stayed: settled.pathname === "/bazi",
      preparing: /正在准备免费盘面/.test(settled.text || ""),
      hasChart: /日主|年柱|月柱/.test(settled.text || "") && !/正在准备免费盘面/.test(settled.text || ""),
      white: !(settled.text || "").trim(),
      waitedMs: settled.waitedMs,
      timedOut: settled.timedOut || false,
      consoleErrors,
    };
    fs.writeFileSync(path.join(dir, "bazi-result.json"), JSON.stringify(out.bazi, null, 2));
    await ctx.close();
  }

  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "zh-CN" });
    const page = await ctx.newPage();
    const consoleErrors = [];
    page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });
    page.on("pageerror", (e) => consoleErrors.push(String(e)));
    await page.goto(`${BASE}/liuyao`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(800);
    await page.locator("#liuyao-issue").fill(QUESTION);
    await page.locator("#liuyao-focus").selectOption("coins");
    await page.locator("#liuyao-event-time").fill(EVENT_TIME);
    await page.locator("#liuyao-timezone").fill("Asia/Shanghai");
    await page.locator("#liuyao-location").fill(LOCATION);
    // Try radio labels first, then selects.
    const labels = ["少阳（7 · 静爻）", "少阴（8 · 静爻）", "少阳（7 · 静爻）", "少阴（8 · 静爻）", "少阳（7 · 静爻）", "少阴（8 · 静爻）"];
    for (let i = 0; i < 6; i += 1) {
      const radios = page.locator(`input[name="liuyao-line-${i}-value"]`);
      if (await radios.count()) {
        await page.locator(`input[name="liuyao-line-${i}-value"][value="7"], input[name="liuyao-line-${i}-value"][value="8"]`).first().check({ force: true }).catch(async () => {
          await page.locator(`label:has(input[name="liuyao-line-${i}-value"])`).nth(i % 2 === 0 ? 1 : 2).click();
        });
        continue;
      }
      const sel = page.getByLabel(new RegExp(`第 ${i + 1} 次|${["初","二","三","四","五","上"][i]}爻`));
      if (await sel.count()) {
        await sel.selectOption({ label: labels[i] }).catch(async () => {
          await sel.selectOption({ index: 2 });
        });
      } else {
        const anySel = page.locator("select").nth(i + 1);
        if (await anySel.count()) await anySel.selectOption({ index: 2 }).catch(() => {});
      }
    }
    // Fallback: click visible option texts in each line fieldset
    const empties = page.getByText("请选择", { exact: true });
    if (await empties.count()) {
      const lineSelects = page.locator("select");
      const n = await lineSelects.count();
      for (let i = 0; i < n; i += 1) {
        const el = lineSelects.nth(i);
        const opts = await el.locator("option").allTextContents().catch(() => []);
        const hit = opts.find((t) => /少阳|7/.test(t));
        if (hit) await el.selectOption({ label: hit }).catch(() => {});
      }
    }
    await shot(page, path.join(dir, "liuyao-01b-filled.png"));
    await page.getByRole("button", { name: /立即起卦/ }).click();
    const settled = await waitChart(page, (d) => {
      const t = d.text || "";
      const stillForm = /请完成六次|请选择第/.test(t);
      const chart = /本卦|世爻|应爻|爻塔/.test(t) && !stillForm;
      return chart || /需要登录/.test(t);
    });
    await shot(page, path.join(dir, "liuyao-03-waited.png"));
    fs.writeFileSync(path.join(dir, "liuyao-waited-text.txt"), settled.text || "");
    out.liuyao = {
      url: settled.url,
      pathname: settled.pathname,
      stayed: settled.pathname === "/liuyao",
      loginWall: /需要登录|登录后才能/.test(settled.text || ""),
      hasChart: /本卦|世爻|应爻|爻塔/.test(settled.text || "") && !/请完成六次/.test(settled.text || ""),
      stillForm: /请完成六次|请选择第/.test(settled.text || ""),
      white: !(settled.text || "").trim(),
      waitedMs: settled.waitedMs,
      timedOut: settled.timedOut || false,
      consoleErrors,
    };
    fs.writeFileSync(path.join(dir, "liuyao-result.json"), JSON.stringify(out.liuyao, null, 2));
    await ctx.close();
  }
} catch (err) {
  out.error = String(err && err.stack ? err.stack : err);
} finally {
  fs.writeFileSync(path.join(dir, "smoke-fix.json"), JSON.stringify(out, null, 2));
  await browser.close();
}

console.log(JSON.stringify(out, null, 2));
