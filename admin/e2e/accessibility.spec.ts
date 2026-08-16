import { expect, test } from "@playwright/test";

test("mobile Admin navigation is keyboard operable and restores focus", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/", { waitUntil: "domcontentloaded" });

  const trigger = page.getByRole("button", { name: "打开运营导航" });
  await expect(trigger).toBeVisible();
  await trigger.focus();
  await page.keyboard.press("Enter");

  const dialog = page.getByRole("dialog", { name: "运营导航" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "关闭" })).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
});

test("Admin shell reflows without horizontal overflow at 200% and 400% equivalents", async ({
  page,
}) => {
  for (const width of [640, 320]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/", { waitUntil: "domcontentloaded" });
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

test("Admin shell honors reduced motion without long-running animations", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/", { waitUntil: "domcontentloaded" });

  const longRunningAnimations = await page.evaluate(() =>
    document.getAnimations().filter((animation) => {
      const duration = animation.effect?.getComputedTiming().duration;
      return typeof duration === "number" && duration > 50;
    }).length,
  );

  expect(longRunningAnimations).toBe(0);
});

test("Admin landmarks and navigation have named nodes in the Chrome accessibility tree", async ({
  page,
}) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const cdp = await page.context().newCDPSession(page);
  const { nodes } = await cdp.send("Accessibility.getFullAXTree");
  const activeNodes = nodes.filter((node) => !node.ignored);
  const namedNodes = nodes.filter((node) => !node.ignored && node.name?.value);

  expect(activeNodes.some((node) => node.role?.value === "main")).toBe(true);
  expect(namedNodes.some((node) => node.role?.value === "heading")).toBe(true);

  await page.setViewportSize({ width: 1024, height: 768 });
  await page.reload({ waitUntil: "domcontentloaded" });
  const desktopCdp = await page.context().newCDPSession(page);
  const { nodes: desktopNodes } = await desktopCdp.send("Accessibility.getFullAXTree");
  expect(
    desktopNodes.some(
      (node) => !node.ignored && node.role?.value === "navigation" && node.name?.value === "运营导航",
    ),
  ).toBe(true);
});

test("Admin login exposes a named form and labelled credentials", async ({ page }) => {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  const form = page.getByRole("form", { name: "员工登录" });

  await expect(form).toBeVisible();
  await expect(page.getByLabel("工作邮箱")).toBeVisible();
  await expect(page.getByLabel("密码")).toBeVisible();
});
