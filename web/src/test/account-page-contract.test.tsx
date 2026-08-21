import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

function stubApiFetch(
  accountStatus: number,
  accountBody: unknown,
  historyBody: unknown = { roots: [] },
) {
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    const url = String(input);
    if (url.includes("/api/v1/guest-sessions")) {
      return jsonResponse({ csrf_token: "stub-csrf-token" });
    }
    if (url.includes("/api/v1/account/history")) {
      return jsonResponse(historyBody);
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


describe("account home contract", () => {
  it("uses the shared AppPageHeader shape with one h1 named 我的", () => {
    const { container } = render(<AccountPage />);
    const header = container.querySelector("header");

    expect(header).not.toBeNull();
    expect(header?.firstElementChild).toBe(
      screen.getByRole("heading", { level: 1, name: "我的" }),
    );
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("keeps guest data private without the six-grid or OTP form", async () => {
    const { container } = render(<AccountPage />);

    expect(await screen.findByRole("heading", { level: 2, name: "未登录" })).toBeVisible();
    expect(screen.getByText("登录后才能看档案和历史")).toBeVisible();
    expect(screen.getByRole("link", { name: "登录" })).toHaveAttribute("href", "/auth/login");
    expect(screen.getByRole("link", { name: "用验证码登录" })).toHaveAttribute("href", "/auth/verify");
    expect(screen.queryByRole("navigation", { name: "我的账户入口" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("邮箱地址")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "账户边界" })).not.toBeInTheDocument();
    expect(container).not.toHaveTextContent("4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41");
    expect(container).not.toHaveTextContent("q***@example.com");
  });

  it("shows a signed-in identity card, six routes, and server-backed delivery status", async () => {
    stubApiFetch(200, signedInAccount, { roots: [] });
    const { container } = render(<AccountPage />);

    expect(await screen.findByRole("heading", { level: 2, name: "q***@example.com" })).toBeVisible();
    expect(screen.getByText("已登录")).toBeVisible();
    expect(screen.getByText("以订单与权益页为准")).toBeVisible();
    expect(screen.queryByLabelText("邮箱地址")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "退出当前设备" })).toBeVisible();
    expect(await screen.findByText("还没有可显示的解读")).toBeVisible();

    const navigation = screen.getByRole("navigation", { name: "我的账户入口" });
    expect(within(navigation).getAllByRole("link")).toHaveLength(6);
    expect(container).not.toHaveTextContent("4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41");
    expect(container).not.toHaveTextContent("8d2f1a4b-6c3e-4d9f-8a5b-2e7c4f1d9a3b");
  });

  it("renders pending delivery labels from the account history projection", async () => {
    stubApiFetch(200, signedInAccount, {
      roots: [
        {
          reading_root_id: "44444444-4444-4444-8444-444444444444",
          profile_version_id: null,
          capability_id: "bazi",
          created_at: "2026-08-10T01:00:00Z",
          versions: [
            {
              reading_version_id: "33333333-3333-4333-8333-333333333333",
              reading_root_id: "44444444-4444-4444-8444-444444444444",
              capability_id: "bazi",
              version: 1,
              status: "waiting_input",
              object_id: "natal",
              dimension_ids: ["overview"],
              horizon: { kind_id: "day", start: "2026-08-10", end: "2026-08-10" },
              created_at: "2026-08-10T01:00:00Z",
            },
          ],
        },
      ],
    });
    render(<AccountPage />);

    expect(await screen.findByRole("heading", { name: "最近交付与待处理事项" })).toBeVisible();
    expect(screen.getByText("八字任务")).toBeVisible();
    expect(screen.getByText("等待输入")).toBeVisible();
  });

  it("does not request account history for a signed-out device", async () => {
    const fetchMock = stubApiFetch(401, { title: "Authentication required" });
    render(<AccountPage />);

    await screen.findByRole("heading", { level: 2, name: "未登录" });
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/v1/account/history"))).toBe(false);
  });

  it("does not expose guest shortcuts or identity details while checking", async () => {
    let resolveAccount: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const url = String(input);
        if (url.includes("/api/v1/account")) {
          return new Promise<Response>((resolve) => {
            resolveAccount = resolve;
          });
        }
        return jsonResponse({ csrf_token: "stub-csrf-token" });
      }),
    );

    render(<AccountPage />);

    expect(screen.getByRole("heading", { level: 2, name: "确认中" })).toBeVisible();
    expect(screen.queryByRole("navigation", { name: "我的账户入口" })).not.toBeInTheDocument();
    expect(screen.queryByText(/@example\.com/)).not.toBeInTheDocument();

    resolveAccount?.(jsonResponse({ title: "Authentication required" }, 401));
    expect(await screen.findByRole("heading", { level: 2, name: "未登录" })).toBeVisible();
  });

  it("shows an honest retry state when the account probe fails", async () => {
    stubApiFetch(502, { title: "服务暂时不可用" });
    render(<AccountPage />);

    expect((await screen.findAllByRole("heading", { level: 2, name: "读取失败，请重试" })).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "重新读取账户状态" })).toBeEnabled();
    expect(screen.queryByText(/4f9c3d6a/)).not.toBeInTheDocument();
  });
});
