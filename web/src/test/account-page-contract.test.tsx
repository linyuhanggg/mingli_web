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
    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    const header = container.querySelector("header");
    expect(header).not.toBeNull();

    const heading = screen.getByRole("heading", {
      level: 1,
      name: "个人中心",
    });
    expect(header?.firstElementChild).toBe(heading);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("explains the personal-center purpose and the real login methods", async () => {
    const { container } = render(<AccountPage />);
    const main = container;
    const header = container.querySelector("header");
    expect(header).not.toBeNull();

    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    const description = within(header!).getByText(
      "登录后在这里确认当前身份、进入个人首页、管理设备并找到自己的档案与解读；未登录时只显示邮箱验证入口。",
    );
    expect(description).toHaveTextContent(/确认当前身份/);
    expect(description).toHaveTextContent(/进入个人首页/);
    expect(description).toHaveTextContent(/未登录时只显示邮箱验证入口/);
    expect(within(main).getByText("邮箱验证为主")).toBeVisible();
    expect(within(main).getByText("设备会话可撤销")).toBeVisible();
    expect(within(main).getByText("邮箱验证码")).toBeVisible();
    expect(within(main).getByText("手机号验证码")).toBeVisible();
    expect(within(main).getByText("稍后开放")).toBeVisible();
    expect(within(main).getByText(/验证码将发送到该邮箱/)).toBeVisible();
  });

  it("shows the login form and account boundary only for a signed-out device", async () => {
    const { container } = render(<AccountPage />);
    const main = container;

    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    expect(within(main).getByRole("heading", { level: 2, name: "验证码登录" })).toBeVisible();
    expect(within(main).getByLabelText("邮箱地址")).toBeVisible();
    expect(within(main).getByRole("heading", { level: 2, name: "账户边界" })).toBeVisible();
    expect(within(main).queryByRole("heading", { level: 2, name: "我的档案与记录" })).not.toBeInTheDocument();
    expect(within(main).queryByRole("heading", { level: 2, name: "设备、订单与数据权利" })).not.toBeInTheDocument();
  });

  it("keeps internal user identifiers out of the public copy", async () => {
    const { container } = render(<AccountPage />);
    const main = container;

    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    expect(within(main).queryByText(/User/i)).not.toBeInTheDocument();
    expect(within(main).queryByText(/用户 ID/i)).not.toBeInTheDocument();
  });

  it("mounts the session control and stays honest when the device is signed out", async () => {
    const { container } = render(<AccountPage />);
    const main = container;

    await screen.findByRole("heading", { level: 2, name: "身份与设备" });

    expect(within(main).getByText(/当前设备尚未登录。邮箱验证码登录后/)).toBeVisible();
    expect(within(main).queryByRole("button", { name: "退出当前设备" })).not.toBeInTheDocument();
    expect(within(main).getByLabelText("邮箱地址")).toBeVisible();
  });

  it("surfaces the signed-in device session with masked identity and a logout action", async () => {
    stubApiFetch(200, signedInAccount);
    const { container } = render(<AccountPage />);
    const main = container;

    await screen.findByRole("button", { name: "退出当前设备" });

    expect(within(main).getByText("当前设备已登录")).toBeVisible();
    expect(within(main).getAllByText("q***@example.com")).toHaveLength(2);
    expect(within(main).queryByLabelText("邮箱地址")).not.toBeInTheDocument();
    expect(within(main).getByRole("link", { name: /^进入我的首页/ })).toHaveAttribute("href", "/app");
    expect(within(main).getByRole("heading", { level: 2, name: "设备、订单与数据权利" })).toBeVisible();
    expect(within(main).queryByText(/4f9c3d6a/)).not.toBeInTheDocument();
    expect(within(main).queryByText(/8d2f1a4b/)).not.toBeInTheDocument();
  });
});
