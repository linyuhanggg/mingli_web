from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.commerce.models import NotificationOutbox


@dataclass(frozen=True, slots=True)
class InAppNotificationProjection:
    title: str
    summary: str
    target_href: str | None


def is_in_app_notification(item: NotificationOutbox) -> bool:
    channel: Any = item.payload.get("channel")
    return isinstance(channel, str) and channel.strip() == "in_app"


def project_in_app_notification(
    item: NotificationOutbox,
) -> InAppNotificationProjection | None:
    if not is_in_app_notification(item):
        return None

    projections = {
        "reading.accepted": InAppNotificationProjection(
            title="解读已完成",
            summary="一项解读已经完成，可以在历史中查看服务端结果。",
            target_href="/account/history",
        ),
        "reading.input_required": InAppNotificationProjection(
            title="需要补充解读资料",
            summary="这项解读需要补充资料后才能继续。",
            target_href="/account/history",
        ),
        "reading.delayed": InAppNotificationProjection(
            title="解读暂时延迟",
            summary="这项解读还没有完成，请稍后查看任务状态。",
            target_href="/account/history",
        ),
        "reading.failed": InAppNotificationProjection(
            title="解读未完成",
            summary="这项解读没有完成，请返回历史查看服务端状态。",
            target_href="/account/history",
        ),
        "referral.reward.committed": InAppNotificationProjection(
            title="邀请奖励已确认",
            summary="一次邀请奖励已经确认，账户权益以服务端账本为准。",
            target_href="/account/invitations",
        ),
        "referral.reward.expired": InAppNotificationProjection(
            title="邀请奖励已过期",
            summary="一项尚未使用的邀请奖励已经过期。",
            target_href="/account/invitations",
        ),
        "referral.reward.refunded": InAppNotificationProjection(
            title="邀请奖励已冲正",
            summary="一项邀请奖励已按服务端退款事实冲正。",
            target_href="/account/invitations",
        ),
        "account.data_export.ready": InAppNotificationProjection(
            title="数据导出已准备好",
            summary="你的数据导出请求已经有新的服务端状态。",
            target_href="/account/settings/privacy-data",
        ),
        "account.security": InAppNotificationProjection(
            title="账户安全通知",
            summary="账户安全状态有更新，请返回安全设置查看。",
            target_href="/account/settings/security",
        ),
    }
    return projections.get(
        item.kind,
        InAppNotificationProjection(
            title="账户通知",
            summary="账户有一条新的通知。",
            target_href=None,
        ),
    )
