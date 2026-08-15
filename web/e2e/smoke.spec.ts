import { mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

test("public methodology page is reachable and records browser evidence", async ({
  page,
}, testInfo) => {
  const browserErrors: string[] = [];
  const criticalHttpErrors: string[] = [];
  const nonCriticalHttpErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().includes("Failed to load resource")) {
      browserErrors.push(`console: ${message.text()}`);
    }
  });
  page.on("response", (resource) => {
    if (resource.status() < 400) return;
    const request = resource.request();
    const entry = `${resource.status()} ${request.resourceType()} ${resource.url()}`;
    if (["document", "script", "stylesheet", "font", "image"].includes(request.resourceType())) {
      criticalHttpErrors.push(entry);
    } else {
      nonCriticalHttpErrors.push(entry);
    }
  });

  const response = await page.goto("/methodology", { waitUntil: "domcontentloaded" });
  if (!response) throw new Error("navigation did not return an HTTP response");
  expect(response.ok(), `unexpected HTTP status ${response.status()}`).toBe(true);
  await expect(page.locator("body")).toBeVisible();

  const screenshotDirectory = resolve(
    process.env.BROWSER_EVIDENCE_DIR ?? resolve(process.cwd(), "e2e/screenshots"),
    testInfo.project.name,
  );
  const screenshotPath = resolve(screenshotDirectory, "methodology.png");
  await mkdir(screenshotDirectory, { recursive: true });
  await rm(screenshotPath, { force: true });
  await page.screenshot({
    path: screenshotPath,
    fullPage: true,
  });

  await testInfo.attach("http-errors", {
    body: Buffer.from(JSON.stringify({ criticalHttpErrors, nonCriticalHttpErrors }, null, 2)),
    contentType: "application/json",
  });
  expect(criticalHttpErrors, criticalHttpErrors.join("\n")).toEqual([]);
  expect(browserErrors, browserErrors.join("\n")).toEqual([]);
});
