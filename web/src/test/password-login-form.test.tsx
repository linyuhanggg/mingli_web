import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PasswordLoginForm } from "@/components/password-login-form";

const api = vi.hoisted(() => ({
  loginWithPassword: vi.fn(),
}));

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    loginWithPassword: api.loginWithPassword,
  };
});

beforeEach(() => {
  api.loginWithPassword.mockReset();
  replaceMock.mockReset();
});

describe("PasswordLoginForm", () => {
  it("submits an email identity and routes to the account after login", async () => {
    api.loginWithPassword.mockResolvedValue({
      csrf_token: "device-csrf-token",
    });
    const user = userEvent.setup();

    render(<PasswordLoginForm />);
    expect(screen.getByText("密码不会保存在这台设备上。")).toBeVisible();
    expect(screen.queryByText(/浏览器存储/)).not.toBeInTheDocument();
    expect(screen.queryByText(/继续原来的任务/)).not.toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "手机或邮箱" }), "user@example.com");
    await user.type(screen.getByLabelText("密码"), "correct-password");
    await user.click(screen.getByRole("button", { name: "登录" }));

    await waitFor(() => {
      expect(api.loginWithPassword).toHaveBeenCalledWith({
        channel: "email",
        destination: "user@example.com",
        password: "correct-password",
      });
      expect(replaceMock).toHaveBeenCalledWith("/account");
    });
  });

  it("submits a phone identity and keeps a generic error on invalid credentials", async () => {
    api.loginWithPassword.mockRejectedValue(new Error("Invalid credentials"));
    const user = userEvent.setup();

    render(<PasswordLoginForm />);
    await user.type(screen.getByRole("textbox", { name: "手机或邮箱" }), "13800138000");
    await user.type(screen.getByLabelText("密码"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "登录" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("账号或密码不正确");
    expect(api.loginWithPassword).toHaveBeenCalledWith({
      channel: "phone",
      destination: "13800138000",
      password: "wrong-password",
    });
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
