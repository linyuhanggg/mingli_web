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
    expect(await screen.findByTestId("session-state")).toHaveTextContent("signedIn");

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

    expect(await screen.findByTestId("session-state")).toHaveTextContent("signedIn");
    const expiredRequests = await Promise.allSettled([
      getReadingResult("55555555-5555-4555-8555-555555555555"),
      getReadingResult("66666666-6666-4666-8666-666666666666"),
    ]);
    expect(expiredRequests).toHaveLength(2);
    expect(expiredRequests.every((result) => result.status === "rejected")).toBe(true);

    await waitFor(() => {
      expect(screen.getByTestId("session-state")).toHaveTextContent("signedOut");
    });
    expect(api.getAccount).toHaveBeenCalledTimes(2);
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

    const navigation = screen.getByRole("navigation", {
      name: "私人应用导航",
      hidden: true,
    });
    expect(
      within(navigation).getByRole("link", { name: "我的首页", hidden: true }),
    ).toHaveAttribute("href", "/app");
    expect(
      within(navigation).getByRole("link", { name: "个人中心", hidden: true }),
    ).toHaveAttribute("href", "/account");
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
    expect(loginLink).toHaveAttribute("href", "/account");
    expect(screen.getByText("游客模式")).toBeVisible();
    expect(screen.getByText("登录或注册")).toBeVisible();
  });
});

describe("personal center", () => {
  it("becomes a signed-in personal page instead of showing the login form again", async () => {
    api.getAccount.mockResolvedValue(signedInAccount);

    render(<AccountPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "个人中心" }),
    ).toBeVisible();
    expect(
      await screen.findByRole("heading", {
        level: 2,
        name: "q***@example.com",
      }),
    ).toBeVisible();
    expect(screen.getByText("当前设备已登录")).toBeVisible();
    expect(screen.queryByLabelText("邮箱地址")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^进入我的首页/ })).toHaveAttribute(
      "href",
      "/app",
    );
    expect(screen.getByRole("link", { name: /^查看命理档案/ })).toHaveAttribute(
      "href",
      "/app/profiles",
    );
    expect(screen.getByRole("link", { name: /^查看解读历史/ })).toHaveAttribute(
      "href",
      "/app/readings",
    );
  });

  it("shows the email login flow only when the device is signed out", async () => {
    render(<AccountPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "个人中心" }),
    ).toBeVisible();
    expect(await screen.findByText("当前设备尚未登录")).toBeVisible();
    expect(screen.getByLabelText("邮箱地址")).toBeVisible();
    expect(screen.queryByRole("button", { name: "退出当前设备" })).not.toBeInTheDocument();
  });

  it("confirms the shared session before routing to the personal home without a duplicate probe", async () => {
    const user = userEvent.setup();
    api.getAccount.mockReset();
    api.getAccount
      .mockRejectedValueOnce(new ApiError("Authentication required", 401))
      .mockResolvedValue(signedInAccount);
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/otp/request")) {
          return new Response(
            JSON.stringify({
              challenge_id: "967ea7cc-7b77-4db3-8d27-5a897679791f",
              development_code: "246810",
            }),
            { status: 202, headers: { "content-type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            csrf_token: "device-csrf-token-with-at-least-32-characters",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }),
    );

    render(
      <AccountSessionProvider>
        <AccountPage />
      </AccountSessionProvider>,
    );
    const email = await screen.findByLabelText("邮箱地址");
    await user.type(email, "user@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));
    const code = await screen.findByLabelText("六位验证码");
    await user.type(code, "246810");
    await user.click(screen.getByRole("button", { name: "验证并登录" }));

    await waitFor(() => {
      expect(navigation.replace).toHaveBeenCalledWith("/app");
    });
    expect(api.getAccount).toHaveBeenCalledTimes(2);
    expect(
      screen.getByRole("heading", { level: 2, name: "q***@example.com" }),
    ).toBeVisible();
    expect(screen.queryByLabelText("邮箱地址")).not.toBeInTheDocument();
  });
});

describe("public account entry", () => {
  it("changes from login to a clear signed-in destination", async () => {
    api.getAccount.mockResolvedValue(signedInAccount);

    render(<SiteHeader />);

    const accountLink = await screen.findByRole("link", {
      name: "已登录，进入我的首页",
    });
    expect(accountLink).toHaveAttribute("href", "/app");
    expect(accountLink).toHaveTextContent("已登录");
    expect(accountLink).toHaveTextContent("我的首页");
  });

  it("keeps a direct login entry when signed out", async () => {
    render(<SiteHeader />);

    const accountLink = await screen.findByRole("link", { name: "登录" });
    expect(accountLink).toHaveAttribute("href", "/account");
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
