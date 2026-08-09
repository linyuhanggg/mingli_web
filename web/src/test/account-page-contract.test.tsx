import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

import AccountPage from "@/app/account/page";


vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));


function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function stubApiFetch(accountStatus: number, accountBody: unknown) {
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    const url = String(input);
    if (url.includes("/api/v1/guest-sessions")) {
      return jsonResponse({ csrf_token: "stub-csrf-token" });
    }
    if (url.includes("/api/v1/account")) {
      return jsonResponse(accountBody, accountStatus);
    }
    return jsonResponse({ title: "Not Found" }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const signedInAccount = {
  user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
  identities: [
    {
      id: "8d2f1a4b-6c3e-4d9f-8a5b-2e7c4f1d9a3b",
      provider: "email",
      masked_destination: "q***@example.com",
      verified_at: "2026-08-01T00:00:00Z",
    },
  ],
};

beforeEach(() => {
  stubApiFetch(401, { title: "Authentication required" });
});

afterEach(() => {
  vi.unstubAllGlobals();
});


describe("account page header contract", () => {
  it("uses the shared AppPageHeader shape with a single h1 and no eyebrow", async () => {
    const { container } = render(<AccountPage />);
    // Let the session probe settle so the page reaches its stable state.
    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    const header = container.querySelector("header");
    expect(header).not.toBeNull();

    const heading = screen.getByRole("heading", {
      level: 1,
      name: "邮箱是你的默认登录入口。",
    });
    expect(header?.firstElementChild).toBe(heading);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("explains auto-registration, direct login, preview test-code boundary, and phone timing", async () => {
    const { container } = render(<AccountPage />);
    const main = screen.getByRole("main");
    const header = container.querySelector("header");
    expect(header).not.toBeNull();

    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    const description = within(header!).getByText(
      "首次邮箱验证自动注册账户，已有邮箱直接登录。当前公开测试预览显示测试码；真实邮件启用后不显示。手机号登录稍后开放。",
    );
    expect(description).toHaveTextContent(/首次邮箱验证自动注册/);
    expect(description).toHaveTextContent(/已有邮箱直接登录/);
    expect(description).toHaveTextContent(/当前公开测试预览显示测试码/);
    expect(description).toHaveTextContent(/真实邮件启用后不显示/);
    expect(description).not.toHaveTextContent(/Fake 环境/);
    expect(description).not.toHaveTextContent(/不会真的发送邮件/);
    expect(description).toHaveTextContent(/手机号登录稍后开放/);
    expect(within(main).getByText("邮箱验证为主")).toBeVisible();
    expect(within(main).getByText("设备会话可撤销")).toBeVisible();
  });

  it("keeps the email login form, identity notes, and account-boundary notes", async () => {
    render(<AccountPage />);
    const main = screen.getByRole("main");

    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    expect(within(main).getByRole("heading", { level: 2, name: "邮箱验证码登录" })).toBeVisible();
    expect(within(main).getByLabelText("邮箱地址")).toBeVisible();
    expect(within(main).getByRole("heading", { level: 2, name: "账户边界" })).toBeVisible();
    expect(within(main).getByRole("heading", { level: 2, name: "设备、订单与数据权利" })).toBeVisible();
  });

  it("keeps internal user identifiers out of the public copy", async () => {
    render(<AccountPage />);
    const main = screen.getByRole("main");

    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    expect(within(main).queryByText(/User/i)).not.toBeInTheDocument();
    expect(within(main).queryByText(/用户 ID/i)).not.toBeInTheDocument();
  });

  it("mounts the session control and stays honest when the device is signed out", async () => {
    render(<AccountPage />);
    const main = screen.getByRole("main");

    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    expect(within(main).getByText(/当前未登录；邮箱验证码登录后/)).toBeVisible();
    expect(within(main).queryByRole("button", { name: "退出当前设备" })).not.toBeInTheDocument();
    expect(within(main).getByLabelText("邮箱地址")).toBeVisible();
  });

  it("surfaces the signed-in device session with masked identity and a logout action", async () => {
    stubApiFetch(200, signedInAccount);
    render(<AccountPage />);
    const main = screen.getByRole("main");

    await screen.findByRole("button", { name: "退出当前设备" });

    expect(within(main).getByText("当前设备已登录")).toBeVisible();
    expect(within(main).getByText("q***@example.com")).toBeVisible();
    expect(within(main).queryByText(/4f9c3d6a/)).not.toBeInTheDocument();
    expect(within(main).queryByText(/8d2f1a4b/)).not.toBeInTheDocument();
  });
});
