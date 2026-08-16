export type AdminReading = {
  reading_version_id: string;
  reading_root_id: string;
  capability_id: string;
  product_id: string | null;
  version: number;
  status: string;
  dimension_count: number;
  created_at: string;
};

export type AdminReadingsResponse = {
  readings: readonly AdminReading[];
};

export type AdminReadingDetail = AdminReading & {
  job_count: number;
  verification_event_count: number;
  document_available: boolean;
  document_view_model_schema: string | null;
  physiognomy_source_summary: {
    source_count: number;
    disagreement_count: number;
    disagreements_retained: boolean;
    forced_resolution: boolean;
    active_rule_count: number;
  } | null;
  time_check_summary: {
    candidate_count: number;
    known_event_count: number;
    event_input_status: "not_supplied" | "invalid_structured_events" | "structured_valid";
    ranking_status: "not_ranked" | "candidate_evidence_ranked";
    event_matching_status: "not_calculated" | "structured_evidence";
    ranked_candidate_count: number;
    event_match_count: number;
  } | null;
};
