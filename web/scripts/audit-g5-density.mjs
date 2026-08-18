/**
 * G5/C6 browser evidence audit.
 *
 * Defaults to the noindex `/_ui-lab/bazi-result` synthetic fixture. Runtime
 * owner mode submits the real `/bazi` form and waits for its signed Runtime
 * result. Neither mode represents BROWSER_VERIFIED user acceptance.
 */
import { chromium } from "@playwright/test";
import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const WEB_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = path.resolve(WEB_ROOT, "..");
const REFERENCE_ROOT = path.join(REPO_ROOT, "qingnang", "site");
const APP_BASE_URL = process.env.MINGLI_G5_APP_BASE_URL ?? "http://127.0.0.1:3000";
const PRODUCT_ROUTE = process.env.MINGLI_G5_PRODUCT_ROUTE ?? "/_ui-lab/bazi-result";
const PRODUCT_DATA_BOUNDARY = process.env.MINGLI_G5_PRODUCT_DATA_BOUNDARY
  ?? "synthetic-ui-lab-fixture-not-runtime-release";
const OUTPUT_ROOT = path.resolve(
  REPO_ROOT,
  process.env.MINGLI_G5_OUTPUT_ROOT
    ?? "artifacts/browser-evidence/2026-08-18-bazi-g5-density",
);
const RUNTIME_OWNER_MODE = PRODUCT_DATA_BOUNDARY === "signed-runtime-release-owner-result";
const RELEASE_MANIFEST_PATH = path.join(
  REPO_ROOT,
  ".runtime",
  "v53-time-check-release",
  ".mingli-release-manifest.json",
);
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const VIEWPORTS = [
  { width: 360, height: 800 },
  { width: 768, height: 1024 },
  { width: 1024, height: 768 },
  { width: 1440, height: 900 },
];
const COUNT_VIEWPORTS = new Set([768, 1440]);
const LAYERS = [
  { id: "natal", name: /^本命/ },
  { id: "decadal", name: /^大运/ },
  { id: "yearly", name: /^流年/, runtimeField: "core_facts.year_layers" },
  { id: "monthly", name: /^流月/, runtimeField: "core_facts.month_layers" },
  { id: "daily", name: /^流日/, runtimeField: "core_facts.day_layers" },
];

function mimeType(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (filePath.endsWith(".webmanifest")) return "application/manifest+json";
  if (filePath.endsWith(".png")) return "image/png";
  if (filePath.endsWith(".webp")) return "image/webp";
  return "application/octet-stream";
}

function mirrorFile(pathname) {
  if (pathname === "/" || pathname === "/bazi" || pathname === "/pages/bazi.html") {
    return path.join(REFERENCE_ROOT, "pages", "bazi.html");
  }
  const basename = path.basename(pathname);
  if (pathname.includes("/_next/static/") && basename.endsWith(".css")) {
    return path.join(REFERENCE_ROOT, "css", basename);
  }
  if (pathname.includes("/_next/static/") && basename.endsWith(".js")) {
    return path.join(REFERENCE_ROOT, "js", basename);
  }
  if (pathname.startsWith("/icons/") || pathname === "/og.png") {
    return path.join(REFERENCE_ROOT, "img", basename);
  }
  if (pathname === "/manifest.webmanifest") {
    return path.join(REFERENCE_ROOT, "meta", "manifest.webmanifest");
  }
  return null;
}

async function startReferenceServer() {
  const server = createServer((request, response) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    if (url.pathname.startsWith("/api/") || url.pathname === "/sw.js") {
      response.writeHead(404, { "content-type": "application/json" });
      response.end('{"error":"not mirrored"}');
      return;
    }
    const filePath = mirrorFile(url.pathname);
    if (!filePath) {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end("not mirrored");
      return;
    }
    try {
      const body = readFileSync(filePath);
      response.writeHead(200, {
        "cache-control": "no-store",
        "content-type": mimeType(filePath),
      });
      response.end(body);
    } catch {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end("missing mirror asset");
    }
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("reference server has no TCP port");
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve()))),
  };
}

async function pageLayout(page) {
  return page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));
}

async function structuredUnits(root, mode) {
  return root.evaluate((element, selectedMode) => {
    const visible = (candidate) => {
      const style = getComputedStyle(candidate);
      const rect = candidate.getBoundingClientRect();
      return style.display !== "none"
        && style.visibility !== "hidden"
        && candidate.getAttribute("aria-hidden") !== "true"
        && rect.width > 0
        && rect.height > 0;
    };
    const normalize = (value) => value.replace(/\s+/g, " ").trim();
    const missing = /未返回|尚未返回|未生成|暂无可|暂不可用/;
    const candidates = [];
    for (const [kind, selector] of [
      ["table-row", "table tbody tr"],
      ["definition", "dl > div"],
      ["list-item", "ul > li, ol > li"],
      ["pillar", '[role="group"][aria-label="四柱"] > button'],
    ]) {
      for (const candidate of element.querySelectorAll(selector)) {
        candidates.push({ candidate, kind });
      }
    }
    if (selectedMode === "reference") {
      for (const parent of element.querySelectorAll("div")) {
        if (!visible(parent) || getComputedStyle(parent).display !== "grid") continue;
        for (const candidate of parent.children) {
          if (!(candidate instanceof HTMLElement) || !visible(candidate)) continue;
          if (candidate.matches('form, nav, [role="tablist"], [role="tabpanel"]')) continue;
          if (candidate.querySelector("table, dl, ul, ol, form, [role=tablist]")) continue;
          const text = normalize(candidate.innerText);
          if (candidate.childElementCount === 0 || text.length < 2 || text.length > 260) continue;
          candidates.push({ candidate, kind: "grid-cell" });
        }
      }
    }

    const units = [];
    const seen = new Set();
    for (const { candidate, kind } of candidates) {
      if (!visible(candidate)) continue;
      const text = normalize(candidate.innerText);
      if (!text || missing.test(text)) continue;
      const signature = `${kind}:${text}`;
      if (seen.has(signature)) continue;
      seen.add(signature);
      const style = getComputedStyle(candidate);
      units.push({
        kind,
        text,
        fontSizePx: Number.parseFloat(style.fontSize),
        truncated:
          style.textOverflow === "ellipsis"
          || ((style.overflowX === "hidden" || style.overflow === "hidden")
            && candidate.scrollWidth > candidate.clientWidth + 1),
      });
    }
    return units;
  }, mode);
}

async function selectLayer(page, layer) {
  const tab = page.getByRole("tab", { name: layer.name });
  const status = await tab.getAttribute("data-status");
  if (await tab.isDisabled()) {
    return { available: false, status: status ?? "unavailable" };
  }
  await tab.click();
  await page.waitForTimeout(180);
  if ((await tab.getAttribute("aria-selected")) !== "true") {
    throw new Error(`layer ${layer.id} did not become active`);
  }
  return { available: true, status: status ?? "ready" };
}

async function openEvidenceDrawer(page) {
  const drawer = page.locator("details").filter({ hasText: "命中古法" }).first();
  if ((await drawer.count()) === 0) {
    if (RUNTIME_OWNER_MODE) return false;
    throw new Error("verified-exact evidence drawer missing");
  }
  if (!(await drawer.getAttribute("open"))) await drawer.locator("summary").click();
  return true;
}

async function prepareProduct(page) {
  if (!RUNTIME_OWNER_MODE) {
    await page.goto(`${APP_BASE_URL}${PRODUCT_ROUTE}`, { waitUntil: "networkidle", timeout: 45000 });
    return null;
  }

  await page.goto(`${APP_BASE_URL}${PRODUCT_ROUTE}`, { waitUntil: "networkidle", timeout: 45000 });
  await page.getByLabel("受测对象").fill("真实 Runtime 密度样例");
  await page.getByLabel("男").check();
  await page.getByLabel("出生年份").selectOption("1994");
  await page.getByLabel("出生月份").selectOption("04");
  await page.getByLabel("出生日期").selectOption("30");
  await page.getByLabel("出生小时").selectOption("05");
  await page.getByLabel("出生分钟").selectOption("55");
  await page.getByRole("button", { name: "海外或找不到？直接输入" }).click();
  await page.getByLabel("出生地点").fill("北京市朝阳区");

  const previewResponse = page.waitForResponse(
    (response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === "/api/v1/readings/preview",
    { timeout: 45000 },
  );
  await page.getByRole("button", { name: /立即排盘（免费）/ }).click();
  const response = await previewResponse;
  if (!response.ok()) {
    throw new Error(`real preview failed with HTTP ${response.status()}: ${await response.text()}`);
  }
  const body = await response.json();
  if (typeof body.reading_version_id !== "string") {
    throw new Error("real preview response omitted reading_version_id");
  }
  await page.locator('[aria-label="排盘工作台"]').waitFor({ timeout: 120000 });
  return body.reading_version_id;
}

async function prepareReference(page, baseUrl) {
  const query = new URLSearchParams({
    y: "1994",
    m: "4",
    d: "30",
    h: "5",
    min: "55",
    g: "male",
    province: "北京",
    city: "北京",
  });
  await page.goto(`${baseUrl}/bazi?${query}`, { waitUntil: "domcontentloaded", timeout: 45000 });
  const heading = page.locator("h1").filter({ hasText: "八字排盘" });
  await heading.waitFor();
  await page.getByPlaceholder(/请输入有缘人的称呼/).fill("密度对照样例");
  await page.getByRole("button", { name: "开启推演（免费）" }).click();
  await page.waitForFunction(() => document.body.innerText.includes("真太阳时："), null, { timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.evaluate(() => {
    const marker = [...document.querySelectorAll("*")].find(
      (candidate) => candidate.children.length === 0 && candidate.textContent?.includes("真太阳时："),
    );
    if (!marker) throw new Error("reference result marker missing");
    let root = marker.parentElement;
    while (root && !root.classList.contains("space-y-6")) root = root.parentElement;
    if (!root) throw new Error("reference result root missing");
    root.setAttribute("data-g5-reference-root", "true");
  });
}

async function createComparison(browser, width, productPath, referencePath, outputPath) {
  const page = await browser.newPage({ viewport: { width: width * 2 + 48, height: 900 } });
  const product = readFileSync(productPath).toString("base64");
  const reference = readFileSync(referencePath).toString("base64");
  await page.setContent(`<!doctype html>
    <meta charset="utf-8">
    <style>
      * { box-sizing: border-box; }
      body { margin: 0; padding: 16px; background: #e8e6df; font: 16px system-ui, sans-serif; }
      main { display: grid; grid-template-columns: ${width}px ${width}px; gap: 16px; align-items: start; }
      figure { margin: 0; background: white; }
      figcaption { position: sticky; top: 0; z-index: 1; padding: 10px 12px; background: #111; color: white; }
      img { display: block; width: ${width}px; height: auto; }
    </style>
    <main>
      <figure><figcaption>mingli_web · ${RUNTIME_OWNER_MODE ? "真实签名 Runtime" : "合成 Fixture"} · ${width}px</figcaption><img src="data:image/png;base64,${product}"></figure>
      <figure><figcaption>qingnang/site · 本地镜像 · ${width}px</figcaption><img src="data:image/png;base64,${reference}"></figure>
    </main>`);
  await page.screenshot({ path: outputPath, fullPage: true });
  await page.close();
}

async function run() {
  mkdirSync(OUTPUT_ROOT, { recursive: true });
  const referenceServer = await startReferenceServer();
  const browser = await chromium.launch({ executablePath: CHROME_PATH, headless: true });
  const results = [];
  const failures = [];
  const readingVersionIds = [];

  try {
    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
      const page = await context.newPage();
      const runtimeErrors = [];
      page.on("pageerror", (error) => runtimeErrors.push(String(error)));
      const readingVersionId = await prepareProduct(page);
      if (readingVersionId) readingVersionIds.push(readingVersionId);
      const root = page.locator('[aria-label="排盘工作台"]');
      await root.waitFor();
      const evidenceDrawerRendered = await openEvidenceDrawer(page);

      const layerReports = [];
      const allUnits = [];
      for (const layer of LAYERS) {
        const layerState = await selectLayer(page, layer);
        const layout = await pageLayout(page);
        const units = layerState.available ? await structuredUnits(root, "product") : [];
        allUnits.push(...units);
        const screenshot = path.join(OUTPUT_ROOT, String(viewport.width), `mingli-${layer.id}.png`);
        mkdirSync(path.dirname(screenshot), { recursive: true });
        await page.screenshot({ path: screenshot, fullPage: true });
        const overflow = layout.scrollWidth - layout.innerWidth;
        if (overflow > 1) failures.push(`${viewport.width}px ${layer.id}: page overflow ${overflow}px`);
        const truncated = units.filter((unit) => unit.truncated);
        if (truncated.length > 0) failures.push(`${viewport.width}px ${layer.id}: ${truncated.length} counted facts truncated`);
        const minFontSizePx = units.length > 0
          ? Math.min(...units.map((unit) => unit.fontSizePx).filter(Number.isFinite))
          : null;
        if (minFontSizePx !== null && minFontSizePx < 12) {
          failures.push(`${viewport.width}px ${layer.id}: counted fact font ${minFontSizePx}px below 12px`);
        }
        layerReports.push({
          layer: layer.id,
          available: layerState.available,
          status: layerState.status,
          missingRuntimeField: layerState.available ? null : layer.runtimeField ?? null,
          layout,
          overflow,
          minFontSizePx,
          truncatedCount: truncated.length,
          unitCount: units.length,
          screenshot: path.relative(REPO_ROOT, screenshot),
        });
      }
      if (runtimeErrors.length > 0) failures.push(`${viewport.width}px product runtime errors: ${runtimeErrors.join(" | ")}`);

      let comparison = null;
      let density = null;
      if (COUNT_VIEWPORTS.has(viewport.width)) {
        const uniqueProductUnits = [...new Map(allUnits.map((unit) => [`${unit.kind}:${unit.text}`, unit])).values()];
        const referencePage = await context.newPage();
        await prepareReference(referencePage, referenceServer.baseUrl);
        const referenceRoot = referencePage.locator('[data-g5-reference-root="true"]');
        const referenceUnits = await structuredUnits(referenceRoot, "reference");
        const referenceScreenshot = path.join(OUTPUT_ROOT, String(viewport.width), "qingnang-result.png");
        await referencePage.screenshot({ path: referenceScreenshot, fullPage: true });
        const referenceLayout = await pageLayout(referencePage);
        await referencePage.close();

        if (uniqueProductUnits.length < referenceUnits.length) {
          failures.push(`${viewport.width}px density: product ${uniqueProductUnits.length} < reference ${referenceUnits.length}`);
        }
        const comparisonPath = path.join(OUTPUT_ROOT, `comparison-${viewport.width}.png`);
        await createComparison(
          browser,
          viewport.width,
          path.join(OUTPUT_ROOT, String(viewport.width), "mingli-natal.png"),
          referenceScreenshot,
          comparisonPath,
        );
        comparison = path.relative(REPO_ROOT, comparisonPath);
        density = {
          methodVersion: "visible-structured-row-v1",
          productCount: uniqueProductUnits.length,
          referenceCount: referenceUnits.length,
          productUnits: uniqueProductUnits,
          referenceUnits,
          referenceLayout,
          referenceScreenshot: path.relative(REPO_ROOT, referenceScreenshot),
        };
      }
      results.push({
        viewport,
        source: RUNTIME_OWNER_MODE ? "signed-runtime-release-owner-result" : "synthetic-ui-lab-fixture",
        readingVersionId,
        evidenceDrawerRendered,
        layerReports,
        density,
        comparison,
      });
      await context.close();
    }
  } finally {
    await browser.close();
    await referenceServer.close();
  }

  const releaseManifestSha256 = RUNTIME_OWNER_MODE
    ? createHash("sha256").update(readFileSync(RELEASE_MANIFEST_PATH)).digest("hex")
    : null;
  const report = {
    generatedAt: new Date().toISOString(),
    gitSha: process.env.MINGLI_G5_GIT_SHA ?? null,
    productBaseUrl: APP_BASE_URL,
    productRoute: PRODUCT_ROUTE,
    productDataBoundary: PRODUCT_DATA_BOUNDARY,
    releaseManifestSha256,
    readingVersionIds,
    referenceBoundary: "local-qingnang-site-mirror-client-preview",
    ok: failures.length === 0,
    failures,
    results,
  };
  writeFileSync(path.join(OUTPUT_ROOT, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    ok: report.ok,
    failures,
    counts: results
      .filter((entry) => entry.density)
      .map((entry) => ({
        viewport: entry.viewport.width,
        product: entry.density.productCount,
        reference: entry.density.referenceCount,
      })),
  }, null, 2));
  if (!report.ok) process.exitCode = 1;
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
