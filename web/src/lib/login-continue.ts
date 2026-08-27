const UNSAFE_CONTINUE_CHARS = /[\u0000-\u001F\u007F\\]/;
const PENDING_START_PREFIX = "mingli.pending-start:";

export type PendingStartTask = {
  productId: string;
  fingerprint: string;
  values: unknown;
};

export const PENDING_START_STORAGE_FAILURE_CODE = "pending_start_storage_unavailable";

export type PendingStartStorageFailure = Readonly<{
  code: typeof PENDING_START_STORAGE_FAILURE_CODE;
  operation: "read" | "write";
}>;

export type PendingStartTaskLoadResult =
  | PendingStartTask
  | PendingStartStorageFailure
  | null;

const pendingStartReadFailure: PendingStartStorageFailure = Object.freeze({
  code: PENDING_START_STORAGE_FAILURE_CODE,
  operation: "read",
});
const pendingStartWriteFailure: PendingStartStorageFailure = Object.freeze({
  code: PENDING_START_STORAGE_FAILURE_CODE,
  operation: "write",
});

export function isPendingStartStorageFailure(
  value: PendingStartTaskLoadResult,
): value is PendingStartStorageFailure {
  return Boolean(
    value
    && "code" in value
    && value.code === PENDING_START_STORAGE_FAILURE_CODE,
  );
}

export function withIdempotencyKey(
  pathAndSearch: string,
  idempotencyKey?: string,
): string {
  if (!idempotencyKey) return pathAndSearch;
  const [path, rawQuery = ""] = pathAndSearch.split("?");
  const params = new URLSearchParams(rawQuery.startsWith("?") ? rawQuery.slice(1) : rawQuery);
  params.set("idempotency_key", idempotencyKey);
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function loginContinueHref(
  pathname: string,
  search = "",
  idempotencyKey?: string,
): string {
  const next = withIdempotencyKey(`${pathname}${search}`, idempotencyKey);
  return `/auth/login?${new URLSearchParams({ next }).toString()}`;
}

export function safeContinuePath(
  candidate: string | null | undefined,
  fallback = "/account",
): string {
  if (
    !candidate
    || !candidate.startsWith("/")
    || candidate.startsWith("//")
    || candidate.includes("://")
    || UNSAFE_CONTINUE_CHARS.test(candidate)
  ) {
    return fallback;
  }
  try {
    const resolved = new URL(candidate, "https://mingli.invalid");
    if (resolved.origin !== "https://mingli.invalid") {
      return fallback;
    }
  } catch {
    return fallback;
  }
  return candidate;
}

export function destinationAfterLogin(): string {
  if (typeof window === "undefined") return "/account";
  const params = new URLSearchParams(window.location.search);
  const next = safeContinuePath(params.get("next"));
  const siblingKey = params.get("idempotency_key");
  return siblingKey ? safeContinuePath(withIdempotencyKey(next, siblingKey)) : next;
}

const pendingStartCache = new Map<string, PendingStartTask>();
const pendingStartListeners = new Set<() => void>();

function notifyPendingStartListeners() {
  pendingStartListeners.forEach((listener) => listener());
}

export function persistPendingStartTask(
  idempotencyKey: string,
  payload: PendingStartTask,
): PendingStartStorageFailure | null {
  if (typeof window === "undefined") return null;
  try {
    window.sessionStorage.setItem(
      `${PENDING_START_PREFIX}${idempotencyKey}`,
      JSON.stringify(payload),
    );
  } catch {
    return pendingStartWriteFailure;
  }
  pendingStartCache.set(idempotencyKey, payload);
  notifyPendingStartListeners();
  return null;
}

export function consumePendingStartTask(
  idempotencyKey: string | null | undefined,
): PendingStartStorageFailure | null {
  if (!idempotencyKey || typeof window === "undefined") return null;
  pendingStartCache.delete(idempotencyKey);
  try {
    window.sessionStorage.removeItem(`${PENDING_START_PREFIX}${idempotencyKey}`);
  } catch {
    notifyPendingStartListeners();
    return pendingStartWriteFailure;
  }
  notifyPendingStartListeners();
  return null;
}

export function loadPendingStartTask(
  idempotencyKey: string | null | undefined,
): PendingStartTaskLoadResult {
  if (!idempotencyKey || typeof window === "undefined") return null;
  const cached = pendingStartCache.get(idempotencyKey);
  if (cached) return cached;
  let raw: string | null;
  try {
    raw = window.sessionStorage.getItem(`${PENDING_START_PREFIX}${idempotencyKey}`);
  } catch {
    return pendingStartReadFailure;
  }
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as PendingStartTask;
    if (!parsed || typeof parsed.productId !== "string" || typeof parsed.fingerprint !== "string") {
      return null;
    }
    pendingStartCache.set(idempotencyKey, parsed);
    return parsed;
  } catch {
    return null;
  }
}

export function subscribePendingStartTasks(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  pendingStartListeners.add(onStoreChange);
  window.addEventListener("storage", onStoreChange);
  return () => {
    pendingStartListeners.delete(onStoreChange);
    window.removeEventListener("storage", onStoreChange);
  };
}
