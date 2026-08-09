import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  adoptCsrfToken,
  createProfileDraft,
  getCsrfToken,
  resetApiCache,
} from "@/lib/api";


function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function clearCsrfCookie() {
  document.cookie =
    "mingli_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
}

beforeEach(() => {
  clearCsrfCookie();
  resetApiCache();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("reads the readable mingli_csrf cookie before creating a Guest Session", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "mingli_csrf=session-csrf-read-from-cookie; path=/";

  await expect(getCsrfToken()).resolves.toBe("session-csrf-read-from-cookie");
  expect(fetchMock).not.toHaveBeenCalled();
});

it("locates mingli_csrf among other application cookies", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "theme=dark; path=/";
  document.cookie = "mingli_csrf=device-csrf-with-among-others; path=/";
  document.cookie = "debug=true; path=/";

  await expect(getCsrfToken()).resolves.toBe(
    "device-csrf-with-among-others",
  );
  expect(fetchMock).not.toHaveBeenCalled();
});

it("creates a Guest Session and caches its CSRF when no cookie exists", async () => {
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
    );
  vi.stubGlobal("fetch", fetchMock);

  await expect(getCsrfToken()).resolves.toBe(
    "guest-csrf-token-with-at-least-32-characters",
  );
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/guest-sessions",
    expect.objectContaining({ method: "POST", credentials: "include" }),
  );
  await expect(getCsrfToken()).resolves.toBe(
    "guest-csrf-token-with-at-least-32-characters",
  );
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("adopts a verified device CSRF and never creates a Guest afterwards", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);

  adoptCsrfToken("device-csrf-adopted-after-verify");

  await expect(getCsrfToken()).resolves.toBe(
    "device-csrf-adopted-after-verify",
  );
  expect(fetchMock).not.toHaveBeenCalled();
});

it("prefers a fresh mingli_csrf cookie over a stale in-memory token", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  adoptCsrfToken("stale-in-memory-guest-token");
  document.cookie = "mingli_csrf=device-csrf-from-login-cookie; path=/";

  await expect(getCsrfToken()).resolves.toBe("device-csrf-from-login-cookie");
  expect(fetchMock).not.toHaveBeenCalled();
});

it("re-creates a Guest only after logout clears both cookie and memory", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      jsonResponse(
        {
          status: "active",
          expires_at: "2026-08-10T00:00:00Z",
          csrf_token: "fresh-guest-csrf-token-after-logout",
        },
        201,
      ),
    )
    .mockResolvedValueOnce(
      jsonResponse(
        {
          status: "active",
          expires_at: "2026-08-10T00:00:00Z",
          csrf_token: "fresh-guest-csrf-token-after-logout",
        },
        201,
      ),
    );
  vi.stubGlobal("fetch", fetchMock);

  await getCsrfToken();
  resetApiCache();

  await expect(getCsrfToken()).resolves.toBe(
    "fresh-guest-csrf-token-after-logout",
  );
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("sends the adopted device CSRF on authenticated calls without a second Guest", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      jsonResponse({ draft_id: "86c9d8d9-1b45-4a27-8efd-946ef0e5186b", status: "draft" }),
    );
  vi.stubGlobal("fetch", fetchMock);
  adoptCsrfToken("device-csrf-token-with-at-least-32-characters");

  const draft = await createProfileDraft("本人");

  expect(draft.draft_id).toBe("86c9d8d9-1b45-4a27-8efd-946ef0e5186b");
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, requestInit] = fetchMock.mock.calls[0]!;
  expect(url).toBe("/api/v1/profiles/drafts");
  expect(requestInit).toMatchObject({
    method: "POST",
    credentials: "include",
  });
  expect(new Headers(requestInit?.headers).get("X-CSRF-Token")).toBe(
    "device-csrf-token-with-at-least-32-characters",
  );
});
