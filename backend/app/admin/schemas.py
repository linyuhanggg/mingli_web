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
