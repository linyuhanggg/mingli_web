import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PasswordSetForm } from "@/components/password-set-form";

const api = vi.hoisted(() => ({
  setPassword: vi.fn(),
}));

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    setPassword: api.setPassword,
  };
});

beforeEach(() => {
  api.setPassword.mockReset();
  replaceMock.mockReset();
});

describe("PasswordSetForm", () => {
  it("saves a matching password and routes back to the account", async () => {
    api.setPassword.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<PasswordSetForm />);
    await user.type(screen.getByLabelText("新密码"), "correct-password");
    await user.type(screen.getByLabelText("确认新密码"), "correct-password");
    await user.click(screen.getByRole("button", { name: "保存密码" }));

    await waitFor(() => {
      expect(api.setPassword).toHaveBeenCalledWith("correct-password");
      expect(replaceMock).toHaveBeenCalledWith("/account");
    });
  });
});
