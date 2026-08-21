from __future__ import annotations

from typing import Any
from uuid import UUID

from app.adapters.runtime import FakeMingliRuntimeAdapter
from app.readings.models import ReadingRoot, ReadingVersion
from app.readings.runtime_contracts import Prepare, Prepared, ReadingBrief
from httpx import AsyncClient

from test_profiles_api import create_confirmed_profile, create_guest
from test_readings_api import run_worker_once, seed_runtime_release


class RelationshipFakeRuntime(FakeMingliRuntimeAdapter):
    """A local worker fixture with two calculated Bazi fact bundles."""

    def _prepare(self, command: Prepare) -> Prepared:
        raw_subjects = command.intent.get("subject_refs")
        subject_refs = tuple(raw_subjects) if isinstance(raw_subjects, tuple) else ()
        capability_id = command.intent.get("capability_id")
        if len(subject_refs) != 2 or capability_id != "bazi":
            return super()._prepare(command)  # type: ignore[return-value]
        facts = [
            {
                "ref": f"fact:{subject_ref}/calculated/bazi/four_pillars",
                "subject_ref": subject_ref,
                "kind_id": "kind.bazi.four_pillars",
                "value": value,
                "display_text": "四柱",
            }
            for subject_ref, value in zip(
                subject_refs,
                (
                    {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"},
                    {"year": "戊午", "month": "己未", "day": "庚申", "hour": "辛酉"},
                ),
                strict=True,
            )
        ]
        facts.append(
            {
                "ref": "fact:relationship/calculated/bazi/relationship_signals",
                "subject_ref": "relationship",
                "kind_id": "kind.bazi.relationship_signals",
                "value": [
                    {
                        "dimension_id": "relationship",
                        "subject_refs": list(subject_refs),
                        "signal_id": "bazi.cross_branch.liu_chong.year.year",
                        "display_text": "甲方年支与乙方年支构成六冲（跨盘结构事实）。",
                        "fact_refs": [
                            f"fact:{subject_refs[0]}/calculated/bazi/four_pillars",
                            f"fact:{subject_refs[1]}/calculated/bazi/four_pillars",
                        ],
                    }
                ],
                "display_text": "跨盘结构事实",
            }
        )
        raw_horizon = command.intent.get("horizon")
        horizon = raw_horizon if isinstance(raw_horizon, dict) else {}
        brief = ReadingBrief.from_dict(
            {
                "question": command.query,
                "vocabulary": [],
                "facts": facts,
                "evidence": [],
                "findings": [],
                "claim_scopes": [],
                "limits": [],
                "prior_answer": None,
                "request_view": {
                    "subject_refs": list(subject_refs),
                    "capability_ids": ["bazi"],
                    "object_id": str(command.intent["object_id"]),
                    "dimension_ids": ["relationship"],
                    "horizon": {
                        "kind_id": str(horizon.get("kind_id", "life")),
                        "start": horizon.get("start"),
                        "end": horizon.get("end"),
                    },
                },
            }
        )
        return Prepared(state_token="relationship-fake-token", brief=brief)


async def test_bazi_relationship_persists_two_profiles_and_projects_view_model(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    first = await create_confirmed_profile(client, headers)
    second = await create_confirmed_profile(client, headers, location="上海市浦东新区")
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/bazi-relationship",
        headers=headers,
        json={
            "profile_version_ids": [
                first["profile_version_id"],
                second["profile_version_id"],
            ],
            "relationship_type": "romantic",
        },
    )

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["product_id"] == "bazi-relationship"
    assert body["profile_version_id"] == first["profile_version_id"]
    version_id = UUID(body["reading_version_id"])
    async with database.sessions() as session:
        version = await session.get(ReadingVersion, version_id)
        assert version is not None
        root = await session.get(ReadingRoot, version.reading_root_id)
        assert root is not None
        assert root.profile_version_ids == [
            first["profile_version_id"],
            second["profile_version_id"],
        ]
        assert root.relationship_type == "romantic"
        assert version.relationship_type == "romantic"

    assert await run_worker_once(
        database,
        test_settings,
        runtime=RelationshipFakeRuntime(),
    ) is True
    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    result_body = result.json()
    assert result_body["view_model"]["schema_version"] == "bazi-relationship/v1"
    assert result_body["view_model"]["signals"]


async def test_chart_similarity_persists_two_profiles_and_projects_exact_pillars(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    first = await create_confirmed_profile(client, headers)
    second = await create_confirmed_profile(client, headers, location="上海市浦东新区")
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/chart-similarity",
        headers=headers,
        json={
            "profile_version_ids": [
                first["profile_version_id"],
                second["profile_version_id"],
            ],
            "dimension_ids": ["state"],
        },
    )

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["product_id"] == "chart-similarity"
    assert body["profile_version_id"] == first["profile_version_id"]
    version_id = UUID(body["reading_version_id"])

    assert await run_worker_once(
        database,
        test_settings,
        runtime=RelationshipFakeRuntime(),
    ) is True
    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    result_body = result.json()
    view = result_body["view_model"]
    assert view["schema_version"] == "chart-similarity-view/v1"
    assert view["basis"] == "bazi.four_pillars.exact"
    assert view["exact_match"] is False
    assert view["differing_positions"] == ["year", "month", "day", "hour"]


async def test_relationship_api_rejects_the_same_profile_twice(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    profile = await create_confirmed_profile(client, headers)

    response = await client.post(
        "/api/v1/readings/bazi-relationship",
        headers=headers,
        json={
            "profile_version_ids": [
                profile["profile_version_id"],
                profile["profile_version_id"],
            ],
            "relationship_type": "romantic",
        },
    )

    assert response.status_code == 400


async def test_relationship_api_rejects_two_versions_of_one_subject_profile(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    first = await create_confirmed_profile(client, headers)
    appended = await client.post(
        f"/api/v1/profiles/{first['profile_id']}/versions",
        headers=headers,
        json={
            "birth_datetime": "1995-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市海淀区",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "difference_acknowledged": True,
        },
    )
    assert appended.status_code == 201, appended.text

    response = await client.post(
        "/api/v1/readings/bazi-relationship",
        headers=headers,
        json={
            "profile_version_ids": [
                first["profile_version_id"],
                appended.json()["profile_version_id"],
            ],
            "relationship_type": "romantic",
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid reading input"
