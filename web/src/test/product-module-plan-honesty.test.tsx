import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import BaziPage from "@/app/bazi/page";
import { PRODUCT_CATALOG } from "@/products/catalog";

const mockGetCapabilityProjection = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  getCapabilityProjection: mockGetCapabilityProjection,
}));

mockGetCapabilityProjection.mockResolvedValue({
  runtime_release_profile: "v53-time-check",
  source_status: "available",
  capabilities: [
    {
      capability_id: "bazi",
      label: "八字",
      tier: "A",
      source_system: "bazi",
      runtime_active_rule_count: 24,
      judgment_rule_count: 19,
      source_status: "available",
    },
  ],
});

afterEach(cleanup);

/**
 * §17 禁止正常产品路由出现假成功。录入页的模块清单是一份对用户的交付承诺，
 * 真实 Runtime 结果页当前不渲染「旺衰贡献」与「格局、喜忌与病药依据」两个槽位
 * （§19.2：缺字段时该区块整体不渲染），所以清单不得把它们写成必然拿到的内容。
 */
describe("bazi module plan honesty", () => {
  it("marks slots the result page cannot deliver as pending instead of promising them", () => {
    render(<BaziPage />);

    const plan = screen.getByRole("complementary", { name: /四柱与五行力量/ });

    for (const label of ["旺衰贡献", "格局、喜忌与病药依据"]) {
      const item = within(plan).getByText(label).closest("li");
      expect(item, `${label} 应在模块清单中`).not.toBeNull();
      expect(
        item?.getAttribute("data-module-status"),
        `${label} 当前结果页不渲染，必须标为 pending`,
      ).toBe("pending");
      expect(item?.textContent).toContain("待接入");
    }
  });

  it("keeps delivered slots unmarked", () => {
    render(<BaziPage />);

    const plan = screen.getByRole("complementary", { name: /四柱与五行力量/ });

    for (const label of ["年月日时四柱", "四柱图与五行力量"]) {
      const item = within(plan).getByText(label).closest("li");
      expect(item?.getAttribute("data-module-status")).toBe("available");
      expect(item?.textContent).not.toContain("待接入");
    }
  });

  it("does not promise every slot unconditionally", () => {
    render(<BaziPage />);

    const plan = screen.getByRole("complementary", { name: /四柱与五行力量/ });
    expect(within(plan).queryByText("提交后你会依次拿到这些内容。")).toBeNull();
  });

  it("states the target-time condition for temporal layers", () => {
    expect(PRODUCT_CATALOG.bazi.modules).not.toContain("大运、流年与关键流月");
    expect(
      PRODUCT_CATALOG.bazi.modules.some((module) => module.includes("指定目标时间")),
    ).toBe(true);
  });
});
