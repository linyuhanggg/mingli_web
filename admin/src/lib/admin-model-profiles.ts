export type AdminModelProfile = {
  generation_attempt_id: string;
  reading_version_id: string;
  attempt_number: number;
  model_profile_id: string;
  provider: string;
  provider_model_version: string | null;
  outcome: "succeeded" | "failed";
  error_code: string | null;
  narrative_policy_version: string;
  output_contract_id: string;
  latency_ms: number;
  usage_known: boolean;
  cost_known: boolean;
  guard_error_count: number;
  created_at: string;
};

export type AdminModelProfilesResponse = {
  profiles: readonly AdminModelProfile[];
};
