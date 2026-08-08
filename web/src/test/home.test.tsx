import { render, screen, within } from "@testing-library/react";

import HomePage from "@/app/page";


describe("responsive public home", () => {
  it("offers the three frozen first tasks", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("link", { name: "免费建立命理档案" }),
    ).toHaveAttribute("href", "/app/profile/new");
    expect(screen.getByText("今日与近七日")).toBeVisible();
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
        name: /把时间读成一份.*可核对的个人档案/,
      }),
    ).toBeVisible();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("explains deterministic calculation, AI boundaries, and verification", () => {
    render(<HomePage />);

    expect(screen.getByText(/确定性命理核心/)).toBeVisible();
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
