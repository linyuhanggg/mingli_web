export type AdminVerificationEvent = {
  id: string;
  source: "reading" | "claim" | "feedback";
  reading_version_id: string;
  claim_id: string | null;
  outcome: string;
  actor_ref: string;
  created_at: string;
};

export type AdminVerificationEventsResponse = {
  events: readonly AdminVerificationEvent[];
};
