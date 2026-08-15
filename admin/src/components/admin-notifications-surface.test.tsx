import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminNotificationsSurface } from "@/components/admin-notifications-surface";
import type { AdminNotification, AdminNotificationsResponse } from "@/lib/admin-notifications";

const failed: AdminNotification = {
  id: "notification-1",
  owner_user_id: "user-1",
  kind: "reading.accepted",
  dedupe_key: "dedupe-1",
  channel: "email",
  status: "failed",
  available_at: "2026-08-14T01:00:00Z",
  attempt_count: 3,
  processing_until: null,
  sent_at: null,
  last_error: "provider timeout",
};

describe("AdminNotificationsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows delivery facts without payload and retries a failed notification", async () => {
    const user = userEvent.setup();
    const response: AdminNotificationsResponse = { notifications: [failed] };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: response })
      .mockResolvedValueOnce({ ok: true, data: { ...failed, status: "pending" } })
      .mockResolvedValueOnce({ ok: true, data: { notifications: [{ ...failed, status: "pending" }] } });

    render(<AdminNotificationsSurface role="superadmin" />);

    expect(await screen.findByText("终态失败")).toBeVisible();
    expect(screen.getByText("provider timeout")).toBeVisible();
    expect(screen.queryByText("隐藏内容")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("操作原因"), "供应商恢复，人工确认重试");
    await user.click(screen.getByRole("button", { name: "重新投递" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/notifications/notification-1/retry",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reason: "供应商恢复，人工确认重试" }),
      }),
    );
    expect(await screen.findByText("通知已重新排队，尝试次数保持不变。")).toBeVisible();
  });

  it("does not expose retry controls to an ordinary role", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { notifications: [] } });

    render(<AdminNotificationsSurface role="support" />);

    expect(await screen.findByText("暂无通知投递记录")).toBeVisible();
    expect(screen.queryByRole("button", { name: "重新投递" })).not.toBeInTheDocument();
  });
});
