import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { adminFetch } from "@/lib/api";

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));
vi.mock("next/navigation", () => {
  const router = { replace: replaceMock };
  return {
    useRouter: () => router,
    usePathname: () => "/",
  };
});

import { AdminShell } from "@/components/admin-shell";

function setAdminCsrfCookie(value: string | null) {
  document.cookie = "mingli_admin_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
  if (value) {
    document.cookie = `mingli_admin_csrf=${encodeURIComponent(value)}; path=/`;
  }
}

function mockFetchSequence(
  ...responses: Array<{ status: number; body?: unknown; statusText?: string }>
) {
  const fetchMock = vi.fn();
  for (const entry of responses) {
    fetchMock.mockResolvedValueOnce(
      new Response(entry.body === undefined ? null : JSON.stringify(entry.body), {
        status: entry.status,
        statusText: entry.statusText,
        headers: { "content-type": "application/json" },
      }),
    );
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("adminFetch", () => {
  beforeEach(() => {
    setAdminCsrfCookie(null);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setAdminCsrfCookie(null);
  });

  it("attaches the CSRF cookie as x-csrf-token header on writes", async () => {
    setAdminCsrfCookie("csrf-token-123");
    const fetchMock = mockFetchSequence({ status: 204 });
    const result = await adminFetch("/api/v1/admin/auth/logout", { method: "POST" });
    expect(result.ok).toBe(true);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("x-csrf-token")).toBe("csrf-token-123");
    expect(init.credentials).toBe("same-origin");
    expect(init.cache).toBe("no-store");
  });

  it("omits the CSRF header when no cookie is present", async () => {
    const fetchMock = mockFetchSequence({ status: 204 });
    await adminFetch("/api/v1/admin/auth/logout", { method: "POST" });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("x-csrf-token")).toBeNull();
  });

  it("maps 401 problem details into an error result", async () => {
    mockFetchSequence({ status: 401, body: { title: "Staff authentication required" } });
    const result = await adminFetch("/api/v1/admin/me");
    expect(result).toEqual({ ok: false, status: 401, title: "Staff authentication required" });
  });

  it("falls back to a status based title for non JSON errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(new Response("oops", { status: 500 })),
    );
    const result = await adminFetch("/api/v1/admin/overview");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(500);
      expect(result.title).toContain("500");
    }
  });
});

describe("AdminShell auth gate", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    replaceMock.mockReset();
  });

  it("redirects to /login when the session check returns 401", async () => {
    mockFetchSequence({ status: 401, body: { title: "Staff authentication required" } });
    render(
      <AdminShell title="总览" duty="duty">
        <p>private content</p>
      </AdminShell>,
    );
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("校验会话中…")).toBeInTheDocument();
  });

  it("renders staff identity after a valid session", async () => {
    mockFetchSequence({
      status: 200,
      body: {
        staff_id: "s1",
        role: "ops",
        email: "ops@example.com",
        display_name: "运营同学",
        session_id: "sess-1",
        expires_at: "2026-08-12T12:00:00Z",
      },
    });
    render(
      <AdminShell title="总览" duty="duty">
        <p>private content</p>
      </AdminShell>,
    );
    expect(await screen.findByText("运营同学 · ops")).toBeInTheDocument();
    expect(screen.getByText("private content")).toBeInTheDocument();
  });

  it("shows an alert instead of redirecting on non-401 failures", async () => {
    mockFetchSequence({ status: 500, body: { title: "服务不可用" } });
    render(
      <AdminShell title="总览" duty="duty">
        <p>private content</p>
      </AdminShell>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("服务不可用");
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("logs out through the API and returns to /login", async () => {
    mockFetchSequence(
      {
        status: 200,
        body: {
          staff_id: "s1",
          role: "ops",
          email: "ops@example.com",
          display_name: "运营同学",
          session_id: "sess-1",
          expires_at: "2026-08-12T12:00:00Z",
        },
      },
      { status: 204 },
    );
    const user = userEvent.setup();
    render(
      <AdminShell title="总览" duty="duty">
        <p>private content</p>
      </AdminShell>,
    );
    await screen.findByText("运营同学 · ops");
    await user.click(screen.getByRole("button", { name: "退出" }));
    const fetchMock = vi.mocked(fetch);
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/login"));
    const [url, init] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(url).toBe("/api/v1/admin/auth/logout");
    expect(init.method).toBe("POST");
  });
});
