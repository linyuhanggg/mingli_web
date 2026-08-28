import type { ViewModel } from "@/view-models/registry";

export type Gender = "male" | "female" | "other";
export type TimeBasisPolicy = "civil" | "solar" | "lunar";
export type ZiHourPolicy = "midnight" | "substitute" | "solar";

export type ProfileSummary = {
  profile_id: string;
  profile_version_id: string;
  subject_ref: string;
  version: number;
  display_name?: string | null;
  birth_date?: string | null;
  created_at: string;
};

export type ProfileDraftResponse = {
  draft_id: string;
  status: "draft";
};

export type ProfileConfirmRequest = {
  birth_datetime: string;
  timezone: string;
  location: string;
  gender: Gender;
  time_basis_policy: TimeBasisPolicy;
  zi_hour_policy: ZiHourPolicy;
  longitude?: number | null;
  latitude?: number | null;
  coordinate_source?: string | null;
  subject_type?: "self" | "other";
  is_minor?: boolean;
  authorization_confirmed?: boolean;
  photo_authorization_confirmed?: boolean;
  minor_guardian_confirmed?: boolean;
  on_name_conflict?: "reject" | "save_as" | "overwrite";
};

export type ProfileVersionRequest = ProfileConfirmRequest & {
  subject_type?: "self" | "other";
  is_minor?: boolean;
  authorization_confirmed?: boolean;
  photo_authorization_confirmed?: boolean;
  minor_guardian_confirmed?: boolean;
  difference_acknowledged: boolean;
};

export type ProfileVersionListResponse = {
  versions: ProfileSummary[];
};

export type ReadingStatus =
  | "input_ready"
  | "waiting_input"
  | "prepared"
  | "completing"
  | "accepted"
  | "delayed"
  | "runtime_unknown"
  | "terminal_stopped";

/** Public payment/job projection; internal ReadingJob statuses stay server-only. */
export type DeliveryState =
  | "not_required"
  | "payment_required"
  | "queued"
  | "processing"
  | "waiting_input"
  | "delivered"
  | "delayed"
  | "failed";

export type ReadingHorizon = {
  kind_id: string;
  start: string | null;
  end: string | null;
};

export type PublicTerm = {
  id: string;
  label: string;
  description: string | null;
};

export type NeedInputField = {
  id: string;
  label: string;
  type_id: string;
  description: string | null;
  choices: PublicTerm[];
};

export type NeedInputRequirement = {
  any_of: NeedInputField[];
};

export type NeedInputRequest = {
  requirements: NeedInputRequirement[];
};

export type ReadingVersionSummary = {
  reading_version_id: string;
  reading_root_id: string;
  profile_version_id: string | null;
  capability_id: string;
  product_id?: string | null;
  runtime_capability_ids?: string[];
  version: number;
  status: ReadingStatus;
  object_id: string;
  dimension_ids: string[];
  horizon: ReadingHorizon;
  prior_answer: string | null;
  input_request: NeedInputRequest | null;
  created_at: string;
  delivery_state?: DeliveryState;
  result_available?: boolean;
  poll_required?: boolean;
  poll_after_seconds?: number | null;
  view_model?: ViewModel | null;
};

export type PreviewStartRequest = {
  profile_version_id: string;
  query?: string;
  dimension_ids?: ("overview" | "career")[];
  target_year?: number;
  target_month?: string;
  target_date?: string;
};

export type BaziDeepStartRequest = {
  profile_version_id: string;
  query?: string;
};

export type BaziDeepCheckoutRequest = {
  reading_version_id: string;
};

export type CheckoutGatewayStatus = "unavailable" | "pending" | "succeeded" | "failed";

export type BaziDeepCheckoutResponse = {
  order: {
    order_id: string;
    reading_version_id: string | null;
    product_id: "bazi-deep";
    product_version: string;
    amount_minor: number;
    currency: string;
    status: string;
    created_at: string;
    paid_at: string | null;
  };
  attempt: {
    attempt_id: string;
    channel: string;
    status: string;
    created_at: string;
  };
  gateway_status: CheckoutGatewayStatus;
  redirect_url?: string | null;
  /** Omitted until the backend confirms a Payment for this order. */
  payment_id?: string | null;
  created: boolean;
};

/** A confirmed checkout Payment is bound to the current deep-reading Job by the backend. */
export type FulfillmentBindingRequest = {
  payment_id: string;
};

export type FulfillmentBindingResponse = {
  fulfillment_id: string;
  reading_version_id: string;
  reading_job_id: string;
  status: string;
  created: boolean;
};

export type QimenDeepStartRequest = EventArtStartRequest;

export type LumingNayinStartRequest = PreviewStartRequest;
export type RhythmStartRequest = {
  profile_version_id: string;
  query?: string;
  dimension_ids?: ["state"];
};

export type FiveElementsFactsStartRequest = {
  profile_version_id: string;
  query?: string;
  dimension_ids?: ["state"];
};

export type ChartSimilarityStartRequest = {
  profile_version_ids: [string, string];
  query?: string;
  dimension_ids?: ["state"];
};

export type TimeCheckStartRequest = {
  profile_version_id: string;
  time_range_start: string;
  time_range_end: string;
  known_events?: string[];
  known_event_facts?: Array<{
    event_id: string;
    occurred_at: string;
    domain: "career" | "education" | "finance" | "relationship" | "family" | "location" | "health";
  }>;
  query?: string;
  dimension_ids?: ["time_options"];
};

export type CanwenStartRequest = {
  profile_version_id: string;
  selected_art_ids: ("bazi" | "ziwei" | "qizheng")[];
  query?: string;
  dimension_ids?: ("career" | "health" | "location" | "outcome" | "relationship" | "state" | "timing")[];
};

export type HecanStartRequest = {
  profile_version_id: string;
  selected_art_ids: ("bazi" | "ziwei" | "qizheng")[];
  dimension_ids?: ("career" | "health" | "location" | "outcome" | "relationship" | "state" | "timing")[];
};

export type RelationshipStartRequest = {
  profile_version_ids: [string, string];
  relationship_type:
    | "romantic"
    | "married"
    | "parent_child"
    | "business"
    | "work"
    | "friend";
  dimension_ids?: ["relationship"];
};

export type EventArtStartRequest = {
  event_datetime: string;
  timezone: string;
  location: string;
  subject_ref?: string;
  query?: string;
  dimension_ids?: (
    | "career"
    | "location"
    | "money"
    | "outcome"
    | "relationship"
    | "state"
    | "timing"
    | "work"
  )[];
  time_basis_policy?:
    | "civil"
    | "solar"
    | "longitude_mean_solar-v1"
    | "local_apparent_solar-v1";
  zi_hour_policy?: "midnight" | "substitute" | "solar";
  longitude?: number | null;
  latitude?: number | null;
  coordinate_source?: string | null;
};

export type DaliurenStartRequest = EventArtStartRequest & {
  timing_start?: string;
  timing_end?: string;
};

export type TaiyiStartRequest = Omit<EventArtStartRequest, "dimension_ids"> & {
  dimension_ids?: ("location" | "outcome" | "state" | "timing")[];
};

export type SelectionStartRequest = {
  event_profile: string;
  requested_actions?: string[];
  date_range_start: string;
  date_range_end: string;
  requested_scopes?: "directional_judgment"[];
  hard_constraints?: Record<string, unknown>;
  participant_facts?: Record<string, unknown>[];
  directional_context?: Record<string, string> | null;
  include_folk_comparison?: boolean;
  timezone: string;
  location: string;
  subject_ref?: string;
  query?: string;
  dimension_ids?: ("location" | "state" | "timing")[];
  longitude?: number | null;
  latitude?: number | null;
  coordinate_source?: string | null;
};

export type FengshuiStartRequest = {
  fengshui_spec: Record<string, unknown>;
  subject_ref?: string;
  query?: string;
  dimension_ids?: ("current_state" | "direction" | "location" | "state")[];
};

export type MeihuaCastingMethod =
  | "time"
  | "supplied_number"
  | "sound_count"
  | "observation"
  | "supplied_hexagram";

export type MeihuaTrigram = "乾" | "兑" | "离" | "震" | "巽" | "坎" | "艮" | "坤";

export type MeihuaStartRequest = {
  casting_method?: MeihuaCastingMethod;
  event_datetime: string;
  timezone: string;
  location: string;
  subject_ref?: string;
  query?: string;
  dimension_ids?: ("outcome" | "state")[];
  time_basis_policy?:
    | "civil"
    | "solar"
    | "longitude_mean_solar-v1"
    | "local_apparent_solar-v1";
  zi_hour_policy?: "midnight" | "substitute" | "solar";
  longitude?: number | null;
  latitude?: number | null;
  coordinate_source?: string | null;
  number?: number;
  count?: number;
  upper_trigram?: MeihuaTrigram;
  lower_trigram?: MeihuaTrigram;
  moving_line?: number;
  provenance?: Record<string, unknown>;
  observation_source?: Record<string, unknown>;
};

export type PhysiognomyMediaResponse = {
  asset_id: string;
  content_type: "image/jpeg" | "image/png" | "image/heic";
  byte_size: number;
  width: number;
  height: number;
  mode: "face" | "palm" | "posture" | "combined";
  status: "ready" | "deleted" | "expired";
  created_at: string;
  expires_at: string;
};

export type PhysiognomyObservationInput = {
  region: string;
  feature_kind: "visible_morphology";
  descriptor: string;
  visibility: "full" | "partial";
  uncertainty?: number;
  occlusion?: number;
};

export type PhysiognomyStartRequest = {
  asset_id: string;
  subject_ref: string;
  query?: string;
  dimension_ids?: ("state" | "source_comparison")[];
  observations: PhysiognomyObservationInput[];
};

export type FortuneStartRequest = {
  profile_version_id: string;
  query?: string;
};

export type LiuyaoStartRequest = {
  cast: "digital_coin" | [number, number, number, number, number, number];
  event_datetime: string;
  timezone: string;
  location: string;
  subject_ref?: string;
  query?: string;
  dimension_ids?: ("career" | "outcome" | "state" | "timing")[];
};

export type LiuyaoDeepStartRequest = LiuyaoStartRequest;

export type WenshiStartRequest = {
  cast: "digital_coin" | [number, number, number, number, number, number];
  event_datetime: string;
  timezone: string;
  location: string;
  subject_ref?: string;
  query?: string;
  dimension_ids?: ("outcome" | "timing")[];
  time_basis_policy?:
    | "civil"
    | "solar"
    | "longitude_mean_solar-v1"
    | "local_apparent_solar-v1";
  zi_hour_policy?: "midnight" | "substitute" | "solar";
  longitude?: number | null;
  latitude?: number | null;
  coordinate_source?: string | null;
};

export type RecastProfileRequest = {
  action: "profile_preview" | "today" | "week";
  profile_version_id: string;
  query?: string;
  dimension_ids?: ("overview" | "career")[];
};

export type RecastLiuyaoRequest = {
  action: "liuyao_one_question";
  cast: "digital_coin" | [number, number, number, number, number, number];
  event_datetime: string;
  timezone: string;
  location: string;
  subject_ref?: string;
  query?: string;
  dimension_ids?: ("career" | "outcome" | "timing")[];
};

export type RecastRequest = RecastProfileRequest | RecastLiuyaoRequest;

export type ReadingFact = {
  ref: string;
  subject_ref: string;
  kind_id: string;
  value: unknown;
  display_text: string;
};

export type VerifiedExactCitation = {
  source_title: string;
  locator: string;
  verbatim_excerpt: string;
  verification_status: "verified_exact";
};

export type ReadingEvidence = {
  ref: string;
  evidence_ref?: string;
  rule_id?: string;
  source_title: string;
  locator: string | null;
  excerpt: string | null;
  verification_status?: "verified_exact";
  verbatim_excerpt?: string;
  verbatim_citations?: VerifiedExactCitation[];
  supports_fact_refs: string[];
};

export type ReadingLimit = {
  kind_id: string;
  public_text: string;
  scope_refs: string[];
  detail_ids: string[];
};

export type ReadingRequestView = {
  subject_refs: string[];
  capability_ids: string[];
  object_id: string;
  dimension_ids: string[];
  horizon: ReadingHorizon;
};

export type ReadingFactPanel = {
  question: string;
  vocabulary: PublicTerm[];
  facts: ReadingFact[];
  evidence: ReadingEvidence[];
  findings: unknown[];
  claim_scopes: unknown[];
  limits: ReadingLimit[];
  prior_answer: string | null;
  request_view: ReadingRequestView | null;
};

export type VerificationOutcome =
  | "accepted"
  | "partial"
  | "disagreed"
  | "unknown";

export type ReadingVerificationSummary = {
  verification_id: string;
  reading_version_id: string;
  outcome: VerificationOutcome;
  note: string | null;
  created_at: string;
};

export type CapabilityProjection = {
  capability_id: string;
  label: string;
  tier: "A" | "B" | "C";
  source_system: string | null;
  runtime_active_rule_count: number;
  judgment_rule_count: number;
  source_status: "available" | "unavailable";
  user_decision_pending?: boolean;
};

export type CapabilityProjectionResponse = {
  runtime_release_profile: string;
  source_status: "available" | "unavailable";
  capabilities: CapabilityProjection[];
};

export type TimeLayerCapabilityItemResponse = {
  layer_id: string;
  label: string;
  available: boolean;
  unavailable_reason: string | null;
};

export type TimeLayerEntitlementLayerResponse = {
  layer_id:
    | "life"
    | "luck_cycles"
    | "major_limits"
    | "year"
    | "month"
    | "day"
    | "hour";
  tier: "free" | "paid";
  access:
    | "readable"
    | "locked_paywall"
    | "fail_closed_unknown"
    | "unavailable";
  upgrade_cta: "professional_info" | null;
};

export type TimeLayerEntitlementResponse = {
  schema_version: "time-layer-entitlement/v1";
  capability_id: "bazi" | "ziwei";
  resolution:
    | "granted"
    | "denied"
    | "unknown"
    | "unauthenticated"
    | "request_failed";
  free_boundary_layer_id: "year";
  paid_layer_ids: ["month", "day", "hour"];
  free_year_set: number[];
  capability: { time_layers: TimeLayerCapabilityItemResponse[] };
  layers: TimeLayerEntitlementLayerResponse[];
};

export type ReadingResultResponse = {
  reading_version_id: string;
  status: ReadingStatus;
  accepted_copy: string | null;
  fact_panel: ReadingFactPanel | null;
  view_model?: import("@/view-models/registry").ViewModel | null;
  capability?: CapabilityProjection | null;
  verification: ReadingVerificationSummary | null;
  input_request: NeedInputRequest | null;
  document: ReadingDocumentV1 | null;
  result_available?: boolean;
  poll_required?: boolean;
  poll_after_seconds?: number | null;
  time_layer_entitlement?: TimeLayerEntitlementResponse | null;
};

export type ReadingDocumentV1 = {
  schema_version: "reading-document/v1";
  document_id: string;
  reading_version_id: string;
  accepted_copy_ref: string;
  product_version: string;
  presentation_contract_version: string;
  view_model: ViewModel;
  answer_summary: string;
  subject_summaries: { subject_ref: string; label: string }[];
  themes: { theme_id: string; label: string }[];
  claims: {
    claim_id: string;
    section_id: string;
    text: string;
    subject_ref: string;
    dimension_id: string;
    claim_kind_id: string;
    certainty_id: string;
    fact_refs: string[];
    finding_refs: string[];
    evidence_refs: string[];
    limit_refs: string[];
    verification: { enabled: boolean };
  }[];
  evidence: {
    evidence_ref: string;
    title: string;
    supports_fact_refs: string[];
  }[];
  boundaries: { limit_ref: string; text: string }[];
  actions: {
    correction: { enabled: boolean };
    follow_up: { enabled: boolean };
    export: { enabled: boolean };
    share: { enabled: boolean };
  };
  versions: {
    runtime_release: string;
    view_model_schema: string;
    reading_document_schema: "reading-document/v1";
  };
};

export type ReadingShareDocument = {
  schema_version: "shared-reading-document/v1";
  document_id: string;
  reading_version_id: string;
  accepted_copy_ref: string;
  product_version: string;
  presentation_contract_version: string;
  answer_summary: string;
  themes: { theme_id: string; label: string }[];
  claims: { claim_id: string; text: string }[];
  evidence: { evidence_ref: string; title: string }[];
  boundaries: { limit_ref: string; text: string }[];
  versions: {
    runtime_release: string;
    view_model_schema: string;
    reading_document_schema: "reading-document/v1";
  };
};

export type ReadingShareResponse = {
  document: ReadingShareDocument;
};

export type ReadingShareCreateResponse = {
  snapshot_id: string;
  token: string;
  expires_at: string;
};

export type ReadingExportFormat = "png" | "pdf";

export type ReadingExportCreateResponse = {
  export_id: string;
  token: string;
  format: ReadingExportFormat;
  content_type: string;
  file_name: string;
  expires_at: string;
};

export type ReadingListResponse = {
  readings: ReadingVersionSummary[];
};

export type AccountHistoryVersionSummary = {
  reading_version_id: string;
  reading_root_id: string;
  capability_id: string;
  version: number;
  status: ReadingStatus;
  object_id: string;
  dimension_ids: string[];
  horizon: ReadingHorizon;
  created_at: string;
};

export type AccountHistoryRootResponse = {
  reading_root_id: string;
  profile_version_id: string | null;
  capability_id: string;
  created_at: string;
  versions: AccountHistoryVersionSummary[];
};

export type AccountHistoryResponse = {
  roots: AccountHistoryRootResponse[];
};

export type LoginIdentitySummary = {
  id: string;
  provider: "phone" | "email";
  masked_destination: string;
  verified_at: string;
};

export type AccountResponse = {
  user_id: string;
  identities: LoginIdentitySummary[];
};

export type AccountClosure = {
  closure_id: string;
  user_id: string;
  status: string;
  requested_at: string;
  cancel_until: string;
  cancelled_at: string | null;
  executed_at: string | null;
};

export type AccountExportResponse = {
  generated_at: string;
  user_id: string;
  payload: Record<string, unknown>;
};

export type NotificationPreferences = {
  in_app_enabled: boolean;
  email_enabled: boolean;
  sms_enabled: boolean;
};

export type AccountNotification = {
  id: string;
  title: string;
  summary: string;
  available_at: string;
  read_at: string | null;
  target_href: string | null;
};

export type AccountNotificationsResponse = {
  notifications: AccountNotification[];
  unread_count: number;
};

export type AccountReferralReward = {
  status: string;
  occurred_at: string;
};

export type AccountReferralCampaign = {
  campaign_key: string;
  version: string;
  state: string;
  starts_at: string;
  ends_at: string | null;
  per_inviter_limit: number;
  codes: string[];
  invited_count: number;
  my_attribution_stage: string | null;
  rewards: AccountReferralReward[];
};

export type AccountReferralsResponse = {
  campaigns: AccountReferralCampaign[];
};

export type ReferralPublicResponse = {
  code: string;
  campaign_key: string;
  version: string;
  status: "planned" | "active" | "paused" | "full" | "ended";
  starts_at: string;
  ends_at: string | null;
  per_inviter_limit: number;
  attribution_recorded: boolean;
  self_invite: boolean;
};

export type ReferralAttributionCaptureResponse = {
  status: "recorded";
};

export type AccountOrder = {
  order_id: string;
  product_label: string;
  amount_minor: number;
  currency: string;
  status: string;
  fulfillment_status: string | null;
  created_at: string;
  paid_at: string | null;
};

export type AccountOrdersResponse = {
  orders: AccountOrder[];
};

export type AccountEntitlementEvent = {
  kind: "GRANT" | "RESERVE" | "CONSUME" | "RELEASE" | "REVERSE" | "EXPIRE";
  quantity: number;
  occurred_at: string;
};

export type AccountEntitlement = {
  label: string;
  granted: number;
  reserved: number;
  consumed: number;
  released: number;
  reversed: number;
  expired: number;
  available: number;
  events: AccountEntitlementEvent[];
};

export type AccountEntitlementsResponse = {
  entitlements: AccountEntitlement[];
};

export type AuthSessionResponse = {
  user_id: string;
  session_id: string;
  expires_at: string;
  csrf_token: string;
};

export type ContentPublicItem = {
  content_key: string;
  locale: string;
  revision: number;
  title: string | null;
  summary: string | null;
  topic: string | null;
  source_title: string | null;
  source_url: string | null;
  body: string;
  created_at: string;
};

export type ContentPublicResponse = {
  items: ContentPublicItem[];
};
