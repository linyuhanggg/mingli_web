import { expect, test } from "@playwright/test";

test("mobile public navigation is keyboard operable and restores focus", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/methodology", { waitUntil: "domcontentloaded" });

  const trigger = page.getByRole("button", { name: "打开术数菜单" });
  await expect(trigger).toBeVisible();
  await trigger.focus();
  await page.keyboard.press("Enter");

  const dialog = page.getByRole("dialog", { name: "术数导航" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "关闭" })).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
});

test("public shell reflows without horizontal overflow at 200% and 400% equivalents", async ({
  page,
}) => {
  for (const width of [640, 320]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/tools", { waitUntil: "domcontentloaded" });
    const dimensions = await page.evaluate(() => ({
      client: document.documentElement.clientWidth,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    }));

    expect(
      Math.max(dimensions.document, dimensions.body),
      `${width}px CSS viewport has horizontal overflow`,
    ).toBeLessThanOrEqual(dimensions.client);
  }
});

test("public shell honors reduced motion without long-running animations", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/methodology", { waitUntil: "domcontentloaded" });

  const longRunningAnimations = await page.evaluate(() =>
    document.getAnimations().filter((animation) => {
      const duration = animation.effect?.getComputedTiming().duration;
      return typeof duration === "number" && duration > 50;
    }).length,
  );

  expect(longRunningAnimations).toBe(0);
});

test("public task forms announce a validation summary and focus the first invalid field", async ({
  page,
}) => {
  await page.goto("/bazi", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /^立即排盘（免费）/ }).click();

  const summary = page.getByRole("alert", { name: "请先修正以下输入" });
  await expect(summary).toBeVisible();
  await expect(summary.getByRole("link", { name: "受测对象" })).toHaveAttribute(
    "href",
    "#bazi-subject",
  );
  await expect(page.getByLabel("受测对象")).toBeFocused();

  await summary.getByRole("link", { name: "受测对象" }).click();
  await expect(page.getByLabel("受测对象")).toBeFocused();
});

test("public landmarks and task form have named nodes in the Chrome accessibility tree", async ({
  page,
}) => {
  await page.goto("/bazi", { waitUntil: "domcontentloaded" });
  const cdp = await page.context().newCDPSession(page);
  const { nodes } = await cdp.send("Accessibility.getFullAXTree");
  const activeNodes = nodes.filter((node) => !node.ignored);
  const namedNodes = nodes.filter((node) => !node.ignored && node.name?.value);

  expect(activeNodes.some((node) => node.role?.value === "main")).toBe(true);
  expect(namedNodes.some((node) => node.role?.value === "navigation")).toBe(true);
  expect(
    namedNodes.some(
      (node) => node.role?.value === "form" && node.name?.value === "八字任务输入",
    ),
  ).toBe(true);
  expect(
    namedNodes.some((node) => node.role?.value === "heading" && node.name?.value?.includes("八字")),
  ).toBe(true);
});
