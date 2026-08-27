"""MING-21 user-acceptance FAIL: Backend service/contract closures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.charts.projectors import project_daliuren_view_model, project_meihua_view_model
from app.charts.public_labels import DALIUREN_PUBLIC_LABELS, MEIHUA_PUBLIC_LABELS
from app.main import create_app
from app.readings.runtime_contracts import Prepare, Stopped
from httpx import ASGITransport, AsyncClient

# isort: split
from test_chart_fast_path import DeterministicChartRuntime
from test_chart_projectors import brief
from test_profiles_api import create_confirmed_profile, create_guest
from test_readings_api import seed_runtime_release


def _liuyao_payload() -> dict[str, object]:
    return {
        "cast": [6, 7, 8, 9, 7, 8],
        "event_datetime": "2026-08-14T10:00:00+08:00",
        "timezone": "Asia/Shanghai",
        "location": "上海市",
        "query": "公开基础六爻排盘",
        "dimension_ids": ["career"],
    }


class StoppedErrorRuntime:
    adapter_kind = "test-stopped-error-runtime"

    async def execute(self, command: object) -> Stopped:
        assert isinstance(command, Prepare)
        return Stopped(reason="error", public_copy="紫微盘面计算失败。")


async def test_guest_public_liuyao_is_not_blocked_by_dogfood_paid_gate(
    database: Any,
    test_settings: Any,
) -> None:
    runtime = DeterministicChartRuntime()
    settings = test_settings.model_copy(
        update={
            "dogfood_entitlement_gates_enabled": True,
            "dogfood_daily_reading_limit": 10,
            "reading_write_rate_limit": 100,
        }
    )
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
        await seed_runtime_release(database, settings)
        response = await client.post(
            "/api/v1/readings/liuyao",
            headers={**headers, "Idempotency-Key": "guest-liuyao-public"},
            json=_liuyao_payload(),
        )
        deep = await client.post(
            "/api/v1/readings/liuyao-deep",
            headers={**headers, "Idempotency-Key": "guest-liuyao-deep"},
            json=_liuyao_payload(),
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "prepared"
    assert body["result_available"] is True
    assert body["poll_required"] is False
    assert body["poll_after_seconds"] is None
    assert deep.status_code == 403, deep.text
    assert deep.json()["code"] == "paid_reading_requires_account"


async def test_guest_daily_limit_is_typed_and_isolated_per_session(
    database: Any,
    test_settings: Any,
) -> None:
    runtime = DeterministicChartRuntime()
    settings = test_settings.model_copy(
        update={
            "dogfood_entitlement_gates_enabled": True,
            "dogfood_daily_reading_limit": 1,
            "reading_write_rate_limit": 100,
        }
    )
    application = create_app(
        settings=settings,
        database=database,
        chart_runtime=runtime,
    )
    transport = ASGITransport(app=application)
    async with (
        AsyncClient(transport=transport, base_url="https://testserver") as first_client,
        AsyncClient(transport=transport, base_url="https://testserver") as second_client,
    ):
        first = await create_guest(first_client)
        second = await create_guest(second_client)
        profile = await create_confirmed_profile(first_client, first)
        await seed_runtime_release(database, settings)
        accepted = await first_client.post(
            "/api/v1/readings/preview",
            headers={**first, "Idempotency-Key": "guest-limit-1"},
            json={"profile_version_id": profile["profile_version_id"]},
        )
        limited = await first_client.post(
            "/api/v1/readings/preview",
            headers={**first, "Idempotency-Key": "guest-limit-2"},
            json={"profile_version_id": profile["profile_version_id"]},
        )
        other_profile = await create_confirmed_profile(
            second_client,
            second,
            label="另一访客",
            birth_datetime="1991-02-03T08:00:00+08:00",
        )
        isolated = await second_client.post(
            "/api/v1/readings/preview",
            headers={**second, "Idempotency-Key": "guest-limit-isolated"},
            json={"profile_version_id": other_profile["profile_version_id"]},
        )

    assert accepted.status_code == 201, accepted.text
    assert limited.status_code == 429, limited.text
    body = limited.json()
    assert body["code"] == "guest_daily_reading_limit"
    assert body["type"] == "urn:mingli:problem:guest_daily_reading_limit"
    assert body["owner_kind"] == "guest"
    assert body["limit_scope"] == "guest_session"
    assert body["limit"] == 1
    assert body["remaining"] == 0
    assert isolated.status_code == 201, isolated.text


async def test_exact_name_and_birth_conflict_and_fallback_name(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    first = await create_confirmed_profile(
        client,
        headers,
        label="访客测试",
        birth_datetime="1990-05-06T08:00:00+08:00",
    )
    draft = await client.post("/api/v1/profiles/drafts", headers=headers, json={})
    assert draft.status_code == 201, draft.text
    conflict = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1990-05-06T08:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
        },
    )
    named_draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "访客测试"},
    )
    named_conflict = await client.post(
        f"/api/v1/profiles/drafts/{named_draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1990-05-06T08:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
        },
    )
    saved = await client.post(
        f"/api/v1/profiles/drafts/{named_draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1990-05-06T08:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "on_name_conflict": "save_as",
        },
    )
    unnamed = await client.post("/api/v1/profiles/drafts", headers=headers, json={})
    fallback = await client.post(
        f"/api/v1/profiles/drafts/{unnamed.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1992-07-08T08:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
        },
    )

    assert conflict.status_code == 201, conflict.text
    assert conflict.json()["display_name"] == "档案 · 1990-05-06"
    assert named_conflict.status_code == 409, named_conflict.text
    assert named_conflict.json()["code"] == "profile_name_conflict"
    assert named_conflict.json()["existing_profile_id"] == first["profile_id"]
    assert named_conflict.json()["options"] == ["overwrite", "save_as", "cancel"]
    assert saved.status_code == 201, saved.text
    assert saved.json()["display_name"] == "访客测试 (2)"
    assert fallback.status_code == 201, fallback.text
    assert fallback.json()["display_name"] == "档案 · 1992-07-08"


def test_meihua_and_daliuren_view_models_publish_public_labels() -> None:
    meihua = project_meihua_view_model(
        brief(
            "meihua",
            {
                "casting_method": "time",
                "primary_hexagram": {
                    "name": "风雷益",
                    "upper_trigram": "巽",
                    "lower_trigram": "震",
                },
                "moving_lines": [2],
                "body_use": {
                    "body": {"position": "upper", "trigram": "巽", "element": "木"},
                    "use": {"position": "lower", "trigram": "震", "element": "木"},
                    "relation": "比和",
                    "status": "calculated_relation_not_verdict",
                },
            },
        )
    )
    assert meihua is not None
    labels = {item.key: item.label for item in meihua.public_labels}
    assert labels["calculated_relation_not_verdict"] == "关系已计算，尚非断语"
    assert labels["upper"] == "上卦"
    assert set(labels) >= {key for key, _ in MEIHUA_PUBLIC_LABELS}

    fixture = json.loads(
        (
            Path(__file__).resolve().parent
            / "fixtures"
            / "liuren-runtime-core-facts-v1.json"
        ).read_text(encoding="utf-8")
    )
    daliuren = project_daliuren_view_model(
        brief("liuren", {"runtime_core_facts": fixture})
    )
    assert daliuren is not None
    daliuren_labels = {item.key: item.label for item in daliuren.public_labels}
    assert daliuren_labels["transmissions_to_day"] == "传至日辰"
    assert daliuren_labels["initial_final_relation"] == "初末关系"
    assert set(daliuren_labels) >= {key for key, _ in DALIUREN_PUBLIC_LABELS}


async def test_chart_start_stops_polling_when_result_is_available(
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
        started = await client.post(
            "/api/v1/readings/preview",
            headers={**headers, "Idempotency-Key": "poll-stop"},
            json={"profile_version_id": profile["profile_version_id"]},
        )
        version_id = started.json()["reading_version_id"]
        polled = await client.get(f"/api/v1/readings/{version_id}")
        result = await client.get(f"/api/v1/readings/{version_id}/result")

    assert started.status_code == 201, started.text
    for body in (started.json(), polled.json(), result.json()):
        assert body["result_available"] is True
        assert body["poll_required"] is False
        assert body["poll_after_seconds"] is None


async def test_ziwei_runtime_stopped_error_is_typed_not_generic(
    database: Any,
    test_settings: Any,
) -> None:
    settings = test_settings.model_copy(update={"reading_write_rate_limit": 100})
    application = create_app(
        settings=settings,
        database=database,
        chart_runtime=StoppedErrorRuntime(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        headers = await create_guest(client)
        profile = await create_confirmed_profile(client, headers)
        await seed_runtime_release(database, settings)
        response = await client.post(
            "/api/v1/readings/ziwei",
            headers={**headers, "Idempotency-Key": "ziwei-typed-error"},
            json={"profile_version_id": profile["profile_version_id"]},
        )

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["code"] == "chart_runtime_error"
    assert body["type"] == "urn:mingli:problem:chart_runtime_error"
    assert body["detail"] == "紫微盘面计算失败。"
