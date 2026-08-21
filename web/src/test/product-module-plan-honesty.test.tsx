import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import BaziPage from "@/app/bazi/page";
import LiuyaoPage from "@/app/liuyao/page";
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
  listProfiles: vi.fn().mockResolvedValue({ profiles: [] }),
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
 * 录入屏不再挂完整 ModulePlan / 「待接入」徽章。
 * 目录里未交付的槽位仍不得写成必然拿到的内容。
 */
describe("bazi module plan honesty", () => {
  it("does not hang ModulePlan or 待接入 badges on the input screen", () => {
    render(<BaziPage />);

    expect(screen.queryByRole("complementary", { name: /四柱与五行力量/ })).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText("标「待接入」的现在不会出现")).not.toBeInTheDocument();
  });

  it("does not hang ModulePlan or 待接入 badges on liuyao input either", () => {
    render(<LiuyaoPage />);

    expect(screen.queryByRole("complementary", { name: /六次过程与本卦变卦/ })).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.getByText("确认后生成盘面")).toBeVisible();
  });

  it("does not promise every slot unconditionally", () => {
    render(<BaziPage />);

    expect(screen.queryByText("提交后你会依次拿到这些内容。")).toBeNull();
  });

  it("states the target-time condition for temporal layers", () => {
    expect(PRODUCT_CATALOG.bazi.modules).not.toContain("大运、流年与关键流月");
    expect(
      PRODUCT_CATALOG.bazi.modules.some((module) => module.includes("指定目标时间")),
    ).toBe(true);
  });
});
