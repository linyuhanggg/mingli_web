export type AdminSessionStatus = "active" | "expired" | "revoked";

export type AdminSession = {
  id: string;
  staff_user_id: string;
  actor: string;
  status: AdminSessionStatus;
  expires_at: string;
  last_seen_at: string;
  revoked_at: string | null;
  created_at: string;
};

export type AdminSessionsResponse = {
  sessions: readonly AdminSession[];
};
