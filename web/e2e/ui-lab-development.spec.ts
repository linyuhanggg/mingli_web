import { expect, test } from "@playwright/test";

test("Web UI Lab hydrates on a local development origin", async ({ page }, testInfo) => {
  test.skip(!process.env.UI_LAB_E2E, "development-only UI Lab evidence");
  test.skip(testInfo.project.name !== "1440", "wide host is required to measure preview widths");

  await page.goto("/_ui-lab", { waitUntil: "domcontentloaded" });
  await expect(page.locator('[data-ui-lab-ready="true"]')).toBeVisible();

  await page.getByRole("combobox", { name: "页面与场景" }).selectOption("bazi-input");
  await page.getByRole("combobox", { name: "状态" }).selectOption("filled");
  await page.getByRole("button", { name: "768 像素" }).click();

  const preview = page.getByTestId("ui-lab-preview");
  await expect(preview).toHaveAttribute("data-viewport", "768");
  await expect(page.getByText("预览：八字任务录入")).toBeVisible();
  await expect(preview.getByRole("form", { name: "八字任务输入" })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(Math.max(dimensions.document, dimensions.body)).toBeLessThanOrEqual(
    dimensions.viewport,
  );
});
