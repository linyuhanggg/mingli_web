import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminStaffSurface } from "@/components/admin-staff-surface";
import type { AdminStaff, AdminStaffResponse } from "@/lib/admin-staff";

const analyst: AdminStaff = {
  id: "staff-1",
  email: "analyst@example.com",
  display_name: "分析员工",
  role: "support",
  status: "active",
  created_at: "2026-08-14T00:00:00Z",
  last_login_at: "2026-08-14T01:00:00Z",
  unrevoked_session_count: 1,
};

describe("AdminStaffSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows staff facts and submits audited status and role changes", async () => {
    const user = userEvent.setup();
    const response: AdminStaffResponse = { staff: [analyst] };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: response })
      .mockResolvedValueOnce({ ok: true, data: { ...analyst, status: "suspended", unrevoked_session_count: 0 } })
      .mockResolvedValueOnce({ ok: true, data: { staff: [{ ...analyst, status: "suspended", unrevoked_session_count: 0 }] } })
      .mockResolvedValueOnce({ ok: true, data: { ...analyst, status: "suspended", role: "finance", unrevoked_session_count: 0 } })
      .mockResolvedValueOnce({ ok: true, data: { staff: [{ ...analyst, status: "suspended", role: "finance", unrevoked_session_count: 0 }] } });

    render(<AdminStaffSurface role="superadmin" />);

    expect(await screen.findByText("analyst@example.com")).toBeVisible();
    expect(screen.getByText("在职")).toBeVisible();
    expect(screen.queryByText("员工目录已接入")).not.toBeInTheDocument();
    expect(document.querySelectorAll('[data-variant="compact"]')).toHaveLength(0);
    expect(screen.queryByText("not-returned")).not.toBeInTheDocument();
    await user.type(
      screen.getByRole("textbox", { name: "员工变更原因" }),
      "调整员工权限和排班",
    );
    await user.click(screen.getByRole("button", { name: "停用 analyst@example.com" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/staff/staff-1/status",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ status: "suspended", reason: "调整员工权限和排班" }),
      }),
    );
    expect(await screen.findByText("员工状态已更新")).toBeVisible();
    expect(document.querySelectorAll('[data-variant="compact"]')).toHaveLength(1);

    await user.selectOptions(screen.getByLabelText("角色 analyst@example.com"), "finance");
    await user.click(screen.getByRole("button", { name: "保存角色 analyst@example.com" }));
    expect(adminFetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/v1/admin/staff/staff-1/role",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ role: "finance", reason: "调整员工权限和排班" }),
      }),
    );
    expect(await screen.findByText("员工角色已更新")).toBeVisible();
  });

  it("keeps staff commands away from a support role", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { staff: [analyst] } });

    render(<AdminStaffSurface role="support" />);

    expect(await screen.findByText("analyst@example.com")).toBeVisible();
    expect(screen.queryByRole("button", { name: "停用 analyst@example.com" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "员工变更原因" })).not.toBeInTheDocument();
  });

  it("keeps a forbidden superadmin on the page without staff write controls", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: false, status: 403, title: "Forbidden" });

    render(<AdminStaffSurface role="superadmin" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByRole("textbox", { name: "员工变更原因" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "创建员工账号" })).not.toBeInTheDocument();
    expect(document.querySelectorAll('[data-variant="compact"]')).toHaveLength(1);
  });

  it("resets a staff password without rendering the secret", async () => {
    const user = userEvent.setup();
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { staff: [analyst] } })
      .mockResolvedValueOnce({ ok: true, data: analyst })
      .mockResolvedValueOnce({ ok: true, data: { staff: [analyst] } });

    render(<AdminStaffSurface role="superadmin" />);

    await screen.findByText("analyst@example.com");
    await user.type(screen.getByRole("textbox", { name: "员工变更原因" }), "员工请求重置登录密码");
    await user.type(screen.getByLabelText("新密码"), "new-password-123");
    await user.click(screen.getByRole("button", { name: "重置密码 analyst@example.com" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/staff/staff-1/password-reset",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ password: "new-password-123", reason: "员工请求重置登录密码" }),
      }),
    );
    expect(screen.queryByText("new-password-123")).not.toBeInTheDocument();
  });

  it("creates a staff account with an audited reason", async () => {
    const user = userEvent.setup();
    const created: AdminStaff = {
      ...analyst,
      id: "staff-2",
      email: "new-operator@example.com",
      display_name: "新运营",
      role: "ops",
    };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { staff: [analyst] } })
      .mockResolvedValueOnce({ ok: true, data: created })
      .mockResolvedValueOnce({ ok: true, data: { staff: [analyst, created] } });

    render(<AdminStaffSurface role="superadmin" />);

    await screen.findByText("analyst@example.com");
    await user.type(screen.getByRole("textbox", { name: "新员工邮箱" }), "new-operator@example.com");
    await user.type(screen.getByRole("textbox", { name: "新员工显示名称" }), "新运营");
    await user.selectOptions(screen.getByLabelText("新员工角色"), "ops");
    await user.type(screen.getByLabelText("新员工初始密码"), "initial-password-123");
    await user.type(screen.getByRole("textbox", { name: "创建员工原因" }), "补充运营值班");
    await user.click(screen.getByRole("button", { name: "创建员工账号" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/staff",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "new-operator@example.com",
          display_name: "新运营",
          role: "ops",
          password: "initial-password-123",
          reason: "补充运营值班",
        }),
      }),
    );
    expect(await screen.findByText("员工账号已创建")).toBeVisible();
    expect(screen.queryByText("initial-password-123")).not.toBeInTheDocument();
  });
});
