import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConsentForm } from "@/components/consent-form";

const api = vi.hoisted(() => ({
  recordConsent: vi.fn(),
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
    recordConsent: api.recordConsent,
  };
});

beforeEach(() => {
  api.recordConsent.mockReset();
  replaceMock.mockReset();
});

describe("ConsentForm", () => {
  it("records privacy and terms separately after both are selected", async () => {
    api.recordConsent.mockResolvedValue({});
    const user = userEvent.setup();

    render(<ConsentForm />);
    const submit = screen.getByRole("button", { name: "确认并保存" });
    expect(submit).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: "我已阅读并同意隐私政策" }));
    await user.click(screen.getByRole("checkbox", { name: "我已阅读并同意服务条款" }));
    await user.click(submit);

    await waitFor(() => {
      expect(api.recordConsent).toHaveBeenNthCalledWith(1, {
        policy_key: "privacy",
        policy_version: "development-preview-v0.1",
        context: "reaccept",
      });
      expect(api.recordConsent).toHaveBeenNthCalledWith(2, {
        policy_key: "terms",
        policy_version: "development-preview-v0.1",
        context: "reaccept",
      });
      expect(replaceMock).toHaveBeenCalledWith("/account");
    });
  });
});
