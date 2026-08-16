import { expect, test } from "@playwright/test";

test("UI Lab selected viewport drives inner layout and selected write targets", async ({
  page,
}, testInfo) => {
  test.skip(!process.env.ADMIN_UI_LAB_E2E, "development-only UI Lab evidence");
  test.skip(testInfo.project.name !== "1440", "wide host is required to measure preview widths");

  await page.goto("/_ui-lab", { waitUntil: "domcontentloaded" });
  await expect(page.locator('[data-ui-lab-ready="true"]')).toBeVisible();
  await page.getByRole("combobox", { name: "演示路由" }).selectOption("/refunds");
  await page.getByRole("combobox", { name: "员工角色" }).selectOption("finance");
  await page.getByRole("combobox", { name: "预览视口" }).selectOption("360");

  const preview = page.locator('[data-preview-scope="business-surface"]');
  await expect(preview).toHaveAttribute("data-preview-viewport", "360");
  await expect(page.getByText("当前业务内层预览：360px")).toBeVisible();
  expect(Math.round((await preview.boundingBox())?.width ?? 0)).toBe(360);

  const table = preview.getByRole("table", { name: "退款列表" });
  await expect(table).toHaveCSS("display", "block");
  await expect(table.locator('td[data-label="退款"]').first()).toBeVisible();

  const writeButton = preview.getByRole("button", { name: "审批退款" });
  await expect(preview.getByText(/查看“允许” · 写入“允许”/)).toBeVisible();
  await expect(writeButton).toBeDisabled();
  const secondRowCheckbox = preview.getByRole("checkbox", { name: /选择 退款-DEMO-002/ });
  await secondRowCheckbox.check();
  await expect(writeButton).toBeEnabled();
  await writeButton.click();

  const dialog = page.getByRole("dialog", { name: "确认审批退款" });
  await expect(dialog).toContainText("退款只读样例");
  await expect(dialog).not.toContainText("退款演示记录");

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(Math.max(dimensions.document, dimensions.body)).toBeLessThanOrEqual(
    dimensions.viewport,
  );
});
