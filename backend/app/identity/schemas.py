from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GuestSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active"] = "active"
    expires_at: datetime
    csrf_token: str


class OtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["phone", "email"]
    destination: str = Field(min_length=3, max_length=320)


class OtpChallengeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: UUID
    expires_at: datetime
    retry_after_seconds: int
    development_code: str | None = None


class OtpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: UUID
    code: str = Field(pattern=r"^[0-9]{6}$")


class PasswordLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["phone", "email"]
    destination: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class PasswordRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: UUID
    code: str = Field(pattern=r"^[0-9]{6}$")
    password: str = Field(min_length=8, max_length=256)


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: UUID
    code: str = Field(pattern=r"^[0-9]{6}$")
    password: str = Field(min_length=8, max_length=256)
    policy_version: str = Field(min_length=1, max_length=80)


class SetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=8, max_length=256)


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_key: str = Field(min_length=1, max_length=80)
    policy_version: str = Field(min_length=1, max_length=80)
    context: Literal["registration", "purchase", "reaccept"]


class ConsentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_id: UUID
    policy_key: str
    policy_version: str
    context: Literal["registration", "purchase", "reaccept"]
    accepted_at: datetime


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    session_id: UUID
    expires_at: datetime
    csrf_token: str


class LoginIdentitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    provider: Literal["phone", "email"]
    masked_destination: str
    verified_at: datetime


class AccountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    identities: list[LoginIdentitySummary]
