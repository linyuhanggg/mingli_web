from __future__ import annotations

import importlib
import json
import os
import shutil
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from app.adapters.model import FakeModelGateway
from app.adapters.runtime import build_runtime_startup_gate
from app.config import _RUNTIME_RELEASE_PROFILES, Settings
from app.main import create_app
from app.readings.models import ReadingJobRecord, ReadingVersion, RuntimeRelease
from app.readings.repository import SqlReadingRepository
from app.security.envelope import EnvelopeCipher
from httpx import ASGITransport, AsyncClient
from mingli_paths import MINGLI_RUNTIME_RELEASE_ROOT
from sqlalchemy import func, select
from worker.readings import build_reading_worker

# isort: split
from test_bazi_deep_vertical import _ExtractiveModel
from test_reading_worker import MutableClock

pytest_plugins = ("test_reading_worker",)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_RELEASE = MINGLI_RUNTIME_RELEASE_ROOT
RUNTIME_PYTHON = Path(
    os.environ.get(
        "MINGLI_RUNTIME_TEST_PYTHON",
        str(Path.home() / ".local/share/mingli-master/venv/bin/python"),
    )
)
RUNTIME_PYTHON_AVAILABLE = RUNTIME_PYTHON.is_file()

pytestmark = pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real PostgreSQL and frozen Runtime test is opt-in",
)


def _copy_admitted_release(tmp_path: Path) -> Path:
    if not SOURCE_RELEASE.is_dir():
        pytest.skip("the V53 Runtime release is not present")
    release_root = tmp_path / "v53-time-check-release"
    shutil.copytree(SOURCE_RELEASE, release_root, copy_function=shutil.copy2)
    manifest = json.loads(
        (release_root / ".mingli-release-manifest.json").read_text(encoding="utf-8")
    )
    for relative, mode in manifest["modes"].items():
        (release_root / relative).chmod(mode)
    return release_root


def _settings(tmp_path: Path, release_root: Path, database_url: str) -> Settings:
    profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]
    state_root = tmp_path / "runtime-state"
    state_root.mkdir(mode=0o700)
    state_root.chmod(0o700)
    return Settings(
        environment="test",
        database_url=database_url,
        cookie_secure=True,
        otp_adapter="fake",
        admin_bootstrap_email="ops@example.com",
        admin_bootstrap_password="correct-horse",
        runtime_adapter="one-shot",
        runtime_release_profile="v53-time-check",
        runtime_launcher_path=release_root / "scripts" / "run_reading_transaction.sh",
        runtime_python_path=RUNTIME_PYTHON,
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest=profile["manifest_digest"],
        runtime_expected_capability_shape_sha256=profile["capability_shape_sha256"],
    )


async def _create_v53_release(database: Any, settings: Settings) -> None:
    profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )
        await repository.create_runtime_release(
            name=profile["release_name"],
            version="5.3",
            source_commit=profile["source_commit"],
            release_manifest_digest=profile["release_manifest_sha256"],
            protocol_version="mingli-portable-interface-v2",
            describe_manifest_digest=profile["manifest_digest"],
            image_digest=None,
            production_ready=True,
        )


async def _create_v53_profile(client: AsyncClient, headers: dict[str, str]) -> dict[str, object]:
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "V53 时间校验夹具"},
    )
    assert draft.status_code == 201, draft.text
    confirmed = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "福建省福州市",
            "gender": "female",
            "time_basis_policy": "solar",
            "zi_hour_policy": "solar",
            "longitude": 119.2965,
            "latitude": 26.0745,
            "coordinate_source": "synthetic-fixture",
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    return cast(dict[str, object], confirmed.json())


class _FreePreviewExtractiveModel(_ExtractiveModel):
    """Exercise preview-v1 with three distinct exact public-source blocks."""

    async def generate(self, request: Any) -> Any:
        three_block_contract = replace(request.output_contract, min_blocks=3)
        return await super().generate(
            replace(request, output_contract=three_block_contract)
        )


def _write_stage_m_evidence(
    output_root: Path,
    result_payload: dict[str, object],
    citations: list[str],
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "vertical-result.json").write_text(
        json.dumps(result_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_root / "citations.txt").write_text(
        "\n".join(citations) + "\n",
        encoding="utf-8",
    )


async def test_bazi_free_preview_api_to_postgres_worker_accepted_document(
    postgres_worker_database: Any,
    tmp_path: Path,
) -> None:
    if not RUNTIME_PYTHON_AVAILABLE:
        pytest.skip("the dedicated Mingli Runtime Python is not installed")
    database_url = os.environ.get("MINGLI_TEST_POSTGRES_URL", "")
    release_root = _copy_admitted_release(tmp_path)
    settings = _settings(tmp_path, release_root, database_url)
    await _create_v53_release(postgres_worker_database, settings)

    application = create_app(
        settings=settings,
        database=postgres_worker_database,
        readiness_probe=_ready,
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        started_guest = await client.post("/api/v1/guest-sessions")
        assert started_guest.status_code == 201, started_guest.text
        headers = {"X-CSRF-Token": started_guest.json()["csrf_token"]}
        profile = await _create_v53_profile(client, headers)
        started = await client.post(
            "/api/v1/readings/preview",
            headers={**headers, "Idempotency-Key": "bazi-free-real-start"},
            json={
                "profile_version_id": profile["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )
        assert started.status_code == 201, started.text
        assert started.json()["product_id"] == "bazi"
        assert started.json()["delivery_state"] == "not_required"
        version_id = UUID(started.json()["reading_version_id"])

        gate = build_runtime_startup_gate(settings)
        await gate.startup()
        worker = build_reading_worker(
            settings=settings,
            database=postgres_worker_database,
            worker_id="bazi-free-postgres-vertical",
            runtime=gate.runtime,
            model=_FreePreviewExtractiveModel(),
        )
        assert [await worker.run_once() for _ in range(3)] == [True, True, True]
        assert await worker.run_once() is False

        result = await client.get(
            f"/api/v1/readings/{version_id}/result",
            headers=headers,
        )
        assert result.status_code == 200, result.text
        result_payload = result.json()
        release_profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]
        assert result_payload["status"] == "accepted"
        assert result_payload["view_model"]["schema_version"] == "bazi-chart/v1"
        assert result_payload["document"]["schema_version"] == "reading-document/v1"
        assert result_payload["document"]["view_model"] == result_payload["view_model"]
        assert result_payload["document"]["versions"]["runtime_release"] == (
            f"{release_profile['release_name']}@5.3"
        )

        citations = [
            item["excerpt"]
            for item in result_payload["fact_panel"]["evidence"]
            if item.get("verification_status") == "verified_exact"
            and isinstance(item.get("excerpt"), str)
            and item["excerpt"]
        ]
        assert len(citations) == 7

        evidence_root = os.environ.get("MINGLI_STAGE_M_EVIDENCE_DIR")
        if evidence_root:
            _write_stage_m_evidence(Path(evidence_root), result_payload, citations)

    async with postgres_worker_database.sessions() as session:
        repository = SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )
        version = await session.get(ReadingVersion, version_id)
        assert version is not None and version.status == "accepted"
        runtime_release = await session.get(RuntimeRelease, version.runtime_release_id)
        release_profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]
        assert runtime_release is not None
        assert runtime_release.release_manifest_digest == release_profile[
            "release_manifest_sha256"
        ]
        assert runtime_release.source_commit == release_profile["source_commit"]
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version_id
            )
        )
        assert job is not None and job.status == "complete"
        brief = await repository.load_fact_brief(version_id)
        candidate = await repository.load_successful_candidate(str(job.id))
        accepted_copy = await repository.load_accepted_copy(version_id)
        document = await repository.load_reading_document(version_id)
        assert brief is not None and candidate is not None
        assert accepted_copy is not None and document is not None

        brief_payload = brief.to_dict()
        public_sources = {
            **{
                str(item["ref"]): str(item["display_text"])
                for item in brief_payload["facts"]
            },
            **{
                str(item["ref"]): str(item["public_text"])
                for item in brief_payload["findings"]
                if isinstance(item.get("public_text"), str)
            },
            **{
                str(item["kind_id"]): str(item["public_text"])
                for item in brief_payload["limits"]
                if isinstance(item.get("public_text"), str)
            },
        }
        assert len(candidate.blocks) == 3
        source_refs: list[str] = []
        source_texts: list[str] = []
        for block in candidate.blocks:
            refs = [*block.fact_refs, *block.finding_refs, *block.limit_kind_ids]
            assert len(refs) == 1
            assert block.text == public_sources[refs[0]]
            source_refs.append(refs[0])
            source_texts.append(block.text)
        assert len(source_refs) == len(set(source_refs))
        assert len(source_texts) == len(set(source_texts))
        assert tuple(claim.text for claim in document.claims) == tuple(source_texts)
        assert accepted_copy == "\n\n".join(
            [*source_texts, "AI 辅助生成，仅供传统文化参考。"]
        )


async def _ready() -> None:
    return None


async def test_time_check_api_to_postgres_worker_document_and_web_result(
    postgres_worker_database: Any,
    tmp_path: Path,
) -> None:
    if not RUNTIME_PYTHON_AVAILABLE:
        pytest.skip("the dedicated Mingli Runtime Python is not installed")
    database_url = os.environ.get("MINGLI_TEST_POSTGRES_URL", "")
    release_root = _copy_admitted_release(tmp_path)
    settings = _settings(tmp_path, release_root, database_url)
    await _create_v53_release(postgres_worker_database, settings)

    async def readiness() -> None:
        return None

    application = create_app(
        settings=settings,
        database=postgres_worker_database,
        readiness_probe=readiness,
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        started_guest = await client.post("/api/v1/guest-sessions")
        assert started_guest.status_code == 201, started_guest.text
        headers = {"X-CSRF-Token": started_guest.json()["csrf_token"]}
        profile = await _create_v53_profile(client, headers)
        started = await client.post(
            "/api/v1/readings/time-check",
            headers={**headers, "Idempotency-Key": "time-check-sql-vertical-1"},
            json={
                "profile_version_id": profile["profile_version_id"],
                "time_range_start": "05:00",
                "time_range_end": "07:00",
                "known_events": ["synthetic-event-a"],
                "known_event_facts": [
                    {
                        "event_id": "synthetic-education",
                        "occurred_at": "2012-09-01",
                        "domain": "education",
                    },
                    {
                        "event_id": "synthetic-career",
                        "occurred_at": "2018-07-01T09:00:00+08:00",
                        "domain": "career",
                    },
                ],
                "query": "验证寻时定盘十二候选 Worker 闭环",
                "dimension_ids": ["time_options"],
            },
        )
        assert started.status_code == 201, started.text
        assert started.json()["capability_id"] == "time-check"
        assert started.json()["product_id"] == "time-check"
        version_id = UUID(started.json()["reading_version_id"])

        gate = build_runtime_startup_gate(settings)
        await gate.startup()
        worker = build_reading_worker(
            settings=settings,
            database=postgres_worker_database,
            worker_id="time-check-postgres-vertical",
            clock=MutableClock(datetime.now(UTC) + timedelta(minutes=1)),
            runtime=gate.runtime,
            model=FakeModelGateway(),
        )
        assert [await worker.run_once() for _ in range(3)] == [True, True, True]
        assert await worker.run_once() is False

        result = await client.get(
            f"/api/v1/readings/{version_id}/result",
            headers=headers,
        )
        assert result.status_code == 200, result.text
        result_payload = result.json()
        assert result_payload["document"]["schema_version"] == "reading-document/v1"
        assert result_payload["document"]["view_model"]["schema_version"] == "time-check-view/v1"
        assert result_payload["view_model"] == result_payload["document"]["view_model"]

        admin_login = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "ops@example.com", "password": "correct-horse"},
        )
        assert admin_login.status_code == 200, admin_login.text
        admin_detail = await client.get(
            f"/api/v1/admin/readings/{version_id}",
            headers={"X-CSRF-Token": admin_login.json()["csrf_token"]},
        )
        assert admin_detail.status_code == 200, admin_detail.text
        assert admin_detail.json()["time_check_summary"] == {
            "candidate_count": 12,
            "known_event_count": 2,
            "event_input_status": "structured_valid",
            "ranking_status": "candidate_evidence_ranked",
            "event_matching_status": "structured_evidence",
            "ranked_candidate_count": 12,
            "event_match_count": 2,
        }
        assert "synthetic-career" not in admin_detail.text
        assert "subject_ref" not in admin_detail.json()["time_check_summary"]

    readings = importlib.import_module("app.readings.models")
    async with postgres_worker_database.sessions() as session:
        version = await session.get(readings.ReadingVersion, version_id)
        job = await session.scalar(
            select(readings.ReadingJobRecord).where(
                readings.ReadingJobRecord.reading_version_id == version_id
            )
        )
        accepted_copy_count = await session.scalar(
            select(func.count(readings.AcceptedCopy.id)).where(
                readings.AcceptedCopy.reading_version_id == version_id
            )
        )
        document_count = await session.scalar(
            select(func.count(readings.ReadingDocumentRecord.id)).where(
                readings.ReadingDocumentRecord.reading_version_id == version_id
            )
        )
        assert version is not None
        assert job is not None
        assert version.status == "accepted"
        assert job.status == "complete"
        assert accepted_copy_count == 1
        assert document_count == 1

        document = await SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        ).load_reading_document(version_id)
        assert document is not None
        view = document.view_model
        assert view.schema_version == "time-check-view/v1"
        assert view.candidate_count == 12
        assert view.known_event_count == 2
        assert view.event_input_status == "structured_valid"
        assert view.ranking_status == "candidate_evidence_ranked"
        assert view.event_matching_status == "structured_evidence"
        assert len(view.candidate_rankings) == 12
        assert len(view.event_matches) == 2
        assert any("不等于古法断定" in text for text in view.limitations)
