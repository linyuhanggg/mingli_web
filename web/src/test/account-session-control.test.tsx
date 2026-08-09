import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AccountSessionControl from "@/components/account-session-control";
import { ApiError } from "@/lib/api";


const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  logoutCurrentDevice: vi.fn(),
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
    getAccount: api.getAccount,
    logoutCurrentDevice: api.logoutCurrentDevice,
  };
});


function account(overrides: Record<string, unknown> = {}) {
  return {
    user_id: "2ec4dc6c-3e6e-4aef-ae3b-c900b3f1d239",
    identities: [
      {
        id: "11111111-1111-4111-8111-111111111111",
        provider: "email",
        masked_destination: "y***@example.com",
        verified_at: "2026-08-09T00:00:00Z",
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  api.getAccount.mockReset();
  api.logoutCurrentDevice.mockReset();
  replaceMock.mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AccountSessionControl", () => {
  it("probes the account on mount and shows the masked identity and signed-in state", async () => {
    api.getAccount.mockResolvedValue(account());

    render(<AccountSessionControl />);

    expect(await screen.findByText("y***@example.com")).toBeVisible();
    expect(screen.getByText("当前设备已登录")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "退出当前设备" }),
    ).toBeVisible();
    expect(api.getAccount).toHaveBeenCalledTimes(1);
  });

  it("renders the masked identity as a static list without internal ids", async () => {
    api.getAccount.mockResolvedValue(account());

    render(<AccountSessionControl />);

    const list = await screen.findByRole("list", { name: "已绑定登录身份" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    expect(within(list).getByText("邮箱")).toBeVisible();
    expect(within(list).getByText("y***@example.com")).toBeVisible();
    expect(screen.queryByText(/2ec4dc6c-3e6e-4aef-ae3b-c900b3f1d239/)).not.toBeInTheDocument();
    expect(screen.queryByText(/11111111-1111-4111-8111-111111111111/)).not.toBeInTheDocument();
  });

  it("logs out the current device and routes back to the public home", async () => {
    api.getAccount.mockResolvedValue(account());
    api.logoutCurrentDevice.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<AccountSessionControl />);
    await user.click(await screen.findByRole("button", { name: "退出当前设备" }));

    await waitFor(() => {
      expect(api.logoutCurrentDevice).toHaveBeenCalledTimes(1);
      expect(replaceMock).toHaveBeenCalledWith("/");
    });
  });

  it("keeps a retryable logout button and a clear error when logout fails", async () => {
    api.getAccount.mockResolvedValue(account());
    api.logoutCurrentDevice.mockRejectedValueOnce(
      new Error("退出失败：服务暂时不可用，请稍后重试"),
    );
    const user = userEvent.setup();

    render(<AccountSessionControl />);
    await user.click(await screen.findByRole("button", { name: "退出当前设备" }));

    expect(await screen.findByText(/退出失败/)).toBeVisible();
    const retryButton = screen.getByRole("button", { name: "退出当前设备" });
    expect(retryButton).toBeEnabled();
    expect(replaceMock).not.toHaveBeenCalled();

    api.logoutCurrentDevice.mockResolvedValueOnce(undefined);
    await user.click(retryButton);
    await waitFor(() => {
      expect(api.logoutCurrentDevice).toHaveBeenCalledTimes(2);
      expect(replaceMock).toHaveBeenCalledWith("/");
    });
  });

  it("does not fake a signed-in state when the session is missing (401)", async () => {
    api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));

    render(<AccountSessionControl />);

    await waitFor(() => expect(api.getAccount).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("当前设备已登录")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "退出当前设备" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/未登录/)).toBeVisible();
    expect(screen.queryByText(/2ec4dc6c-3e6e-4aef-ae3b-c900b3f1d239/)).not.toBeInTheDocument();
  });

  it("recovers from a probe failure with an explicit retry", async () => {
    api.getAccount
      .mockRejectedValueOnce(new ApiError("服务暂时不可用，请稍后重试", 502))
      .mockResolvedValueOnce(account());
    const user = userEvent.setup();

    render(<AccountSessionControl />);

    expect(await screen.findByText("无法读取账户状态")).toBeVisible();
    expect(screen.queryByText("当前设备已登录")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "重试" }));

    expect(await screen.findByText("y***@example.com")).toBeVisible();
    expect(api.getAccount).toHaveBeenCalledTimes(2);
  });
});
