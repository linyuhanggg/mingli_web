import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AccountSettingsPage from "@/app/account/settings/page";
import AccountSecurityPage from "@/app/account/settings/security/page";
import AccountPreferencesPage from "@/app/account/settings/preferences/page";
import AccountPrivacyDataPage from "@/app/account/settings/privacy-data/page";
import AccountDataRightsPage from "@/app/account/data-rights/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getNotificationPreferences: vi.fn(),
  getAccountClosure: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/account/settings",
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  getNotificationPreferences: api.getNotificationPreferences,
  getAccountClosure: api.getAccountClosure,
}));

beforeEach(() => {
  api.getAccount.mockReset();
  api.getNotificationPreferences.mockReset();
  api.getAccountClosure.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.getNotificationPreferences.mockResolvedValue({
    in_app_enabled: true,
    email_enabled: false,
    sms_enabled: false,
  });
  api.getAccountClosure.mockResolvedValue(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("account settings five-page shell", () => {
  it.each([
    ["设置", "管理登录设备、通知和数据权利。", () => <AccountSettingsPage />],
    ["设备安全", "查看已验证身份，并可以退出全部设备。", () => <AccountSecurityPage />],
    ["通知偏好", "站内通知默认开启；邮件和短信由你分别控制。", () => <AccountPreferencesPage />],
    ["隐私与数据", "导出资料，或申请注销账号。", () => <AccountPrivacyDataPage />],
    ["数据权利", "导出资料，或申请注销账号。", () => <AccountDataRightsPage />],
  ] as const)("keeps %s on a 30px title without construction copy", async (title, intro, renderPage) => {
    render(renderPage());

    expect(screen.getByRole("heading", { level: 1, name: title })).toBeVisible();
    expect(screen.getByText(intro)).toBeVisible();
    expect(screen.queryByText(/数据权利合同|浏览器存储|localStorage|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("locks the shared header to --font-size-page", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/account-section-shell.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
  });

  it("does not put construction chrome on the five production files", () => {
    for (const file of [
      "src/app/account/settings/page.tsx",
      "src/app/account/settings/security/page.tsx",
      "src/app/account/settings/preferences/page.tsx",
      "src/app/account/settings/privacy-data/page.tsx",
      "src/app/account/data-rights/page.tsx",
      "src/components/account-section-shell.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondarySurfaceFrame|authGrid|§10|§6\.2/);
    }
  });
});
