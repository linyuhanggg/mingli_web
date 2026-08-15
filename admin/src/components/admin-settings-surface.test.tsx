import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminSettingsSurface } from "@/components/admin-settings-surface";
import type { AdminSettingsResponse } from "@/lib/admin-settings";

const settings: AdminSettingsResponse = {
  environment: "test",
  cookie_secure: true,
  otp_adapter: "fake",
  runtime_adapter: "fake",
  admin_session_hours: 8,
  dogfood_entitlement_gates_enabled: false,
  real_traffic_enabled: false,
  alert_sink_enabled: false,
};

describe("AdminSettingsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows safe runtime settings returned by the server", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: settings });

    render(<AdminSettingsSurface role="superadmin" />);

    expect(await screen.findByText("test")).toBeVisible();
    expect(screen.getAllByText("fake")).toHaveLength(2);
    expect(screen.getAllByText("已关闭")).toHaveLength(3);
    expect(screen.queryByText("database_url")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/settings");
  });

  it("renders the server permission boundary", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Settings reader permission required",
    });

    render(<AdminSettingsSurface role="support" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.getByRole("heading", { name: "系统设置面" })).toBeVisible();
    expect(screen.queryByText("database_url")).not.toBeInTheDocument();
  });
});
