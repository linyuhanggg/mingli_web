from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import uuid4


class ContentError(ValueError):
    """A content transition or permission is invalid."""


class ContentState(StrEnum):
    DRAFT = "draft"
    PREVIEW = "preview"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class ContentRevision:
    revision_id: str
    key: str
    body: str
    author: str
    revision: int
    state: ContentState
    created_at: datetime
    publish_at: datetime | None = None
    withdrawn_reason: str | None = None


class ContentWorkflow:
    def __init__(self, *, now: datetime, editor_role: str) -> None:
        self.now = now
        self.editor_role = editor_role
        self._revisions: dict[str, ContentRevision] = {}
        self._by_key: dict[str, list[str]] = {}

    def _require_editor(self) -> None:
        if self.editor_role not in {"ops", "superadmin"}:
            raise ContentError("editor role is required")

    def create(self, *, key: str, body: str, author: str) -> ContentRevision:
        self._require_editor()
        if not key or not body.strip():
            raise ContentError("content key and body are required")
        revision = len(self._by_key.get(key, [])) + 1
        item = ContentRevision(
            revision_id=uuid4().hex,
            key=key,
            body=body,
            author=author,
            revision=revision,
            state=ContentState.DRAFT,
            created_at=self.now,
        )
        self._revisions[item.revision_id] = item
        self._by_key.setdefault(key, []).append(item.revision_id)
        return item

    def get(self, revision_id: str) -> ContentRevision:
        try:
            return self._revisions[revision_id]
        except KeyError as error:
            raise ContentError("content revision not found") from error

    def edit(self, revision_id: str, *, body: str) -> ContentRevision:
        self._require_editor()
        item = self.get(revision_id)
        if item.state is not ContentState.DRAFT:
            raise ContentError("published revision is immutable")
        if not body.strip():
            raise ContentError("content body is required")
        item = replace(item, body=body)
        self._revisions[revision_id] = item
        return item

    def preview(self, revision_id: str) -> ContentRevision:
        self._require_editor()
        item = self.get(revision_id)
        if item.state is not ContentState.DRAFT:
            raise ContentError("only draft content can enter preview")
        item = replace(item, state=ContentState.PREVIEW)
        self._revisions[revision_id] = item
        return item

    def schedule(self, revision_id: str, *, at: datetime) -> ContentRevision:
        self._require_editor()
        item = self.get(revision_id)
        if item.state not in {ContentState.DRAFT, ContentState.PREVIEW}:
            raise ContentError("only draft or preview content can be scheduled")
        if at <= self.now:
            raise ContentError("scheduled publish time must be in the future")
        item = replace(item, state=ContentState.SCHEDULED, publish_at=at)
        self._revisions[revision_id] = item
        return item

    def publish(self, revision_id: str) -> ContentRevision:
        self._require_editor()
        item = self.get(revision_id)
        if item.state not in {ContentState.DRAFT, ContentState.PREVIEW} and not (
            item.state is ContentState.SCHEDULED and item.publish_at and item.publish_at <= self.now
        ):
            raise ContentError("content is not ready to publish")
        item = replace(item, state=ContentState.PUBLISHED, publish_at=None)
        self._revisions[revision_id] = item
        return item

    def withdraw(self, revision_id: str, *, reason: str) -> ContentRevision:
        self._require_editor()
        item = self.get(revision_id)
        if item.state is not ContentState.PUBLISHED:
            raise ContentError("only published content can be withdrawn")
        if not reason.strip():
            raise ContentError("withdraw reason is required")
        item = replace(item, state=ContentState.WITHDRAWN, withdrawn_reason=reason)
        self._revisions[revision_id] = item
        return item

    def archive(self, revision_id: str) -> ContentRevision:
        self._require_editor()
        item = self.get(revision_id)
        if item.state not in {ContentState.DRAFT, ContentState.WITHDRAWN}:
            raise ContentError("only draft or withdrawn content can be archived")
        item = replace(item, state=ContentState.ARCHIVED)
        self._revisions[revision_id] = item
        return item

    def restore(self, revision_id: str, *, author: str) -> ContentRevision:
        source = self.get(revision_id)
        if source.state is not ContentState.WITHDRAWN:
            raise ContentError("only withdrawn content can be restored")
        return self.create(key=source.key, body=source.body, author=author)

    def history(self, key: str) -> list[ContentRevision]:
        return sorted(
            (self._revisions[revision_id] for revision_id in self._by_key.get(key, [])),
            key=lambda item: item.revision,
            reverse=True,
        )

    def current(self, key: str) -> ContentRevision:
        for item in self.history(key):
            if item.state is ContentState.PUBLISHED:
                return item
        raise ContentError("no published content")
