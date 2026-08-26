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
  ) {
    return fallback;
  }
  return candidate;
}

export function destinationAfterLogin(): string {
  if (typeof window === "undefined") return "/account";
  return safeContinuePath(new URLSearchParams(window.location.search).get("next"));
}
