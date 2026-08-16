import { render, screen, within } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import HomePage from "@/app/page";


vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

afterEach(() => {
  vi.unstubAllGlobals();
});


describe("responsive public home", () => {
  it("is a value proposition plus task selector hybrid", () => {
    render(<HomePage />);

    const main = screen.getByRole("main");
    expect(within(main).getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      within(main).getByRole("heading", {
        level: 1,
        name: "十三术同根，五十五部古籍为证",
      }),
    ).toBeVisible();

    // 价值主张只讲机制与真实规模，不做效果承诺
    expect(within(main).getByText("13 个术数体系")).toBeVisible();
    expect(within(main).getByText("55 部古籍")).toBeVisible();
    expect(within(main).getByText("1328 条证据索引")).toBeVisible();
    expect(within(main).getByText(/先给确定性盘面事实，再谈解释与边界/)).toBeVisible();

    // Hero CTA
    const hero = within(main).getByRole("region", { name: "十三术同根，五十五部古籍为证" });
    expect(within(hero).getByRole("link", { name: /开始排盘/ })).toHaveAttribute("href", "/bazi");
    expect(within(hero).getByRole("link", { name: "命盘合参" })).toHaveAttribute("href", "/hecan");

    // 装饰层不进入阅读或交互语义
    expect(within(main).getByTestId("home-atmosphere")).toHaveAttribute("aria-hidden", "true");

    // 任务入口链接矩阵：七术 + 见相 + 合参两产品 + 辅助三入口；/canwen 已并入命盘合参
    const expectedEntries = [
      ["八字", "/bazi"],
      ["紫微", "/ziwei"],
      ["七政", "/qizheng"],
      ["六爻", "/liuyao"],
      ["奇门", "/qimen"],
      ["大六壬", "/daliuren"],
      ["见相", "/jianxiang"],
      ["命盘合参", "/hecan"],
      ["问事合参", "/wenshi"],
      ["每日", "/daily"],
      ["工具", "/tools"],
      ["知识内容", "/library"],
    ] as const;

    const links = within(main).getAllByRole("link");
    for (const [name, href] of expectedEntries) {
      const matching = links.filter((entry) => entry.getAttribute("href") === href);
      expect(matching.length, `missing home task link: ${href}`).toBeGreaterThan(0);
      expect(
        matching.some((entry) => new RegExp(name).test(entry.textContent ?? "")),
        `home link ${href} should expose ${name}`,
      ).toBe(true);
    }
    expect(
      links.find((entry) => entry.getAttribute("href") === "/canwen"),
      "retired /canwen entry must not appear on home",
    ).toBeUndefined();
    expect(within(main).queryByText("多盘问答")).not.toBeInTheDocument();
    expect(within(main).queryByText("三术合参")).not.toBeInTheDocument();

    // 分区：命盘 / 事件判断 / 合参 / 辅助
    expect(within(main).getByRole("region", { name: "命盘" })).toBeVisible();
    expect(within(main).getByRole("region", { name: "事件判断" })).toBeVisible();
    expect(within(main).getByRole("region", { name: "合参" })).toBeVisible();
    expect(within(main).getByRole("region", { name: "辅助" })).toBeVisible();

    // 合参区只有命盘合参与问事合参两个入口
    const crossRegion = within(main).getByRole("region", { name: "合参" });
    expect(within(crossRegion).getAllByRole("link")).toHaveLength(2);

    // 旧品牌与旧营销语言不得出现
    expect(within(main).queryByText(/TimeArchive/i)).not.toBeInTheDocument();
    expect(within(main).queryByRole("region", { name: "免费能力与两种单次报告" })).not.toBeInTheDocument();
    expect(within(main).queryByText(/把时间变成私密/)).not.toBeInTheDocument();
    expect(within(main).queryByRole("link", { name: /免费体验起盘档案/ })).not.toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeVisible();
  });

  it("observes the hero section so its negative-z-index art is not paused on screen", () => {
    const observe = vi.fn();

    class IntersectionObserverMock {
      readonly root = null;
      readonly rootMargin = "0px";
      readonly thresholds = [0.01];

      disconnect = vi.fn();
      observe = observe;
      takeRecords = vi.fn(() => []);
      unobserve = vi.fn();
    }

    vi.stubGlobal(
      "IntersectionObserver",
      IntersectionObserverMock,
    );

    render(<HomePage />);

    const atmosphere = screen.getByTestId("home-atmosphere");
    expect(observe).toHaveBeenCalledWith(atmosphere.parentElement);
  });
});
