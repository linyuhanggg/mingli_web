import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RegistrationForm } from "@/components/registration-form";

const api = vi.hoisted(() => ({
  registerWithOtp: vi.fn(),
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
    registerWithOtp: api.registerWithOtp,
    requestOtp: api.requestOtp,
  };
});

beforeEach(() => {
  api.registerWithOtp.mockReset();
  api.requestOtp.mockReset();
  replaceMock.mockReset();
});

describe("RegistrationForm", () => {
  it("requires both policy consents before registering with the verified identity", async () => {
    api.requestOtp.mockResolvedValue({
      challenge_id: "967ea7cc-7b77-4db3-8d27-5a897679791f",
      development_code: "246810",
    });
    api.registerWithOtp.mockResolvedValue({ csrf_token: "device-csrf-token" });
    const user = userEvent.setup();

    render(<RegistrationForm />);
    await user.type(screen.getByRole("textbox", { name: "手机或邮箱" }), "new-user@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));
    await screen.findByRole("textbox", { name: "验证码" });
    await user.type(screen.getByRole("textbox", { name: "验证码" }), "246810");
    await user.type(screen.getByLabelText("设置密码"), "correct-password");
    await user.type(screen.getByLabelText("确认密码"), "correct-password");

    const submit = screen.getByRole("button", { name: "注册并登录" });
    expect(submit).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: "我已阅读并同意隐私政策" }));
    await user.click(screen.getByRole("checkbox", { name: "我已阅读并同意服务条款" }));
    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() => {
      expect(api.registerWithOtp).toHaveBeenCalledWith({
        challenge_id: "967ea7cc-7b77-4db3-8d27-5a897679791f",
        code: "246810",
        password: "correct-password",
        policy_version: "development-preview-v0.1",
      });
      expect(replaceMock).toHaveBeenCalledWith("/account");
    });
  });
});
