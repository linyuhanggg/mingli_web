import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminRuntimeSurface } from "@/components/admin-runtime-surface";

describe("AdminRuntimeSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows registered runtime release metadata without digests", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        releases: [
          {
            id: "release-1",
            name: "mingli-runtime",
            version: "2026.08.14",
            source_commit: "source-commit",
            protocol_version: "reading-runtime-v1",
            production_ready: true,
            created_at: "2026-08-14T01:00:00Z",
          },
        ],
      },
    });

    render(<AdminRuntimeSurface role="ops" />);

    expect(await screen.findByText("mingli-runtime")).toBeVisible();
    expect(screen.getByText("2026.08.14")).toBeVisible();
    expect(screen.getByText("可用于生产")).toBeVisible();
    expect(screen.queryByText("manifest-secret-like")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/runtime-releases?limit=100",
    );
  });

  it("keeps runtime metadata away from support staff", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Runtime release read permission required",
    });

    render(<AdminRuntimeSurface role="support" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.getByRole("heading", { name: "运行时控制面" })).toBeVisible();
    expect(screen.queryByText("mingli-runtime")).not.toBeInTheDocument();
  });
});
