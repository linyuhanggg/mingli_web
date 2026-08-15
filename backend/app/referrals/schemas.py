"""Referral projections for public invites and private account progress."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountReferralRewardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    occurred_at: datetime


class AccountReferralCampaignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_key: str
    version: str
    state: str
    starts_at: datetime
    ends_at: datetime | None
    per_inviter_limit: int = Field(ge=1)
    codes: list[str]
    invited_count: int = Field(ge=0)
    my_attribution_stage: str | None
    rewards: list[AccountReferralRewardResponse]


class AccountReferralsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaigns: list[AccountReferralCampaignResponse]


class ReferralPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    campaign_key: str
    version: str
    status: str
    starts_at: datetime
    ends_at: datetime | None
    per_inviter_limit: int = Field(ge=1)
    attribution_recorded: bool
    self_invite: bool


class ReferralAttributionCaptureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
