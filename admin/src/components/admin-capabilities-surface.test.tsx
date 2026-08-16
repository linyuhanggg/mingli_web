import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminCapabilitiesSurface } from "@/components/admin-capabilities-surface";

describe("AdminCapabilitiesSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows product policy states without claiming runtime readiness", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        environment: "test",
        runtime_adapter: "fake",
        runtime_health: "unverified",
        production_ready: false,
        capabilities: [
          {
            capability_id: "bazi",
            label: "八字",
            release_state: "PUBLIC",
            audience: "P0 产品",
            product_actions: ["profile_preview", "bazi_deep"],
          },
          {
            capability_id: "physiognomy",
            label: "相法",
            release_state: "INTERNAL_TEST",
            audience: "内部 Provider",
            product_actions: [],
          },
        ],
      },
    });

    render(<AdminCapabilitiesSurface role="ops" />);

    expect(await screen.findByText("八字")).toBeVisible();
    expect(screen.getByText("PUBLIC")).toBeVisible();
    expect(screen.getByText("INTERNAL_TEST")).toBeVisible();
    expect(screen.getByText("runtime_health：unverified")).toBeVisible();
    expect(screen.getByText("生产准入：未验证")).toBeVisible();
    expect(screen.queryByText(/api.?key/i)).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/capabilities?limit=100",
    );
  });

  it("keeps capability policy away from finance staff", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Capability policy read permission required",
    });

    render(<AdminCapabilitiesSurface role="finance" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByText("八字")).not.toBeInTheDocument();
  });
});
