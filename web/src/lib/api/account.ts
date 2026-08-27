import type {
  AccountResponse,
  AccountClosure,
  AccountExportResponse,
  AccountNotification,
  AccountNotificationsResponse,
  AccountEntitlementsResponse,
  AccountHistoryResponse,
  AccountOrdersResponse,
  AccountReferralsResponse,
  NotificationPreferences,
  ProfileConfirmRequest,
  ProfileDraftResponse,
  ProfileSummary,
  ProfileVersionListResponse,
  ProfileVersionRequest,
} from "./contracts";
import {
  getCsrfToken,
  jsonDelete,
  jsonPatch,
  jsonPut,
  jsonPost,
  requestJson,
  resetApiCache,
} from "./client";

export async function createProfileDraft(
  label?: string,
): Promise<ProfileDraftResponse> {
  const normalizedLabel = label?.trim();
  return jsonPost<ProfileDraftResponse>(
    "/api/v1/profiles/drafts",
    normalizedLabel ? { label: normalizedLabel } : {},
  );
}

export async function confirmProfileDraft(
  draftId: string,
  body: ProfileConfirmRequest,
): Promise<ProfileSummary> {
  return jsonPost<ProfileSummary>(
    `/api/v1/profiles/drafts/${encodeURIComponent(draftId)}/confirm`,
    body,
  );
}

export async function discardProfileDraft(draftId: string): Promise<void> {
  await jsonDelete<void>(
    `/api/v1/profiles/drafts/${encodeURIComponent(draftId)}`,
  );
}

export async function appendProfileVersion(
  profileId: string,
  body: ProfileVersionRequest,
): Promise<ProfileSummary> {
  return jsonPost<ProfileSummary>(
    `/api/v1/profiles/${encodeURIComponent(profileId)}/versions`,
    body,
  );
}

export async function listProfileVersions(
  profileId: string,
): Promise<ProfileVersionListResponse> {
  await getCsrfToken();
  return requestJson<ProfileVersionListResponse>(
    `/api/v1/profiles/${encodeURIComponent(profileId)}/versions`,
  );
}

export async function listProfiles(): Promise<{ profiles: ProfileSummary[] }> {
  await getCsrfToken();
  return requestJson<{ profiles: ProfileSummary[] }>("/api/v1/profiles");
}

export async function updateProfileDisplayName(
  profileId: string,
  displayName: string,
): Promise<ProfileSummary> {
  return jsonPatch<ProfileSummary>(`/api/v1/profiles/${encodeURIComponent(profileId)}`, {
    display_name: displayName.trim(),
  });
}

export async function getAccount(): Promise<AccountResponse> {
  return requestJson<AccountResponse>("/api/v1/account");
}

export async function exportAccountData(): Promise<AccountExportResponse> {
  return requestJson<AccountExportResponse>("/api/v1/account/export");
}

export async function getAccountClosure(): Promise<AccountClosure | null> {
  return requestJson<AccountClosure | null>("/api/v1/account/closure");
}

export async function requestAccountClosure(): Promise<AccountClosure> {
  return jsonPost<AccountClosure>("/api/v1/account/closure", {});
}

export async function cancelAccountClosure(): Promise<void> {
  await jsonDelete<void>("/api/v1/account/closure");
}

export async function revokeAllSessions(): Promise<void> {
  await jsonPost<void>("/api/v1/auth/sessions/revoke-all", {});
  resetApiCache();
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  return requestJson<NotificationPreferences>(
    "/api/v1/account/notification-preferences",
  );
}

export async function updateNotificationPreferences(
  body: NotificationPreferences,
): Promise<NotificationPreferences> {
  return jsonPut<NotificationPreferences>(
    "/api/v1/account/notification-preferences",
    body,
  );
}

export async function listAccountNotifications(
  options: { readonly unreadOnly?: boolean } = {},
): Promise<AccountNotificationsResponse> {
  await getCsrfToken();
  const query = options.unreadOnly ? "?unread_only=true" : "";
  return requestJson<AccountNotificationsResponse>(
    `/api/v1/account/notifications${query}`,
  );
}

export async function markAccountNotificationRead(
  notificationId: string,
): Promise<AccountNotification> {
  return jsonPost<AccountNotification>(
    `/api/v1/account/notifications/${encodeURIComponent(notificationId)}/read`,
    {},
  );
}

export async function markAllAccountNotificationsRead(): Promise<{
  unread_count: number;
}> {
  return jsonPost<{ unread_count: number }>(
    "/api/v1/account/notifications/read-all",
    {},
  );
}

export async function deleteAccountNotification(notificationId: string): Promise<void> {
  await jsonDelete<void>(
    `/api/v1/account/notifications/${encodeURIComponent(notificationId)}`,
  );
}

export async function listAccountReferrals(): Promise<AccountReferralsResponse> {
  await getCsrfToken();
  return requestJson<AccountReferralsResponse>("/api/v1/account/referrals");
}

export async function listAccountOrders(): Promise<AccountOrdersResponse> {
  await getCsrfToken();
  return requestJson<AccountOrdersResponse>("/api/v1/account/orders");
}

export async function listAccountEntitlements(): Promise<AccountEntitlementsResponse> {
  await getCsrfToken();
  return requestJson<AccountEntitlementsResponse>("/api/v1/account/entitlements");
}

export async function listAccountHistory(): Promise<AccountHistoryResponse> {
  await getCsrfToken();
  return requestJson<AccountHistoryResponse>("/api/v1/account/history");
}

export async function logoutCurrentDevice(): Promise<void> {
  await jsonPost<void>("/api/v1/auth/logout", {});
  resetApiCache();
}

export function formatProfileOption(profile: ProfileSummary): string {
  const displayName = profile.display_name?.trim();
  if (displayName) {
    return displayName;
  }
  return `档案 ${profile.version} · ${new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(profile.created_at))}`;
}
