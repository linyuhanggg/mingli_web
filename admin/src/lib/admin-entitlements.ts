export type AdminEntitlementAction = "grant" | "compensate" | "revoke";
export type AdminEntitlementEventKind =
  | "GRANT"
  | "RESERVE"
  | "CONSUME"
  | "RELEASE"
  | "REVERSE"
  | "EXPIRE";

export type AdminEntitlementEvent = {
  id: string;
  owner_user_id: string;
  entitlement_id: string;
  kind: AdminEntitlementEventKind;
  quantity: number;
  source_type: string;
  source_ref: string;
  target_ref: string | null;
  created_at: string;
};

export type AdminEntitlementEventsResponse = {
  events: readonly AdminEntitlementEvent[];
};

export type AdminEntitlementAdjustmentResponse = {
  event: AdminEntitlementEvent;
  created: boolean;
};
