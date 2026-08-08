import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";

import { OtpForm } from "@/components/otp-form";


function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

it("bootstraps a Guest Session and requests phone OTP through same-origin API", async () => {
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
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<OtpForm />);

  await screen.findByText("安全会话已建立");
  await user.type(screen.getByRole("textbox", { name: "中国大陆手机号" }), "13800138000");
  await user.click(screen.getByRole("button", { name: "发送验证码" }));

  expect(fetchMock).toHaveBeenNthCalledWith(
    1,
    "/api/v1/guest-sessions",
    expect.objectContaining({ method: "POST", credentials: "include" }),
  );
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
  expect(await screen.findByText("本地测试验证码：246810")).toBeVisible();
});

it("supports email OTP verification and shows the internal account root", async () => {
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
    )
    .mockResolvedValueOnce(
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

  await screen.findByText("安全会话已建立");
  await user.click(screen.getByRole("button", { name: "邮箱验证码" }));
  await user.type(screen.getByRole("textbox", { name: "邮箱地址" }), "user@example.com");
  await user.click(screen.getByRole("button", { name: "发送验证码" }));
  await user.type(await screen.findByRole("textbox", { name: "六位验证码" }), "246810");
  await user.click(screen.getByRole("button", { name: "验证并登录" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/auth/otp/verify",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: expect.objectContaining({
          "X-CSRF-Token": "guest-csrf-token-with-at-least-32-characters",
        }),
      }),
    );
  });
  expect(await screen.findByText("登录成功")).toBeVisible();
  expect(screen.getByText(/2ec4dc6c-3e6e-4aef-ae3b-c900b3f1d239/)).toBeVisible();
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

  expect(
    await screen.findByText("登录服务暂时不可用，请稍后重试。"),
  ).toBeVisible();
  expect(screen.queryByText(/Unexpected token/)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "重新连接" }));

  expect(await screen.findByText("安全会话已建立")).toBeVisible();
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
  const input = screen.getByRole("textbox", { name: "中国大陆手机号" });
  await user.type(input, "123");
  await user.click(screen.getByRole("button", { name: "发送验证码" }));

  expect(await screen.findByText("请输入有效的中国大陆手机号")).toBeVisible();
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
  const input = screen.getByRole("textbox", { name: "中国大陆手机号" });
  await user.type(input, "13800138000");
  await user.click(screen.getByRole("button", { name: "发送验证码" }));

  expect(await screen.findByText("请求过于频繁，请稍后重试")).toBeVisible();
  expect(input.getAttribute("aria-describedby")).toContain("otp-destination-error");
});
