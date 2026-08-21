import { expect, test, type Locator, type Page } from "@playwright/test";

async function pageOverflow(page: Page) {
  return page.evaluate(() => {
    const innerWidth = window.innerWidth;
    const scrollWidth = document.documentElement.scrollWidth;
    return {
      innerWidth,
      scrollWidth,
      overflowPx: scrollWidth - innerWidth,
    };
  });
}

async function assertNoOverflow(page: Page, label: string) {
  const measure = await pageOverflow(page);
  expect(
    measure.scrollWidth,
    `${label}: scrollWidth ${measure.scrollWidth} > innerWidth ${measure.innerWidth} (+${measure.overflowPx}px)`,
  ).toBeLessThanOrEqual(measure.innerWidth + 1);
  return measure;
}

const RESULT_TABS = [
  "已返回事实",
  "loading",
  "empty",
  "error",
  "processing",
  "unavailable",
  "unauthorized",
] as const;

const WORKBENCH_STATES = [
  "pristine",
  "loading",
  "empty",
  "failed",
  "queued",
  "unavailable",
  "unauthorized",
] as const;

test("bazi 360 first-screen controls stay above the mobile bottom bar", async ({ page }) => {
  test.skip(page.viewportSize()?.width !== 360, "This is the focused 360px geometry contract.");

  await page.goto("/bazi", { waitUntil: "domcontentloaded" });
  const bottomBar = page.getByRole("navigation", { name: "移动底栏" });
  await expect(bottomBar).toBeVisible();

  const controls: Array<[string, Locator]> = [
    ["受测对象", page.getByRole("textbox", { name: "受测对象" })],
    ["性别", page.getByRole("group", { name: /性别/ })],
    ["出生日期", page.getByRole("group", { name: /出生日期/ })],
    ["出生时间", page.getByRole("group", { name: /出生时间/ })],
    ["出生地点", page.getByRole("group", { name: /出生地点/ })],
    ["主提交", page.getByRole("button", { name: "立即排盘（免费）· 查看八字四柱" })],
  ];
  const bottomBarBox = await bottomBar.boundingBox();
  expect(bottomBarBox).not.toBeNull();

  for (const [label, control] of controls) {
    await expect(control).toBeVisible();
    const box = await control.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.y, label).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height, label)
      .toBeLessThanOrEqual(bottomBarBox!.y);
  }

  await expect(page.getByText("八字任务输入", { exact: true })).toHaveCount(0);
  await expect(page.getByText("排盘资料", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("group", { name: /历法/ })).toHaveCount(0);
  await expect(page.getByRole("checkbox", { name: /不知道出生时辰/ })).toHaveCount(0);
});

test("bazi result, workbench and hepan do not overflow the viewport", async ({ page }, testInfo) => {
  const viewport = testInfo.project.name;
  const table: Array<Record<string, unknown>> = [];

  await page.goto("/bazi", { waitUntil: "domcontentloaded" });
  table.push({ viewport, surface: "/bazi input", ...(await assertNoOverflow(page, `${viewport} /bazi`)) });

  await page.goto("/_ui-lab/bazi-result", { waitUntil: "domcontentloaded" });
  for (const tab of RESULT_TABS) {
    await page.getByRole("button", { name: tab, exact: true }).click();
    table.push({
      viewport,
      surface: `/_ui-lab/bazi-result ${tab}`,
      ...(await assertNoOverflow(page, `${viewport} bazi-result ${tab}`)),
    });
  }

  await page.goto("/_ui-lab", { waitUntil: "domcontentloaded" });
  await expect(page.locator('[data-ui-lab-ready="true"]')).toBeVisible();
  await page.getByRole("combobox", { name: "页面与场景" }).selectOption("workbench-handle");
  for (const state of WORKBENCH_STATES) {
    await page.getByRole("combobox", { name: "状态" }).selectOption(state);
    await expect(page.getByTestId("ui-lab-preview")).toBeVisible();
    table.push({
      viewport,
      surface: `/_ui-lab workbench-handle ${state}`,
      ...(await assertNoOverflow(page, `${viewport} ui-lab workbench ${state}`)),
    });
  }

  await page.goto("/_ui-lab/bazi-hepan", { waitUntil: "domcontentloaded" });
  for (const tab of RESULT_TABS) {
    await page.getByRole("button", { name: tab, exact: true }).click();
    table.push({
      viewport,
      surface: `/_ui-lab/bazi-hepan ${tab}`,
      ...(await assertNoOverflow(page, `${viewport} bazi-hepan ${tab}`)),
    });
  }

  await page.goto("/bazi/hepan", { waitUntil: "domcontentloaded" });
  table.push({
    viewport,
    surface: "/bazi/hepan",
    ...(await assertNoOverflow(page, `${viewport} /bazi/hepan`)),
  });

  console.log(`OVERFLOW_TABLE ${JSON.stringify(table)}`);
});
