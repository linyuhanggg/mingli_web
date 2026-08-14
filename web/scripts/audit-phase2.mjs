/**
 * One-shot phase-2 browser audit (2026-08-14).
 *
 * The script connects only to the already-running Web app at
 * http://127.0.0.1:3000. It never starts or stops the server.
 * Screenshots are written to:
 *   web/e2e/screenshots/audit-2026-08-14/phase2/{viewport}/{route}.png
 *
 * Results are emitted to stdout as JSON followed by a short human summary.
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASE = "http://127.0.0.1:3000";
const ROUTES = [
  ["/", "home"],
  ["/hecan", "hecan"],
  ["/wenshi", "wenshi"],
  ["/canwen", "canwen"],
  ["/liuyao", "liuyao"],
  ["/jianxiang", "jianxiang"],
  ["/account", "account"],
  ["/auth/login", "auth-login"],
  ["/daily", "daily"],
  ["/tools", "tools"],
  ["/library", "library"],
  ["/about", "about"],
  ["/pricing", "pricing"],
  ["/methodology", "methodology"],
  ["/workbench/demo", "workbench-demo"],
  ["/_ui-lab", "ui-lab"],
];
const VIEWPORTS = [360, 768, 1024, 1440];
const outRoot = path.join(ROOT, "e2e", "screenshots", "audit-2026-08-14", "phase2");

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

function addFailure(entry, check, reason) {
  entry.failures.push({ check, reason });
}

async function assertHomeContract(page, entry) {
  const home = await page.evaluate(() => {
    const expectedRegions = ["命盘", "事件判断", "合参", "辅助"];
    const isVisible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    const mains = [...document.querySelectorAll("main")].filter(isVisible);
    const h1s = mains.flatMap((main) => [...main.querySelectorAll("h1")].filter(isVisible));
    const namedRegions = [...document.querySelectorAll("section[aria-labelledby]")].filter((section) => {
      if (!isVisible(section)) return false;
      const labelId = section.getAttribute("aria-labelledby");
      const label = labelId ? document.getElementById(labelId)?.textContent?.trim() : "";
      return expectedRegions.includes(label ?? "");
    });
    const regionCounts = Object.fromEntries(
      expectedRegions.map((name) => [
        name,
        namedRegions.filter((section) => {
          const labelId = section.getAttribute("aria-labelledby");
          return labelId ? document.getElementById(labelId)?.textContent?.trim() === name : false;
        }).length,
      ]),
    );
    const crossRegions = namedRegions.filter((section) => {
      const labelId = section.getAttribute("aria-labelledby");
      return labelId ? document.getElementById(labelId)?.textContent?.trim() === "合参" : false;
    });

    return {
      mainCount: mains.length,
      h1Count: h1s.length,
      h1Text: h1s.map((heading) => heading.textContent?.trim() ?? ""),
      regionCounts,
      crossRegionCount: crossRegions.length,
      crossEntryCount: crossRegions.length === 1
        ? [...crossRegions[0].querySelectorAll("a[href]")].filter(isVisible).length
        : null,
    };
  });

  entry.home = home;
  if (home.mainCount !== 1) {
    addFailure(entry, "home-main", `expected exactly one visible main landmark, found ${home.mainCount}`);
  }
  if (home.h1Count !== 1) {
    addFailure(entry, "home-h1", `expected exactly one visible h1 inside main, found ${home.h1Count}`);
  }
  for (const [name, count] of Object.entries(home.regionCounts)) {
    if (count !== 1) {
      addFailure(entry, "home-regions", `expected exactly one visible region named ${name}, found ${count}`);
    }
  }
  if (home.crossRegionCount !== 1) {
    addFailure(entry, "home-cross-region", `expected exactly one visible region named 合参, found ${home.crossRegionCount}`);
  } else if (home.crossEntryCount !== 2) {
    addFailure(entry, "home-cross-entries", `expected exactly two links in the 合参 region, found ${home.crossEntryCount}`);
  }
}

async function assertKeyboardAndAria(page, entry, viewport) {
  const navigationName = viewport >= 768 ? "主导航" : "移动底栏";
  const navigation = page.getByRole("navigation", { name: navigationName, exact: true });
  const navigationCount = await navigation.count();

  if (navigationCount !== 1 || !(await navigation.isVisible())) {
    addFailure(
      entry,
      "keyboard-navigation",
      `expected one visible navigation landmark named ${navigationName}, found ${navigationCount}`,
    );
    return;
  }

  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  });
  let reachedNavigation = false;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await page.keyboard.press("Tab");
    if (await navigation.evaluate((node) => node.contains(document.activeElement))) {
      reachedNavigation = true;
      break;
    }
  }
  entry.keyboard = { navigationName, reachedNavigation };
  if (!reachedNavigation) {
    addFailure(entry, "keyboard-navigation", `${navigationName} was not reachable within 40 forward Tab presses`);
  }

  if (viewport < 768) return;

  const crossTrigger = navigation.getByRole("button", { name: "合参", exact: true });
  const triggerCount = await crossTrigger.count();
  if (triggerCount !== 1 || !(await crossTrigger.isVisible())) {
    addFailure(entry, "cross-trigger", `expected one visible desktop 合参 trigger, found ${triggerCount}`);
    return;
  }

  const initialExpanded = await crossTrigger.getAttribute("aria-expanded");
  if (initialExpanded !== "false") {
    addFailure(
      entry,
      "cross-trigger-aria-expanded",
      `expected initial aria-expanded=false, received ${JSON.stringify(initialExpanded)}`,
    );
  }

  await crossTrigger.focus();
  await crossTrigger.press("Enter");
  try {
    await page.waitForFunction(
      (trigger) => trigger.getAttribute("aria-expanded") === "true",
      await crossTrigger.elementHandle(),
      { timeout: 3000 },
    );
  } catch {
    addFailure(entry, "cross-trigger-keyboard", "pressing Enter did not set aria-expanded=true");
  }

  await page.keyboard.press("Escape");
  try {
    await page.waitForFunction(
      (trigger) => trigger.getAttribute("aria-expanded") === "false",
      await crossTrigger.elementHandle(),
      { timeout: 3000 },
    );
  } catch {
    addFailure(entry, "cross-trigger-keyboard", "pressing Escape did not restore aria-expanded=false");
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
        for (const [route, name] of ROUTES) {
          const entry = { viewport, route, failures: [] };
          const screenshotPath = path.join(outRoot, String(viewport), `${name}.png`);

          try {
            const response = await page.goto(BASE + route, {
              waitUntil: "networkidle",
              timeout: 45000,
            });
            await page.waitForTimeout(250);

            entry.httpStatus = response ? response.status() : null;
            entry.finalUrl = page.url();
            entry.finalPathname = new URL(page.url()).pathname;

            const expectedPathname = route === "/canwen" ? "/hecan" : route;
            if (entry.finalPathname !== expectedPathname) {
              addFailure(
                entry,
                "final-url",
                `expected final pathname ${expectedPathname}, received ${entry.finalPathname}`,
              );
            }

            const layout = await page.evaluate(() => ({
              scrollWidth: document.documentElement.scrollWidth,
              innerWidth: window.innerWidth,
            }));
            entry.layout = {
              ...layout,
              overflow: layout.scrollWidth - layout.innerWidth,
            };
            if (layout.scrollWidth > layout.innerWidth + 1) {
              addFailure(
                entry,
                "horizontal-overflow",
                `scrollWidth ${layout.scrollWidth}px exceeds innerWidth ${layout.innerWidth}px by more than 1px`,
              );
            }

            if (route === "/") {
              await assertHomeContract(page, entry);
              await assertKeyboardAndAria(page, entry, viewport);
            }
          } catch (error) {
            addFailure(entry, "route-audit", errorMessage(error));
          }

          try {
            fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
            await page.screenshot({ path: screenshotPath });
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

  fs.mkdirSync(outRoot, { recursive: true });
  fs.writeFileSync(path.join(outRoot, "report.json"), JSON.stringify(report, null, 2));

  console.log(JSON.stringify(report, null, 2));
  console.log(`phase-2 audit: ${report.passed}/${report.total} route/viewport combinations passed`);
  for (const entry of failures) {
    for (const failure of entry.failures) {
      console.log(`FAIL ${entry.viewport}px ${entry.route} [${failure.check}] ${failure.reason}`);
    }
  }

  process.exitCode = failures.length > 0 ? 1 : 0;
}

run().catch((error) => {
  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE,
    fatal: errorMessage(error),
  };
  console.log(JSON.stringify(report, null, 2));
  console.log(`FATAL phase-2 audit: ${report.fatal}`);
  process.exitCode = 1;
});
