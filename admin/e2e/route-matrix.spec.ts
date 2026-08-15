import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { ADMIN_ROUTE_CATALOG } from "../src/lib/admin-route-catalog";

const ADMIN_ROUTES = ADMIN_ROUTE_CATALOG.map(({ path }) =>
  path.replace(/\[[^\]]+\]/g, "demo"),
);

type RouteEvidenceRecord = {
  requestedRoute: string;
  finalPath: string;
  httpStatus: number | null;
  viewport: { width: number; height: number };
  states: string[];
  screenshot: string;
};

function routeEvidenceFileName(route: string, index: number): string {
  const label =
    route === "/"
      ? "home"
      : route.replace(/^\/+/, "").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-|-$/g, "") ||
        "route";
  return `${String(index + 1).padStart(3, "0")}-${label}.jpg`;
}

test("Admin route catalog has no critical browser failures or horizontal overflow", async ({
  page,
}, testInfo) => {
  let currentRoute = "";
  const browserErrors: string[] = [];
  const criticalHttpErrors: string[] = [];
  const evidenceRoot = process.env.ROUTE_EVIDENCE_DIR
    ? resolve(process.env.ROUTE_EVIDENCE_DIR)
    : undefined;
  const evidenceRecords: RouteEvidenceRecord[] = [];

  page.on("pageerror", (error) => browserErrors.push(`${currentRoute}: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().includes("Failed to load resource")) {
      browserErrors.push(`${currentRoute}: ${message.text()}`);
    }
  });
  page.on("response", (resource) => {
    if (resource.status() < 400) return;
    const request = resource.request();
    if (["document", "script", "stylesheet", "font", "image"].includes(request.resourceType())) {
      criticalHttpErrors.push(`${currentRoute}: ${resource.status()} ${request.resourceType()} ${resource.url()}`);
    }
  });

  for (const route of ADMIN_ROUTES) {
    currentRoute = route;
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    expect(response, `${route} did not return a response`).not.toBeNull();
    expect(response?.ok(), `${route} returned HTTP ${response?.status()}`).toBe(true);
    await expect(page.locator("body")).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      height: window.innerHeight,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    }));
    expect(
      Math.max(dimensions.document, dimensions.body),
      `${route} overflows ${dimensions.viewport}px viewport`,
    ).toBeLessThanOrEqual(dimensions.viewport);

    if (evidenceRoot) {
      const screenshotPath = resolve(
        evidenceRoot,
        testInfo.project.name,
        "screenshots",
        routeEvidenceFileName(route, evidenceRecords.length),
      );
      await mkdir(dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath, type: "jpeg", quality: 65 });
      const states = await page.locator("[data-state]").evaluateAll((elements) =>
        Array.from(
          new Set(
            elements
              .map((element) => element.getAttribute("data-state"))
              .filter((state): state is string => state !== null),
          ),
        ).sort(),
      );
      evidenceRecords.push({
        requestedRoute: route,
        finalPath: new URL(page.url()).pathname,
        httpStatus: response?.status() ?? null,
        viewport: { width: dimensions.viewport, height: dimensions.height },
        states,
        screenshot: relative(evidenceRoot, screenshotPath),
      });
    }
  }

  expect(browserErrors, browserErrors.join("\n")).toEqual([]);
  expect(criticalHttpErrors, criticalHttpErrors.join("\n")).toEqual([]);

  if (process.env.ROUTE_EVIDENCE_DIR) {
    const generatedAt = new Date().toISOString();
    const reviewedAt = process.env.ROUTE_EVIDENCE_REVIEWED_AT ?? null;
    await writeFile(
      resolve(evidenceRoot!, `${testInfo.project.name}.json`),
      `${JSON.stringify(
        {
          schema: "mingli.route-evidence/v1",
          app: "admin",
          gitCommit: process.env.GIT_COMMIT ?? "not-provided",
          generatedAt,
          reviewedAt,
          reviewStatus: reviewedAt ? "reviewed" : "automated-only",
          test: {
            file: relative(process.cwd(), testInfo.file),
            name: testInfo.title,
            checks: ["http-200", "critical-browser-errors", "horizontal-overflow"],
          },
          baseURL: process.env.ADMIN_BASE_URL ?? "http://127.0.0.1:3001",
          project: testInfo.project.name,
          routes: evidenceRecords,
        },
        null,
        2,
      )}\n`,
      "utf8",
    );
    expect(
      existsSync(resolve(evidenceRoot!, `${testInfo.project.name}.json`)),
      "ROUTE_EVIDENCE_DIR requires a route evidence manifest",
    ).toBe(true);
  }
});

test("Admin UI Lab remains absent from the production route surface", async ({ page }) => {
  const response = await page.goto("/_ui-lab", { waitUntil: "domcontentloaded" });
  expect(response?.status()).toBe(404);
});

test("Admin skip link moves keyboard focus to the main content", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const skipLink = page.getByRole("link", { name: "跳到主内容" });

  await page.keyboard.press("Tab");
  await expect(skipLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
});

test("Admin navigation exposes every static route from the catalog", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const expected = ADMIN_ROUTE_CATALOG.filter(
    (route) => route.navigation !== false && !route.path.includes("["),
  ).map((route) => route.path);
  const actual = await page.locator('nav[aria-label="运营导航"] a').evaluateAll((links) =>
    links.map((link) => link.getAttribute("href")),
  );

  expect(actual).toEqual(expected);
});
