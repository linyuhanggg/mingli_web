from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from app.main import create_app
from app.readings.models import (
    GenerationAttempt,
    ReadingIdempotencyKey,
    ReadingJobRecord,
    ReadingRoot,
    ReadingVersion,
)
from app.readings.runtime_contracts import Prepare, Prepared, ReadingBrief
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from test_profiles_api import create_confirmed_profile, create_guest
from test_readings_api import seed_runtime_release
from worker.readings import build_reading_worker

_SCHEMA_BY_CAPABILITY = {
    "bazi": "bazi-chart/v1",
    "ziwei": "ziwei-chart/v1",
    "liuyao": "liuyao-chart/v1",
    "meihua": "meihua-chart/v1",
    "liuren": "daliuren-chart/v1",
}


def _values_for_capability(capability_id: str) -> dict[str, object]:
    if capability_id == "bazi":
        return {
            "four_pillars": {
                "year": "甲戌",
                "month": "戊辰",
                "day": "丙戌",
                "hour": "辛卯",
            },
            "element_inventory": {
                "visible_stem_branch_counts": {
                    "木": 2,
                    "火": 1,
                    "土": 4,
                    "金": 1,
                }
            },
        }
    if capability_id == "ziwei":
        return {
            "palaces": [
                {
                    "index": index,
                    "name": "命宫" if index == 0 else f"宫{index}",
                    "heavenlyStem": "甲",
                    "earthlyBranch": "子",
                    "majorStars": [{"name": "紫微"}] if index == 0 else [],
                    "isBodyPalace": index == 1,
                }
                for index in range(12)
            ]
        }
    if capability_id == "liuyao":
        return {
            "primary_hexagram": {
                "name": "泽天夬",
                "upper_trigram": "兑",
                "lower_trigram": "乾",
            },
            "changed_hexagram": {
                "name": "天风姤",
                "upper_trigram": "乾",
                "lower_trigram": "巽",
            },
            "lines": [
                {"line": 1, "state": "老阳", "moving": True},
                {"line": 2, "state": "少阳", "moving": False},
                {"line": 3, "state": "少阴", "moving": False},
                {"line": 4, "state": "老阴", "moving": True},
                {"line": 5, "state": "少阳", "moving": False},
                {"line": 6, "state": "少阴", "moving": False},
            ],
        }
    if capability_id == "meihua":
        return {
            "casting_method": "time",
            "primary_hexagram": {
                "name": "风雷益",
                "upper_trigram": "巽",
                "lower_trigram": "震",
            },
            "mutual_hexagram": {
                "name": "山地剥",
                "upper_trigram": "艮",
                "lower_trigram": "坤",
            },
            "changed_hexagram": {
                "name": "风泽中孚",
                "upper_trigram": "巽",
                "lower_trigram": "兑",
            },
            "moving_lines": [2],
            "body_use": {
                "body": {"position": "upper", "trigram": "巽", "element": "木"},
                "use": {"position": "lower", "trigram": "震", "element": "木"},
                "relation": "比和",
                "status": "calculated_relation_not_verdict",
            },
        }
    if capability_id == "liuren":
        fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "liuren-runtime-core-facts-v1.json"
        )
        return {"runtime_core_facts": json.loads(fixture.read_text(encoding="utf-8"))}
    raise AssertionError(f"unexpected chart capability: {capability_id}")


def _brief(command: Prepare) -> ReadingBrief:
    command_payload = command.to_dict()
    intent = command_payload["intent"]
    assert isinstance(intent, dict)
    capability_id = str(intent["capability_id"])
    raw_subjects = intent["subject_refs"]
    assert isinstance(raw_subjects, list) and raw_subjects
    subject_ref = str(raw_subjects[0])
    facts = [
        {
            "ref": f"fact:{subject_ref}/calculated/{capability_id}/{field_id}",
            "subject_ref": subject_ref,
            "kind_id": "kind.fact",
            "value": value,
            "display_text": f"{field_id} 已由 Runtime 计算。",
        }
        for field_id, value in _values_for_capability(capability_id).items()
    ]
    return ReadingBrief.from_dict(
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
                "subject_refs": raw_subjects,
                "capability_ids": [capability_id],
                "object_id": intent["object_id"],
                "dimension_ids": intent["dimension_ids"],
                "horizon": intent["horizon"],
            },
        }
    )


class DeterministicChartRuntime:
    adapter_kind = "test-chart-runtime"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(self, command: Any) -> Prepared:
        assert isinstance(command, Prepare)
        capability_id = str(command.intent["capability_id"])
        self.calls.append(capability_id)
        return Prepared(
            state_token=f"chart-fast-path:{capability_id}:{len(self.calls)}",
            brief=_brief(command),
        )


class HangingChartRuntime:
    adapter_kind = "test-hanging-chart-runtime"

    async def execute(self, command: Any) -> Prepared:
        assert isinstance(command, Prepare)
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


class ExplodingModel:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: Any) -> Any:
        del request
        self.calls += 1
        raise AssertionError("a base chart must never call the narrative model")


def _chart_cases(profile_version_id: str) -> tuple[tuple[str, dict[str, object], str], ...]:
    event = "2026-08-14T10:00:00+08:00"
    return (
        (
            "/api/v1/readings/preview",
            {"profile_version_id": profile_version_id, "dimension_ids": ["career"]},
            "bazi",
        ),
        (
            "/api/v1/readings/ziwei",
            {"profile_version_id": profile_version_id, "dimension_ids": ["career"]},
            "ziwei",
        ),
        (
            "/api/v1/readings/liuyao",
            {
                "cast": [6, 7, 8, 9, 7, 8],
                "event_datetime": event,
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "验证基础六爻盘面快路径",
                "dimension_ids": ["career"],
            },
            "liuyao",
        ),
        (
            "/api/v1/readings/meihua",
            {
                "casting_method": "time",
                "event_datetime": event,
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "验证基础梅花盘面快路径",
                "dimension_ids": ["outcome", "state"],
            },
            "meihua",
        ),
        (
            "/api/v1/readings/daliuren",
            {
                "event_datetime": event,
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "验证基础大六壬盘面快路径",
                "dimension_ids": ["outcome"],
            },
            "liuren",
        ),
    )


async def test_five_base_charts_finish_inline_without_worker_or_model(
    database: Any,
    test_settings: Any,
) -> None:
    runtime = DeterministicChartRuntime()
    settings = test_settings.model_copy(update={"reading_write_rate_limit": 100})
    application = create_app(
        settings=settings,
        database=database,
        chart_runtime=runtime,
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        headers = await create_guest(client)
        profile = await create_confirmed_profile(client, headers)
        await seed_runtime_release(database, settings)

        version_ids: list[UUID] = []
        for index, (path, payload, capability_id) in enumerate(
            _chart_cases(profile["profile_version_id"]),
            start=1,
        ):
            started = await client.post(
                path,
                headers={**headers, "Idempotency-Key": f"chart-fast-path-{index}"},
                json=payload,
            )
            assert started.status_code == 201, started.text
            body = started.json()
            assert body["status"] == "prepared"
            assert body["view_model"]["schema_version"] == _SCHEMA_BY_CAPABILITY[capability_id]
            assert body["fast_path_timing"]["execution_lane"] == "direct_runtime"
            assert body["fast_path_timing"]["queue_wait_ms"] == 0
            assert body["fast_path_timing"]["worker_pickup_ms"] == 0
            assert "chart-runtime" in started.headers["server-timing"]
            version_id = UUID(body["reading_version_id"])
            version_ids.append(version_id)

            first_ready_poll = await client.get(f"/api/v1/readings/{version_id}")
            assert first_ready_poll.status_code == 200
            assert first_ready_poll.json()["status"] == "prepared"
            assert (
                first_ready_poll.json()["view_model"]["schema_version"]
                == _SCHEMA_BY_CAPABILITY[capability_id]
            )

            result = await client.get(f"/api/v1/readings/{version_id}/result")
            assert result.status_code == 200
            assert result.json()["status"] == "prepared"
            assert result.json()["view_model"]["schema_version"] == _SCHEMA_BY_CAPABILITY[
                capability_id
            ]
            assert result.json()["accepted_copy"] is None
            public_capability_id = (
                "daliuren" if capability_id == "liuren" else capability_id
            )
            capability = result.json()["capability"]
            assert capability["capability_id"] == public_capability_id

    assert runtime.calls == ["bazi", "ziwei", "liuyao", "meihua", "liuren"]
    async with database.sessions() as session:
        jobs = list(
            await session.scalars(
                select(ReadingJobRecord)
                .where(ReadingJobRecord.reading_version_id.in_(version_ids))
                .order_by(ReadingJobRecord.created_at, ReadingJobRecord.id)
            )
        )
        attempts = int(
            await session.scalar(select(func.count()).select_from(GenerationAttempt)) or 0
        )
    assert [job.status for job in jobs] == ["complete"] * 5
    assert attempts == 0

    model = ExplodingModel()
    worker = build_reading_worker(
        settings=test_settings,
        database=database,
        worker_id="chart-fast-path-proof",
        model=model,
    )
    assert await worker.run_once() is False
    assert model.calls == 0


async def test_existing_queue_does_not_delay_direct_chart_path(
    database: Any,
    test_settings: Any,
) -> None:
    runtime = DeterministicChartRuntime()
    settings = test_settings.model_copy(update={"reading_write_rate_limit": 100})
    application = create_app(
        settings=settings,
        database=database,
        chart_runtime=runtime,
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        headers = await create_guest(client)
        profile = await create_confirmed_profile(client, headers)
        await seed_runtime_release(database, settings)
        for index in range(20):
            queued = await client.post(
                "/api/v1/readings/qimen",
                headers={**headers, "Idempotency-Key": f"queued-qimen-{index:02d}"},
                json={
                    "event_datetime": "2026-08-14T10:00:00+08:00",
                    "timezone": "Asia/Shanghai",
                    "location": "上海市",
                    "query": f"保留异步积压任务 {index}",
                    "dimension_ids": ["outcome"],
                },
            )
            assert queued.status_code == 201
            assert queued.json()["status"] == "input_ready"

        started_at = time.perf_counter()
        chart = await client.post(
            "/api/v1/readings/preview",
            headers={**headers, "Idempotency-Key": "direct-bazi-proof"},
            json={
                "profile_version_id": profile["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )
        elapsed = time.perf_counter() - started_at

    assert chart.status_code == 201, chart.text
    assert chart.json()["status"] == "prepared"
    assert chart.json()["fast_path_timing"]["queue_wait_ms"] == 0
    assert elapsed < 1.0
    async with database.sessions() as session:
        statuses = list(
            await session.scalars(
                select(ReadingJobRecord.status).order_by(ReadingJobRecord.created_at)
            )
        )
    assert statuses.count("queued") == 20
    assert statuses.count("complete") == 1
    assert runtime.calls == ["bazi"]


async def test_chart_runtime_timeout_fails_fast_and_rolls_back(
    database: Any,
    test_settings: Any,
) -> None:
    settings = test_settings.model_copy(update={"chart_fast_path_timeout_seconds": 0.01})
    application = create_app(
        settings=settings,
        database=database,
        chart_runtime=HangingChartRuntime(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        headers = await create_guest(client)
        profile = await create_confirmed_profile(client, headers)
        await seed_runtime_release(database, settings)
        started_at = time.perf_counter()
        response = await client.post(
            "/api/v1/readings/preview",
            headers={**headers, "Idempotency-Key": "chart-timeout-proof"},
            json={
                "profile_version_id": profile["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )
        elapsed = time.perf_counter() - started_at

    assert response.status_code == 503
    assert response.json()["title"] == "Chart generation unavailable"
    assert response.json()["detail"] == "chart_runtime_timeout"
    assert response.json()["request_id"]
    assert elapsed < 0.5
    async with database.sessions() as session:
        counts = {
            "roots": int(await session.scalar(select(func.count()).select_from(ReadingRoot)) or 0),
            "versions": int(
                await session.scalar(select(func.count()).select_from(ReadingVersion)) or 0
            ),
            "jobs": int(
                await session.scalar(select(func.count()).select_from(ReadingJobRecord)) or 0
            ),
            "idempotency": int(
                await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)) or 0
            ),
        }
    assert counts == {"roots": 0, "versions": 0, "jobs": 0, "idempotency": 0}
