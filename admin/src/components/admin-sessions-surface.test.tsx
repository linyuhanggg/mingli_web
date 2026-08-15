import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminSessionsSurface } from "@/components/admin-sessions-surface";
import type { AdminSession, AdminSessionsResponse } from "@/lib/admin-sessions";

const active: AdminSession = {
  id: "session-1",
  staff_user_id: "staff-1",
  actor: "ops@example.com",
  status: "active",
  expires_at: "2026-08-14T04:00:00Z",
  last_seen_at: "2026-08-14T01:00:00Z",
  revoked_at: null,
  created_at: "2026-08-14T00:00:00Z",
};

describe("AdminSessionsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows session facts and revokes a session with an audited reason", async () => {
    const user = userEvent.setup();
    const response: AdminSessionsResponse = { sessions: [active] };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: response })
      .mockResolvedValueOnce({
        ok: true,
        data: { ...active, status: "revoked", revoked_at: "2026-08-14T01:05:00Z" },
      })
      .mockResolvedValueOnce({
        ok: true,
        data: {
          sessions: [
            { ...active, status: "revoked", revoked_at: "2026-08-14T01:05:00Z" },
          ],
        },
      });

    render(<AdminSessionsSurface role="superadmin" />);

    expect(await screen.findByText("ops@example.com")).toBeVisible();
    expect(screen.getByText("有效")).toBeVisible();
    expect(screen.queryByText("token_hash")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("会话强退原因"), "撤销异常员工登录");
    await user.click(screen.getByRole("button", { name: "撤销会话" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/sessions/session-1/revoke",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reason: "撤销异常员工登录" }),
      }),
    );
    expect(await screen.findByText("会话已撤销")).toBeVisible();
  });

  it("keeps the revoke command away from a support role", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { sessions: [] } });

    render(<AdminSessionsSurface role="support" />);

    expect(await screen.findByText("暂无员工会话")).toBeVisible();
    expect(screen.queryByRole("button", { name: "撤销会话" })).not.toBeInTheDocument();
  });
});
