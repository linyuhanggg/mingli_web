import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PasswordRecoveryForm } from "@/components/password-recovery-form";

const api = vi.hoisted(() => ({
  recoverPassword: vi.fn(),
  requestOtp: vi.fn(),
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
    recoverPassword: api.recoverPassword,
    requestOtp: api.requestOtp,
  };
});

beforeEach(() => {
  api.recoverPassword.mockReset();
  api.requestOtp.mockReset();
  replaceMock.mockReset();
});

describe("PasswordRecoveryForm", () => {
  it("requests an email OTP, resets the password, and routes to the account", async () => {
    api.requestOtp.mockResolvedValue({
      challenge_id: "967ea7cc-7b77-4db3-8d27-5a897679791f",
      development_code: "246810",
    });
    api.recoverPassword.mockResolvedValue({ csrf_token: "device-csrf-token" });
    const user = userEvent.setup();

    render(<PasswordRecoveryForm />);
    expect(screen.getByText(/不会因为找回请求创建新账号/)).toBeVisible();
    expect(screen.queryByText(/不覆盖历史事实/)).not.toBeInTheDocument();
    expect(screen.queryByText(/调试码/)).not.toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "手机或邮箱" }), "user@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));

    await screen.findByRole("textbox", { name: "验证码" });
    await user.type(screen.getByRole("textbox", { name: "验证码" }), "246810");
    await user.type(screen.getByLabelText("新密码"), "new-password");
    await user.type(screen.getByLabelText("确认新密码"), "new-password");
    await user.click(screen.getByRole("button", { name: "重设密码并登录" }));

    await waitFor(() => {
      expect(api.requestOtp).toHaveBeenCalledWith({
        channel: "email",
        destination: "user@example.com",
      });
      expect(api.recoverPassword).toHaveBeenCalledWith({
        challenge_id: "967ea7cc-7b77-4db3-8d27-5a897679791f",
        code: "246810",
        password: "new-password",
      });
      expect(replaceMock).toHaveBeenCalledWith("/account");
    });
  });
});
