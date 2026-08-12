from typing import Any

from app.readings.models import GenerationAttempt, ReadingJobRecord, ReadingRoot
from httpx import AsyncClient
from sqlalchemy import func, select
from test_profiles_api import (
    assert_private_headers,
    create_confirmed_profile,
    create_guest,
)


async def _row_count(database: Any, model: type[Any]) -> int:
    async with database.sessions() as session:
        count = await session.scalar(select(func.count()).select_from(model))
    return int(count or 0)


async def test_guest_syncs_public_bazi_chart_without_creating_a_reading_job(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)

    response = await client.post(
        "/api/v1/charts/bazi/sync",
        headers={**headers, "Idempotency-Key": "chart-sync-fixture-0001"},
        json={"profile_version_id": confirmed["profile_version_id"]},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "profile_version_id": confirmed["profile_version_id"],
        "status": "ready",
        "chart_handle": None,
        "fact_panel": {
            "question": "查看这个档案的确定性八字盘。",
            "vocabulary": [],
            "facts": [
                {
                    "ref": "fact:fake-1",
                    "subject_ref": f"profile-version:{confirmed['profile_version_id']}",
                    "kind_id": "kind.fixture",
                    "value": {"fixture": True},
                    "display_text": "这是 Fake Runtime 合同事实，不是命理结果。",
                }
            ],
            "evidence": [],
            "findings": [
                {
                    "ref": "finding:fake-1",
                    "subject_ref": f"profile-version:{confirmed['profile_version_id']}",
                    "dimension_ids": ["overview"],
                    "kind_id": "kind.tendency",
                    "data": {"fixture": True},
                    "fact_refs": ["fact:fake-1"],
                    "evidence_refs": [],
                    "limit_kind_ids": ["limit:traditional"],
                    "support_mode": "exact",
                }
            ],
            "claim_scopes": [
                {
                    "subject_ref": f"profile-version:{confirmed['profile_version_id']}",
                    "dimension_id": "overview",
                    "allowed_kind_ids": ["kind.tendency"],
                    "certainty_ceiling_id": "certainty.tendency",
                    "fact_refs": ["fact:fake-1"],
                    "evidence_refs": [],
                }
            ],
            "limits": [
                {
                    "kind_id": "limit:traditional",
                    "public_text": "这是 Fake Runtime 合同边界。",
                    "scope_refs": [f"profile-version:{confirmed['profile_version_id']}"],
                    "detail_ids": [],
                }
            ],
            "prior_answer": None,
            "request_view": {
                "subject_refs": [f"profile-version:{confirmed['profile_version_id']}"],
                "capability_ids": ["bazi"],
                "object_id": "natal",
                "dimension_ids": ["overview"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
            },
        },
        "input_request": None,
    }
    assert_private_headers(response)
    assert "state_token" not in response.text
    assert "accepted_copy" not in response.text
    assert await _row_count(database, ReadingRoot) == 0
    assert await _row_count(database, ReadingJobRecord) == 0
    assert await _row_count(database, GenerationAttempt) == 0
