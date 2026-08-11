export type StaffRole = "support" | "finance" | "ops" | "superadmin";

export type AdminSessionResponse = {
  staff_id: string;
  session_id: string;
  role: StaffRole;
  display_name: string;
  expires_at: string;
  csrf_token: string;
};

export type AdminMeResponse = {
  staff_id: string;
  role: StaffRole;
  email: string;
  display_name: string;
  session_id: string;
  expires_at: string;
};

export type AdminOverviewResponse = {
  generated_at: string;
  is_stub: boolean;
  kpis: Array<{ id: string; label: string; value: number; is_stub: boolean }>;
  queues: Array<{ id: string; label: string; count: number; is_stub: boolean }>;
};

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const parts = document.cookie.split(";").map((part) => part.trim());
  for (const part of parts) {
    if (part.startsWith(`${name}=`)) {
      return decodeURIComponent(part.slice(name.length + 1));
    }
  }
  return null;
}

export function getAdminCsrfToken(): string | null {
  return readCookie("mingli_admin_csrf");
}

export async function adminFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<{ ok: true; data: T } | { ok: false; status: number; title: string }> {
  const headers = new Headers(init.headers);
  if (!headers.has("content-type") && init.body) {
    headers.set("content-type", "application/json");
  }
  const csrf = getAdminCsrfToken();
  if (csrf && !headers.has("x-csrf-token")) {
    headers.set("x-csrf-token", csrf);
  }
  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (response.status === 204) {
    return { ok: true, data: undefined as T };
  }
  const text = await response.text();
  let parsed: unknown = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = null;
  }
  if (!response.ok) {
    const title =
      parsed && typeof parsed === "object" && parsed !== null && "title" in parsed
        ? String((parsed as { title: unknown }).title)
        : `请求失败（${response.status}）`;
    return { ok: false, status: response.status, title };
  }
  return { ok: true, data: parsed as T };
}
