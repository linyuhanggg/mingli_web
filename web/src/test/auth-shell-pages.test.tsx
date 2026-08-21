import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/auth/login/page";
import RecoverPage from "@/app/auth/recover/page";
import RegisterPage from "@/app/auth/register/page";
import AuthConsentPage from "@/app/auth/consent/page";
import AuthSetPasswordPage from "@/app/auth/set-password/page";
import AuthVerifyPage from "@/app/auth/verify/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/auth/login",
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
}));

vi.mock("@/components/password-login-form", () => ({
  PasswordLoginForm: () => (
    <form aria-label="密码主登录表单">
      <button type="submit">登录</button>
    </form>
  ),
}));

vi.mock("@/components/registration-form", () => ({
  RegistrationForm: () => (
    <form aria-label="注册表单">
      <button type="submit">注册并登录</button>
    </form>
  ),
}));

vi.mock("@/components/otp-form", () => ({
  OtpForm: () => (
    <form aria-label="验证码登录表单">
      <button type="submit">验证</button>
    </form>
  ),
}));

vi.mock("@/components/consent-form", () => ({
  ConsentForm: () => (
    <form aria-label="政策确认">
      <button type="submit">确认并保存</button>
    </form>
  ),
}));

vi.mock("@/components/password-set-form", () => ({
  PasswordSetForm: () => (
    <form aria-label="设置密码">
      <button type="submit">保存密码</button>
    </form>
  ),
}));

vi.mock("@/components/password-recovery-form", () => ({
  PasswordRecoveryForm: () => (
    <form aria-label="找回账号表单">
      <button type="submit">发送验证码</button>
    </form>
  ),
}));

beforeEach(() => {
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("auth four-page shell", () => {
  it("keeps login as a 30px title, one intro, and no side Status", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { level: 1, name: "登录" })).toBeVisible();
    expect(screen.getByText("登录后进入账户")).toBeVisible();
    expect(screen.queryByText("登录暂不可用")).not.toBeInTheDocument();
    expect(screen.queryByText("登录后继续原来的任务。")).not.toBeInTheDocument();
    expect(screen.queryByText(/接管当前游客|继续原来的任务|调试码|OTP 快捷登录/)).not.toBeInTheDocument();

    const nav = screen.getByRole("navigation", { name: "其他认证入口" });
    expect(within(nav).getByRole("link", { name: "用验证码登录" })).toHaveAttribute("href", "/auth/verify");
    expect(within(nav).getByRole("link", { name: "注册" })).toHaveAttribute("href", "/auth/register");
    expect(within(nav).getByRole("link", { name: "找回账号" })).toHaveAttribute("href", "/auth/recover");
  });

  it("keeps register as a 30px title with the policy-first intro", () => {
    render(<RegisterPage />);

    expect(screen.getByRole("heading", { level: 1, name: "注册" })).toBeVisible();
    expect(screen.getByText("先验证手机或邮箱，再设密码并同意政策。")).toBeVisible();
    expect(screen.queryByText("注册暂不可用")).not.toBeInTheDocument();
    expect(screen.queryByText("注册按验证、设密码、同意政策推进。")).not.toBeInTheDocument();
  });

  it("keeps verify as 验证身份 and does not mention device or guest takeover", () => {
    render(<AuthVerifyPage />);

    expect(screen.getByRole("heading", { level: 1, name: "验证身份" })).toBeVisible();
    expect(screen.getByText("验证后进入账户")).toBeVisible();
    expect(screen.queryByText("验证暂不可用")).not.toBeInTheDocument();
    expect(screen.queryByText(/设备会话|接管游客|正在进入 \/account|返回密码登录/)).not.toBeInTheDocument();
  });

  it("keeps recover title and the reset-and-logout intro", () => {
    render(<RecoverPage />);

    expect(screen.getByRole("heading", { level: 1, name: "找回账号" })).toBeVisible();
    expect(
      screen.getByText("用已验证的手机或邮箱重设密码。成功后其他已登录设备会退出。"),
    ).toBeVisible();
    expect(screen.getByText("不会因为找回请求创建新账号")).toBeVisible();
    expect(screen.queryByText("账号找回暂不可用")).not.toBeInTheDocument();
    expect(screen.queryByText("恢复访问，不覆盖历史事实。")).not.toBeInTheDocument();
  });

  it("locks auth header to --font-size-page and submit to the black action token", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/auth-shell.module.css"),
      "utf8",
    );

    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(css).toMatch(/button\[type="submit"\][^}]*background:\s*var\(--color-action\)/s);
    expect(css).toMatch(/button\[type="submit"\][^}]*min-height:\s*var\(--target-submit\)/s);
    expect(css).toMatch(/\.column\s*\{[^}]*width:\s*min\(var\(--container-form\)/s);
  });

  it("keeps consent on AuthShell with reaccept-only page and no side Status", () => {
    render(<AuthConsentPage />);

    expect(screen.getByRole("heading", { level: 1, name: "政策同意" })).toBeVisible();
    expect(screen.getByText("请分别确认隐私政策和服务条款。")).toBeVisible();
    expect(screen.queryByText("每次同意都绑定具体政策版本。")).not.toBeInTheDocument();
    expect(screen.queryByText("需要已验证会话")).not.toBeInTheDocument();
    expect(screen.queryByText(/development_code|调试码/)).not.toBeInTheDocument();
  });

  it("keeps set-password on AuthShell without the identity-lecture title", () => {
    render(<AuthSetPasswordPage />);

    expect(screen.getByRole("heading", { level: 1, name: "设置密码" })).toBeVisible();
    expect(screen.getByText("为当前账户设置密码。")).toBeVisible();
    expect(screen.queryByText("设置密码前必须先确认身份。")).not.toBeInTheDocument();
    expect(screen.queryByText("需要已验证会话")).not.toBeInTheDocument();
  });

  it("does not put development_code on the four production auth pages", () => {
    for (const file of [
      "src/app/auth/login/page.tsx",
      "src/app/auth/register/page.tsx",
      "src/app/auth/verify/page.tsx",
      "src/app/auth/recover/page.tsx",
      "src/app/auth/consent/page.tsx",
      "src/app/auth/set-password/page.tsx",
      "src/components/auth-shell.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondaryStatus|statusTitle|authGrid/);
    }
  });
});
