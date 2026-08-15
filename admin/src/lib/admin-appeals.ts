export type AdminReferralAppealStatus =
  | "submitted"
  | "accepted"
  | "rejected"
  | "correction_pending"
  | "corrected";

export type AdminReferralRiskSignal = {
  id: string;
  signal_type: string;
  severity: string;
  reason: string;
  created_by_staff_user_id: string | null;
  created_at: string;
};

export type AdminReferralAppealApproval = {
  id: string;
  staff_user_id: string;
  reason: string;
  created_at: string;
};

export type AdminReferralAppeal = {
  id: string;
  attribution_id: string;
  requester_user_id: string;
  inviter_user_id: string;
  status: AdminReferralAppealStatus;
  reason: string;
  decision_reason: string | null;
  created_at: string;
  decided_at: string | null;
  approval_count: number;
  risk_signals: readonly AdminReferralRiskSignal[];
  approvals: readonly AdminReferralAppealApproval[];
  correction_event_id: string | null;
  correction_event_kind: string | null;
  participation_restriction_user_ids: readonly string[];
};

export type AdminReferralAppealsResponse = {
  appeals: readonly AdminReferralAppeal[];
};
