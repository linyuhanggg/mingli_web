import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminDataRightsSurface } from "@/components/admin-data-rights-surface";

const closure = {
  closure_id: "closure-1",
  user_id: "user-1",
  status: "pending",
  requested_at: "2026-08-14T01:00:00Z",
  cancel_until: "2026-08-15T01:00:00Z",
  cancelled_at: null,
  executed_at: null,
};

describe("AdminDataRightsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows pending closures and executes one through the real API", async () => {
    const user = userEvent.setup();
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { closures: [closure] } })
      .mockResolvedValueOnce({ ok: true, data: { ...closure, status: "executed", executed_at: "2026-08-14T02:00:00Z" } })
      .mockResolvedValueOnce({ ok: true, data: { closures: [] } });

    render(<AdminDataRightsSurface role="ops" />);

    expect(await screen.findByText("closure-1")).toBeVisible();
    expect(screen.getByText("待执行")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "执行删除 closure-1" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/privacy/closures/closure-1/execute",
      expect.objectContaining({ method: "POST" }),
    );
    expect(await screen.findByText("数据权利执行已记录")).toBeVisible();
  });

  it("keeps the command away from a support role", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { closures: [closure] } });

    render(<AdminDataRightsSurface role="support" />);

    expect(await screen.findByText("closure-1")).toBeVisible();
    expect(screen.queryByRole("button", { name: "执行删除 closure-1" })).not.toBeInTheDocument();
  });
});
