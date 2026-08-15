from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.content.service import ContentService
from app.content.workflow import ContentError, ContentState


def service(session, *, role: str = "ops", now: datetime | None = None):  # type: ignore[no-untyped-def]
    return ContentService(
        session,
        editor_role=role,
        now=now or datetime(2026, 8, 13, tzinfo=UTC),
    )


async def test_persistent_cms_keeps_history_and_restores_as_new_revision(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        cms = service(session, now=now)
        draft = await cms.create(
            content_key="home.hero",
            locale="zh-CN",
            body="第一版",
            author_ref="ops@example.com",
            author_staff_user_id=None,
        )
        await cms.edit(draft.id, body="预览版")
        await cms.preview(draft.id)
        published = await cms.publish(draft.id)
        assert published.state == ContentState.PUBLISHED
        with pytest.raises(ContentError, match="immutable"):
            await cms.edit(draft.id, body="篡改")

        withdrawn = await cms.withdraw(draft.id, reason="事实待复核")
        assert withdrawn.state == ContentState.WITHDRAWN
        restored = await cms.restore(
            draft.id,
            author_ref="ops@example.com",
            author_staff_user_id=None,
        )
        assert restored.revision == 2
        assert restored.state == ContentState.DRAFT
        await cms.archive(restored.id)
        history = await cms.history(content_key="home.hero")
        assert [item.revision for item in history] == [2, 1]
        assert history[0].state == ContentState.ARCHIVED
        with pytest.raises(ContentError, match="no published"):
            await cms.current(content_key="home.hero")


async def test_scheduled_cms_revision_publishes_only_after_due_time(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        cms = service(session, now=now)
        draft = await cms.create(
            content_key="daily",
            locale="zh-CN",
            body="每日内容",
            author_ref="ops@example.com",
            author_staff_user_id=None,
        )
        await cms.schedule(draft.id, publish_at=now + timedelta(hours=1))
        with pytest.raises(ContentError, match="not ready"):
            await cms.publish(draft.id)
        due_cms = service(session, now=now + timedelta(hours=1))
        published = await due_cms.publish(draft.id)
        assert published.state == ContentState.PUBLISHED


async def test_public_index_keeps_the_latest_published_revision_visible(database) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        cms = service(session)
        published_draft = await cms.create(
            content_key="library.intro",
            locale="zh-CN",
            body="已发布版本",
            author_ref="ops@example.com",
            author_staff_user_id=None,
        )
        await cms.publish(published_draft.id)
        newer_draft = await cms.create(
            content_key="library.intro",
            locale="zh-CN",
            body="尚未发布版本",
            author_ref="ops@example.com",
            author_staff_user_id=None,
        )

        public_items = await cms.public_index(prefix="library.")

        assert [(item.revision, item.body) for item in public_items] == [(1, "已发布版本")]
        assert newer_draft.state == ContentState.DRAFT


async def test_cms_requires_ops_or_superadmin(database) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        cms = service(session, role="support")
        with pytest.raises(ContentError, match="editor"):
            await cms.create(
                content_key="faq",
                locale="zh-CN",
                body="内容",
                author_ref="support@example.com",
                author_staff_user_id=None,
            )


async def test_admin_cms_rejects_unknown_content_namespace(client) -> None:  # type: ignore[no-untyped-def]
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text

    response = await client.post(
        "/api/v1/admin/cms",
        headers={"X-CSRF-Token": login.json()["csrf_token"]},
        json={
            "content_key": "unregistered.random",
            "locale": "zh-CN",
            "body": "不应登记的内容",
            "reason": "验证内容命名空间",
        },
    )

    assert response.status_code == 409, response.text
    assert "namespace" in response.json()["detail"]


async def test_admin_cms_routes_write_and_read_persistent_history(client) -> None:  # type: ignore[no-untyped-def]
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}
    draft = await client.post(
        "/api/v1/admin/cms",
        headers=headers,
        json={
            "content_key": "faq.home",
            "locale": "zh-CN",
            "body": "帮助",
            "reason": "创建帮助草稿",
        },
    )
    assert draft.status_code == 201, draft.text
    revision_id = draft.json()["revision_id"]
    preview = await client.post(
        f"/api/v1/admin/cms/{revision_id}/preview",
        headers=headers,
        json={"reason": "进入审核预览"},
    )
    assert preview.status_code == 200, preview.text
    published = await client.post(
        f"/api/v1/admin/cms/{revision_id}/publish",
        headers=headers,
        json={"reason": "帮助内容审核通过"},
    )
    assert published.status_code == 200, published.text
    history = await client.get("/api/v1/admin/cms/faq.home/history")
    assert history.status_code == 200, history.text
    assert history.json()["revisions"][0]["state"] == "published"


async def test_public_content_routes_only_expose_published_projection(client) -> None:  # type: ignore[no-untyped-def]
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}

    published_draft = await client.post(
        "/api/v1/admin/cms",
        headers=headers,
        json={
            "content_key": "library.intro",
            "locale": "zh-CN",
            "body": "公开文章正文",
            "reason": "发布公开文章",
        },
    )
    assert published_draft.status_code == 201, published_draft.text
    published = await client.post(
        f"/api/v1/admin/cms/{published_draft.json()['revision_id']}/publish",
        headers=headers,
        json={"reason": "公开文章审核通过"},
    )
    assert published.status_code == 200, published.text

    unpublished = await client.post(
        "/api/v1/admin/cms",
        headers=headers,
        json={
            "content_key": "library.draft-only",
            "locale": "zh-CN",
            "body": "不应公开的正文",
            "reason": "建立未发布文章",
        },
    )
    assert unpublished.status_code == 201, unpublished.text

    item = await client.get("/api/v1/content/library.intro")
    assert item.status_code == 200, item.text
    assert item.json() == {
        "content_key": "library.intro",
        "locale": "zh-CN",
        "revision": 1,
        "title": None,
        "summary": None,
        "topic": None,
        "source_title": None,
        "source_url": None,
        "body": "公开文章正文",
        "created_at": item.json()["created_at"],
    }
    assert "author_ref" not in item.text
    assert "state" not in item.text
    assert "公开文章审核通过" not in item.text

    indexed = await client.get("/api/v1/content", params={"prefix": "library."})
    assert indexed.status_code == 200, indexed.text
    assert [entry["content_key"] for entry in indexed.json()["items"]] == [
        "library.intro"
    ]

    hidden = await client.get("/api/v1/content/library.draft-only")
    assert hidden.status_code == 404, hidden.text


async def test_public_content_projection_supports_metadata_search_and_topic_filter(client) -> None:  # type: ignore[no-untyped-def]
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}

    for key, title, topic, body in (
        ("library.time-basis", "时间口径怎么选", "方法与边界", "民用时间与地点会影响排盘口径。"),
        ("library.source-check", "如何核对来源", "现实核对", "先看来源，再判断内容是否适用。"),
    ):
        draft = await client.post(
            "/api/v1/admin/cms",
            headers=headers,
            json={
                "content_key": key,
                "locale": "zh-CN",
                "title": title,
                "summary": f"{title}的公开摘要",
                "topic": topic,
                "source_title": "公开方法说明",
                "source_url": "https://example.com/methodology",
                "body": body,
                "reason": "建立可检索的公开内容",
            },
        )
        assert draft.status_code == 201, draft.text
        published = await client.post(
            f"/api/v1/admin/cms/{draft.json()['revision_id']}/publish",
            headers=headers,
            json={"reason": "公开内容审核通过"},
        )
        assert published.status_code == 200, published.text

    response = await client.get(
        "/api/v1/content",
        params={"prefix": "library.", "q": "口径", "topic": "方法与边界"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"] == [
        {
            "content_key": "library.time-basis",
            "locale": "zh-CN",
            "revision": 1,
            "title": "时间口径怎么选",
            "summary": "时间口径怎么选的公开摘要",
            "topic": "方法与边界",
            "source_title": "公开方法说明",
            "source_url": "https://example.com/methodology",
            "body": "民用时间与地点会影响排盘口径。",
            "created_at": response.json()["items"][0]["created_at"],
        }
    ]


async def test_admin_cms_write_commands_require_reason_and_are_audited(client) -> None:  # type: ignore[no-untyped-def]
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}

    draft = await client.post(
        "/api/v1/admin/cms",
        headers=headers,
        json={
            "content_key": "faq.audit",
            "locale": "zh-CN",
            "body": "不可进入审计的正文",
            "reason": "补充客服审核后的帮助内容",
        },
    )
    assert draft.status_code == 201, draft.text
    revision_id = draft.json()["revision_id"]

    published = await client.post(
        f"/api/v1/admin/cms/{revision_id}/publish",
        headers=headers,
        json={"reason": "内容审核完成，允许对外发布"},
    )
    assert published.status_code == 200, published.text

    audits = await client.get(
        "/api/v1/admin/audit",
        params={"action": "cms.revision.published"},
    )
    assert audits.status_code == 200, audits.text
    assert audits.json()["events"] == [
        {
            "id": audits.json()["events"][0]["id"],
            "action": "cms.revision.published",
            "actor": "ops@example.com",
            "metadata": {
                "content_key": "faq.audit",
                "locale": "zh-CN",
                "reason": "内容审核完成，允许对外发布",
                "revision": 1,
                "state": "published",
                "target_id": revision_id,
            },
            "created_at": audits.json()["events"][0]["created_at"],
        }
    ]
    assert "不可进入审计的正文" not in audits.text


async def test_admin_cms_transitions_and_edit_are_each_audited(client) -> None:  # type: ignore[no-untyped-def]
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}

    draft = await client.post(
        "/api/v1/admin/cms",
        headers=headers,
        json={
            "content_key": "faq.transitions",
            "locale": "zh-CN",
            "body": "初始正文",
            "reason": "建立状态转换测试内容",
        },
    )
    assert draft.status_code == 201, draft.text
    revision_id = draft.json()["revision_id"]

    edited = await client.patch(
        f"/api/v1/admin/cms/{revision_id}",
        headers=headers,
        json={"body": "更新后的正文", "reason": "修正事实表述"},
    )
    assert edited.status_code == 200, edited.text

    preview = await client.post(
        f"/api/v1/admin/cms/{revision_id}/preview",
        headers=headers,
        json={"reason": "提交内容预览"},
    )
    assert preview.status_code == 200, preview.text
    published = await client.post(
        f"/api/v1/admin/cms/{revision_id}/publish",
        headers=headers,
        json={"reason": "审核通过并发布"},
    )
    assert published.status_code == 200, published.text
    withdrawn = await client.post(
        f"/api/v1/admin/cms/{revision_id}/withdraw",
        headers=headers,
        json={"reason": "发现内容需要复核"},
    )
    assert withdrawn.status_code == 200, withdrawn.text
    restored = await client.post(
        f"/api/v1/admin/cms/{revision_id}/restore",
        headers=headers,
        json={"reason": "复核完成，恢复为新草稿"},
    )
    assert restored.status_code == 201, restored.text
    archived = await client.post(
        f"/api/v1/admin/cms/{restored.json()['revision_id']}/archive",
        headers=headers,
        json={"reason": "保留历史但归档草稿"},
    )
    assert archived.status_code == 200, archived.text

    scheduled_draft = await client.post(
        "/api/v1/admin/cms",
        headers=headers,
        json={
            "content_key": "faq.scheduled",
            "locale": "zh-CN",
            "body": "定时正文",
            "reason": "建立定时内容",
        },
    )
    assert scheduled_draft.status_code == 201, scheduled_draft.text
    scheduled = await client.post(
        f"/api/v1/admin/cms/{scheduled_draft.json()['revision_id']}/schedule",
        headers=headers,
        json={
            "publish_at": "2099-01-01T00:00:00Z",
            "reason": "安排未来发布",
        },
    )
    assert scheduled.status_code == 200, scheduled.text

    for action in (
        "cms.draft.edited",
        "cms.revision.previewed",
        "cms.revision.published",
        "cms.revision.withdrawn",
        "cms.revision.restored",
        "cms.revision.archived",
        "cms.revision.scheduled",
    ):
        audits = await client.get("/api/v1/admin/audit", params={"action": action})
        assert audits.status_code == 200, audits.text
        assert audits.json()["events"]
        assert all(event["actor"] == "ops@example.com" for event in audits.json()["events"])
        assert all("body" not in event["metadata"] for event in audits.json()["events"])

    missing_reason = await client.post(
        f"/api/v1/admin/cms/{scheduled_draft.json()['revision_id']}/publish",
        headers=headers,
    )
    assert missing_reason.status_code == 400, missing_reason.text


async def test_admin_cms_index_returns_latest_metadata_without_body(client) -> None:  # type: ignore[no-untyped-def]
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}
    for body in ("第一版", "第二版"):
        created = await client.post(
            "/api/v1/admin/cms",
            headers=headers,
            json={
                "content_key": "faq.home",
                "locale": "zh-CN",
                "body": body,
                "reason": "创建帮助版本",
            },
        )
        assert created.status_code == 201, created.text
    daily = await client.post(
        "/api/v1/admin/cms",
        headers=headers,
        json={
            "content_key": "daily",
            "locale": "zh-CN",
            "body": "每日内容",
            "reason": "创建每日内容版本",
        },
    )
    assert daily.status_code == 201, daily.text

    indexed = await client.get(
        "/api/v1/admin/cms",
        params={"prefix": "faq", "locale": "zh-CN"},
    )
    assert indexed.status_code == 200, indexed.text
    revisions = indexed.json()["revisions"]
    assert len(revisions) == 1
    assert revisions[0]["content_key"] == "faq.home"
    assert revisions[0]["revision"] == 2
    assert revisions[0]["state"] == "draft"
    assert "body" not in indexed.text
