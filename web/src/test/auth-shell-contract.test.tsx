import { readFileSync } from "node:fs";
import path from "node:path";

import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/auth/login/page";
import RecoverPage from "@/app/auth/recover/page";
import RegisterPage from "@/app/auth/register/page";
import ConsentPage from "@/app/auth/consent/page";
import SetPasswordPage from "@/app/auth/set-password/page";
import VerifyPage from "@/app/auth/verify/page";
import { resetApiCache } from "@/lib/api";


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
}));


function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  document.cookie = "mingli_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
  resetApiCache();
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.includes("/api/v1/guest-sessions")) {
        return jsonResponse({
          status: "active",
          expires_at: "2026-08-20T00:00:00Z",
          csrf_token: "guest-csrf-token-with-at-least-32-characters",
        }, 201);
      }
      if (url.includes("/api/v1/account")) {
        return jsonResponse({ title: "Authentication required" }, 401);
      }
      return jsonResponse({ title: "Not Found" }, 404);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const forbidden = [
  "继续原来的任务",
  "支持密码主登录",
  "不会写入浏览器存储",
  "浏览器存储",
  "不覆盖历史事实",
  "调试码",
  "development_code",
  "正在进入 /account",
  "接管游客",
];

function expectSharedShell(title: string, intro: string) {
  const main = screen.getByRole("main");
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getByRole("heading", { level: 1, name: title })).toBeVisible();
  expect(within(main).getByText(intro)).toBeVisible();
  expect(screen.queryByRole("status", { name: /支持密码主登录|需要验证身份|需要一次性验证码|先确认身份/ })).not.toBeInTheDocument();
  for (const phrase of forbidden) {
    expect(main).not.toHaveTextContent(phrase);
  }
}

describe("auth shell pages", () => {
  it("centers login on a 30px title, one sentence, and text links under the form", () => {
    render(<LoginPage />);
    expectSharedShell("登录", "登录后进入账户");
    const nav = screen.getByRole("navigation", { name: "其他认证入口" });
    expect(within(nav).getByRole("link", { name: "用验证码登录" })).toHaveAttribute("href", "/auth/verify");
    expect(within(nav).getByRole("link", { name: "注册" })).toHaveAttribute("href", "/auth/register");
    expect(within(nav).getByRole("link", { name: "找回账号" })).toHaveAttribute("href", "/auth/recover");
    expect(screen.getByText("密码不会保存在这台设备上。")).toBeVisible();
  });

  it("keeps register as 注册 plus policy-linked consents, not a manual-as-title", () => {
    render(<RegisterPage />);
    expectSharedShell("注册", "先验证手机或邮箱，再设密码并同意政策。");
    const nav = screen.getByRole("navigation", { name: "其他认证入口" });
    expect(within(nav).getByRole("link", { name: "返回登录" })).toHaveAttribute("href", "/auth/login");
    expect(within(nav).getByRole("link", { name: "找回账号" })).toHaveAttribute("href", "/auth/recover");
    expect(screen.queryByRole("heading", { name: /注册按验证/ })).not.toBeInTheDocument();
  });

  it("uses 验证身份 and 验证后进入账户 without device-session copy", async () => {
    render(<VerifyPage />);
    expectSharedShell("验证身份", "验证后进入账户");
    expect(await screen.findByText("安全会话已建立")).toBeVisible();
    expect(screen.queryByText(/设备会话/)).not.toBeInTheDocument();
    expect(screen.queryByText(/正在进入/)).not.toBeInTheDocument();
  });

  it("uses 找回账号 and keeps the no-new-account fact", () => {
    render(<RecoverPage />);
    expectSharedShell(
      "找回账号",
      "用已验证的手机或邮箱重设密码。成功后其他已登录设备会退出。",
    );
    expect(screen.getAllByText(/不会因为找回请求创建新账号/).length).toBeGreaterThan(0);
  });

  it("keeps consent as 政策同意 without the version-binding lecture", () => {
    render(<ConsentPage />);
    expectSharedShell("政策同意", "请分别确认隐私政策和服务条款。");
    expect(screen.queryByText("每次同意都绑定具体政策版本。")).not.toBeInTheDocument();
    expect(screen.queryByText("需要已验证会话")).not.toBeInTheDocument();
  });

  it("keeps set-password as 设置密码 without the identity-first lecture", () => {
    render(<SetPasswordPage />);
    expectSharedShell("设置密码", "为当前账户设置密码。");
    expect(screen.queryByText("设置密码前必须先确认身份。")).not.toBeInTheDocument();
    expect(screen.queryByText("需要已验证会话")).not.toBeInTheDocument();
  });
});

describe("auth shell css contract", () => {
  const css = readFileSync(
    path.join(import.meta.dirname, "../components/auth-shell.module.css"),
    "utf8",
  );

  it("uses the 30px / 496 / black-48 tokens", () => {
    expect(css).toContain("font-size: var(--font-size-page)");
    expect(css).toContain("width: min(var(--container-form), calc(100% - 32px))");
    expect(css).toContain("min-height: var(--target-submit)");
    expect(css).toContain("background: var(--color-action)");
    expect(css).not.toContain("font-size-hero");
    expect(css).not.toContain("authGrid");
  });
});
