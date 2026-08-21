import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountOrdersPage from "@/app/account/orders/page";
import AccountEntitlementsPage from "@/app/account/entitlements/page";
import AccountInvitesPage from "@/app/account/invites/page";
import AccountInvitationsPage from "@/app/account/invitations/page";
import AccountNotificationsPage from "@/app/account/notifications/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getCsrfToken: vi.fn(),
  listAccountOrders: vi.fn(),
  listAccountEntitlements: vi.fn(),
  listAccountReferrals: vi.fn(),
  listAccountNotifications: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => "/account/orders",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  getCsrfToken: api.getCsrfToken,
  listAccountOrders: api.listAccountOrders,
  listAccountEntitlements: api.listAccountEntitlements,
  listAccountReferrals: api.listAccountReferrals,
  listAccountNotifications: api.listAccountNotifications,
}));

beforeEach(() => {
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.getCsrfToken.mockReset();
  api.getCsrfToken.mockResolvedValue("csrf-token-with-at-least-thirty-two-characters");
  api.listAccountOrders.mockReset();
  api.listAccountOrders.mockResolvedValue({ orders: [] });
  api.listAccountEntitlements.mockReset();
  api.listAccountEntitlements.mockResolvedValue({ entitlements: [] });
  api.listAccountReferrals.mockReset();
  api.listAccountReferrals.mockResolvedValue({ campaigns: [] });
  api.listAccountNotifications.mockReset();
  api.listAccountNotifications.mockResolvedValue({ notifications: [], unread_count: 0 });
});

describe("account orders / entitlements / invites / notifications shell", () => {
  it.each([
    ["订单", "查看你的订单。", () => <AccountOrdersPage />],
    ["权益", "查看你的权益。", () => <AccountEntitlementsPage />],
    ["邀请", "查看你的邀请活动。", () => <AccountInvitesPage />],
    ["邀请", "查看你的邀请活动。", () => <AccountInvitationsPage />],
    ["通知", "查看任务、账号和订单通知。", () => <AccountNotificationsPage />],
  ] as const)("keeps %s on a 30px title without construction copy", (title, intro, renderPage) => {
    render(renderPage());

    expect(screen.getByRole("heading", { level: 1, name: title })).toBeVisible();
    expect(screen.getByText(intro)).toBeVisible();
    expect(screen.queryByText(/订单与履约|账户权益|商业事实|追加式账本|公开归因|§10|§6\.2/)).not.toBeInTheDocument();
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
      "src/app/account/orders/page.tsx",
      "src/app/account/entitlements/page.tsx",
      "src/app/account/invites/page.tsx",
      "src/app/account/invitations/page.tsx",
      "src/app/account/notifications/page.tsx",
      "src/components/surfaces/account-commerce-surface.tsx",
      "src/components/surfaces/account-referrals-surface.tsx",
      "src/components/surfaces/account-notifications-surface.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondarySurfaceFrame|authGrid|§10|§6\.2/);
      expect(source).not.toMatch(/AppPageHeader/);
    }
  });
});
