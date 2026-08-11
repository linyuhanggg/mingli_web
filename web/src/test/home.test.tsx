import { render, screen, within } from "@testing-library/react";

import AppPage from "@/app/app/page";
import HomePage from "@/app/page";


describe("responsive public home", () => {
  it("offers the three frozen first tasks", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("link", { name: /免费体验起盘档案/ }),
    ).toHaveAttribute("href", "/app/profile/new");
    expect(screen.getByText("今日与近七日")).toBeVisible();
    expect(
      screen.getByRole("link", { name: /开启阶段推算/ }),
    ).toHaveAttribute("href", "/app/fortune/today");
    expect(
      screen.getByRole("link", { name: /进入学术典籍库/ }),
    ).toHaveAttribute("href", "/methodology");
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
    expect(screen.getByText(/3 条现实核对位/)).toBeVisible();
  });

  it("provides public navigation and a contentinfo landmark", () => {
    render(<HomePage />);

    const navigation = screen.getByRole("navigation", { name: "主导航" });
    expect(within(navigation).getByRole("link", { name: /首页/ })).toHaveAttribute(
      "href",
      "/",
    );
    expect(within(navigation).getByRole("link", { name: /在线起盘/ })).toHaveAttribute(
      "href",
      "/app/profile/new",
    );
    expect(within(navigation).getByRole("link", { name: /学术与古籍库/ })).toHaveAttribute(
      "href",
      "/methodology",
    );
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
