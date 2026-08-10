import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.adapters.runtime import FakeMingliRuntimeAdapter
from app.identity.models import GuestSession
from app.readings.models import (
    GenerationAttempt,
    ReadingIdempotencyKey,
    ReadingJobRecord,
    ReadingRoot,
    ReadingVerification,
    ReadingVersion,
    RuntimeRelease,
)
from app.readings.request_compiler import compile_liuyao_prepare
from app.readings.runtime_contracts import Accepted, Prepared, ReadingBrief, Stopped
from app.security.envelope import EnvelopeCipher
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from test_profiles_api import (
    assert_private_headers,
    create_confirmed_profile,
    create_guest,
    login_current_guest,
)
from worker.readings import build_reading_worker

ACCEPTED_COPY = (
    "本命格局以稳定积累为主线。\n\n"
    "本解读仅供传统文化参考，不构成现实决策保证。"
)


async def seed_runtime_release(
    database: Any,
    settings: Any,
    *,
    production_ready: bool = True,
) -> None:
    readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
    cipher = EnvelopeCipher.from_settings(settings)
    async with database.sessions() as session:
        repository = readings.SqlReadingRepository(session, cipher)
        await repository.create_runtime_release(
            name="mingli-master-portable-core",
            version="5.1",
            source_commit="494ce0bba174a77800daf9b9c38ce9c9166d9a94",
            release_manifest_digest="e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68",
            protocol_version="mingli-portable-interface-v2",
            describe_manifest_digest="7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342",
            image_digest=None,
            production_ready=production_ready,
        )
        await session.commit()


class TokenEchoRuntime:
    """Fake Runtime that keeps the persisted state token across resumes."""

    def __init__(self) -> None:
        self._inner = FakeMingliRuntimeAdapter()

    async def execute(self, command: Any) -> Any:
        result = await self._inner.execute(command)
        if isinstance(result, Prepared):
            token = command.state_token or result.state_token
            return Prepared(state_token=token, brief=result.brief)
        return result


async def run_worker_once(
    database: Any,
    settings: Any,
    *,
    runtime: Any | None = None,
) -> bool:
    worker = build_reading_worker(
        settings=settings,
        database=database,
        worker_id="api-test-worker",
        runtime=runtime,
    )
    return await worker.run_once()


def brief_payload(subject_ref: str, horizon: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": "事业上最该先抓住哪条主线？",
        "vocabulary": [],
        "facts": [
            {
                "ref": "fact:career-structure",
                "subject_ref": subject_ref,
                "kind_id": "kind.structure",
                "value": {"fixture": "stable"},
                "display_text": "当前结构更支持持续积累。",
            }
        ],
        "evidence": [
            {
                "ref": "evidence:classic-1",
                "source_title": "测试古籍",
                "locator": "测试卷",
                "excerpt": "只用于合同测试的短摘录。",
                "supports_fact_refs": ["fact:career-structure"],
            }
        ],
        "findings": [
            {
                "ref": "finding:career-main",
                "subject_ref": subject_ref,
                "dimension_ids": ["career"],
                "kind_id": "kind.tendency",
                "data": {"fixture": True},
                "fact_refs": ["fact:career-structure"],
                "evidence_refs": ["evidence:classic-1"],
                "limit_kind_ids": ["limit:traditional"],
                "support_mode": "exact",
            }
        ],
        "claim_scopes": [
            {
                "subject_ref": subject_ref,
                "dimension_id": "career",
                "allowed_kind_ids": ["kind.tendency"],
                "certainty_ceiling_id": "certainty.tendency",
                "fact_refs": ["fact:career-structure"],
                "evidence_refs": ["evidence:classic-1"],
            }
        ],
        "limits": [
            {
                "kind_id": "limit:traditional",
                "public_text": "本解读仅供传统文化参考，不构成现实决策保证。",
                "scope_refs": [subject_ref],
                "detail_ids": [],
            }
        ],
        "prior_answer": None,
        "request_view": {
            "subject_refs": [subject_ref],
            "capability_ids": ["bazi"],
            "object_id": "natal",
            "dimension_ids": ["career"],
            "horizon": {
                "kind_id": str(horizon.get("kind_id")),
                "start": horizon.get("start"),
                "end": horizon.get("end"),
            },
        },
    }


async def advance_to_accepted(
    database: Any,
    settings: Any,
    *,
    version_id: str,
    subject_ref: str,
) -> None:
    readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
    cipher = EnvelopeCipher.from_settings(settings)
    async with database.sessions() as session:
        repository = readings.SqlReadingRepository(session, cipher)
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version.id,
                ReadingJobRecord.status == "queued",
            )
        )
        assert job is not None
        brief = ReadingBrief.from_dict(brief_payload(subject_ref, version.horizon))
        now = datetime.now(UTC)
        await repository.record_prepared(
            str(job.id),
            Prepared(state_token="api-test-token", brief=brief),
            now,
        )
        await repository.record_accepted(
            str(job.id),
            Accepted(state_token="api-test-token", public_copy=ACCEPTED_COPY),
            now,
        )
        await session.commit()


async def simulate_waiting_input(
    database: Any,
    settings: Any,
    *,
    version_id: str,
    input_request: dict[str, Any] | None = None,
) -> None:
    readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
    cipher = EnvelopeCipher.from_settings(settings)
    async with database.sessions() as session:
        repository = readings.SqlReadingRepository(session, cipher)
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version.id,
                ReadingJobRecord.status == "queued",
            )
        )
        assert job is not None
        stopped = Stopped(
            reason="need_input",
            public_copy="还需要补充摇卦输入。",
            state_token="api-supply-token",
            input_request=input_request
            or {
                "requirements": [
                    {
                        "any_of": [
                            {
                                "id": f"cast_{index}",
                                "label": f"第{index}爻",
                                "type_id": "integer",
                                "description": None,
                                "choices": [],
                            }
                        ]
                    }
                    for index in range(1, 7)
                ]
            },
        )
        await repository.record_waiting_input(
            str(job.id),
            stopped,
            datetime.now(UTC),
        )
        await session.commit()


async def start_waiting_liuyao(
    client: AsyncClient,
    database: Any,
    settings: Any,
    headers: dict[str, str],
) -> str:
    await seed_runtime_release(database, settings)
    started = await client.post(
        "/api/v1/readings/liuyao",
        headers=headers,
        json={
            "cast": "digital_coin",
            "event_datetime": "2026-08-10T12:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
            "dimension_ids": ["career"],
        },
    )
    assert started.status_code == 201, started.text
    version_id = started.json()["reading_version_id"]
    await simulate_waiting_input(database, settings, version_id=version_id)
    return version_id


async def start_preview(
    client: AsyncClient,
    headers: dict[str, str],
    profile_version_id: str,
    *,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    request_headers = dict(headers)
    if idempotency_key is not None:
        request_headers["Idempotency-Key"] = idempotency_key
    response = await client.post(
        "/api/v1/readings/preview",
        headers=request_headers,
        json={
            "profile_version_id": profile_version_id,
            "dimension_ids": ["career"],
        },
    )
    assert response.status_code in {200, 201}, response.text
    return response.json()


async def test_guest_starts_preview_reading_and_polls_a_queued_job(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )

    assert started.status_code == 201
    body = started.json()
    UUID(body["reading_version_id"])
    UUID(body["reading_root_id"])
    assert body["profile_version_id"] == confirmed["profile_version_id"]
    assert body["capability_id"] == "bazi"
    assert body["version"] == 1
    assert body["status"] == "input_ready"
    assert body["object_id"] == "natal"
    assert body["horizon"]["kind_id"] == "life"
    assert body["prior_answer"] is None
    assert_private_headers(started)

    polled = await client.get(f"/api/v1/readings/{body['reading_version_id']}")

    assert polled.status_code == 200
    assert polled.json()["status"] == "input_ready"
    assert_private_headers(polled)
    assert "state_token" not in polled.text
    assert "ciphertext" not in polled.text
    assert "1994-04-30" not in polled.text

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(body["reading_version_id"]))
        assert version is not None
        assert version.status == "input_ready"
        jobs = list(
            await session.scalars(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == version.id
                )
            )
        )
        assert len(jobs) == 1
        assert jobs[0].status == "queued"
        assert jobs[0].narrative_policy_version
        assert jobs[0].output_contract["contract_id"] == "preview-v1"


async def test_preview_job_reaches_accepted_under_default_local_fake_stack(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    assert started.status_code == 201, started.text
    version_id = started.json()["reading_version_id"]

    # run_worker_once builds the default local fake stack: the real
    # FakeMingliRuntimeAdapter + FakeModelGateway wiring driving the real
    # PREVIEW_V1 OutputContract through the real ReadingOrchestrator.
    processed = await run_worker_once(database, test_settings)
    assert processed is True

    # Drive the state machine until no job is claimable, with a hard bound so a
    # future requeue-without-progress regression fails instead of hanging tests.
    for _ in range(7):
        if not await run_worker_once(database, test_settings):
            break
    else:
        pytest.fail("preview job did not quiesce within eight worker iterations")

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version.id
            )
        )
        assert job is not None
        attempts = list(
            await session.scalars(
                select(GenerationAttempt)
                .where(GenerationAttempt.reading_version_id == version.id)
                .order_by(GenerationAttempt.attempt_number)
            )
        )

    assert job.status == "complete", (
        "preview job must reach accepted under the default local fake stack; "
        f"actual job status={job.status!r}, version status={version.status!r}, "
        "persisted attempts="
        f"{[(attempt.attempt_number, tuple(attempt.guard_errors)) for attempt in attempts]!r}"
    )
    assert version.status == "accepted"
    assert job.output_contract["contract_id"] == "preview-v1"
    assert len(attempts) == 1


async def test_today_and_week_jobs_reach_accepted_under_default_local_fake_stack(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    today = await client.post(
        "/api/v1/readings/today",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    week = await client.post(
        "/api/v1/readings/week",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    assert today.status_code == 201, today.text
    assert week.status_code == 201, week.text
    version_ids = [
        today.json()["reading_version_id"],
        week.json()["reading_version_id"],
    ]

    # run_worker_once builds the default local fake stack: the real
    # FakeMingliRuntimeAdapter + FakeModelGateway wiring driving the real
    # PREVIEW_V1 OutputContract through the real ReadingOrchestrator.
    processed = await run_worker_once(database, test_settings)
    assert processed is True

    # Drive the state machine until no job is claimable, with a hard bound so a
    # future requeue-without-progress regression fails instead of hanging tests.
    for _ in range(7):
        if not await run_worker_once(database, test_settings):
            break
    else:
        pytest.fail("fortune jobs did not quiesce within eight worker iterations")

    async with database.sessions() as session:
        for version_id in version_ids:
            version = await session.get(ReadingVersion, UUID(version_id))
            assert version is not None
            job = await session.scalar(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == version.id
                )
            )
            assert job is not None
            attempts = list(
                await session.scalars(
                    select(GenerationAttempt)
                    .where(GenerationAttempt.reading_version_id == version.id)
                    .order_by(GenerationAttempt.attempt_number)
                )
            )
            attempt_summary = [
                (attempt.attempt_number, tuple(attempt.guard_errors))
                for attempt in attempts
            ]
            assert job.status == "complete", (
                "fortune job must reach accepted under the default local fake stack; "
                f"actual job status={job.status!r}, version status={version.status!r}, "
                f"persisted attempts={attempt_summary!r}"
            )
            assert version.status == "accepted"
            assert len(attempts) == 1


async def test_reading_start_fails_closed_without_an_admitted_runtime_release(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(
        database,
        test_settings,
        production_ready=False,
    )

    response = await client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )

    assert response.status_code == 503
    assert response.json()["title"] == "Runtime release unavailable"


async def test_same_idempotency_key_returns_the_same_reading_version(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    first = await start_preview(
        client,
        headers,
        confirmed["profile_version_id"],
        idempotency_key="profile-preview-v1",
    )
    second = await start_preview(
        client,
        headers,
        confirmed["profile_version_id"],
        idempotency_key="profile-preview-v1",
    )

    assert second["reading_version_id"] == first["reading_version_id"]
    assert second["version"] == first["version"]
    async with database.sessions() as session:
        keys = list(await session.scalars(select(ReadingIdempotencyKey)))
        versions = list(await session.scalars(select(ReadingVersion)))
    assert len(keys) == 1
    assert len(versions) == 1
    assert len(keys[0].key_hash) == 64
    assert keys[0].key_hash != hashlib.sha256(b"profile-preview-v1").hexdigest()
    assert len(keys[0].request_fingerprint) == 64
    assert keys[0].action == "profile_preview"
    assert str(keys[0].reading_version_id) == first["reading_version_id"]


async def test_same_idempotency_key_with_different_payload_returns_conflict(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    first = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "payload-conflict-v1"},
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    assert first.status_code == 201, first.text

    conflict = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "payload-conflict-v1"},
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["overview"],
        },
    )

    assert conflict.status_code == 409
    assert conflict.json()["title"] == "Idempotency-Key conflict"


async def test_same_idempotency_key_with_different_action_returns_conflict(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    first = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "action-conflict-v1"},
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    assert first.status_code == 201, first.text

    conflict = await client.post(
        "/api/v1/readings/today",
        headers={**headers, "Idempotency-Key": "action-conflict-v1"},
        json={"profile_version_id": confirmed["profile_version_id"]},
    )

    assert conflict.status_code == 409
    assert conflict.json()["title"] == "Idempotency-Key conflict"


async def test_idempotency_replay_happens_before_profile_payload_decryption(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    monkeypatch: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    request = {
        "profile_version_id": confirmed["profile_version_id"],
        "dimension_ids": ["career"],
    }
    first = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "pre-decrypt-replay-v1"},
        json=request,
    )
    assert first.status_code == 201, first.text

    repository = __import__(
        "app.profiles.repository",
        fromlist=["ProfileRepository"],
    )

    async def fail_if_decrypted(*_: object, **__: object) -> dict[str, object]:
        raise AssertionError("profile payload must not be decrypted during replay")

    monkeypatch.setattr(
        repository.ProfileRepository,
        "load_version_payload",
        fail_if_decrypted,
    )
    replayed = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "pre-decrypt-replay-v1"},
        json=request,
    )

    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["reading_version_id"] == first.json()["reading_version_id"]


async def test_guest_idempotency_key_replays_the_same_version_after_login_claim(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    guest_headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, guest_headers)
    await seed_runtime_release(database, test_settings)
    payload = {
        "profile_version_id": confirmed["profile_version_id"],
        "dimension_ids": ["career"],
    }
    first = await client.post(
        "/api/v1/readings/preview",
        headers={**guest_headers, "Idempotency-Key": "claim-replay-v1"},
        json=payload,
    )
    assert first.status_code == 201, first.text

    logged_in = await login_current_guest(client, guest_headers)
    replayed = await client.post(
        "/api/v1/readings/preview",
        headers={
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "claim-replay-v1",
        },
        json=payload,
    )

    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["reading_version_id"] == first.json()["reading_version_id"]
    async with database.sessions() as session:
        records = list(await session.scalars(select(ReadingIdempotencyKey)))
    assert len(records) == 1
    assert str(records[0].owner_user_id) == logged_in["user_id"]
    assert records[0].owner_guest_session_id is None


async def test_guest_claim_resolves_user_idempotency_key_collision_in_favor_of_guest_flow(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    guest_headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, guest_headers)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/preview",
        headers={**guest_headers, "Idempotency-Key": "claim-collision-v1"},
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    assert started.status_code == 201, started.text

    identity_models = __import__(
        "app.identity.models",
        fromlist=["GuestSession", "User"],
    )
    profile_service = __import__(
        "app.profiles.service",
        fromlist=["ProfileService"],
    )
    async with database.sessions() as session:
        guest = (await session.scalars(select(identity_models.GuestSession))).one()
        guest_record = (
            await session.scalars(
                select(ReadingIdempotencyKey).where(
                    ReadingIdempotencyKey.owner_guest_session_id == guest.id
                )
            )
        ).one()
        user = identity_models.User()
        session.add(user)
        await session.flush()
        session.add(
            ReadingIdempotencyKey(
                key_hash=guest_record.key_hash,
                action=guest_record.action,
                request_fingerprint=guest_record.request_fingerprint,
                owner_user_id=user.id,
                reading_version_id=guest_record.reading_version_id,
            )
        )
        await session.flush()

        await profile_service.ProfileService(
            session,
            test_settings,
        ).claim_guest_ownership(guest, user.id)
        await session.commit()

    async with database.sessions() as session:
        records = list(await session.scalars(select(ReadingIdempotencyKey)))
    assert len(records) == 1
    assert records[0].id == guest_record.id
    assert records[0].owner_user_id == user.id
    assert records[0].owner_guest_session_id is None


async def test_reading_resources_are_owner_scoped_with_cross_owner_404(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=test_settings, database=database)

    async with (
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as first,
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as second,
    ):
        first_headers = await create_guest(first)
        confirmed = await create_confirmed_profile(first, first_headers)
        await seed_runtime_release(database, test_settings)
        started = await first.post(
            "/api/v1/readings/preview",
            headers=first_headers,
            json={
                "profile_version_id": confirmed["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )
        assert started.status_code == 201
        version_id = started.json()["reading_version_id"]

        second_headers = await create_guest(second)
        polled = await second.get(f"/api/v1/readings/{version_id}")
        supplied = await second.post(
            f"/api/v1/readings/{version_id}/input",
            headers=second_headers,
            json={"values": {"cast_1": 8}},
        )
        verified = await second.post(
            f"/api/v1/readings/{version_id}/verification",
            headers=second_headers,
            json={"outcome": "unknown"},
        )
        followed = await second.post(
            f"/api/v1/readings/{version_id}/follow-up",
            headers=second_headers,
            json={},
        )

    assert polled.status_code == 404
    assert supplied.status_code == 404
    assert verified.status_code == 404
    assert followed.status_code == 404


async def test_today_and_week_project_server_horizons(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    today = await client.post(
        "/api/v1/readings/today",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    week = await client.post(
        "/api/v1/readings/week",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )

    assert today.status_code == 201
    assert week.status_code == 201
    today_horizon = today.json()["horizon"]
    week_horizon = week.json()["horizon"]
    week_start = datetime.fromisoformat(week_horizon["start"]).date()
    assert today_horizon["end"] == today_horizon["start"]
    assert week_horizon["end"] == (week_start + timedelta(days=6)).isoformat()
    assert today.json()["capability_id"] == "fortune"
    assert week.json()["capability_id"] == "fortune"
    assert today.json()["version"] == 1
    assert week.json()["version"] == 1


@pytest.mark.parametrize(
    "forged_key",
    ["prior_answer", "unknown_runtime_field"],
)
async def test_supply_input_rejects_forged_or_unknown_keys(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    forged_key: str,
) -> None:
    headers = await create_guest(client)
    version_id = await start_waiting_liuyao(
        client,
        database,
        test_settings,
        headers,
    )

    response = await client.post(
        f"/api/v1/readings/{version_id}/input",
        headers=headers,
        json={"values": {"cast_1": 8, forged_key: "forged"}},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid reading input"


async def test_supply_input_rejects_wrong_runtime_field_type(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    version_id = await start_waiting_liuyao(
        client,
        database,
        test_settings,
        headers,
    )

    response = await client.post(
        f"/api/v1/readings/{version_id}/input",
        headers=headers,
        json={"values": {"cast_1": "8"}},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid reading input"


@pytest.mark.parametrize("cast_value", [5, 10])
async def test_supply_input_rejects_values_outside_the_field_range(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    cast_value: int,
) -> None:
    headers = await create_guest(client)
    version_id = await start_waiting_liuyao(
        client,
        database,
        test_settings,
        headers,
    )

    response = await client.post(
        f"/api/v1/readings/{version_id}/input",
        headers=headers,
        json={"values": {"cast_1": cast_value}},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid reading input"


async def test_supply_input_rejects_value_outside_declared_choices(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/liuyao",
        headers=headers,
        json={
            "cast": "digital_coin",
            "event_datetime": "2026-08-10T12:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
        },
    )
    assert started.status_code == 201, started.text
    version_id = started.json()["reading_version_id"]
    await simulate_waiting_input(
        database,
        test_settings,
        version_id=version_id,
        input_request={
            "requirements": [
                {
                    "any_of": [
                        {
                            "id": "zi_policy",
                            "label": "子时口径",
                            "type_id": "choice",
                            "description": None,
                            "choices": [
                                {
                                    "id": "midnight",
                                    "label": "午夜换日",
                                    "description": None,
                                },
                                {
                                    "id": "solar",
                                    "label": "太阳时",
                                    "description": None,
                                },
                            ],
                        }
                    ]
                }
            ]
        },
    )

    response = await client.post(
        f"/api/v1/readings/{version_id}/input",
        headers=headers,
        json={"values": {"zi_policy": "forged"}},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid reading input"


async def test_liuyao_need_input_supply_enqueues_a_tokenized_job(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/liuyao",
        headers=headers,
        json={
            "cast": "digital_coin",
            "event_datetime": "2026-08-10T12:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
            "dimension_ids": ["career"],
        },
    )

    assert started.status_code == 201
    version_id = started.json()["reading_version_id"]
    assert started.json()["capability_id"] == "liuyao"

    await simulate_waiting_input(database, test_settings, version_id=version_id)
    polled = await client.get(f"/api/v1/readings/{version_id}")
    assert polled.status_code == 200
    assert polled.json()["status"] == "waiting_input"
    assert polled.json()["input_request"]["requirements"][0]["any_of"][0]["id"] == "cast_1"

    supplied = await client.post(
        f"/api/v1/readings/{version_id}/input",
        headers=headers,
        json={
            "values": {
                "cast_1": 8,
                "cast_2": 7,
                "cast_3": 8,
                "cast_4": 7,
                "cast_5": 8,
                "cast_6": 7,
            }
        },
    )

    assert supplied.status_code == 201
    assert supplied.json()["reading_version_id"] == version_id
    assert supplied.json()["status"] == "input_ready"
    assert supplied.json()["input_request"] is None

    repeated = await client.post(
        f"/api/v1/readings/{version_id}/input",
        headers=headers,
        json={
            "values": {
                "cast_1": 8,
                "cast_2": 7,
                "cast_3": 8,
                "cast_4": 7,
                "cast_5": 8,
                "cast_6": 7,
            }
        },
    )
    assert repeated.status_code == 409
    assert repeated.json()["title"] == "Reading is not waiting for input"

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        jobs = list(
            await session.scalars(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == version.id
                )
            )
        )
        assert [job.status for job in jobs] == ["waiting_input", "queued"]
        cipher = EnvelopeCipher.from_settings(test_settings)
        readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
        repository = readings.SqlReadingRepository(session, cipher)
        supplied_job = next(job for job in jobs if job.status == "queued")
        loaded = await repository.load_job(str(supplied_job.id))
        assert loaded.prepare_command.state_token == "api-supply-token"
        assert loaded.prepare_command.transition == "correct"
        subject_ref = str(loaded.prepare_command.intent["subject_refs"][0])
        supplied_facts = loaded.prepare_command.facts[subject_ref]
        assert supplied_facts["cast"] == (8, 7, 8, 7, 8, 7)
        assert supplied_facts["event_datetime"] == "2026-08-10T12:00:00+08:00"
        assert supplied_facts["location"] == "北京市朝阳区"
        assert "prior_answer" not in supplied_facts

    processed = await run_worker_once(database, test_settings, runtime=TokenEchoRuntime())
    assert processed is True
    advanced = await client.get(f"/api/v1/readings/{version_id}")
    assert advanced.status_code == 200
    assert advanced.json()["status"] in {"prepared", "completing", "accepted"}


async def test_liuyao_start_rejects_an_unknown_timezone(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/liuyao",
        headers=headers,
        json={
            "cast": "digital_coin",
            "event_datetime": "2026-08-10T12:00:00+08:00",
            "timezone": "Mars/Olympus",
            "location": "北京市朝阳区",
            "dimension_ids": ["career"],
        },
    )

    assert started.status_code == 400
    assert started.json()["title"] == "Invalid request"


async def test_supply_input_active_job_collision_returns_conflict_not_500(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    version_id = await start_waiting_liuyao(
        client,
        database,
        test_settings,
        headers,
    )
    readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
    contracts = __import__("app.readings.output_contracts", fromlist=["PREVIEW_V1"])
    cipher = EnvelopeCipher.from_settings(test_settings)
    async with database.sessions() as session:
        repository = readings.SqlReadingRepository(session, cipher)
        await repository.create_job(
            reading_version_id=UUID(version_id),
            narrative_policy_version="narrative-policy-v1",
            output_contract=contracts.PREVIEW_V1,
            language="zh-CN",
            max_output_chars=1200,
            max_attempts=2,
        )
        await session.commit()

    response = await client.post(
        f"/api/v1/readings/{version_id}/input",
        headers=headers,
        json={
            "values": {
                "cast_1": 8,
                "cast_2": 7,
                "cast_3": 8,
                "cast_4": 7,
                "cast_5": 8,
                "cast_6": 7,
            }
        },
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Reading is already queued"
    polled = await client.get(f"/api/v1/readings/{version_id}")
    assert polled.status_code == 200
    assert polled.json()["status"] == "waiting_input"
    assert polled.json()["input_request"] is not None


async def test_accepted_result_verification_and_idempotent_verification(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    version_id = started.json()["reading_version_id"]
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    await advance_to_accepted(
        database,
        test_settings,
        version_id=version_id,
        subject_ref=subject_ref,
    )

    result = await client.get(f"/api/v1/readings/{version_id}/result")

    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "accepted"
    assert body["accepted_copy"] == ACCEPTED_COPY
    assert body["fact_panel"]["facts"][0]["display_text"] == "当前结构更支持持续积累。"
    assert body["fact_panel"]["limits"][0]["kind_id"] == "limit:traditional"
    assert body["verification"] is None
    assert_private_headers(result)
    assert "state_token" not in result.text
    assert "candidate" not in result.text
    assert "ciphertext" not in result.text
    assert "1994-04-30" not in result.text

    first_verification = await client.post(
        f"/api/v1/readings/{version_id}/verification",
        headers=headers,
        json={"outcome": "partial", "note": "部分准确"},
    )

    assert first_verification.status_code == 201
    verification_id = first_verification.json()["verification_id"]
    UUID(verification_id)
    assert first_verification.json()["outcome"] == "partial"
    assert first_verification.json()["note"] == "部分准确"

    # A verification is saved independently: it must not enqueue a new job,
    # transition the version, or change the published result.
    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        assert version.status == "accepted"
        jobs = list(
            await session.scalars(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == version.id
                )
            )
        )
        assert [job.status for job in jobs] == ["complete"]

    rechecked = await client.get(f"/api/v1/readings/{version_id}/result")
    assert rechecked.status_code == 200
    assert rechecked.json()["verification"]["verification_id"] == verification_id
    assert rechecked.json()["verification"]["outcome"] == "partial"
    assert rechecked.json()["status"] == "accepted"

    second_verification = await client.post(
        f"/api/v1/readings/{version_id}/verification",
        headers=headers,
        json={"outcome": "partial", "note": "部分准确"},
    )

    assert second_verification.status_code == 200
    assert second_verification.json()["verification_id"] == verification_id

    async with database.sessions() as session:
        stored = list(await session.scalars(select(ReadingVerification)))
        assert len(stored) == 1
        assert stored[0].outcome == "partial"
        assert stored[0].note == "部分准确"


def test_verification_request_accepts_only_the_four_authoritative_outcomes() -> None:
    schemas = __import__(
        "app.readings.api_schemas",
        fromlist=["VerificationRequest"],
    )
    for outcome in ("accepted", "partial", "disagreed", "unknown"):
        parsed = schemas.VerificationRequest.model_validate({"outcome": outcome})
        assert parsed.outcome == outcome
        assert parsed.note is None

    with pytest.raises(ValidationError):
        schemas.VerificationRequest.model_validate({"outcome": "accurate"})


async def test_follow_up_creates_a_new_version_with_projected_prior_answer(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    started = await start_preview(
        client,
        headers,
        confirmed["profile_version_id"],
        idempotency_key="follow-up-base",
    )
    version_id = started["reading_version_id"]
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    await advance_to_accepted(
        database,
        test_settings,
        version_id=version_id,
        subject_ref=subject_ref,
    )

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-v1"},
        json={},
    )

    assert followed.status_code == 201
    body = followed.json()
    assert body["version"] == 2
    assert body["reading_root_id"] == started["reading_root_id"]
    assert body["prior_answer"] == ACCEPTED_COPY
    assert body["status"] == "input_ready"

    replayed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-v1"},
        json={},
    )
    assert replayed.status_code == 200
    assert replayed.json()["reading_version_id"] == body["reading_version_id"]

    async with database.sessions() as session:
        versions = list(
            await session.scalars(
                select(ReadingVersion).order_by(ReadingVersion.version)
            )
        )
        roots = list(await session.scalars(select(ReadingRoot)))
        assert len(roots) == 1
        assert [version.version for version in versions] == [1, 2]
        assert len(
            list(
                await session.scalars(
                    select(ReadingJobRecord).where(
                        ReadingJobRecord.reading_version_id == versions[1].id
                    )
                )
            )
        ) == 1
        cipher = EnvelopeCipher.from_settings(test_settings)
        readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
        repository = readings.SqlReadingRepository(session, cipher)
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == versions[1].id
            )
        )
        loaded = await repository.load_job(str(job.id))
        assert loaded.prepare_command.facts[subject_ref]["prior_answer"] == ACCEPTED_COPY


async def test_reading_writes_require_matching_csrf(client: AsyncClient) -> None:
    await create_guest(client)
    response = await client.post(
        "/api/v1/readings/preview",
        json={"profile_version_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 403
    assert response.json()["title"] == "CSRF validation failed"


async def test_reading_start_writes_are_rate_limited(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    responses = []
    for _ in range(10):
        response = await client.post(
            "/api/v1/readings/preview",
            headers=headers,
            json={
                "profile_version_id": confirmed["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )
        responses.append(response.status_code)
    limited = await client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )

    assert responses == [201] * 10
    assert limited.status_code == 429
    assert limited.json()["title"] == "Too many reading requests"
    assert int(limited.headers["retry-after"]) >= 1


async def test_user_owner_can_start_a_reading_after_login_claim(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    logged_in = await login_current_guest(client, headers)
    user_headers = {"X-CSRF-Token": logged_in["csrf_token"]}

    started = await client.post(
        "/api/v1/readings/preview",
        headers=user_headers,
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )

    assert started.status_code == 201
    assert started.json()["profile_version_id"] == confirmed["profile_version_id"]

    async with database.sessions() as session:
        root = (await session.scalars(select(ReadingRoot))).one()
        assert str(root.owner_user_id) == logged_in["user_id"]
        assert root.owner_guest_session_id is None


async def _seed_release_id(database: Any) -> UUID:
    async with database.sessions() as session:
        release = await session.scalar(select(RuntimeRelease))
        assert release is not None
        return release.id


async def _seed_listed_version(
    database: Any,
    test_settings: Any,
    *,
    release_id: UUID,
    owner_guest_session_id: UUID | None,
    owner_user_id: UUID | None = None,
    version_id: UUID | None = None,
    created_at: datetime | None = None,
) -> str:
    version_id = version_id or uuid4()
    prepare = compile_liuyao_prepare(
        action="liuyao_one_question",
        query="请为这个问题起一卦。",
        subject_ref=f"liuyao:{uuid4().hex}",
        cast=(7, 8, 6, 9, 7, 8),
        event_datetime=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
        confirmed_timezone="Asia/Shanghai",
        location="北京市朝阳区",
        dimension_ids=("career",),
    )
    encrypted = EnvelopeCipher.from_settings(test_settings).encrypt_json(
        prepare.to_dict(),
        context=f"reading-version:{version_id}:prepare",
    )
    root_id = uuid4()
    version = ReadingVersion(
        id=version_id,
        reading_root_id=root_id,
        runtime_release_id=release_id,
        version=1,
        status="input_ready",
        capability_id="liuyao",
        object_id="one_question",
        dimension_ids=["career"],
        horizon={"kind_id": "one_question", "start": None, "end": None},
        prepare_key_id=encrypted.key_id,
        prepare_nonce=encrypted.nonce,
        prepare_ciphertext=encrypted.ciphertext,
        prepare_digest=encrypted.fingerprint,
        created_at=created_at or datetime.now(UTC),
    )
    root = ReadingRoot(
        id=root_id,
        owner_user_id=owner_user_id,
        owner_guest_session_id=owner_guest_session_id,
        capability_id="liuyao",
    )
    async with database.sessions() as session:
        session.add_all([root, version])
        await session.commit()
    return str(version.id)


async def test_list_readings_orders_newest_first_caps_at_50_and_stays_private(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    await create_guest(client)
    await seed_runtime_release(database, test_settings)
    release_id = await _seed_release_id(database)
    async with database.sessions() as session:
        guest = await session.scalar(
            select(GuestSession).order_by(GuestSession.created_at.desc())
        )
    assert guest is not None

    base = datetime(2026, 8, 1, tzinfo=UTC)
    seeded: list[str] = []
    for index in range(55):
        seeded.append(
            await _seed_listed_version(
                database,
                test_settings,
                release_id=release_id,
                owner_guest_session_id=guest.id,
                created_at=base + timedelta(minutes=index),
            )
        )

    # Two versions share the newest created_at; the id-descending tie-break
    # must order the higher UUID first.
    older_id, newer_id = uuid4(), uuid4()
    if older_id.int > newer_id.int:
        older_id, newer_id = newer_id, older_id
    shared_created_at = base + timedelta(minutes=60)
    await _seed_listed_version(
        database,
        test_settings,
        release_id=release_id,
        owner_guest_session_id=guest.id,
        version_id=older_id,
        created_at=shared_created_at,
    )
    await _seed_listed_version(
        database,
        test_settings,
        release_id=release_id,
        owner_guest_session_id=guest.id,
        version_id=newer_id,
        created_at=shared_created_at,
    )

    listed = await client.get("/api/v1/readings")

    assert listed.status_code == 200
    body = listed.json()
    version_ids = [item["reading_version_id"] for item in body["readings"]]
    assert len(version_ids) == 50
    assert version_ids[:2] == [str(newer_id), str(older_id)]
    assert version_ids[2:] == seeded[::-1][:48]

    item = body["readings"][0]
    assert set(item) == {
        "reading_version_id",
        "reading_root_id",
        "profile_version_id",
        "capability_id",
        "version",
        "status",
        "object_id",
        "dimension_ids",
        "horizon",
        "prior_answer",
        "input_request",
        "created_at",
    }
    assert item["reading_root_id"]
    assert item["profile_version_id"] is None
    assert item["capability_id"] == "liuyao"
    assert item["version"] == 1
    assert item["status"] == "input_ready"
    assert item["object_id"] == "one_question"
    assert item["dimension_ids"] == ["career"]
    assert item["horizon"] == {"kind_id": "one_question", "start": None, "end": None}
    assert item["prior_answer"] is None
    assert item["input_request"] is None
    assert_private_headers(listed)
    for banned in ("state_token", "ciphertext", "prompt", "candidate"):
        assert banned not in listed.text


async def test_list_readings_is_isolated_per_owner_and_survives_user_claim(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    guest_a = await create_guest(client)
    confirmed = await create_confirmed_profile(client, guest_a)
    await seed_runtime_release(database, test_settings)
    version_a = (
        await start_preview(
            client,
            guest_a,
            confirmed["profile_version_id"],
            idempotency_key="list-isolation-a",
        )
    )["reading_version_id"]

    listed_a = await client.get("/api/v1/readings")
    assert listed_a.status_code == 200
    assert [item["reading_version_id"] for item in listed_a.json()["readings"]] == [
        version_a
    ]

    guest_b = await create_guest(client)
    confirmed_b = await create_confirmed_profile(client, guest_b)
    version_b = (
        await start_preview(
            client,
            guest_b,
            confirmed_b["profile_version_id"],
            idempotency_key="list-isolation-b",
        )
    )["reading_version_id"]

    listed_b = await client.get("/api/v1/readings")
    assert listed_b.status_code == 200
    assert [item["reading_version_id"] for item in listed_b.json()["readings"]] == [
        version_b
    ]

    # After guest B claims a User account, the same session must still see only
    # its own readings: guest A's Version must never leak across owners.
    logged_in = await login_current_guest(client, guest_b)
    claimed = await client.get("/api/v1/readings")
    claimed_ids = [item["reading_version_id"] for item in claimed.json()["readings"]]
    assert claimed_ids == [version_b]
    assert str(logged_in["user_id"])
    assert version_a not in claimed_ids
