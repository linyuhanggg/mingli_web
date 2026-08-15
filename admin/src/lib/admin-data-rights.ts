export type AdminClosure = {
  closure_id: string;
  user_id: string;
  status: string;
  requested_at: string;
  cancel_until: string;
  cancelled_at: string | null;
  executed_at: string | null;
};

export type AdminClosuresResponse = {
  closures: readonly AdminClosure[];
};
