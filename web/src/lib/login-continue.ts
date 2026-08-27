const UNSAFE_CONTINUE_CHARS = /[\u0000-\u001F\u007F\\]/;

export function loginContinueHref(
  pathname: string,
  search = "",
  idempotencyKey?: string,
): string {
  const next = `${pathname}${search}`;
  const params = new URLSearchParams({ next });
  if (idempotencyKey) params.set("idempotency_key", idempotencyKey);
  return `/auth/login?${params.toString()}`;
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
  return safeContinuePath(new URLSearchParams(window.location.search).get("next"));
}
