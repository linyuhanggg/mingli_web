from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.content.workflow import ContentState


class ContentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_key: str = Field(min_length=1, max_length=160)
    locale: str = Field(default="zh-CN", min_length=2, max_length=16)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    topic: str | None = Field(default=None, min_length=1, max_length=80)
    source_title: str | None = Field(default=None, min_length=1, max_length=240)
    source_url: str | None = Field(default=None, min_length=1, max_length=500)
    body: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=500)


class ContentReasonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class ContentEditRequest(ContentReasonRequest):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    topic: str | None = Field(default=None, min_length=1, max_length=80)
    source_title: str | None = Field(default=None, min_length=1, max_length=240)
    source_url: str | None = Field(default=None, min_length=1, max_length=500)


class ContentScheduleRequest(ContentReasonRequest):
    model_config = ConfigDict(extra="forbid")

    publish_at: datetime


class ContentWithdrawRequest(ContentReasonRequest):
    model_config = ConfigDict(extra="forbid")


class ContentRevisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: UUID
    content_key: str
    locale: str
    revision: int
    state: ContentState
    title: str | None
    summary: str | None
    topic: str | None
    source_title: str | None
    source_url: str | None
    body: str
    author_ref: str
    publish_at: datetime | None
    withdrawn_reason: str | None
    created_at: datetime


class ContentHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revisions: list[ContentRevisionResponse]


class ContentIndexItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: UUID
    content_key: str
    locale: str
    revision: int = Field(ge=1)
    state: ContentState
    title: str | None
    summary: str | None
    topic: str | None
    source_title: str | None
    source_url: str | None
    author_ref: str
    publish_at: datetime | None
    withdrawn_reason: str | None
    created_at: datetime


class ContentIndexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revisions: list[ContentIndexItem]


class ContentPublicItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_key: str
    locale: str
    revision: int = Field(ge=1)
    title: str | None
    summary: str | None
    topic: str | None
    source_title: str | None
    source_url: str | None
    body: str = Field(min_length=1)
    created_at: datetime


class ContentPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ContentPublicItem]
