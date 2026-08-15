/**
 * One-shot phase-4 browser audit (product flows / workbench / 合参, 2026-08-15).
 *
 * Uses the already-running local dev server and system Chrome. Product routes
 * are audited without submitting business data; the jianxiang route only
 * selects an in-memory local file to reach its confirmation boundary.
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASE = "http://127.0.0.1:3000";
const ROUTES = [
  ["/bazi", "bazi", "八字", "success"],
  ["/ziwei", "ziwei", "紫微", "success"],
  ["/qizheng", "qizheng", "七政", "success"],
  ["/liuyao", "liuyao", "六爻", "success"],
  ["/qimen", "qimen", "奇门", "success"],
  ["/daliuren", "daliuren", "大六壬", "success"],
  ["/jianxiang", "jianxiang", "见相", "unavailable"],
  ["/hecan", "hecan", "命盘合参", "success"],
  ["/wenshi", "wenshi", "问事合参", "success"],
  ["/workbench/demo", "workbench-demo", "恢复任务", null],
  ["/_ui-lab", "ui-lab", "Web UI Lab", null],
];
const VIEWPORTS = [360, 768, 1024, 1440];
const OUT_ROOT = path.join(ROOT, "e2e", "screenshots", "audit-2026-08-14", "phase4");

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

function addFailure(entry, check, reason) {
  entry.failures.push({ check, reason });
}

async function pageLandmarks(page) {
  return page.evaluate(() => {
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none"
        && style.visibility !== "hidden"
        && rect.width > 0
        && rect.height > 0;
    };
    const mains = [...document.querySelectorAll("main")].filter(visible);
    const h1s = [...document.querySelectorAll("h1")].filter(visible);
    return {
      mainCount: mains.length,
      h1Count: h1s.length,
      h1Text: h1s.map((heading) => heading.textContent?.trim() ?? ""),
      bodyText: document.body.innerText,
    };
  });
}

async function assertProductRoute(page, entry, route, productId, productName, expectedState) {
  const form = page.getByRole("form", { name: `${productName}任务输入`, exact: true });
  if ((await form.count()) !== 1 || !(await form.isVisible())) {
    addFailure(entry, "product-form", `expected one visible ${productName} task form`);
  }
  for (const label of ["输入确认", "工作台", "报告与追问"]) {
    if ((await page.getByText(label, { exact: true }).count()) < 1) {
      addFailure(entry, "task-progress", `missing task progress label ${label}`);
    }
  }
  const productHeading = page.getByRole("heading", {
    level: 1,
    name: new RegExp(`^${productName}`),
  });
  if ((await productHeading.count()) !== 1) {
    addFailure(entry, "product-name", `missing product label ${productName}`);
  }
  if ((await page.locator(`[data-state="${expectedState}"]`).count()) < 1) {
    addFailure(entry, "capability-state", `expected data-state=${expectedState}`);
  }
  const forbidden = entry.landmarks.bodyText.match(/UI 演示数据|页面已预制|provider key|raw JSON|snake_case/i);
  if (forbidden) {
    addFailure(entry, "production-copy-boundary", `found forbidden product copy: ${forbidden[0]}`);
  }
  entry.product = { route, productId, productName, expectedState };
}

async function assertJianxiangConfirmation(page, entry) {
  try {
    // The supported input contract requires an explicitly named subject before
    // the flow can advance to confirmation. Keep this fixture complete so the
    // audit reaches the connected Runtime confirmation boundary it is meant to verify.
    await page.getByLabel("受测对象", { exact: true }).fill("本地验收对象");
    await page.getByRole("checkbox", { name: "照片处理独立同意" }).check();
    await page.locator("#jianxiang-file").setInputFiles({
      name: "audit-local.png",
      mimeType: "image/png",
      buffer: Buffer.from("phase4-local-audit"),
    });
    await page.getByRole("button", { name: "检查输入", exact: true }).click();
    await page.getByRole("heading", { name: "确认见相输入", exact: true }).waitFor();
    const generateButton = page.getByRole("button", { name: "确认并生成盘面", exact: true });
    if ((await generateButton.count()) !== 1 || !(await generateButton.isVisible())) {
      addFailure(entry, "jianxiang-confirmation", "expected the connected Runtime generation action");
    }
    const bodyText = await page.locator("body").innerText();
    if (/UI 演示数据|页面已预制|provider key|raw JSON|snake_case/i.test(bodyText)) {
      addFailure(entry, "confirmation-copy-boundary", "found fixture or internal field copy in confirmation");
    }
    entry.jianxiangConfirmation = { runtimeAction: "确认并生成盘面", submission: "not submitted" };
  } catch (error) {
    addFailure(entry, "jianxiang-confirmation", errorMessage(error));
  }
}

async function assertUiLab(page, entry) {
  if ((await page.getByText("UI 演示数据", { exact: true }).count()) !== 1) {
    addFailure(entry, "ui-lab-boundary", "expected the explicit UI Lab demo boundary");
  }
  if ((await page.getByRole("heading", { name: "预览控制", exact: true }).count()) !== 1) {
    addFailure(entry, "ui-lab-controls", "expected UI Lab controls");
  }
}

async function run() {
  const results = [];
  const browser = await chromium.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
  });

  try {
    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: { width: viewport, height: 900 },
        deviceScaleFactor: 1,
      });
      const page = await context.newPage();

      try {
        for (const [route, name, productName, expectedState] of ROUTES) {
          const entry = { viewport, route, failures: [] };
          const screenshotPath = path.join(OUT_ROOT, String(viewport), `${name}.png`);
          const runtimeErrors = [];
          page.removeAllListeners("pageerror");
          page.on("pageerror", (error) => runtimeErrors.push(errorMessage(error)));

          try {
            const response = await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 45000 });
            await page.waitForTimeout(300);
            entry.httpStatus = response ? response.status() : null;
            entry.finalPathname = new URL(page.url()).pathname;
            if (entry.finalPathname !== route) {
              addFailure(entry, "final-url", `expected ${route}, received ${entry.finalPathname}`);
            }

            const layout = await page.evaluate(() => ({
              scrollWidth: document.documentElement.scrollWidth,
              innerWidth: window.innerWidth,
            }));
            entry.layout = { ...layout, overflow: layout.scrollWidth - layout.innerWidth };
            if (layout.scrollWidth > layout.innerWidth + 1) {
              addFailure(entry, "horizontal-overflow", `scrollWidth ${layout.scrollWidth}px exceeds innerWidth ${layout.innerWidth}px`);
            }

            entry.landmarks = await pageLandmarks(page);
            if (name !== "ui-lab" && entry.landmarks.mainCount < 1) {
              addFailure(entry, "main-landmark", `expected at least one visible main, found ${entry.landmarks.mainCount}`);
            }
            if (entry.landmarks.h1Count !== 1) {
              addFailure(entry, "h1-landmark", `expected one visible h1, found ${entry.landmarks.h1Count}`);
            }

            if (expectedState) {
              await assertProductRoute(page, entry, route, name, productName, expectedState);
            } else if (name === "workbench-demo") {
              if (entry.landmarks.h1Text[0] !== "恢复任务") {
                addFailure(entry, "workbench-recovery", `expected h1 恢复任务, received ${entry.landmarks.h1Text[0]}`);
              }
              if ((await page.locator('[data-state="unavailable"]').count()) < 1) {
                addFailure(entry, "workbench-recovery-state", "expected unavailable recovery state");
              }
            } else {
              await assertUiLab(page, entry);
            }

            if (route === "/jianxiang") {
              await assertJianxiangConfirmation(page, entry);
            }
          } catch (error) {
            addFailure(entry, "route-audit", errorMessage(error));
          }

          if (runtimeErrors.length > 0) {
            entry.runtimeErrors = runtimeErrors;
            addFailure(entry, "runtime-errors", runtimeErrors.join(" | "));
          }

          try {
            fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
            await page.screenshot({ path: screenshotPath, fullPage: true });
            entry.screenshot = path.relative(ROOT, screenshotPath);
          } catch (error) {
            addFailure(entry, "screenshot", errorMessage(error));
          }

          entry.ok = entry.failures.length === 0;
          results.push(entry);
        }
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }

  const failures = results.filter((entry) => !entry.ok);
  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE,
    total: results.length,
    passed: results.length - failures.length,
    failed: failures.length,
    results,
  };
  fs.mkdirSync(OUT_ROOT, { recursive: true });
  fs.writeFileSync(path.join(OUT_ROOT, "report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  console.log(`phase-4 audit: ${report.passed}/${report.total} route/viewport combinations passed`);
  for (const entry of failures) {
    for (const failure of entry.failures) {
      console.log(`FAIL ${entry.viewport}px ${entry.route} [${failure.check}] ${failure.reason}`);
    }
  }
  process.exitCode = failures.length > 0 ? 1 : 0;
}

run().catch((error) => {
  console.log(JSON.stringify({ generatedAt: new Date().toISOString(), baseUrl: BASE, fatal: errorMessage(error) }, null, 2));
  process.exitCode = 1;
});
