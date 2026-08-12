import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";

import AppPage from "@/app/app/page";
import HomePage from "@/app/page";
import {
  isPublicNavigationItemActive,
  PRODUCT_CAPABILITIES,
  PUBLIC_PRIMARY_NAVIGATION,
  PUBLIC_UTILITY_NAVIGATION,
} from "@/lib/product-capabilities";


vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));


describe("responsive public home", () => {
  it("uses one canonical registry for every real P0 product entry", () => {
    expect(
      PRODUCT_CAPABILITIES.map(({ id, href, navigationLabel }) => ({
        id,
        href,
        navigationLabel,
      })),
    ).toEqual([
      {
        id: "bazi",
        href: "/app/profile/new",
        navigationLabel: "建立档案",
      },
      {
        id: "fortune",
        href: "/app/fortune/today",
        navigationLabel: "今日与近七日",
      },
      {
        id: "liuyao",
        href: "/app/ask/liuyao",
        navigationLabel: "一事一问",
      },
    ]);
    expect(PUBLIC_PRIMARY_NAVIGATION.map(({ href, label }) => ({ href, label }))).toEqual([
      { href: "/app/profile/new", label: "建立档案" },
      { href: "/app/fortune/today", label: "今日与近七日" },
      { href: "/app/ask/liuyao", label: "一事一问" },
    ]);
    expect(PUBLIC_UTILITY_NAVIGATION).toEqual([
      { href: "/methodology", label: "方法与边界" },
      { href: "/pricing", label: "价格与交付" },
      { href: "/account", label: "账户" },
    ]);

    const baziEntry = PUBLIC_PRIMARY_NAVIGATION[0];
    const fortuneEntry = PUBLIC_PRIMARY_NAVIGATION[1];
    expect(isPublicNavigationItemActive("/app/bazi", baziEntry)).toBe(true);
    expect(isPublicNavigationItemActive("/app/fortune/week", fortuneEntry)).toBe(true);

    expect(PRODUCT_CAPABILITIES.map(({ id, footerLabel, home }) => ({
      id,
      footerLabel,
      secondaryHref: home.secondaryAction?.href,
      tone: home.tone,
    }))).toEqual([
      {
        id: "bazi",
        footerLabel: "建立命理档案",
        secondaryHref: undefined,
        tone: "paper",
      },
      {
        id: "fortune",
        footerLabel: "今日与近七日",
        secondaryHref: "/app/fortune/week",
        tone: "ink",
      },
      {
        id: "liuyao",
        footerLabel: "一事一问 · 六爻",
        secondaryHref: undefined,
        tone: "clay",
      },
    ]);
  });

  it("offers the three real P0 tasks and keeps methodology secondary", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("link", { name: /免费体验起盘档案/ }),
    ).toHaveAttribute("href", "/app/profile/new");
    expect(
      screen.getByRole("link", { name: /查看今日/ }),
    ).toHaveAttribute("href", "/app/fortune/today");
    expect(
      screen.getByRole("link", { name: /查看近七日/ }),
    ).toHaveAttribute("href", "/app/fortune/week");
    expect(
      screen.getByRole("link", { name: /开始六爻起卦/ }),
    ).toHaveAttribute("href", "/app/ask/liuyao");
    expect(
      screen.getByRole("link", { name: /问一件工作上的事/ }),
    ).toHaveAttribute("href", "/app/ask/liuyao");

    const taskSection = screen.getByRole("region", {
      name: "从当下最想解决的事开始",
    });
    expect(
      within(taskSection).getByRole("heading", {
        level: 3,
        name: "建立档案 · 八字概览",
      }),
    ).toBeVisible();
    expect(
      within(taskSection).getByRole("heading", {
        level: 3,
        name: "一事一问 · 六爻",
      }),
    ).toBeVisible();
    expect(within(taskSection).getByText(/事业或工作问题与起卦方式/)).toBeVisible();
    expect(
      within(taskSection).queryByRole("heading", { name: /方法|古籍/ }),
    ).not.toBeInTheDocument();
    expect(
      within(taskSection)
        .getAllByRole("article")
        .map((card) => card.getAttribute("data-tone")),
    ).toEqual(["paper", "ink", "clay"]);
  });

  it("uses an editorial page hierarchy instead of a blank chat box", () => {
    render(<HomePage />);

    const main = screen.getByRole("main");
    expect(within(main).getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      within(main).getByRole("heading", {
        level: 1,
        name: /把时间变成私密、.*可核对的个人档案/,
      }),
    ).toBeVisible();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("explains deterministic calculation, AI boundaries, and verification", () => {
    render(<HomePage />);

    expect(screen.getAllByText(/确定性命理核心/).length).toBeGreaterThan(0);
    expect(screen.getByText(/AI 只在允许事实内组织白话/)).toBeVisible();
    expect(screen.getByText(/3 条现实核对/)).toBeVisible();
    expect(screen.getByText(/原典命中时才展示可定位来源/)).toBeVisible();
    expect(screen.queryByText(/提供可验证的原典依据/)).not.toBeInTheDocument();
  });

  it("states the free boundary and both real one-off products", () => {
    render(<HomePage />);

    const pricing = screen.getByRole("region", {
      name: "免费能力与两种单次报告",
    });
    expect(within(pricing).getByRole("heading", { name: "免费基础能力" })).toBeVisible();
    expect(
      within(pricing).getByRole("heading", { name: "个人命盘深度解读" }),
    ).toBeVisible();
    expect(
      within(pricing).getByRole("heading", { name: "一事一问 · 六爻事件报告" }),
    ).toBeVisible();
    expect(within(pricing).getByText("¥0")).toBeVisible();
    expect(within(pricing).getByText("¥29.90")).toBeVisible();
    expect(within(pricing).getByText("¥9.90")).toBeVisible();
    expect(within(pricing).getByText(/7 天内 3 次同盘追问/)).toBeVisible();
    expect(within(pricing).getByText(/72 小时内 2 次同盘追问/)).toBeVisible();
    expect(within(pricing).getByText(/测试期无真实支付/)).toBeVisible();
    for (const link of within(pricing).getAllByRole("link")) {
      expect(link).toHaveAttribute("href", "/pricing");
    }
    expect(within(pricing).queryByText(/专业版|专业学术版|永久免费|立即解锁/)).not.toBeInTheDocument();
  });

  it("provides public navigation and a contentinfo landmark", () => {
    render(<HomePage />);

    const navigation = screen.getByRole("navigation", { name: "主导航" });
    expect(
      within(navigation)
        .getAllByRole("link")
        .map((link) => ({ href: link.getAttribute("href"), label: link.textContent })),
    ).toEqual([
      { href: "/app/profile/new", label: "建立档案" },
      { href: "/app/fortune/today", label: "今日与近七日" },
      { href: "/app/ask/liuyao", label: "一事一问" },
    ]);

    const utilities = screen.getByRole("navigation", { name: "辅助导航" });
    expect(
      within(utilities)
        .getAllByRole("link")
        .map((link) => ({ href: link.getAttribute("href"), label: link.textContent })),
    ).toEqual([
      { href: "/methodology", label: "方法与边界" },
      { href: "/pricing", label: "价格与交付" },
      { href: "/account", label: "确认登录" },
    ]);
    expect(screen.getByRole("link", { name: "FateRadar 首页" })).toHaveAttribute("href", "/");
    expect(screen.queryByText("EN")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "专业版" })).not.toBeInTheDocument();

    const coreApplications = screen.getByRole("navigation", { name: "核心应用" });
    expect(
      within(coreApplications)
        .getAllByRole("link")
        .map((link) => ({ href: link.getAttribute("href"), label: link.textContent })),
    ).toEqual([
      { href: "/app/profile/new", label: "建立命理档案" },
      { href: "/app/fortune/today", label: "今日与近七日" },
      { href: "/app/ask/liuyao", label: "一事一问 · 六爻" },
    ]);

    for (const falseEntry of ["合盘分析", "命理双子", "双人合盘分析", "紫微斗数", "倪海厦"]) {
      expect(screen.queryByText(new RegExp(falseEntry))).not.toBeInTheDocument();
    }
    expect(screen.getByRole("contentinfo")).toBeVisible();
  });
});

describe("private app home", () => {
  it("links directly to every available Phase 2 flow", () => {
    render(<AppPage />);

    expect(screen.queryByText(/将在 Phase 2/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "建立命理档案" })).toHaveAttribute(
      "href",
      "/app/profile/new",
    );
    expect(screen.getByRole("link", { name: "查看今日" })).toHaveAttribute(
      "href",
      "/app/fortune/today",
    );
    expect(screen.getByRole("link", { name: "查看近七日" })).toHaveAttribute(
      "href",
      "/app/fortune/week",
    );
    expect(screen.getByRole("link", { name: "查看八字概览" })).toHaveAttribute(
      "href",
      "/app/bazi",
    );
    expect(screen.getByRole("link", { name: "查看已保存档案" })).toHaveAttribute(
      "href",
      "/app/profiles",
    );
    expect(screen.getByRole("link", { name: "开始六爻起卦" })).toHaveAttribute(
      "href",
      "/app/ask/liuyao",
    );
  });
});
