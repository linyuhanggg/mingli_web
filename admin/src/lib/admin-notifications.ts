export type AdminNotification = {
  id: string;
  owner_user_id: string;
  kind: string;
  dedupe_key: string;
  channel: string | null;
  status: "pending" | "processing" | "sent" | "failed";
  available_at: string;
  attempt_count: number;
  processing_until: string | null;
  sent_at: string | null;
  last_error: string | null;
};

export type AdminNotificationsResponse = {
  notifications: readonly AdminNotification[];
};
