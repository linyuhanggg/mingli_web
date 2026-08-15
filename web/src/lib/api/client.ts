type ProblemBody = {
  title?: string;
  detail?: string;
};

type PostOptions = {
  idempotencyKey?: string;
};

type AccountSessionInvalidationListener = () => void | Promise<void>;
const accountSessionInvalidationListeners =
  new Set<AccountSessionInvalidationListener>();
/**
 * Single-flight for private API 401 storms: concurrent/back-to-back notifies
 * share one listener flush that stays open until every listener settles.
 */
let accountSessionInvalidationFlush: Promise<void> | null = null;

const CSRF_COOKIE = "mingli_csrf";

export function subscribeAccountSessionInvalidation(
  listener: AccountSessionInvalidationListener,
): () => void {
  accountSessionInvalidationListeners.add(listener);
  return () => accountSessionInvalidationListeners.delete(listener);
}

function notifyAccountSessionInvalidated(): void {
  if (accountSessionInvalidationListeners.size === 0) {
    return;
  }
  if (accountSessionInvalidationFlush) {
    return;
  }
  const listeners = [...accountSessionInvalidationListeners];
  accountSessionInvalidationFlush = (async () => {
    await Promise.all(
      listeners.map(async (listener) => {
        await listener();
      }),
    );
  })().finally(() => {
    accountSessionInvalidationFlush = null;
  });
}

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status = 0, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function requestJson<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(url, { ...options, credentials: "include" });
  let body: (T & ProblemBody) | null = null;

  if (response.headers.get("content-type")?.includes("json")) {
    try {
      body = (await response.json()) as T & ProblemBody;
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearCsrfCache();
      if (url !== "/api/v1/account") {
        notifyAccountSessionInvalidated();
      }
    }
    throw new ApiError(
      body?.title ?? "服务暂时不可用，请稍后重试",
      response.status,
      body?.detail,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!body) {
    throw new ApiError("服务器响应异常，请稍后重试", response.status);
  }
  return body as T;
}

function validateIdempotencyKey(key: string): void {
  if (key.length < 8 || key.length > 128) {
    throw new ApiError("请求标识无效，请重新发起", 400);
  }
}

export async function jsonPost<T>(
  url: string,
  payload: unknown,
  options: PostOptions = {},
): Promise<T> {
  if (options.idempotencyKey) {
    validateIdempotencyKey(options.idempotencyKey);
  }

  const execute = async () => {
    const csrf = await getCsrfToken();
    const headers = new Headers({
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    });
    if (options.idempotencyKey) {
      headers.set("Idempotency-Key", options.idempotencyKey);
    }
    return requestJson<T>(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
  };

  try {
    return await execute();
  } catch (error) {
    if (
      !(error instanceof ApiError) ||
      error.status !== 403 ||
      error.message !== "CSRF validation failed"
    ) {
      throw error;
    }
    clearCsrfCache();
    return execute();
  }
}

export async function jsonPut<T>(url: string, payload: unknown): Promise<T> {
  const execute = async () => {
    const csrf = await getCsrfToken();
    return requestJson<T>(url, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf,
      },
      body: JSON.stringify(payload),
    });
  };

  try {
    return await execute();
  } catch (error) {
    if (
      !(error instanceof ApiError) ||
      error.status !== 403 ||
      error.message !== "CSRF validation failed"
    ) {
      throw error;
    }
    clearCsrfCache();
    return execute();
  }
}

export async function jsonDelete<T>(url: string): Promise<T> {
  const execute = async () => {
    const csrf = await getCsrfToken();
    return requestJson<T>(url, {
      method: "DELETE",
      headers: { "X-CSRF-Token": csrf },
    });
  };

  try {
    return await execute();
  } catch (error) {
    if (
      !(error instanceof ApiError) ||
      error.status !== 403 ||
      error.message !== "CSRF validation failed"
    ) {
      throw error;
    }
    clearCsrfCache();
    return execute();
  }
}

function readCsrfCookie(): string {
  if (typeof document === "undefined") {
    return "";
  }
  const pair = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${CSRF_COOKIE}=`));
  if (!pair) {
    return "";
  }
  return pair.slice(pair.indexOf("=") + 1);
}

function clearCsrfCache(): void {
  csrfToken = "";
  csrfPromise = null;
}

let csrfToken = "";
let csrfPromise: Promise<string> | null = null;

/** Adopt the device CSRF returned by a successful OTP verification. */
export function adoptCsrfToken(token: string): void {
  if (!token) {
    return;
  }
  csrfToken = token;
  csrfPromise = null;
}

export async function getCsrfToken(): Promise<string> {
  const cookieToken = readCsrfCookie();
  if (cookieToken) {
    csrfToken = cookieToken;
    csrfPromise = null;
    return cookieToken;
  }
  if (csrfToken) {
    return csrfToken;
  }
  if (!csrfPromise) {
    csrfPromise = requestJson<{ csrf_token: string }>(
      "/api/v1/guest-sessions",
      {
        method: "POST",
      },
    )
      .then((session) => {
        if (!session.csrf_token) {
          throw new ApiError("安全会话响应缺少 CSRF Token", 502);
        }
        csrfToken = session.csrf_token;
        return csrfToken;
      })
      .finally(() => {
        csrfPromise = null;
      });
  }
  return csrfPromise;
}

export function createIdempotencyKey(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `reading-${globalThis.crypto.randomUUID()}`;
  }
  return `reading-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function resetApiCache(): void {
  clearCsrfCache();
}
