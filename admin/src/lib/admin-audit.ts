export type AdminAuditEvent = {
  id: string;
  action: string;
  actor: string;
  metadata: Readonly<Record<string, string | number | boolean | null>>;
  created_at: string;
};

export type AdminAuditResponse = {
  events: readonly AdminAuditEvent[];
};
