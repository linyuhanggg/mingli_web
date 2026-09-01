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
    const getStat = (label: string) =>
      within(main).getByText((_, element) => element?.textContent === label);
    expect(getStat("13 个术数体系")).toBeVisible();
    expect(getStat("55 部古籍")).toBeVisible();
    expect(getStat("1328 条证据索引")).toBeVisible();
    expect(within(main).getByText(/先给确定性盘面事实，再谈解释与边界/)).toBeVisible();

    // Hero CTA
    const hero = within(main).getByRole("region", { name: "十三术同根，五十五部古籍为证" });
    expect(within(hero).getByRole("link", { name: /开始排盘/ })).toHaveAttribute("href", "/bazi");
    expect(within(hero).getByRole("link", { name: "命盘合参" })).toHaveAttribute("href", "/hecan");

    // 首页不再创建第二套宣纸剧场或额外品牌氛围层。
    expect(within(main).queryByTestId("home-atmosphere")).not.toBeInTheDocument();

    // 任务入口链接矩阵：七术 + 见相 + 合参两产品 + 两个辅助入口；/canwen 已并入命盘合参
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
      ["人生 K 线", "/life-kline"],
      ["工具", "/tools"],
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
    expect(links.some((entry) => entry.getAttribute("href") === "/daily")).toBe(false);
    expect(links.some((entry) => entry.getAttribute("href") === "/library")).toBe(false);
    expect(within(main).queryByText("多盘问答")).not.toBeInTheDocument();
    expect(within(main).queryByText("三术合参")).not.toBeInTheDocument();
    expect(
      within(main).queryByRole("link", { name: /禄命纳音/ }),
      "禄命纳音 is an internal module, not a homepage natal entry",
    ).toBeNull();

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

  it("renders the complete homepage without the retired atmosphere component", () => {
    render(<HomePage />);

    expect(screen.getByRole("main")).toHaveClass("xuan-order-home");
    expect(screen.queryByTestId("home-atmosphere")).not.toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeVisible();
  });
});
