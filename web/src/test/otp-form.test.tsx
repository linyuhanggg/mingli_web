import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, vi } from "vitest";

import { OtpForm } from "@/components/otp-form";
import { getCsrfToken, resetApiCache } from "@/lib/api";


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

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function guestWithRequestFlow() {
  return vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      jsonResponse(
        {
          status: "active",
          expires_at: "2026-08-10T00:00:00Z",
          csrf_token: "guest-csrf-token-with-at-least-32-characters",
        },
        201,
      ),
    )
    .mockResolvedValueOnce(
      jsonResponse(
        {
          challenge_id: "967ea7cc-7b77-4db3-8d27-5a897679791f",
          expires_at: "2026-08-09T00:05:00Z",
          retry_after_seconds: 60,
          development_code: "246810",
        },
        202,
      ),
    );
}

async function reachCodePhase(
  fetchMock: ReturnType<typeof vi.fn<typeof fetch>>,
  user: ReturnType<typeof userEvent.setup>,
  email = "user@example.com",
) {
  await screen.findByText("安全会话已建立");
  await user.type(screen.getByRole("textbox", { name: "邮箱地址" }), email);
  await user.click(screen.getByRole("button", { name: "发送验证码" }));
  await screen.findByText("本地测试验证码：246810");
  expect(fetchMock).toHaveBeenCalledTimes(2);
}

beforeEach(() => {
  document.cookie = "mingli_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
  resetApiCache();
  replaceMock.mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("bootstraps through the shared API, defaults to email, and locks the phone entry", async () => {
  const fetchMock = guestWithRequestFlow();
  vi.stubGlobal("fetch", fetchMock);

  render(<OtpForm />);

  await screen.findByText("安全会话已建立");
  expect(fetchMock).toHaveBeenNthCalledWith(
    1,
    "/api/v1/guest-sessions",
    expect.objectContaining({ method: "POST", credentials: "include" }),
  );
  const emailInput = screen.getByRole("textbox", { name: "邮箱地址" });
  expect(emailInput).toBeVisible();
  expect(emailInput).toHaveAttribute("spellcheck", "false");

  const group = screen.getByRole("group", { name: "验证码方式" });
  expect(
    within(group).getByRole("button", { name: "邮箱验证码" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(within(group).queryByRole("button", { name: /手机号/ })).not.toBeInTheDocument();
  expect(within(group).getByText("手机号验证码")).toBeVisible();
  expect(within(group).getByText("稍后开放")).toBeVisible();
});

it("explains that the first verification creates the account and an existing email signs in", async () => {
  const fetchMock = guestWithRequestFlow();
  vi.stubGlobal("fetch", fetchMock);

  render(<OtpForm />);

  await screen.findByText("安全会话已建立");
  expect(screen.getByText(/首次验证自动创建账户/)).toBeVisible();
  expect(screen.getByText(/已有邮箱直接登录/)).toBeVisible();
});

it("requests an email OTP and moves focus to the code input", async () => {
  const fetchMock = guestWithRequestFlow();
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<OtpForm />);
  await reachCodePhase(fetchMock, user);

  const [, requestInit] = fetchMock.mock.calls[1]!;
  const payload = JSON.parse(String(requestInit?.body));
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    "/api/v1/auth/otp/request",
    expect.objectContaining({
      method: "POST",
      credentials: "include",
      headers: expect.objectContaining({
        "X-CSRF-Token": "guest-csrf-token-with-at-least-32-characters",
      }),
    }),
  );
  expect(payload).toEqual({
    channel: "email",
    destination: "user@example.com",
  });

  const codeInput = await screen.findByRole("textbox", { name: "六位验证码" });
  expect(codeInput).toHaveAttribute("spellcheck", "false");
  await waitFor(() => {
    expect(codeInput).toHaveFocus();
  });
});

it("resends a code to the same email without leaving the code entry", async () => {
  const fetchMock = guestWithRequestFlow().mockResolvedValueOnce(
    jsonResponse(
      {
        challenge_id: "77cfa29c-4a51-4d3a-9c7e-8b4f6a3bf21d",
        expires_at: "2026-08-09T00:06:00Z",
        retry_after_seconds: 60,
        development_code: "246810",
      },
      202,
    ),
  );
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<OtpForm />);
  await reachCodePhase(fetchMock, user);
  await user.click(screen.getByRole("button", { name: "重新发送验证码" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
  const [, resendInit] = fetchMock.mock.calls[2]!;
  expect(JSON.parse(String(resendInit?.body))).toEqual({
    channel: "email",
    destination: "user@example.com",
  });
  expect(screen.getByRole("textbox", { name: "六位验证码" })).toBeInTheDocument();
});

it("lets the user change the email and clears the pending challenge", async () => {
  const fetchMock = guestWithRequestFlow();
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<OtpForm />);
  await reachCodePhase(fetchMock, user);
  await user.click(screen.getByRole("button", { name: "更换邮箱" }));

  const destinationInput = await screen.findByRole("textbox", {
    name: "邮箱地址",
  });
  expect(screen.queryByRole("textbox", { name: "六位验证码" })).not.toBeInTheDocument();
  await waitFor(() => {
    expect(destinationInput).toHaveFocus();
  });
});

it("verifying adopts the device CSRF, routes to /app, and never leaks the User ID", async () => {
  const fetchMock = guestWithRequestFlow().mockResolvedValueOnce(
    jsonResponse({
      user_id: "2ec4dc6c-3e6e-4aef-ae3b-c900b3f1d239",
      session_id: "58a5a6d0-b804-4c95-8c59-7f13e1813105",
      expires_at: "2026-09-08T00:00:00Z",
      csrf_token: "device-csrf-token-with-at-least-32-characters",
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<OtpForm />);
  await reachCodePhase(fetchMock, user);
  await user.type(screen.getByRole("textbox", { name: "六位验证码" }), "246810");
  await user.click(screen.getByRole("button", { name: "验证并登录" }));

  await waitFor(() => {
    expect(replaceMock).toHaveBeenCalledWith("/app");
  });
  expect(await screen.findByText("登录成功")).toBeVisible();
  expect(screen.getByText(/正在进入 \/app/)).toBeVisible();

  expect(screen.queryByText(/User ID/)).not.toBeInTheDocument();
  expect(screen.queryByText(/2ec4dc6c-3e6e-4aef-ae3b-c900b3f1d239/)).not.toBeInTheDocument();

  await expect(getCsrfToken()).resolves.toBe(
    "device-csrf-token-with-at-least-32-characters",
  );
  expect(fetchMock).toHaveBeenCalledTimes(3);
});

it("turns a non-JSON bootstrap failure into a recoverable service message", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      new Response("Internal Server Error", {
        status: 502,
        headers: { "content-type": "text/plain" },
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse(
        {
          status: "active",
          expires_at: "2026-08-10T00:00:00Z",
          csrf_token: "guest-csrf-token-with-at-least-32-characters",
        },
        201,
      ),
    );
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<OtpForm />);

  expect(await screen.findByText("登录服务暂时不可用，请稍后重试。")).toBeVisible();
  expect(screen.queryByText(/Unexpected token/)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "重新连接" }));

  expect(await screen.findByText("安全会话已建立")).toBeVisible();
  expect(screen.getByRole("textbox", { name: "邮箱地址" })).toBeVisible();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("validates the destination locally and associates the error with the field", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(
    jsonResponse(
      {
        status: "active",
        expires_at: "2026-08-10T00:00:00Z",
        csrf_token: "guest-csrf-token-with-at-least-32-characters",
      },
      201,
    ),
  );
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<OtpForm />);

  await screen.findByText("安全会话已建立");
  const input = screen.getByRole("textbox", { name: "邮箱地址" });
  await user.type(input, "not-an-email");
  await user.click(screen.getByRole("button", { name: "发送验证码" }));

  expect(await screen.findByText("请输入有效的邮箱地址")).toBeVisible();
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(input.getAttribute("aria-describedby")).toContain("otp-destination-error");
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("renders an OTP request failure next to the destination field", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      jsonResponse(
        {
          status: "active",
          expires_at: "2026-08-10T00:00:00Z",
          csrf_token: "guest-csrf-token-with-at-least-32-characters",
        },
        201,
      ),
    )
    .mockResolvedValueOnce(jsonResponse({ title: "请求过于频繁，请稍后重试" }, 429));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<OtpForm />);

  await screen.findByText("安全会话已建立");
  const input = screen.getByRole("textbox", { name: "邮箱地址" });
  await user.type(input, "user@example.com");
  await user.click(screen.getByRole("button", { name: "发送验证码" }));

  expect(await screen.findByText("请求过于频繁，请稍后重试")).toBeVisible();
  expect(input.getAttribute("aria-describedby")).toContain("otp-destination-error");
});
