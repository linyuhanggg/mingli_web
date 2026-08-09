import { render, screen, within } from "@testing-library/react";

import AccountPage from "@/app/account/page";


describe("account page header contract", () => {
  it("uses the shared AppPageHeader shape with a single h1 and no eyebrow", () => {
    const { container } = render(<AccountPage />);

    const header = container.querySelector("header");
    expect(header).not.toBeNull();

    const heading = screen.getByRole("heading", {
      level: 1,
      name: "邮箱是你的默认登录入口。",
    });
    expect(header?.firstElementChild).toBe(heading);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("explains auto-registration, direct login, Fake email, and phone timing in plain language", () => {
    const { container } = render(<AccountPage />);
    const main = screen.getByRole("main");
    const header = container.querySelector("header");
    expect(header).not.toBeNull();

    const description = within(header!).getByText(
      "首次邮箱验证自动注册账户，已有邮箱直接登录。当前是 Fake 环境，不会真的发送邮件；手机号登录稍后开放。",
    );
    expect(description).toHaveTextContent(/首次邮箱验证自动注册/);
    expect(description).toHaveTextContent(/已有邮箱直接登录/);
    expect(description).toHaveTextContent(/Fake 环境，不会真的发送邮件/);
    expect(description).toHaveTextContent(/手机号登录稍后开放/);
    expect(within(main).getByText("邮箱验证为主")).toBeVisible();
    expect(within(main).getByText("设备会话可撤销")).toBeVisible();
  });

  it("keeps the email login form, identity notes, and account-boundary notes", () => {
    render(<AccountPage />);
    const main = screen.getByRole("main");

    expect(within(main).getByRole("heading", { level: 2, name: "邮箱验证码登录" })).toBeVisible();
    expect(within(main).getByLabelText("邮箱地址")).toBeVisible();
    expect(within(main).getByRole("heading", { level: 2, name: "账户边界" })).toBeVisible();
    expect(within(main).getByRole("heading", { level: 2, name: "设备、订单与数据权利" })).toBeVisible();
  });

  it("keeps internal user identifiers out of the public copy", () => {
    render(<AccountPage />);
    const main = screen.getByRole("main");

    expect(within(main).queryByText(/User/i)).not.toBeInTheDocument();
    expect(within(main).queryByText(/用户 ID/i)).not.toBeInTheDocument();
  });
});
