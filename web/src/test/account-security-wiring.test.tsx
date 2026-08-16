import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountSecurityPage from "@/app/account/settings/security/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  revokeAllSessions: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  revokeAllSessions: api.revokeAllSessions,
}));

const account = {
  user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
  identities: [
    {
      id: "22222222-2222-4222-8222-222222222222",
      provider: "email" as const,
      masked_destination: "a***@example.com",
      verified_at: "2026-08-14T05:00:00Z",
    },
  ],
};

beforeEach(() => {
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.revokeAllSessions.mockReset();
  api.revokeAllSessions.mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("account security route wiring", () => {
  it("does not revoke sessions for signed-out users", async () => {
    render(<AccountSecurityPage />);

    expect(await screen.findByRole("status", { name: "需要登录" })).toBeVisible();
    expect(api.revokeAllSessions).not.toHaveBeenCalled();
  });

  it("uses the existing server revoke-all command after confirmation", async () => {
    const user = userEvent.setup();
    api.getAccount.mockResolvedValue(account);

    render(<AccountSecurityPage />);

    expect(await screen.findByRole("heading", { name: "设备安全" })).toBeVisible();
    expect(screen.getByText("a***@example.com")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "撤销所有设备会话" }));

    expect(window.confirm).toHaveBeenCalled();
    expect(api.revokeAllSessions).toHaveBeenCalledTimes(1);
  });
});
