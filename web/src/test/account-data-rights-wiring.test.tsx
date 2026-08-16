import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AccountPrivacyDataPage from "@/app/account/settings/privacy-data/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  cancelAccountClosure: vi.fn(),
  exportAccountData: vi.fn(),
  getAccount: vi.fn(),
  getAccountClosure: vi.fn(),
  requestAccountClosure: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  cancelAccountClosure: api.cancelAccountClosure,
  exportAccountData: api.exportAccountData,
  getAccount: api.getAccount,
  getAccountClosure: api.getAccountClosure,
  requestAccountClosure: api.requestAccountClosure,
}));

const account = {
  user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
  identities: [],
};

beforeEach(() => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  api.cancelAccountClosure.mockReset();
  api.exportAccountData.mockReset();
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.getAccountClosure.mockReset();
  api.getAccountClosure.mockResolvedValue(null);
  api.requestAccountClosure.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("account data rights route wiring", () => {
  it("does not load or mutate data rights for signed-out users", async () => {
    render(<AccountPrivacyDataPage />);

    expect(await screen.findByRole("status", { name: "需要登录" })).toBeVisible();
    expect(api.getAccountClosure).not.toHaveBeenCalled();
    expect(api.exportAccountData).not.toHaveBeenCalled();
    expect(api.requestAccountClosure).not.toHaveBeenCalled();
  });

  it("exports without rendering the payload and requests a reversible closure", async () => {
    const user = userEvent.setup();
    api.getAccount.mockResolvedValue(account);
    api.exportAccountData.mockResolvedValue({
      generated_at: "2026-08-14T04:00:00Z",
      user_id: account.user_id,
      payload: { profiles: [{ location: "private" }], readings: [] },
    });
    api.requestAccountClosure.mockResolvedValue({
      closure_id: "55555555-5555-4555-8555-555555555555",
      user_id: account.user_id,
      status: "pending",
      requested_at: "2026-08-14T04:00:00Z",
      cancel_until: "2026-08-21T04:00:00Z",
      cancelled_at: null,
      executed_at: null,
    });
    api.cancelAccountClosure.mockResolvedValue(undefined);

    render(<AccountPrivacyDataPage />);

    expect(await screen.findByRole("heading", { name: "数据导出" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "导出我的数据" }));
    expect(api.exportAccountData).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("private")).not.toBeInTheDocument();
    expect(await screen.findByRole("status", { name: "数据导出已准备" })).toBeVisible();

    await user.click(screen.getByRole("button", { name: "申请注销账号" }));
    expect(api.requestAccountClosure).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/可撤销至/)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "撤销注销申请" }));
    expect(api.cancelAccountClosure).toHaveBeenCalledTimes(1);
  });
});
