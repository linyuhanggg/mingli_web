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
  "ready",
  "loading",
  "empty",
  "locked",
  "need-input",
  "error",
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

test("bazi result six states stay within the viewport", async ({ page }, testInfo) => {
  const viewport = testInfo.project.name;
  await page.goto("/_ui-lab/bazi-result", { waitUntil: "domcontentloaded" });

  for (const state of RESULT_TABS) {
    await page.getByRole("button", { name: state, exact: true }).click();
    await assertNoOverflow(page, `${viewport} bazi-result ${state}`);
  }

  await page.getByRole("button", { name: "ready", exact: true }).click();
  await expect(page.getByRole("tablist", { name: "时间层" })).toBeVisible();
  await expect(page.getByRole("tab")).toHaveCount(6);
  await expect(page.getByRole("table", { name: "四柱专业矩阵" })).toBeVisible();
});

test("bazi mobile luck cycles form a 4 by 2 grid without local scrolling", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "360",
    "This focused contract covers the 360px and 390px mobile layouts once.",
  );

  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/_ui-lab/bazi-result", {
      waitUntil: "domcontentloaded",
    });
    await page.getByRole("button", { name: "ready", exact: true }).click();
    await page.getByRole("tab", { name: /^大运/ }).click();

    const panel = page.getByRole("tabpanel", { name: /^大运/ });
    const table = panel.getByRole("table", { name: "完整大运序列" });
    await expect(table).toBeVisible();

    const layout = await table.evaluate((element) => {
      const luckTable = element as HTMLTableElement;
      const viewport = luckTable.parentElement;
      const body = luckTable.tBodies.item(0);
      const rows = body ? Array.from(body.rows) : [];
      const rowYs = rows.map((row) => row.getBoundingClientRect().y);

      return {
        bodyDisplay: body ? getComputedStyle(body).display : "missing",
        gridTemplateColumns: body
          ? getComputedStyle(body).gridTemplateColumns
          : "missing",
        rowYs,
        tableWidth: luckTable.getBoundingClientRect().width,
        viewportClientWidth: viewport?.clientWidth ?? 0,
        viewportScrollWidth: viewport?.scrollWidth ?? 0,
      };
    });

    expect(layout.rowYs, `${width}px luck-cycle count`).toHaveLength(8);
    expect(layout.bodyDisplay, `${width}px tbody display`).toBe("grid");
    expect(
      layout.gridTemplateColumns.split(" ").filter(Boolean),
      `${width}px luck-cycle columns`,
    ).toHaveLength(4);
    expect(
      layout.viewportScrollWidth,
      `${width}px luck-cycle viewport scroll width`,
    ).toBeLessThanOrEqual(layout.viewportClientWidth + 1);
    expect(layout.tableWidth, `${width}px luck-cycle table width`)
      .toBeLessThanOrEqual(layout.viewportClientWidth + 1);

    const firstRow = layout.rowYs.slice(0, 4);
    const secondRow = layout.rowYs.slice(4, 8);
    expect(
      Math.max(...firstRow) - Math.min(...firstRow),
      `${width}px first luck-cycle row alignment`,
    ).toBeLessThanOrEqual(1);
    expect(
      Math.max(...secondRow) - Math.min(...secondRow),
      `${width}px second luck-cycle row alignment`,
    ).toBeLessThanOrEqual(1);
    expect(
      Math.min(...secondRow),
      `${width}px second luck-cycle row follows the first`,
    ).toBeGreaterThan(Math.max(...firstRow));

    console.log(`MING58_LUCK_GRID ${JSON.stringify({ width, ...layout })}`);
  }
});

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

test("bazi input Pattern 1 layout has no overflow and keeps the trust rail populated", async ({ page }, testInfo) => {
  const viewport = testInfo.project.name;
  const width = page.viewportSize()?.width ?? 0;

  await page.goto("/bazi", { waitUntil: "domcontentloaded" });

  const layout = page.locator('[data-input-region="first-screen"]');
  const trustRail = page.getByRole("complementary", { name: "提交后的八字盘面预览" });
  const submit = page.getByRole("button", { name: "立即排盘（免费）· 查看八字四柱" });
  await expect(layout).toBeVisible();
  await expect(trustRail).toBeVisible();
  await expect(trustRail).toContainText("提交后填入你的盘");
  await expect(trustRail).toContainText("示意骨架");
  await expect(trustRail).toContainText("verified_exact");
  await expect(trustRail).toContainText("1. 提交资料");
  await expect(trustRail).toContainText("2. 生成事实盘");
  await expect(trustRail).toContainText("3. 核对引文");

  const report = await page.evaluate(() => {
    const firstScreen = document.querySelector('[data-input-region="first-screen"]');
    const placeParts = document.querySelector('[class*="placeParts"]');
    const submitButton = Array.from(document.querySelectorAll("button")).find((button) => button.textContent?.includes("立即排盘"));
    const inputGridColumns = firstScreen ? getComputedStyle(firstScreen).gridTemplateColumns.split(" ").filter(Boolean) : [];
    const placeGridColumns = placeParts ? getComputedStyle(placeParts).gridTemplateColumns.split(" ").filter(Boolean) : [];
    const submitBox = submitButton?.getBoundingClientRect();
    return {
      columns: inputGridColumns.length,
      placeColumns: placeGridColumns.length,
      submitHeight: submitBox?.height ?? 0,
      hasTrustRail: Boolean(document.querySelector('[aria-label="提交后的八字盘面预览"]')),
      overflowPx: document.documentElement.scrollWidth - window.innerWidth,
    };
  });

  expect(report.overflowPx, `${viewport} /bazi input overflow`).toBeLessThanOrEqual(1);
  expect(report.columns, `${viewport} /bazi input columns`).toBe(width >= 1024 ? 2 : 1);
  expect(report.submitHeight, `${viewport} submit target height`).toBeGreaterThanOrEqual(48);
  if (width <= 640) {
    expect(report.placeColumns, `${viewport} place select columns`).toBe(1);
  }
  await expect(submit).toBeVisible();
  await testInfo.attach(`ming-12-bazi-${viewport}.png`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  console.log(`MING12_INPUT_LAYOUT ${JSON.stringify({ viewport, width, ...report })}`);
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
