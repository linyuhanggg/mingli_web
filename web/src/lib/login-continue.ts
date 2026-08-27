const UNSAFE_CONTINUE_CHARS = /[\u0000-\u001F\u007F\\]/;
const PENDING_START_PREFIX = "mingli.pending-start:";

export type PendingStartTask = {
  productId: string;
  fingerprint: string;
  values: unknown;
};

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

export function persistPendingStartTask(
  idempotencyKey: string,
  payload: PendingStartTask,
): void {
  if (typeof window === "undefined") return;
  pendingStartCache.set(idempotencyKey, payload);
  sessionStorage.setItem(`${PENDING_START_PREFIX}${idempotencyKey}`, JSON.stringify(payload));
}

export function loadPendingStartTask(
  idempotencyKey: string | null | undefined,
): PendingStartTask | null {
  if (!idempotencyKey || typeof window === "undefined") return null;
  const cached = pendingStartCache.get(idempotencyKey);
  if (cached) return cached;
  const raw = sessionStorage.getItem(`${PENDING_START_PREFIX}${idempotencyKey}`);
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
  window.addEventListener("storage", onStoreChange);
  return () => window.removeEventListener("storage", onStoreChange);
}
