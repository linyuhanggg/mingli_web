import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountNotificationsPage from "@/app/account/notifications/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  deleteAccountNotification: vi.fn(),
  getAccount: vi.fn(),
  listAccountNotifications: vi.fn(),
  markAccountNotificationRead: vi.fn(),
  markAllAccountNotificationsRead: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  deleteAccountNotification: api.deleteAccountNotification,
  getAccount: api.getAccount,
  listAccountNotifications: api.listAccountNotifications,
  markAccountNotificationRead: api.markAccountNotificationRead,
  markAllAccountNotificationsRead: api.markAllAccountNotificationsRead,
}));

const account = {
  user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
  identities: [],
};

const notification = {
  id: "33333333-3333-4333-8333-333333333333",
  title: "邀请奖励已确认",
  summary: "一次邀请奖励已经确认，账户权益以服务端账本为准。",
  available_at: "2026-08-14T05:00:00Z",
  read_at: null,
  target_href: "/account/invitations",
};

beforeEach(() => {
  api.deleteAccountNotification.mockReset();
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.listAccountNotifications.mockReset();
  api.listAccountNotifications.mockResolvedValue({ notifications: [], unread_count: 0 });
  api.markAccountNotificationRead.mockReset();
  api.markAllAccountNotificationsRead.mockReset();
});

describe("account notifications route wiring", () => {
  it("keeps notifications private for signed-out users", async () => {
    render(<AccountNotificationsPage />);

    expect(await screen.findByRole("status", { name: "需要登录" })).toBeVisible();
    expect(screen.getByRole("link", { name: "前往登录" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(api.listAccountNotifications).not.toHaveBeenCalled();
  });

  it("renders server notifications and supports filtering, read-all, and deletion", async () => {
    const user = userEvent.setup();
    api.getAccount.mockResolvedValue(account);
    api.listAccountNotifications.mockResolvedValue({
      notifications: [notification],
      unread_count: 1,
    });
    api.markAllAccountNotificationsRead.mockResolvedValue({ unread_count: 0 });
    api.markAccountNotificationRead.mockResolvedValue({ ...notification, read_at: "2026-08-14T06:00:00Z" });
    api.deleteAccountNotification.mockResolvedValue(undefined);

    render(<AccountNotificationsPage />);

    expect(await screen.findByRole("heading", { name: "通知" })).toBeVisible();
    expect(await screen.findByText(notification.summary)).toBeVisible();
    expect(screen.getByRole("link", { name: notification.title })).toHaveAttribute(
      "href",
      notification.target_href,
    );
    expect(screen.getByText("未读 1")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "只看未读" }));
    expect(api.listAccountNotifications).toHaveBeenLastCalledWith({ unreadOnly: true });

    await user.click(screen.getByRole("button", { name: "全部标为已读" }));
    expect(api.markAllAccountNotificationsRead).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "删除邀请奖励已确认" }));
    expect(api.deleteAccountNotification).toHaveBeenCalledWith(notification.id);
  });
});
