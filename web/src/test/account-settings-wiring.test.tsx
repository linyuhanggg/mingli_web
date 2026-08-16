import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountSettingsPage from "@/app/account/settings/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
}));

beforeEach(() => {
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
});

describe("account settings route wiring", () => {
  it("keeps settings private for signed-out users", async () => {
    render(<AccountSettingsPage />);

    expect(await screen.findByRole("status", { name: "需要登录" })).toBeVisible();
  });

  it("shows only existing account management links after sign-in", async () => {
    api.getAccount.mockResolvedValue({
      user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
      identities: [],
    });

    render(<AccountSettingsPage />);

    expect(await screen.findByRole("heading", { name: "账号设置" })).toBeVisible();
    expect(screen.getByRole("link", { name: /^设备安全/ })).toHaveAttribute(
      "href",
      "/account/settings/security",
    );
    expect(screen.getByRole("link", { name: /^通知偏好/ })).toHaveAttribute(
      "href",
      "/account/settings/preferences",
    );
    expect(screen.getByRole("link", { name: /^隐私与数据/ })).toHaveAttribute(
      "href",
      "/account/settings/privacy-data",
    );
  });
});
