import { render, screen, within } from "@testing-library/react";

import AppPage from "@/app/app/page";
import HomePage from "@/app/page";


describe("responsive public home", () => {
  it("offers the three frozen first tasks", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("link", { name: "免费建立命理档案" }),
    ).toHaveAttribute("href", "/app/profile/new");
    expect(screen.getByText("今日与近七日")).toBeVisible();
    expect(
      screen.getByRole("link", { name: "查看今日提示" }),
    ).toHaveAttribute("href", "/app/fortune/today");
    expect(
      screen.getByRole("link", { name: "问一件具体的事" }),
    ).toHaveAttribute("href", "/app/ask/liuyao");
  });

  it("uses an editorial page hierarchy instead of a blank chat box", () => {
    render(<HomePage />);

    const main = screen.getByRole("main");
    expect(within(main).getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      within(main).getByRole("heading", {
        level: 1,
        name: /先把人生事实算清楚/,
      }),
    ).toBeVisible();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("explains deterministic calculation, AI boundaries, and verification", () => {
    render(<HomePage />);

    expect(screen.getByText(/确定性计算/)).toBeVisible();
    expect(screen.getByText(/AI 只负责白话表达/)).toBeVisible();
    expect(screen.getByText(/三条现实核对/)).toBeVisible();
  });

  it("provides public navigation and a contentinfo landmark", () => {
    render(<HomePage />);

    const navigation = screen.getByRole("navigation", { name: "主导航" });
    expect(within(navigation).getByRole("link", { name: "价格" })).toHaveAttribute(
      "href",
      "/pricing",
    );
    expect(within(navigation).getByRole("link", { name: "方法" })).toHaveAttribute(
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
    expect(screen.getByRole("link", { name: "开始六爻起卦" })).toHaveAttribute(
      "href",
      "/app/ask/liuyao",
    );
  });
});
