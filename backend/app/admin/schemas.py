"""Admin API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

StaffRole = Literal["support", "finance", "ops", "superadmin"]


class AdminLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class AdminSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    staff_id: UUID
    session_id: UUID
    role: StaffRole
    display_name: str
    expires_at: datetime
    csrf_token: str


class AdminMeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    staff_id: UUID
    role: StaffRole
    email: EmailStr
    display_name: str
    session_id: UUID
    expires_at: datetime


class AdminKpi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    value: int = Field(ge=0)
    is_stub: bool


class AdminQueueSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    count: int = Field(ge=0)
    is_stub: bool


class AdminOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    is_stub: bool
    kpis: list[AdminKpi]
    queues: list[AdminQueueSummary]


class AdminReadingJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    reading_version_id: UUID
    reading_root_id: UUID
    reading_version: int = Field(ge=1)
    capability_id: str
    product_id: str | None = None
    reading_status: str
    job_status: str
    language: str
    narrative_policy_version: str
    max_attempts: int = Field(ge=1)
    available_at: datetime
    lease_generation: int = Field(ge=0)
    created_at: datetime


class AdminReadingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_version_id: UUID
    reading_root_id: UUID
    capability_id: str
    product_id: str | None = None
    version: int = Field(ge=1)
    status: str
    dimension_count: int = Field(ge=0)
    created_at: datetime


class AdminReadingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    readings: list[AdminReadingResponse]


class AdminPhysiognomySourceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_count: int = Field(ge=0)
    disagreement_count: int = Field(ge=0)
    disagreements_retained: bool
    forced_resolution: bool
    active_rule_count: int = Field(ge=0)


class AdminTimeCheckSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_count: int = Field(ge=0)
    known_event_count: int = Field(ge=0)
    event_input_status: Literal[
        "not_supplied",
        "invalid_structured_events",
        "structured_valid",
    ]
    ranking_status: Literal["not_ranked", "candidate_evidence_ranked"]
    event_matching_status: Literal["not_calculated", "structured_evidence"]
    ranked_candidate_count: int = Field(ge=0)
    event_match_count: int = Field(ge=0)


class AdminReadingDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_version_id: UUID
    reading_root_id: UUID
    capability_id: str
    product_id: str | None = None
    version: int = Field(ge=1)
    status: str
    dimension_count: int = Field(ge=0)
    job_count: int = Field(ge=0)
    verification_event_count: int = Field(ge=0)
    document_available: bool
    document_view_model_schema: str | None = None
    physiognomy_source_summary: AdminPhysiognomySourceSummary | None = None
    time_check_summary: AdminTimeCheckSummary | None = None
    created_at: datetime


class AdminRuntimeReleaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    version: str
    source_commit: str
    protocol_version: str
    production_ready: bool
    created_at: datetime


class AdminRuntimeReleasesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    releases: list[AdminRuntimeReleaseResponse]


class AdminCapabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    label: str
    release_state: Literal["PUBLIC", "INTERNAL_TEST"]
    audience: Literal["P0 产品", "内部 Provider"]
    product_actions: list[str]


class AdminCapabilitiesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: Literal["local", "test", "staging", "production"]
    runtime_adapter: Literal["fake", "one-shot"]
    runtime_health: Literal["unverified"]
    production_ready: bool
    capabilities: list[AdminCapabilityResponse]


AdminSupportCaseCategory = Literal[
    "account",
    "delivery",
    "billing",
    "reading",
    "referral",
    "profile_correction",
    "algorithm_review",
    "after_sales",
    "compensation",
    "other",
]
AdminSupportCaseStatus = Literal["open", "in_review", "resolved", "rejected"]


class AdminSupportCaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_user_id: UUID | None = None
    subject_ref: str = Field(min_length=1, max_length=180)
    category: AdminSupportCaseCategory
    summary: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=500)


class AdminSupportCaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    owner_user_id: UUID | None
    subject_ref: str
    category: AdminSupportCaseCategory
    summary: str
    status: AdminSupportCaseStatus
    created_by_staff_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class AdminSupportCasesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: list[AdminSupportCaseResponse]


class AdminModelProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation_attempt_id: UUID
    reading_version_id: UUID
    attempt_number: int = Field(ge=1)
    model_profile_id: str
    provider: str
    provider_model_version: str | None
    outcome: Literal["succeeded", "failed"]
    error_code: str | None
    narrative_policy_version: str
    output_contract_id: str
    latency_ms: int = Field(ge=0)
    usage_known: bool
    cost_known: bool
    guard_error_count: int = Field(ge=0)
    created_at: datetime


class AdminModelProfilesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profiles: list[AdminModelProfileResponse]


class AdminReadingJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[AdminReadingJobResponse]


class AdminVerificationEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    source: Literal["reading", "claim", "feedback"]
    reading_version_id: UUID
    claim_id: str | None
    outcome: str
    actor_ref: str
    created_at: datetime


class AdminVerificationEventsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[AdminVerificationEventResponse]


class AdminStaffStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "suspended"]
    reason: str = Field(min_length=1, max_length=500)


class AdminStaffRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: StaffRole
    reason: str = Field(min_length=1, max_length=500)


class AdminStaffPasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=8, max_length=200)
    reason: str = Field(min_length=1, max_length=500)


class AdminStaffCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: StaffRole
    password: str = Field(
        min_length=8,
        max_length=200,
        json_schema_extra={"writeOnly": True},
    )
    reason: str = Field(min_length=1, max_length=500)


class AdminStaffResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: EmailStr
    display_name: str
    role: StaffRole
    status: Literal["active", "suspended"]
    created_at: datetime
    last_login_at: datetime | None
    unrevoked_session_count: int = Field(ge=0)


class AdminStaffListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    staff: list[AdminStaffResponse]


class AdminSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: Literal["local", "test", "staging", "production"]
    cookie_secure: bool
    otp_adapter: Literal["fake", "disabled", "smtp"]
    runtime_adapter: Literal["fake", "one-shot"]
    admin_session_hours: int = Field(ge=1, le=24)
    dogfood_entitlement_gates_enabled: bool
    real_traffic_enabled: bool
    alert_sink_enabled: bool


class AdminUserIdentityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    provider: str
    masked_destination: str
    destination: str | None
    status: str
    verified_at: datetime
    created_at: datetime


class AdminUserConsentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    policy_key: str
    policy_version: str
    context: str
    accepted_at: datetime


class AdminUserSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: Literal["active", "expired", "revoked"]
    expires_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class AdminUserSubjectSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    label: str | None
    status: str
    created_at: datetime
    version_count: int = Field(ge=0)
    latest_version: int | None


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: str
    created_at: datetime
    identity_count: int = Field(ge=0)
    consent_count: int = Field(ge=0)
    subject_count: int = Field(ge=0)
    active_session_count: int = Field(ge=0)


class AdminUsersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    users: list[AdminUserSummary]


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: str
    created_at: datetime
    identities: list[AdminUserIdentityResponse]
    consents: list[AdminUserConsentResponse]
    sessions: list[AdminUserSessionResponse]
    subjects: list[AdminUserSubjectSummary]


class AdminSubjectSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    owner_user_id: UUID | None
    label: str | None
    status: str
    created_at: datetime
    version_count: int = Field(ge=0)
    latest_version: int | None


class AdminSubjectAuthorizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_type: str
    is_minor: bool
    authorization_confirmed: bool
    photo_authorization_confirmed: bool
    minor_guardian_confirmed: bool
    difference_acknowledged: bool


class AdminSubjectProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    birth_datetime: str
    timezone: str
    location: str
    gender: Literal["male", "female", "other"]
    time_basis_policy: Literal["civil", "solar", "lunar"]
    zi_hour_policy: Literal["midnight", "substitute", "solar"]
    longitude: float | None
    latitude: float | None
    coordinate_source: str | None


class AdminSubjectVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    version: int
    created_at: datetime
    authorization: AdminSubjectAuthorizationResponse | None
    profile: AdminSubjectProfileResponse


class AdminSubjectsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subjects: list[AdminSubjectSummary]


class AdminSubjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    owner_user_id: UUID | None
    label: str | None
    status: str
    created_at: datetime
    versions: list[AdminSubjectVersionResponse]


class AdminReferralCampaignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    campaign_key: str
    version: str
    state: str
    starts_at: datetime
    ends_at: datetime | None
    total_limit: int | None
    per_inviter_limit: int
    reward_quantity: int
    reward_window_seconds: int
    code_count: int = Field(ge=0)
    temporary_attribution_count: int = Field(ge=0)
    attribution_count: int = Field(ge=0)
    reservation_count: int = Field(ge=0)
    created_at: datetime


class AdminReferralCampaignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_key: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    starts_at: datetime
    ends_at: datetime | None = None
    total_limit: int = Field(ge=1)
    per_inviter_limit: int = Field(default=10, ge=1)
    reward_quantity: int = Field(default=1, ge=1)
    reward_window_seconds: int = Field(default=90 * 86400, ge=1)
    reason: str = Field(min_length=1, max_length=500)


class AdminReferralCampaignStateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["draft", "scheduled", "active", "paused", "ended"]
    reason: str = Field(min_length=1, max_length=500)


class AdminReferralCodeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    campaign_version_id: UUID
    code: str
    inviter_user_id: UUID
    status: str
    created_at: datetime


class AdminReferralCodeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=120)
    inviter_user_id: UUID
    reason: str = Field(min_length=1, max_length=500)


class AdminReferralAttributionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    campaign_version_id: UUID
    code_id: UUID
    referred_user_id: UUID
    inviter_user_id: UUID
    locked_at: datetime
    status: str


class AdminReferralRewardSlotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    campaign_version_id: UUID
    product_version_id: UUID
    slot_key: str
    enabled: bool
    total_limit: int = Field(ge=1)
    quantity: int = Field(ge=1)
    created_at: datetime


class AdminReferralRewardSlotCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_version_id: UUID
    slot: Literal["inviter_reward", "invitee_reward"]
    enabled: bool = True
    total_limit: int = Field(ge=1)
    quantity: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class AdminReferralRewardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    campaign_version_id: UUID
    attribution_id: UUID
    referred_user_id: UUID
    inviter_user_id: UUID
    product_version_id: UUID | None
    payment_attempt_id: UUID | None
    quantity: int
    status: str
    reserved_at: datetime
    committed_at: datetime | None


class AdminReferralsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaigns: list[AdminReferralCampaignResponse]


class AdminReferralResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign: AdminReferralCampaignResponse
    codes: list[AdminReferralCodeResponse]
    attributions: list[AdminReferralAttributionResponse]
    slots: list[AdminReferralRewardSlotResponse]
    rewards: list[AdminReferralRewardResponse]


class AdminReferralAppealCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribution_id: UUID
    reason: str = Field(min_length=1, max_length=1000)


class AdminReferralRiskSignalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_type: Literal["ip_overlap", "device_overlap", "address_overlap", "other"]
    severity: Literal["low", "medium", "high"]
    reason: str = Field(min_length=1, max_length=500)


class AdminReferralAppealDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["accept", "reject", "correction"]
    reason: str = Field(min_length=1, max_length=500)


class AdminReferralRiskSignalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    signal_type: str
    severity: str
    reason: str
    created_by_staff_user_id: UUID | None
    created_at: datetime


class AdminReferralAppealApprovalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    staff_user_id: UUID
    reason: str
    created_at: datetime


class AdminReferralAppealResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    attribution_id: UUID
    requester_user_id: UUID
    inviter_user_id: UUID
    status: str
    reason: str
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None
    approval_count: int = Field(ge=0)
    risk_signals: list[AdminReferralRiskSignalResponse]
    approvals: list[AdminReferralAppealApprovalResponse]
    correction_event_id: UUID | None
    correction_event_kind: str | None
    participation_restriction_user_ids: list[UUID]


class AdminReferralAppealsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    appeals: list[AdminReferralAppealResponse]
