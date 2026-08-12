from collections.abc import Mapping
from typing import Any

from app.adapters.runtime import FakeMingliRuntimeAdapter
from app.charts.runtime import ChartRuntimeLease
from app.readings.models import GenerationAttempt, ReadingJobRecord, ReadingRoot
from app.readings.runtime_contracts import MingliCommand, Prepare, Prepared, Stopped
from httpx import ASGITransport, AsyncClient
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


async def test_sync_chart_closes_its_runtime_lease(
    database: Any,
    test_settings: Any,
) -> None:
    from app.main import create_app

    opened = 0
    closed = 0

    class RecordingFactory:
        async def startup(self) -> None:
            return None

        async def open(self) -> ChartRuntimeLease:
            nonlocal opened, closed
            opened += 1

            def record_close() -> None:
                nonlocal closed
                closed += 1

            return ChartRuntimeLease(
                FakeMingliRuntimeAdapter(),
                cleanup=record_close,
            )

        async def aclose(self) -> None:
            return None

    application = create_app(
        settings=test_settings,
        database=database,
        chart_runtime_factory=RecordingFactory(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as http_client:
        headers = await create_guest(http_client)
        confirmed = await create_confirmed_profile(http_client, headers)
        response = await http_client.post(
            "/api/v1/charts/bazi/sync",
            headers={**headers, "Idempotency-Key": "chart-sync-fixture-0002"},
            json={"profile_version_id": confirmed["profile_version_id"]},
        )

    assert response.status_code == 200, response.text
    assert opened == 1
    assert closed == 1


async def test_need_input_resumes_with_the_same_private_runtime_token(
    database: Any,
    test_settings: Any,
) -> None:
    from app.main import create_app

    commands: list[MingliCommand] = []
    closed = 0
    fake = FakeMingliRuntimeAdapter()

    class NeedInputRuntime:
        async def execute(self, command: MingliCommand) -> Prepared | Stopped:
            commands.append(command)
            assert isinstance(command, Prepare)
            if len(commands) == 1:
                return Stopped(
                    reason="need_input",
                    public_copy="请选择夜子时口径。",
                    state_token="private-chart-state-token",
                    input_request={
                        "requirements": [
                            {
                                "any_of": [
                                    {
                                        "id": "zi_policy",
                                        "label": "夜子时口径",
                                        "type_id": "choice",
                                        "description": None,
                                        "choices": [
                                            {
                                                "id": "midnight",
                                                "label": "零点换日",
                                                "description": None,
                                            },
                                            {
                                                "id": "zi-hour",
                                                "label": "子初换日",
                                                "description": None,
                                            },
                                        ],
                                    }
                                ]
                            }
                        ]
                    },
                )
            fake_result = await fake.execute(command)
            assert isinstance(fake_result, Prepared)
            return Prepared(
                state_token="private-chart-state-token",
                brief=fake_result.brief,
            )

    runtime = NeedInputRuntime()

    class NeedInputFactory:
        async def startup(self) -> None:
            return None

        async def open(self) -> ChartRuntimeLease:
            def record_close() -> None:
                nonlocal closed
                closed += 1

            return ChartRuntimeLease(runtime, cleanup=record_close)

        async def aclose(self) -> None:
            return None

    application = create_app(
        settings=test_settings,
        database=database,
        chart_runtime_factory=NeedInputFactory(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as http_client:
        headers = await create_guest(http_client)
        confirmed = await create_confirmed_profile(http_client, headers)
        started = await http_client.post(
            "/api/v1/charts/bazi/sync",
            headers={**headers, "Idempotency-Key": "chart-need-input-0001"},
            json={"profile_version_id": confirmed["profile_version_id"]},
        )

        assert started.status_code == 200, started.text
        waiting = started.json()
        assert waiting["status"] == "need_input"
        assert waiting["profile_version_id"] == confirmed["profile_version_id"]
        assert waiting["fact_panel"] is None
        assert waiting["input_request"]["requirements"][0]["any_of"][0]["id"] == (
            "zi_policy"
        )
        assert "private-chart-state-token" not in started.text
        assert closed == 0

        resumed = await http_client.post(
            f"/api/v1/charts/bazi/sync/{waiting['chart_handle']}/input",
            headers={**headers, "Idempotency-Key": "chart-need-input-0002"},
            json={"values": {"zi_policy": "midnight"}},
        )

    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "ready"
    assert resumed.json()["chart_handle"] is None
    assert "private-chart-state-token" not in resumed.text
    assert closed == 1
    assert len(commands) == 2
    resumed_command = commands[1]
    assert isinstance(resumed_command, Prepare)
    assert resumed_command.state_token == "private-chart-state-token"
    assert resumed_command.transition == "correct"
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    subject_facts = resumed_command.facts[subject_ref]
    assert isinstance(subject_facts, Mapping)
    assert subject_facts["zi_hour_policy"] == "midnight"
    assert await _row_count(database, ReadingRoot) == 0
    assert await _row_count(database, ReadingJobRecord) == 0
    assert await _row_count(database, GenerationAttempt) == 0
