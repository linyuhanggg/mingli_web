import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AccountPage from "@/app/account/page";
import {
  AccountSessionProvider,
  useAccountSession,
} from "@/components/account-session-context";
import { PrivateShell } from "@/components/private-shell";
import { SiteHeader } from "@/components/site-header";
import { ApiError, getReadingResult } from "@/lib/api";


const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getCsrfToken: vi.fn(),
  logoutCurrentDevice: vi.fn(),
}));

const navigation = vi.hoisted(() => ({
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/app",
  useRouter: () => ({
    replace: navigation.replace,
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  getCsrfToken: api.getCsrfToken,
  logoutCurrentDevice: api.logoutCurrentDevice,
}));

const signedInAccount = {
  user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
  identities: [
    {
      id: "8d2f1a4b-6c3e-4d9f-8a5b-2e7c4f1d9a3b",
      provider: "email" as const,
      masked_destination: "q***@example.com",
      verified_at: "2026-08-01T00:00:00Z",
    },
  ],
};

function SessionProbe() {
  const { refresh, state } = useAccountSession();
  return (
    <>
      <p data-testid="session-state">{state.status}</p>
      <button type="button" onClick={() => void refresh({ force: true })}>
        强制刷新身份
      </button>
    </>
  );
}

beforeEach(() => {
  api.getAccount.mockReset();
  api.getCsrfToken.mockReset();
  api.logoutCurrentDevice.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.getCsrfToken.mockResolvedValue("csrf-token-with-at-least-thirty-two-characters");
  navigation.replace.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("identity-first application shell", () => {
  it("ignores an older account probe after a newer refresh has completed", async () => {
    const user = userEvent.setup();
    let rejectInitial: ((reason: Error) => void) | undefined;
    api.getAccount
      .mockReturnValueOnce(
        new Promise((_, reject) => {
          rejectInitial = reject;
        }),
      )
      .mockResolvedValueOnce(signedInAccount);

    render(
      <AccountSessionProvider>
        <SessionProbe />
      </AccountSessionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "强制刷新身份" }));
    await waitFor(() => {
      expect(screen.getByTestId("session-state")).toHaveTextContent("signedIn");
    });

    await act(async () => {
      rejectInitial?.(new ApiError("Authentication required", 401));
    });

    expect(screen.getByTestId("session-state")).toHaveTextContent("signedIn");
    expect(api.getAccount).toHaveBeenCalledTimes(2);
  });

  it("coalesces concurrent private API 401s into one shared identity refresh", async () => {
    api.getAccount
      .mockResolvedValueOnce(signedInAccount)
      .mockRejectedValueOnce(new ApiError("Authentication required", 401));
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response(JSON.stringify({ title: "Authentication required" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    render(
      <AccountSessionProvider>
        <SessionProbe />
      </AccountSessionProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("session-state")).toHaveTextContent("signedIn");
    });
    const accountCallsAtSignedIn = api.getAccount.mock.calls.length;
    const expiredRequests = await Promise.allSettled([
      getReadingResult("55555555-5555-4555-8555-555555555555"),
      getReadingResult("66666666-6666-4666-8666-666666666666"),
    ]);
    expect(expiredRequests).toHaveLength(2);
    expect(expiredRequests.every((result) => result.status === "rejected")).toBe(true);

    await waitFor(() => {
      expect(screen.getByTestId("session-state")).toHaveTextContent("signedOut");
    });
    expect(api.getAccount.mock.calls.length - accountCallsAtSignedIn).toBe(1);
  });

  it("revalidates a persistent signed-in shell when another browser tab may have logged out", async () => {
    api.getAccount
      .mockResolvedValueOnce(signedInAccount)
      .mockRejectedValueOnce(new ApiError("Authentication required", 401));

    render(
      <AccountSessionProvider>
        <SessionProbe />
      </AccountSessionProvider>,
    );

    expect(await screen.findByTestId("session-state")).toHaveTextContent("signedIn");
    act(() => {
      window.dispatchEvent(new Event("focus"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("session-state")).toHaveTextContent("signedOut");
    });
    expect(api.getAccount).toHaveBeenCalledTimes(2);
  });

  it("shows the signed-in identity on every private page", async () => {
    api.getAccount.mockResolvedValue(signedInAccount);

    render(
      <PrivateShell>
        <p>私人内容</p>
      </PrivateShell>,
    );

    const identityLink = await screen.findByRole("link", {
      name: "已登录，q***@example.com，前往个人中心",
    });
    expect(identityLink).toHaveAttribute("href", "/account");
    expect(screen.getByText("已登录")).toBeVisible();
    expect(screen.getByText("q***@example.com")).toBeVisible();
    expect(screen.queryByText(/4f9c3d6a/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回公共首页" })).toHaveAttribute("href", "/");

    const navigation = screen.getByRole("navigation", {
      name: "私人应用导航",
      hidden: true,
    });
    expect(
      within(navigation).getByRole("link", { name: "我的", hidden: true }),
    ).toHaveAttribute("href", "/account");
    expect(
      within(navigation).getByRole("link", { name: "受测人档案", hidden: true }),
    ).toHaveAttribute("href", "/account/profiles");
    expect(
      within(navigation).getByRole("link", { name: "推演历史", hidden: true }),
    ).toHaveAttribute("href", "/account/history");
    expect(navigation.querySelector('a[href^="/app"]')).toBeNull();
  });

  it("uses the compact account navigation without the desktop private rail", async () => {
    api.getAccount.mockResolvedValue(signedInAccount);

    render(
      <PrivateShell variant="account">
        <p>账户内容</p>
      </PrivateShell>,
    );

    await screen.findByRole("link", {
      name: "已登录，q***@example.com，前往个人中心",
    });
    expect(screen.queryByRole("link", { name: "返回公共首页" })).not.toBeInTheDocument();
    const primaryNavigation = screen.getByRole("navigation", { name: "主导航" });
    expect(within(primaryNavigation).getByRole("button", { name: "术数" })).toBeVisible();
    expect(within(primaryNavigation).getByRole("button", { name: "合参" })).toBeVisible();
    expect(within(primaryNavigation).getByRole("link", { name: "工具" })).toHaveAttribute(
      "href",
      "/tools",
    );
    expect(within(primaryNavigation).getByRole("link", { name: "每日" })).toHaveAttribute(
      "href",
      "/daily",
    );
    expect(within(primaryNavigation).getByRole("link", { name: "知识内容" })).toHaveAttribute(
      "href",
      "/library",
    );
    expect(within(primaryNavigation).getByRole("button", { name: "更多" })).toBeVisible();
    const accountNavigation = screen.getByRole("navigation", {
      name: "账户中心导航",
      hidden: true,
    });
    expect(accountNavigation).toBeInTheDocument();
    expect(screen.queryByText("私人档案区")).not.toBeInTheDocument();
    expect(
      within(accountNavigation).getByRole("link", {
        name: "受测人档案",
        hidden: true,
      }),
    ).toHaveAttribute("href", "/account/profiles");
  });

  it("makes guest mode and the login action explicit", async () => {
    render(
      <PrivateShell>
        <p>游客内容</p>
      </PrivateShell>,
    );

    const loginLink = await screen.findByRole("link", {
      name: "当前为游客模式，登录或注册",
    });
    expect(loginLink).toHaveAttribute("href", "/auth/login");
    expect(screen.getByText("游客模式")).toBeVisible();
    expect(screen.getByText("登录或注册")).toBeVisible();
  });
});

describe("personal center", () => {
  it("becomes a signed-in personal page instead of showing the login form again", async () => {
    api.getAccount.mockResolvedValue(signedInAccount);

    render(<AccountPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "我的" }),
    ).toBeVisible();
    expect(
      await screen.findByRole("heading", {
        level: 2,
        name: "q***@example.com",
      }),
    ).toBeVisible();
    expect(screen.getByText("当前设备已登录")).toBeVisible();
    expect(screen.queryByLabelText("邮箱地址")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^受测人档案/ })).toHaveAttribute(
      "href",
      "/account/profiles",
    );
    expect(screen.getByRole("link", { name: /^推演历史/ })).toHaveAttribute(
      "href",
      "/account/history",
    );
  });

  it("keeps signed-out account to identity plus a login action", async () => {
    render(<AccountPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "我的" }),
    ).toBeVisible();
    expect(await screen.findByRole("heading", { level: 2, name: "未登录" })).toBeVisible();
    expect(screen.getByText("登录后才能看档案和历史")).toBeVisible();
    expect(screen.getByRole("link", { name: "登录" })).toHaveAttribute("href", "/auth/login");
    expect(screen.getByRole("link", { name: "用验证码登录" })).toHaveAttribute("href", "/auth/verify");
    expect(screen.queryByLabelText("邮箱地址")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "退出当前设备" })).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "我的账户入口" })).not.toBeInTheDocument();
  });

  it("does not embed OTP or show a development code on the account page", async () => {
    render(
      <AccountSessionProvider>
        <AccountPage />
      </AccountSessionProvider>,
    );
    expect(await screen.findByRole("heading", { level: 2, name: "未登录" })).toBeVisible();
    expect(screen.queryByLabelText("邮箱地址")).not.toBeInTheDocument();
    expect(screen.queryByText(/调试码/)).not.toBeInTheDocument();
    expect(screen.queryByText("246810")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "登录" })).toHaveAttribute("href", "/auth/login");
  });
});

describe("public account entry", () => {
  it("changes from login to a clear signed-in destination", async () => {
    api.getAccount.mockResolvedValue(signedInAccount);

    render(<SiteHeader />);

    const accountLink = await screen.findByRole("link", {
      name: "已登录，进入我的首页",
    });
    expect(accountLink).toHaveAttribute("href", "/account");
    expect(accountLink).toHaveTextContent("已登录");
    expect(accountLink).toHaveTextContent("我的首页");
  });

  it("keeps a direct login entry when signed out", async () => {
    render(<SiteHeader />);

    const accountLink = await screen.findByRole("link", { name: "登录" });
    expect(accountLink).toHaveAttribute("href", "/auth/login");
  });

  it("names checking and unknown public identity states instead of collapsing them into account", async () => {
    let rejectAccount: ((reason: Error) => void) | undefined;
    api.getAccount.mockReturnValue(
      new Promise((_, reject) => {
        rejectAccount = reject;
      }),
    );

    render(<SiteHeader />);

    expect(
      screen.getByRole("link", { name: "正在确认登录状态" }),
    ).toHaveTextContent("确认登录");

    rejectAccount?.(new Error("网络暂时不可用"));

    expect(
      await screen.findByRole("link", {
        name: "身份状态暂时未知，前往个人中心",
      }),
    ).toHaveTextContent("身份未知");
  });
});
