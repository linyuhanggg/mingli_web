import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NotificationPreferencesForm from "@/components/notification-preferences-form";
import { AccountSessionProvider } from "@/components/account-session-context";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getNotificationPreferences: vi.fn(),
  updateNotificationPreferences: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getAccount: api.getAccount,
    getNotificationPreferences: api.getNotificationPreferences,
    updateNotificationPreferences: api.updateNotificationPreferences,
  };
});

function account() {
  return {
    user_id: "2ec4dc6c-3e6e-4aef-ae3b-c900b3f1d239",
    identities: [],
  };
}

beforeEach(() => {
  api.getAccount.mockReset();
  api.getNotificationPreferences.mockReset();
  api.updateNotificationPreferences.mockReset();
});

describe("NotificationPreferencesForm", () => {
  it("loads defaults and saves the selected notification channels", async () => {
    api.getAccount.mockResolvedValue(account());
    api.getNotificationPreferences.mockResolvedValue({
      in_app_enabled: true,
      email_enabled: false,
      sms_enabled: false,
    });
    api.updateNotificationPreferences.mockResolvedValue({
      in_app_enabled: true,
      email_enabled: true,
      sms_enabled: false,
    });
    const user = userEvent.setup();

    render(
      <AccountSessionProvider>
        <NotificationPreferencesForm />
      </AccountSessionProvider>,
    );

    const email = await screen.findByRole("checkbox", { name: /邮件通知/ });
    expect(email).not.toBeChecked();
    await user.click(email);
    await user.click(screen.getByRole("button", { name: "保存通知偏好" }));

    await waitFor(() => {
      expect(api.updateNotificationPreferences).toHaveBeenCalledWith({
        in_app_enabled: true,
        email_enabled: true,
        sms_enabled: false,
      });
    });
    expect(await screen.findByText("通知偏好已保存")).toBeVisible();
  });
});
