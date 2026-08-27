type ProblemBody = {
  title?: string;
  detail?: string;
  code?: string;
  options?: unknown;
  suggested_save_as_name?: string;
  existing_profile_id?: string;
  existing_profile_version_id?: string;
  owner_kind?: string;
  limit_scope?: string;
  limit?: number;
  remaining?: number;
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
  code?: string;
  options?: string[];
  suggestedSaveAsName?: string;
  existingProfileId?: string;
  existingProfileVersionId?: string;
  ownerKind?: string;
  limitScope?: string;
  limit?: number;
  remaining?: number;

  constructor(message: string, status = 0, detail?: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}

function problemError(body: ProblemBody | null, status: number): ApiError {
  const error = new ApiError(
    body?.title ?? "服务暂时不可用，请稍后重试",
    status,
    body?.detail,
    body?.code,
  );
  if (Array.isArray(body?.options)) {
    error.options = body.options.filter((item): item is string => typeof item === "string");
  }
  if (typeof body?.suggested_save_as_name === "string") {
    error.suggestedSaveAsName = body.suggested_save_as_name;
  }
  if (typeof body?.existing_profile_id === "string") {
    error.existingProfileId = body.existing_profile_id;
  }
  if (typeof body?.existing_profile_version_id === "string") {
    error.existingProfileVersionId = body.existing_profile_version_id;
  }
  if (typeof body?.owner_kind === "string") {
    error.ownerKind = body.owner_kind;
  }
  if (typeof body?.limit_scope === "string") {
    error.limitScope = body.limit_scope;
  }
  if (typeof body?.limit === "number") {
    error.limit = body.limit;
  }
  if (typeof body?.remaining === "number") {
    error.remaining = body.remaining;
  }
  return error;
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
    throw problemError(body, response.status);
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

export async function jsonPatch<T>(url: string, payload: unknown): Promise<T> {
  const execute = async () => {
    const csrf = await getCsrfToken();
    return requestJson<T>(url, {
      method: "PATCH",
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
