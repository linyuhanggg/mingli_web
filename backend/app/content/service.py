from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.models import ContentRevisionRecord
from app.content.workflow import ContentError, ContentState

_CONTENT_KEY_SINGLETONS = frozenset({"daily", "faq", "notice"})
_CONTENT_KEY_PREFIXES = (
    "home.",
    "page.",
    "notice.",
    "seo.",
    "daily.",
    "tools.",
    "library.",
    "faq.",
    "policy.",
)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class ContentService:
    """Database-backed versioned CMS workflow for staff operations."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        editor_role: str,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.editor_role = editor_role
        self.now = now or datetime.now(UTC)

    def _require_editor(self) -> None:
        if self.editor_role not in {"ops", "superadmin"}:
            raise ContentError("editor role is required")

    @staticmethod
    def _metadata_value(value: str | None, *, label: str) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ContentError(f"{label} cannot be blank")
        return normalized

    @staticmethod
    def _content_key(value: str) -> str:
        normalized = value.strip()
        if normalized in _CONTENT_KEY_SINGLETONS or normalized.startswith(
            _CONTENT_KEY_PREFIXES
        ):
            return normalized
        raise ContentError("unsupported content namespace")

    async def create(
        self,
        *,
        content_key: str,
        locale: str,
        body: str,
        author_ref: str,
        author_staff_user_id: UUID | None,
        title: str | None = None,
        summary: str | None = None,
        topic: str | None = None,
        source_title: str | None = None,
        source_url: str | None = None,
    ) -> ContentRevisionRecord:
        self._require_editor()
        if not content_key.strip() or not locale.strip() or not body.strip():
            raise ContentError("content key, locale and body are required")
        content_key = self._content_key(content_key)
        locale = locale.strip()
        current = await self.session.scalar(
            select(func.max(ContentRevisionRecord.revision)).where(
                ContentRevisionRecord.content_key == content_key,
                ContentRevisionRecord.locale == locale,
            )
        )
        record = ContentRevisionRecord(
            content_key=content_key,
            locale=locale,
            revision=int(current or 0) + 1,
            state=ContentState.DRAFT,
            title=self._metadata_value(title, label="content title"),
            summary=self._metadata_value(summary, label="content summary"),
            topic=self._metadata_value(topic, label="content topic"),
            source_title=self._metadata_value(source_title, label="source title"),
            source_url=self._metadata_value(source_url, label="source URL"),
            body=body,
            author_ref=author_ref,
            author_staff_user_id=author_staff_user_id,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get(self, revision_id: UUID) -> ContentRevisionRecord:
        record = await self.session.get(ContentRevisionRecord, revision_id)
        if record is None:
            raise ContentError("content revision not found")
        return record

    async def edit(
        self,
        revision_id: UUID,
        *,
        body: str,
        metadata: dict[str, str | None] | None = None,
    ) -> ContentRevisionRecord:
        self._require_editor()
        record = await self.get(revision_id)
        if record.state != ContentState.DRAFT:
            raise ContentError("published revision is immutable")
        if not body.strip():
            raise ContentError("content body is required")
        record.body = body
        if metadata:
            for field, value in metadata.items():
                if field not in {"title", "summary", "topic", "source_title", "source_url"}:
                    raise ContentError("unsupported content metadata")
                setattr(record, field, self._metadata_value(value, label=field))
        await self.session.flush()
        return record

    async def preview(self, revision_id: UUID) -> ContentRevisionRecord:
        self._require_editor()
        record = await self.get(revision_id)
        if record.state != ContentState.DRAFT:
            raise ContentError("only draft content can enter preview")
        record.state = ContentState.PREVIEW
        await self.session.flush()
        return record

    async def schedule(
        self,
        revision_id: UUID,
        *,
        publish_at: datetime,
    ) -> ContentRevisionRecord:
        self._require_editor()
        record = await self.get(revision_id)
        if record.state not in {ContentState.DRAFT, ContentState.PREVIEW}:
            raise ContentError("only draft or preview content can be scheduled")
        if _utc(publish_at) <= self.now:
            raise ContentError("scheduled publish time must be in the future")
        record.state = ContentState.SCHEDULED
        record.publish_at = publish_at
        await self.session.flush()
        return record

    async def publish(self, revision_id: UUID) -> ContentRevisionRecord:
        self._require_editor()
        record = await self.get(revision_id)
        if record.state not in {ContentState.DRAFT, ContentState.PREVIEW} and not (
            record.state == ContentState.SCHEDULED
            and record.publish_at is not None
            and _utc(record.publish_at) <= self.now
        ):
            raise ContentError("content is not ready to publish")
        record.state = ContentState.PUBLISHED
        record.publish_at = None
        await self.session.flush()
        return record

    async def withdraw(self, revision_id: UUID, *, reason: str) -> ContentRevisionRecord:
        self._require_editor()
        record = await self.get(revision_id)
        if record.state != ContentState.PUBLISHED:
            raise ContentError("only published content can be withdrawn")
        if not reason.strip():
            raise ContentError("withdraw reason is required")
        record.state = ContentState.WITHDRAWN
        record.withdrawn_reason = reason
        await self.session.flush()
        return record

    async def archive(self, revision_id: UUID) -> ContentRevisionRecord:
        self._require_editor()
        record = await self.get(revision_id)
        if record.state not in {ContentState.DRAFT, ContentState.WITHDRAWN}:
            raise ContentError("only draft or withdrawn content can be archived")
        record.state = ContentState.ARCHIVED
        await self.session.flush()
        return record

    async def restore(
        self,
        revision_id: UUID,
        *,
        author_ref: str,
        author_staff_user_id: UUID | None,
    ) -> ContentRevisionRecord:
        self._require_editor()
        source = await self.get(revision_id)
        if source.state != ContentState.WITHDRAWN:
            raise ContentError("only withdrawn content can be restored")
        return await self.create(
            content_key=source.content_key,
            locale=source.locale,
            body=source.body,
            author_ref=author_ref,
            author_staff_user_id=author_staff_user_id,
            title=source.title,
            summary=source.summary,
            topic=source.topic,
            source_title=source.source_title,
            source_url=source.source_url,
        )

    async def history(
        self,
        *,
        content_key: str,
        locale: str = "zh-CN",
    ) -> list[ContentRevisionRecord]:
        return list(
            await self.session.scalars(
                select(ContentRevisionRecord)
                .where(
                    ContentRevisionRecord.content_key == content_key,
                    ContentRevisionRecord.locale == locale,
                )
                .order_by(ContentRevisionRecord.revision.desc())
            )
        )

    async def index(
        self,
        *,
        prefix: str | None = None,
        locale: str = "zh-CN",
        limit: int = 100,
    ) -> list[ContentRevisionRecord]:
        statement = select(ContentRevisionRecord).where(
            ContentRevisionRecord.locale == locale
        )
        if prefix:
            statement = statement.where(ContentRevisionRecord.content_key.startswith(prefix))
        records = list(
            await self.session.scalars(
                statement.order_by(
                    ContentRevisionRecord.content_key.asc(),
                    ContentRevisionRecord.revision.desc(),
                )
            )
        )
        latest: list[ContentRevisionRecord] = []
        seen_keys: set[str] = set()
        for record in records:
            if record.content_key in seen_keys:
                continue
            seen_keys.add(record.content_key)
            latest.append(record)
            if len(latest) >= limit:
                break
        return latest

    async def current(
        self,
        *,
        content_key: str,
        locale: str = "zh-CN",
    ) -> ContentRevisionRecord:
        record = await self.session.scalar(
            select(ContentRevisionRecord)
            .where(
                ContentRevisionRecord.content_key == content_key,
                ContentRevisionRecord.locale == locale,
                ContentRevisionRecord.state == ContentState.PUBLISHED,
            )
            .order_by(ContentRevisionRecord.revision.desc())
        )
        if record is None:
            raise ContentError("no published content")
        return record

    async def public_index(
        self,
        *,
        prefix: str | None = None,
        locale: str = "zh-CN",
        limit: int = 100,
        query: str | None = None,
        topic: str | None = None,
    ) -> list[ContentRevisionRecord]:
        """Return one current published revision per public content key."""
        statement = select(ContentRevisionRecord).where(
            ContentRevisionRecord.locale == locale,
            ContentRevisionRecord.state == ContentState.PUBLISHED,
        )
        if prefix:
            statement = statement.where(ContentRevisionRecord.content_key.startswith(prefix))
        normalized_query = query.strip() if query else ""
        if normalized_query:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    ContentRevisionRecord.content_key.ilike(pattern),
                    ContentRevisionRecord.title.ilike(pattern),
                    ContentRevisionRecord.summary.ilike(pattern),
                    ContentRevisionRecord.topic.ilike(pattern),
                    ContentRevisionRecord.source_title.ilike(pattern),
                    ContentRevisionRecord.body.ilike(pattern),
                )
            )
        normalized_topic = topic.strip() if topic else ""
        if normalized_topic:
            statement = statement.where(ContentRevisionRecord.topic == normalized_topic)
        records = list(
            await self.session.scalars(
                statement.order_by(
                    ContentRevisionRecord.content_key.asc(),
                    ContentRevisionRecord.revision.desc(),
                )
            )
        )
        latest: list[ContentRevisionRecord] = []
        seen_keys: set[str] = set()
        for record in records:
            if record.content_key in seen_keys:
                continue
            seen_keys.add(record.content_key)
            latest.append(record)
            if len(latest) >= limit:
                break
        return latest
