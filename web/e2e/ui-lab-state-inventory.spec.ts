import { mkdir, writeFile } from "node:fs/promises";
import { relative, resolve } from "node:path";

import { expect, test } from "@playwright/test";

const STATE_INVENTORY = [
  { state: "loading", canonicalState: "loading" },
  { state: "empty", canonicalState: "empty" },
  { state: "failed", canonicalState: "error" },
  { state: "generating", canonicalState: "processing" },
  { state: "unavailable", canonicalState: "unavailable" },
  { state: "unauthorized", canonicalState: "unauthorized" },
  { state: "locked", canonicalState: "locked" },
] as const;

test("UI Lab records the separate seven-state fixture inventory", async ({ page }, testInfo) => {
  test.skip(!process.env.UI_LAB_E2E, "development-only UI Lab fixture evidence");

  const evidenceRoot = process.env.UI_LAB_STATE_EVIDENCE_DIR
    ? resolve(process.env.UI_LAB_STATE_EVIDENCE_DIR)
    : null;
  const viewportWidth = Number.parseInt(testInfo.project.name, 10);
  const records: Array<Record<string, unknown>> = [];
  const failures: string[] = [];

  await page.goto("/_ui-lab", { waitUntil: "domcontentloaded" });
  await expect(page.locator('[data-ui-lab-ready="true"]')).toBeVisible();
  await expect(page.getByText("Fixture 只存在于本验收台，不代表真实算法、支付或权益")).toBeVisible();
  await page.getByRole("combobox", { name: "页面与场景" }).selectOption("bazi-input");
  await page.getByRole("button", { name: `${viewportWidth} 像素` }).click();

  for (const item of STATE_INVENTORY) {
    await page.getByRole("combobox", { name: "状态" }).selectOption(item.state);
    const preview = page.getByTestId("ui-lab-preview");
    const stateSurface = preview
      .getByTestId("ui-lab-preview-body")
      .locator(`:scope > [data-state="${item.state}"]`);
    const canonicalStatus = stateSurface.locator(
      `:scope > [data-state="${item.canonicalState}"]`,
    );

    await expect(preview).toHaveAttribute("data-viewport", String(viewportWidth));
    await expect(stateSurface).toBeVisible();
    await expect(canonicalStatus).toBeVisible();
    await preview.scrollIntoViewIfNeeded();

    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    }));
    const overflowPx = Math.max(dimensions.document, dimensions.body) - dimensions.viewport;
    if (overflowPx > 1) failures.push(`${item.state}: page overflow ${overflowPx}px`);

    const screenshotPath = evidenceRoot
      ? resolve(evidenceRoot, testInfo.project.name, `${item.state}.jpg`)
      : null;
    if (screenshotPath) {
      await mkdir(resolve(evidenceRoot!, testInfo.project.name), { recursive: true });
      await page.screenshot({ path: screenshotPath, type: "jpeg", quality: 70 });
    }

    records.push({
      state: item.state,
      canonicalState: item.canonicalState,
      viewport: {
        width: dimensions.viewport,
        height: await page.evaluate(() => window.innerHeight),
      },
      pageOverflowPx: overflowPx,
      fixtureOnly: true,
      countedAsNormalPass: false,
      screenshot: screenshotPath && evidenceRoot
        ? relative(evidenceRoot, screenshotPath)
        : null,
    });
  }

  await page.getByRole("combobox", { name: "页面与场景" }).selectOption("workbench-handle");
  await page.getByRole("combobox", { name: "状态" }).selectOption("pristine");
  const workspace = page.locator('[data-layout="workbench-workspace"]');
  await expect(workspace).toBeVisible();
  const workbenchLayout = await workspace.evaluate((element) => {
    const first = element.children[0]?.getBoundingClientRect();
    const second = element.children[1]?.getBoundingClientRect();
    if (!first || !second) throw new Error("workbench panes missing");
    const isTwoColumn = Math.abs(first.top - second.top) <= 2 && second.left > first.left;
    return {
      isTwoColumn,
      boardPaneWidthPx: Math.round(first.width * 100) / 100,
      rightReadingPaneWidthPx: Math.round(second.width * 100) / 100,
    };
  });
  const expectedTwoColumn = viewportWidth >= 1024;
  if (workbenchLayout.isTwoColumn !== expectedTwoColumn) {
    failures.push(
      `workbench: two-column=${workbenchLayout.isTwoColumn}, expected ${expectedTwoColumn}`,
    );
  }
  if (workbenchLayout.isTwoColumn && workbenchLayout.rightReadingPaneWidthPx < 360) {
    failures.push(
      `workbench: right reading pane ${workbenchLayout.rightReadingPaneWidthPx}px below 360px`,
    );
  }
  const workbenchScreenshotPath = evidenceRoot
    ? resolve(evidenceRoot, testInfo.project.name, "workbench-layout.jpg")
    : null;
  if (workbenchScreenshotPath) {
    await workspace.scrollIntoViewIfNeeded();
    await page.screenshot({ path: workbenchScreenshotPath, type: "jpeg", quality: 70 });
  }
  const workbenchEvidence = {
    viewportWidth,
    expectedTwoColumn,
    ...workbenchLayout,
    productionComponents: ["WorkbenchShell", "ReadingShell"],
    fixtureOnly: true,
    countedAsNormalPass: false,
    screenshot: workbenchScreenshotPath && evidenceRoot
      ? relative(evidenceRoot, workbenchScreenshotPath)
      : null,
  };

  if (evidenceRoot) {
    await mkdir(evidenceRoot, { recursive: true });
    await writeFile(
      resolve(evidenceRoot, `${testInfo.project.name}.json`),
      `${JSON.stringify(
        {
          schema: "mingli.ui-lab-state-evidence/v1",
          generatedAt: new Date().toISOString(),
          project: testInfo.project.name,
          route: "/_ui-lab",
          environment: "development-only",
          fixtureOnly: true,
          countedAsNormalPass: false,
          failures,
          states: records,
          workbenchLayout: workbenchEvidence,
        },
        null,
        2,
      )}\n`,
      "utf8",
    );
  }

  expect(failures, failures.join("\n")).toEqual([]);
});
