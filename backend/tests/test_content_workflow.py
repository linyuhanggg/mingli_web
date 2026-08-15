from datetime import UTC, datetime, timedelta

import pytest
from app.content.workflow import ContentError, ContentState, ContentWorkflow


def workflow() -> ContentWorkflow:
    return ContentWorkflow(
        now=datetime(2026, 8, 13, tzinfo=UTC),
        editor_role="ops",
    )


def test_content_workflow_publishes_immutable_revision_and_keeps_history() -> None:
    content = workflow()
    draft = content.create(key="home.hero", body="第一版", author="staff-1")
    preview = content.preview(draft.revision_id)
    published = content.publish(preview.revision_id)

    assert published.state is ContentState.PUBLISHED
    assert content.current("home.hero").body == "第一版"
    with pytest.raises(ContentError, match="published revision is immutable"):
        content.edit(published.revision_id, body="篡改")


def test_content_workflow_withdraws_without_deleting_revision_and_restores_history() -> None:
    content = workflow()
    first = content.publish(content.create(key="faq", body="旧版", author="staff-1").revision_id)
    second = content.publish(content.create(key="faq", body="新版", author="staff-1").revision_id)
    content.withdraw(second.revision_id, reason="事实待复核")

    assert content.current("faq").revision_id == first.revision_id
    assert content.get(second.revision_id).state is ContentState.WITHDRAWN
    assert content.history("faq")[0].revision_id == second.revision_id


def test_content_workflow_requires_scheduled_time_in_the_future() -> None:
    content = workflow()
    draft = content.create(key="daily", body="内容", author="staff-1")
    with pytest.raises(ContentError, match="future"):
        content.schedule(draft.revision_id, at=content.now)
    scheduled = content.schedule(draft.revision_id, at=content.now + timedelta(hours=1))
    assert scheduled.state is ContentState.SCHEDULED
