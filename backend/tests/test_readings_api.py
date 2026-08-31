import asyncio
import hashlib
import importlib
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.adapters.runtime import (
    FakeMingliRuntimeAdapter,
    RuntimeTurnAudit,
    generic_runtime_stopped,
    runtime_command_digest,
)
from app.charts.projectors import project_runtime_view_model
from app.identity.models import GuestSession
from app.profiles.models import ProfileVersion, SubjectProfile
from app.readings.errors import RuntimeTransportError
from app.readings.models import (
    FactBrief,
    GenerationAttempt,
    ReadingIdempotencyKey,
    ReadingJobRecord,
    ReadingRoot,
    ReadingVerification,
    ReadingVersion,
    RuntimeRelease,
)
from app.readings.presentation import ReadingDocumentV1
from app.readings.request_compiler import compile_liuyao_prepare
from app.readings.runtime_contracts import (
    TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION,
    Accepted,
    Prepared,
    ReadingBrief,
    Stopped,
    TimeLayerEntitlementV1,
)
from app.readings.service import ReadingService
from app.readings.status import ReadingStatus
from app.security.envelope import EnvelopeCipher
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from worker.readings import build_reading_worker

# isort: split
from test_profiles_api import (
    assert_private_headers,
    create_confirmed_profile,
    create_guest,
    login_current_guest,
)

ACCEPTED_COPY = "本命格局以稳定积累为主线。\n\n本解读仅供传统文化参考，不构成现实决策保证。"


class PostgresApiDatabaseHarness:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def dispose(self) -> None:
        await self.engine.dispose()


@pytest.fixture
async def postgres_api_database() -> AsyncIterator[Any]:
    url = os.environ.get("MINGLI_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("MINGLI_TEST_POSTGRES_URL is required for PostgreSQL concurrency tests")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    importlib.import_module("app.admin.models")
    importlib.import_module("app.support.models")
    importlib.import_module("app.entitlements.models")
    importlib.import_module("app.commerce.models")
    importlib.import_module("app.referrals.models")
    importlib.import_module("app.content.models")
    importlib.import_module("app.privacy.models")
    importlib.import_module("app.media.models")
    schema = f"mingli_api_test_{uuid4().hex}"
    admin_engine = create_async_engine(url, pool_pre_ping=True)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": schema}},
    )
    database = PostgresApiDatabaseHarness(engine)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(identity_models.Base.metadata.create_all)
        yield database
    finally:
        await database.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


class UnsupportedChartRuntime:
    """Terminal Runtime result used to prove atomic Profile rollback."""

    adapter_kind = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, command: Any) -> Stopped:
        del command
        self.calls += 1
        return Stopped(
            reason="unsupported",
            public_copy="当前排盘能力暂不可用。",
        )


class NeedInputChartRuntime:
    """Correctable Runtime stop used to preserve the public 400 contract."""

    adapter_kind = "test-need-input"

    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, command: Any) -> Stopped:
        del command
        self.calls += 1
        return Stopped(
            reason="need_input",
            public_copy="还需要补充排盘信息。",
            state_token="need-input-chart-token",
            input_request={
                "requirements": [
                    {
                        "any_of": [
                            {
                                "id": "missing_chart_input",
                                "label": "补充信息",
                                "type_id": "text",
                                "description": None,
                                "choices": [],
                            }
                        ]
                    }
                ]
            },
        )


class TransportUnknownChartRuntime:
    """Tokenless transport fault that may have created a Runtime Root."""

    adapter_kind = "test-transport-unknown"

    def __init__(self, fault: str = "transport") -> None:
        self.calls = 0
        self.fault = fault

    async def execute(self, command: Any) -> None:
        del command
        self.calls += 1
        if self.fault == "timeout":
            raise TimeoutError
        if self.fault == "eof":
            raise RuntimeTransportError("runtime_pipe_eof")
        raise RuntimeTransportError("runtime_pipe_unavailable")


class PostWriteGenericStoppedChartRuntime:
    """Adapter-shaped post-write protocol fault returned as a generic Stopped."""

    adapter_kind = "runtime-worker-v2"

    def __init__(self, transport_fault: str) -> None:
        self.calls = 0
        self._last_sequence = 0
        self.last_turn: RuntimeTurnAudit | None = None
        self.transport_fault = transport_fault

    async def execute(self, command: Any) -> Stopped:
        self.calls += 1
        self._last_sequence = self.calls
        result = generic_runtime_stopped()
        self.last_turn = RuntimeTurnAudit(
            command_digest=runtime_command_digest(command),
            command_kind=command.kind,
            worker_pid=1234,
            worker_boot_nonce="test-boot",
            sequence=self.calls,
            result_kind=result.kind,
            failure=(
                None if result.failure is None else result.failure.to_audit_dict()
            ),
            transport_fault=self.transport_fault,
            isolated=True,
            store_root="test-runtime-store",
        )
        return result


class AuditPersistenceFailureChartRuntime:
    """WorkerV2-shaped Runtime whose valid result audit cannot be persisted."""

    adapter_kind = "runtime-worker-v2"

    def __init__(self) -> None:
        self.calls = 0
        self._last_sequence = 0
        self.last_turn: RuntimeTurnAudit | None = None
        self.result: Prepared | None = None
        self.published_result_kind: str | None = None

    async def execute(self, command: Any) -> Prepared:
        self.calls += 1
        self._last_sequence = self.calls
        subject_ref = next(iter(command.facts))
        result = Prepared(
            state_token="audit-persistence-failure-chart-token",
            brief=_bazi_chart_brief(subject_ref),
        )
        self.result = result
        self.published_result_kind = result.kind
        self.last_turn = RuntimeTurnAudit(
            command_digest=runtime_command_digest(command),
            command_kind=command.kind,
            worker_pid=1234,
            worker_boot_nonce="test-boot",
            sequence=self.calls,
            result_kind=result.kind,
            failure=None,
            transport_fault=None,
            isolated=False,
            store_root="test-runtime-store",
        )
        raise OSError("runtime audit state is read-only")


class RenderableChartRuntime:
    adapter_kind = "test-renderable"

    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, command: Any) -> Prepared:
        self.calls += 1
        subject_ref = next(iter(command.facts))
        return Prepared(
            state_token="renderable-chart-token",
            brief=_bazi_chart_brief(subject_ref),
        )


class UnrenderableChartRuntime:
    adapter_kind = "test-unrenderable"

    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, command: Any) -> Prepared:
        self.calls += 1
        subject_ref = next(iter(command.facts))
        payload = brief_payload(
            subject_ref,
            {"kind_id": "life", "start": None, "end": None},
        )
        payload["request_view"]["capability_ids"] = ["unsupported-test-capability"]
        return Prepared(
            state_token="unrenderable-chart-token",
            brief=ReadingBrief.from_dict(payload),
        )


def confirm_and_preview_payload() -> dict[str, Any]:
    return {
        "profile": {
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": 116.4074,
            "latitude": 39.9042,
            "coordinate_source": "user_confirmed",
        },
        "reading": {"dimension_ids": ["career"]},
    }


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
    public_copy: str = ACCEPTED_COPY,
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
            )
        )
        assert job is not None
        now = datetime.now(UTC)
        state_token = (
            None
            if version.state_token_fingerprint is None
            else await repository.load_state_token(version.id)
        )
        if await repository.load_fact_brief(version.id) is None:
            brief = ReadingBrief.from_dict(brief_payload(subject_ref, version.horizon))
            state_token = state_token or "api-test-token"
            await repository.record_prepared(
                str(job.id),
                Prepared(state_token=state_token, brief=brief),
                now,
            )
        await repository.record_accepted(
            str(job.id),
            Accepted(
                state_token=state_token or "api-test-token",
                public_copy=public_copy,
            ),
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
            )
        )
        assert job is not None
        state_token = (
            None
            if version.state_token_fingerprint is None
            else await repository.load_state_token(version.id)
        )
        stopped = Stopped(
            reason="need_input",
            public_copy="还需要补充摇卦输入。",
            state_token=state_token or "api-supply-token",
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
        headers={**headers, "Idempotency-Key": "waiting-liuyao-v1"},
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


def _bazi_chart_brief(
    subject_ref: str,
    *,
    include_year: bool = False,
    include_month: bool = False,
) -> ReadingBrief:
    facts: list[dict[str, Any]] = [
        {
            "ref": f"fact:{subject_ref}/calculated/bazi/four_pillars",
            "subject_ref": subject_ref,
            "kind_id": "kind.fact",
            "value": {
                "year": "甲戌",
                "month": "戊辰",
                "day": "丙戌",
                "hour": "辛卯",
            },
            "display_text": "四柱已由 Runtime 计算。",
        },
        {
            "ref": f"fact:{subject_ref}/calculated/bazi/element_inventory",
            "subject_ref": subject_ref,
            "kind_id": "kind.fact",
            "value": {
                "visible_stem_branch_counts": {
                    "木": 2,
                    "火": 1,
                    "土": 4,
                    "金": 1,
                }
            },
            "display_text": "五行可见干支计数已由 Runtime 计算。",
        },
    ]
    if include_year:
        from test_bazi_view_model_projector import _year_layer

        facts.append(
            {
                "ref": f"fact:{subject_ref}/calculated/bazi/year_layers",
                "subject_ref": subject_ref,
                "kind_id": "kind.fact",
                "value": _year_layer(),
                "display_text": "流年层已由 Runtime 计算。",
            }
        )
    if include_month:
        facts.append(
            {
                "ref": f"fact:{subject_ref}/calculated/bazi/month_layers",
                "subject_ref": subject_ref,
                "kind_id": "kind.fact",
                "value": {
                    "2026-08": {
                        "year": 2026,
                        "month": 8,
                        "ganzhi_segments": [{"ganzhi": "甲申"}],
                        "structural_changes": {"status": "fixture"},
                        "seasonal_tiaohou_delta": {"status": "fixture"},
                        "shensha_auxiliary": {"status": "fixture"},
                        "active_luck_cycle": {"status": "fixture"},
                        "calendar_normalization": {"status": "fixture"},
                        "rule_trace": [{"rule_id": "bazi.test.month"}],
                    }
                },
                "display_text": "流月层已由 Runtime 计算。",
            }
        )
    return ReadingBrief.from_dict(
        {
            "question": "查看本命四柱结构",
            "vocabulary": [],
            "facts": facts,
            "evidence": [],
            "findings": [],
            "claim_scopes": [],
            "limits": [],
            "prior_answer": None,
            "request_view": {
                "subject_refs": [subject_ref],
                "capability_ids": ["bazi"],
                "object_id": "natal",
                "dimension_ids": ["overview"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
            },
        }
    )


def _ziwei_chart_brief(
    subject_ref: str,
    *,
    include_month: bool = False,
) -> ReadingBrief:
    palaces = [
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
    facts: list[dict[str, Any]] = [
        {
            "ref": f"fact:{subject_ref}/calculated/ziwei/palaces",
            "subject_ref": subject_ref,
            "kind_id": "kind.structure",
            "value": palaces,
            "display_text": "十二宫盘面事实",
        }
    ]
    if include_month:
        facts.append(
            {
                "ref": f"fact:{subject_ref}/calculated/ziwei/monthly_layers",
                "subject_ref": subject_ref,
                "kind_id": "kind.fact",
                "value": {
                    "2032-01": {
                        "year": 2032,
                        "month": 1,
                        "liu_yue": {"palace": "命宫"},
                        "segments": [{"start": "2032-01-01"}],
                        "representative_scope": "month",
                    }
                },
                "display_text": "流月层已由 Runtime 计算。",
            }
        )
    return ReadingBrief.from_dict(
        {
            "question": "查看本命紫微盘",
            "vocabulary": [],
            "facts": facts,
            "evidence": [],
            "findings": [],
            "claim_scopes": [],
            "limits": [],
            "prior_answer": None,
            "request_view": {
                "subject_refs": [subject_ref],
                "capability_ids": ["ziwei"],
                "object_id": "natal",
                "dimension_ids": ["career"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
            },
        }
    )


async def replace_prepared_brief(
    database: Any,
    settings: Any,
    *,
    version_id: str,
    brief: ReadingBrief,
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
            )
        )
        assert job is not None
        existing_brief = await session.scalar(
            select(FactBrief).where(FactBrief.reading_version_id == version.id)
        )
        if existing_brief is not None:
            await session.delete(existing_brief)
            await session.flush()
        state_token = (
            None
            if version.state_token_fingerprint is None
            else await repository.load_state_token(version.id)
        )
        await repository.record_prepared(
            str(job.id),
            Prepared(
                state_token=state_token or "api-test-token",
                brief=brief,
            ),
            datetime.now(UTC),
        )
        await session.commit()


async def save_fact_referencing_document(
    database: Any,
    settings: Any,
    *,
    version_id: str,
    subject_ref: str,
    product_id: str,
    brief: ReadingBrief,
    public_fact_ref: str,
    supported_time_fact_ref: str,
) -> None:
    claim_texts = (
        "MIXED-CLAIM-MUST-DROP",
        "受支持流月事实形成的结论应保持引用闭包。",
        "公开结果必须保持事实引用闭包。",
        "公开边界可独立支撑这条结论。",
        "这条公开说明没有事实依赖。",
    )
    public_copy_suffix = "本解读仅供传统文化参考，不构成现实决策保证。"
    await advance_to_accepted(
        database,
        settings,
        version_id=version_id,
        subject_ref=subject_ref,
        public_copy="\n\n".join((*claim_texts, public_copy_suffix)),
    )
    view_model = project_runtime_view_model(brief.to_dict(), product_id=product_id)
    assert view_model is not None
    removed_fact_ref = (
        f"fact:{subject_ref}/calculated/{product_id}/unknown_engine_dump"
    )
    cipher = EnvelopeCipher.from_settings(settings)
    async with database.sessions() as session:
        readings = __import__(
            "app.readings.repository",
            fromlist=["SqlReadingRepository"],
        )
        repository = readings.SqlReadingRepository(session, cipher)
        version_uuid = UUID(version_id)
        accepted_copy = await repository.get_accepted_copy(version_uuid)
        assert accepted_copy is not None
        document = ReadingDocumentV1.model_validate(
            {
                "document_id": f"reading-version:{version_id}",
                "reading_version_id": version_id,
                "accepted_copy_ref": f"accepted-copy:{accepted_copy.id}",
                "product_version": f"{product_id}-reading/test",
                "presentation_contract_version": f"{product_id}-presentation/test",
                "view_model": view_model.model_dump(mode="json"),
                "answer_summary": "MIXED-CLAIM-MUST-DROP",
                "subject_summaries": [
                    {"subject_ref": subject_ref, "label": "本人"}
                ],
                "themes": [{"theme_id": "career", "label": "事业"}],
                "claims": [
                    {
                        "claim_id": "claim:mixed-must-drop",
                        "section_id": "overview",
                        "text": "MIXED-CLAIM-MUST-DROP",
                        "subject_ref": subject_ref,
                        "dimension_id": "career",
                        "claim_kind_id": "kind.tendency",
                        "certainty_id": "certainty.tendency",
                        "fact_refs": [public_fact_ref, removed_fact_ref],
                        "finding_refs": [],
                        "evidence_refs": ["evidence:mixed-must-drop"],
                        "limit_refs": [],
                        "verification": {"enabled": True},
                    },
                    {
                        "claim_id": "claim:time-layer",
                        "section_id": "overview",
                        "text": "受支持流月事实形成的结论应保持引用闭包。",
                        "subject_ref": subject_ref,
                        "dimension_id": "career",
                        "claim_kind_id": "kind.tendency",
                        "certainty_id": "certainty.tendency",
                        "fact_refs": [supported_time_fact_ref],
                        "finding_refs": [],
                        "evidence_refs": ["evidence:time-layer"],
                        "limit_refs": [],
                        "verification": {"enabled": True},
                    },
                    {
                        "claim_id": "claim:fact-closure",
                        "section_id": "overview",
                        "text": "公开结果必须保持事实引用闭包。",
                        "subject_ref": subject_ref,
                        "dimension_id": "career",
                        "claim_kind_id": "kind.tendency",
                        "certainty_id": "certainty.tendency",
                        "fact_refs": [public_fact_ref, supported_time_fact_ref],
                        "finding_refs": [],
                        "evidence_refs": [
                            "evidence:fact-closure",
                            "evidence:time-layer",
                        ],
                        "limit_refs": [],
                        "verification": {"enabled": True},
                    },
                    {
                        "claim_id": "claim:limit-only",
                        "section_id": "overview",
                        "text": "公开边界可独立支撑这条结论。",
                        "subject_ref": subject_ref,
                        "dimension_id": "career",
                        "claim_kind_id": "kind.tendency",
                        "certainty_id": "certainty.tendency",
                        "fact_refs": [],
                        "finding_refs": [],
                        "evidence_refs": [],
                        "limit_refs": ["limit:traditional"],
                        "verification": {"enabled": True},
                    },
                    {
                        "claim_id": "claim:empty-dependency",
                        "section_id": "overview",
                        "text": "这条公开说明没有事实依赖。",
                        "subject_ref": subject_ref,
                        "dimension_id": "career",
                        "claim_kind_id": "kind.tendency",
                        "certainty_id": "certainty.tendency",
                        "fact_refs": [],
                        "finding_refs": [],
                        "evidence_refs": [],
                        "limit_refs": [],
                        "verification": {"enabled": True},
                    },
                ],
                "evidence": [
                    {
                        "evidence_ref": "evidence:mixed-must-drop",
                        "title": "MIXED-EVIDENCE-MUST-DROP",
                        "supports_fact_refs": [
                            public_fact_ref,
                            removed_fact_ref,
                        ],
                    },
                    {
                        "evidence_ref": "evidence:fact-closure",
                        "title": "测试依据",
                        "supports_fact_refs": [
                            public_fact_ref,
                            supported_time_fact_ref,
                        ],
                    },
                    {
                        "evidence_ref": "evidence:time-layer",
                        "title": "流月事实依据",
                        "supports_fact_refs": [supported_time_fact_ref],
                    }
                ],
                "boundaries": [],
                "actions": {
                    "correction": {"enabled": True},
                    "follow_up": {"enabled": False},
                    "export": {"enabled": True},
                    "share": {"enabled": True},
                },
                "versions": {
                    "runtime_release": "mingli-runtime/test",
                    "view_model_schema": view_model.schema_version,
                },
            }
        )
        await repository.save_reading_document(
            version_id=version_uuid,
            accepted_copy_id=accepted_copy.id,
            document=document,
        )
        await session.commit()


def _entitlement_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["layer_id"]: item for item in payload["layers"]}


async def test_guest_starts_preview_reading_and_polls_a_prepared_chart(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.readings.service._profile_default_preview_year",
        lambda _profile: 2032,
    )
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "guest-preview-poll"},
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    replayed = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "guest-preview-poll"},
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )

    assert started.status_code == 201
    body = started.json()
    assert replayed.status_code == 200
    assert replayed.json()["reading_version_id"] == body["reading_version_id"]
    UUID(body["reading_version_id"])
    UUID(body["reading_root_id"])
    assert body["profile_version_id"] == confirmed["profile_version_id"]
    assert body["capability_id"] == "bazi"
    assert body["version"] == 1
    assert body["status"] == "prepared"
    assert body["fast_path_timing"]["execution_lane"] == "direct_runtime"
    assert body["fast_path_timing"]["queue_wait_ms"] == 0
    assert body["object_id"] == "natal"
    assert body["horizon"] == {
        "kind_id": "year",
        "start": "2032",
        "end": "2032",
    }
    assert body["prior_answer"] is None
    assert_private_headers(started)

    polled = await client.get(f"/api/v1/readings/{body['reading_version_id']}")

    assert polled.status_code == 200
    assert polled.json()["status"] == "prepared"
    assert polled.json()["poll_required"] is False
    assert polled.json()["poll_after_seconds"] is None
    assert_private_headers(polled)
    assert "state_token" not in polled.text
    assert "ciphertext" not in polled.text
    assert "1994-04-30" not in polled.text

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(body["reading_version_id"]))
        assert version is not None
        assert version.status == "prepared"
        jobs = list(
            await session.scalars(
                select(ReadingJobRecord).where(ReadingJobRecord.reading_version_id == version.id)
            )
        )
        assert len(jobs) == 1
        assert jobs[0].status == "complete"
        assert jobs[0].narrative_policy_version
        assert jobs[0].output_contract["contract_id"] == "preview-v1"
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1


def test_queued_prepared_reading_keeps_polling_until_job_is_complete() -> None:
    queued = ReadingService._poll_fields(
        ReadingStatus.PREPARED,
        object(),
        job_status="running",
    )
    direct_terminal = ReadingService._poll_fields(
        ReadingStatus.PREPARED,
        object(),
        job_status="complete",
    )

    assert queued == (True, True, 4)
    assert direct_terminal == (True, False, None)


@pytest.mark.parametrize(
    ("target", "expected_kind", "expected_boundary"),
    [
        ({"target_year": 2026}, "year", "2026"),
        ({"target_month": "2026-08"}, "month", "2026-08"),
        ({"target_date": "1800-01-01"}, "day", "1800-01-01"),
        ({"target_date": "2199-12-31"}, "day", "2199-12-31"),
        ({"target_date": "2026-08-15"}, "day", "2026-08-15"),
    ],
)
async def test_guest_starts_targeted_bazi_preview_with_public_horizon_boundary(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    target: dict[str, object],
    expected_kind: str,
    expected_boundary: str,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "targeted-bazi-preview"},
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
            **target,
        },
    )

    assert started.status_code == 201, started.text
    assert started.json()["horizon"] == {
        "kind_id": expected_kind,
        "start": expected_boundary,
        "end": expected_boundary,
    }


@pytest.mark.parametrize(
    "target",
    [
        {"target_year": 2026, "target_month": "2026-08"},
        {"target_month": "2026-08", "target_date": "2026-08-15"},
        {"target_month": "1799-12"},
        {"target_month": "2200-01"},
        {"target_date": "1799-12-31"},
        {"target_date": "2200-01-01"},
    ],
)
async def test_preview_rejects_invalid_time_targets_during_validation(
    client: AsyncClient,
    target: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_service_runs(*args: Any, **kwargs: Any) -> None:
        del args, kwargs
        raise AssertionError("request validation must reject before ReadingService")

    monkeypatch.setattr(ReadingService, "start_preview", fail_if_service_runs)
    headers = await create_guest(client)

    response = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "invalid-time-target-v1"},
        json={"profile_version_id": str(uuid4()), **target},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid request"


@pytest.mark.parametrize(
    "path, payload, expected_capability, expected_object",
    [
        (
            "/api/v1/readings/ziwei",
            {"dimension_ids": ["career"]},
            "ziwei",
            "natal",
        ),
        (
            "/api/v1/readings/qizheng",
            {"dimension_ids": ["career"]},
            "xingming",
            "natal",
        ),
        (
            "/api/v1/readings/canwen",
            {
                "selected_art_ids": ["bazi", "ziwei"],
                "query": "比较事业上的共同事实范围",
                "dimension_ids": ["career"],
            },
            "bazi",
            "natal",
        ),
        (
            "/api/v1/readings/hecan",
            {
                "selected_art_ids": ["bazi", "ziwei"],
                "dimension_ids": ["career"],
            },
            "bazi",
            "natal",
        ),
        (
            "/api/v1/readings/wenshi",
            {
                "cast": [6, 7, 8, 9, 6, 7],
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "这件事如何推进？",
                "dimension_ids": ["outcome", "timing"],
            },
            "liuyao",
            "concrete_event",
        ),
        (
            "/api/v1/readings/qimen",
            {
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "这件事如何推进？",
                "dimension_ids": ["outcome"],
            },
            "qimen",
            "concrete_event",
        ),
        (
            "/api/v1/readings/daliuren",
            {
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "这件事如何推进？",
                "dimension_ids": ["timing"],
                "timing_start": "2026-08-15",
                "timing_end": "2026-09-14",
            },
            "liuren",
            "concrete_event",
        ),
        (
            "/api/v1/readings/meihua",
            {
                "casting_method": "time",
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "这件事如何推进？",
                "dimension_ids": ["outcome", "state"],
            },
            "meihua",
            "concrete_event",
        ),
        (
            "/api/v1/readings/meihua",
            {
                "casting_method": "supplied_number",
                "number": 17,
                "provenance": {"kind": "user_supplied", "source": "api-test"},
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "按数字起卦看这件事如何推进？",
                "dimension_ids": ["outcome"],
            },
            "meihua",
            "concrete_event",
        ),
        (
            "/api/v1/readings/meihua",
            {
                "casting_method": "sound_count",
                "count": 9,
                "observation_source": {"kind": "sound_count", "source": "api-test"},
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "按声数起卦看这件事如何推进？",
                "dimension_ids": ["state"],
            },
            "meihua",
            "concrete_event",
        ),
        (
            "/api/v1/readings/meihua",
            {
                "casting_method": "observation",
                "upper_trigram": "乾",
                "lower_trigram": "坤",
                "observation_source": {"kind": "direct_observation", "source": "api-test"},
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "按观察起卦看这件事如何推进？",
                "dimension_ids": ["outcome"],
            },
            "meihua",
            "concrete_event",
        ),
        (
            "/api/v1/readings/meihua",
            {
                "casting_method": "supplied_hexagram",
                "upper_trigram": "乾",
                "lower_trigram": "坤",
                "moving_line": 4,
                "provenance": {"kind": "user_supplied", "source": "api-test"},
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "query": "按完整卦象看这件事如何推进？",
                "dimension_ids": ["state"],
            },
            "meihua",
            "concrete_event",
        ),
    ],
)
async def test_guest_starts_each_new_single_art_reading(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    path: str,
    payload: dict[str, Any],
    expected_capability: str,
    expected_object: str,
) -> None:
    headers = await create_guest(client)
    if expected_object == "natal":
        profile = await create_confirmed_profile(client, headers)
        payload = {**payload, "profile_version_id": profile["profile_version_id"]}
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        path,
        headers={**headers, "Idempotency-Key": "single-art-start"},
        json=payload,
    )

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["capability_id"] == expected_capability
    assert body["object_id"] == expected_object
    is_direct_chart = path in {
        "/api/v1/readings/ziwei",
        "/api/v1/readings/daliuren",
        "/api/v1/readings/meihua",
    }
    assert body["status"] == ("prepared" if is_direct_chart else "input_ready")
    expected_horizon = (
        "year"
        if path == "/api/v1/readings/ziwei"
        else "life"
        if expected_object == "natal"
        else "month"
        if path == "/api/v1/readings/daliuren"
        else "instant"
    )
    assert body["horizon"]["kind_id"] == expected_horizon
    if path == "/api/v1/readings/daliuren":
        assert body["horizon"]["start"] == "2026-08-15"
        assert body["horizon"]["end"] == "2026-09-14"
    if path == "/api/v1/readings/wenshi":
        assert body["product_id"] == "wenshi"
        assert body["runtime_capability_ids"] == ["liuyao", "qimen", "liuren"]
    if path == "/api/v1/readings/canwen":
        assert body["product_id"] == "canwen"
        assert body["runtime_capability_ids"] == ["bazi", "ziwei"]
    if path == "/api/v1/readings/hecan":
        assert body["product_id"] == "hecan"
        assert body["runtime_capability_ids"] == ["bazi", "ziwei"]
    assert_private_headers(started)

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(body["reading_version_id"]))
        assert version is not None
        jobs = list(
            await session.scalars(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == version.id
                )
            )
        )
        assert len(jobs) == 1
        assert jobs[0].status == ("complete" if is_direct_chart else "queued")


async def test_daliuren_timing_rejects_an_unbounded_public_request(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)

    started = await client.post(
        "/api/v1/readings/daliuren",
        headers=headers,
        json={
            "event_datetime": "2026-08-14T10:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "query": "这件事何时可能出现回应？",
            "dimension_ids": ["timing"],
        },
    )

    assert started.status_code == 400
    assert started.json()["title"] == "Invalid request"


async def test_qimen_deep_starts_with_a_frozen_structured_job_contract(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/qimen-deep",
        headers=headers,
        json={
            "event_datetime": "2026-08-14T10:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "subject_ref": "qimen-deep:api-contract",
            "query": "验证奇门深读合同链路",
            "dimension_ids": ["outcome", "timing", "state"],
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": 121.4737,
            "latitude": 31.2304,
            "coordinate_source": "synthetic-fixture",
        },
    )

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["capability_id"] == "qimen"
    assert body["product_id"] == "qimen-deep"
    assert body["object_id"] == "concrete_event"
    assert body["status"] == "input_ready"
    assert body["horizon"]["kind_id"] == "instant"
    assert_private_headers(started)

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(body["reading_version_id"]))
        assert version is not None
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version.id
            )
        )
        assert job is not None
        assert job.status == "awaiting_fulfillment"
        assert job.output_contract["contract_id"] == "qimen-deep-output-v1"
        assert job.output_contract["required_dimension_ids"] == [
            "outcome",
            "timing",
            "state",
        ]


async def test_qimen_deep_rejects_non_structured_dimension_selection(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)

    rejected = await client.post(
        "/api/v1/readings/qimen-deep",
        headers=headers,
        json={
            "event_datetime": "2026-08-14T10:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "dimension_ids": ["outcome"],
        },
    )

    assert rejected.status_code == 400, rejected.text
    assert rejected.json()["title"] == "Invalid reading input"


async def test_liuyao_deep_starts_with_candidate_evidence_contract(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/liuyao-deep",
        headers=headers,
        json={
            "cast": [6, 7, 8, 9, 7, 8],
            "event_datetime": "2026-08-14T10:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "subject_ref": "liuyao-deep:api-contract",
            "query": "验证六爻候选证据深读合同",
            "dimension_ids": ["outcome", "timing", "state"],
        },
    )

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["capability_id"] == "liuyao"
    assert body["product_id"] == "liuyao-deep"
    assert body["object_id"] == "concrete_event"
    assert body["status"] == "input_ready"
    assert body["horizon"]["kind_id"] == "instant"
    assert_private_headers(started)

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(body["reading_version_id"]))
        assert version is not None
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version.id
            )
        )
        assert job is not None
        assert job.status == "awaiting_fulfillment"
        assert job.output_contract["contract_id"] == "liuyao-deep-output-v1"
        assert job.output_contract["required_dimension_ids"] == [
            "outcome",
            "timing",
            "state",
        ]


async def test_liuyao_deep_rejects_partial_dimension_selection(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)

    rejected = await client.post(
        "/api/v1/readings/liuyao-deep",
        headers=headers,
        json={
            "cast": [6, 7, 8, 9, 7, 8],
            "event_datetime": "2026-08-14T10:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "dimension_ids": ["outcome"],
        },
    )

    assert rejected.status_code == 400, rejected.text
    assert rejected.json()["title"] == "Invalid reading input"


async def test_preview_chart_bypasses_worker_and_model_under_default_fake_stack(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "worker-bypass-preview"},
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    assert started.status_code == 201, started.text
    version_id = started.json()["reading_version_id"]

    processed = await run_worker_once(database, test_settings)
    assert processed is False

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        job = await session.scalar(
            select(ReadingJobRecord).where(ReadingJobRecord.reading_version_id == version.id)
        )
        assert job is not None
        attempts = list(
            await session.scalars(
                select(GenerationAttempt)
                .where(GenerationAttempt.reading_version_id == version.id)
                .order_by(GenerationAttempt.attempt_number)
            )
        )

    assert job.status == "complete"
    assert version.status == "prepared"
    assert job.output_contract["contract_id"] == "preview-v1"
    assert attempts == []


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
                select(ReadingJobRecord).where(ReadingJobRecord.reading_version_id == version.id)
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
                (attempt.attempt_number, tuple(attempt.guard_errors)) for attempt in attempts
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
        headers={**headers, "Idempotency-Key": "runtime-release-closed"},
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


async def test_confirm_and_preview_is_atomic_across_terminal_failure_and_retry(
    database: Any,
    test_settings: Any,
    monkeypatch: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = UnsupportedChartRuntime()
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "atomic-profile-preview-v1",
        }
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        draft_id = draft.json()["draft_id"]
        await seed_runtime_release(database, test_settings)

        failed = await atomic_client.post(
            f"/api/v1/profiles/drafts/{draft_id}/readings/preview",
            headers=headers,
            json=payload,
        )

        assert failed.status_code == 503, failed.text
        assert failed.json()["code"] == "chart_runtime_unsupported"
        listed_after_failure = await atomic_client.get("/api/v1/profiles")
        assert listed_after_failure.json() == {"profiles": []}
        async with database.sessions() as session:
            assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
            assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
            assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 0
            assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 0
            assert (
                await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)) == 0
            )

        application.state.chart_runtime = RenderableChartRuntime()
        succeeded = await atomic_client.post(
            f"/api/v1/profiles/drafts/{draft_id}/readings/preview",
            headers=headers,
            json=payload,
        )
        original_replay = ReadingService.replay_confirm_profile_preview
        discard_replay_once = True

        async def simulate_precommit_replay_miss(
            service: ReadingService,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            nonlocal discard_replay_once
            replay_result, context = await original_replay(service, *args, **kwargs)
            if discard_replay_once:
                discard_replay_once = False
                return None, context
            return replay_result, context

        monkeypatch.setattr(
            ReadingService,
            "replay_confirm_profile_preview",
            simulate_precommit_replay_miss,
        )
        replayed = await atomic_client.post(
            f"/api/v1/profiles/drafts/{draft_id}/readings/preview",
            headers=headers,
            json=payload,
        )

    assert succeeded.status_code == 201, succeeded.text
    assert succeeded.json()["status"] == "prepared"
    assert succeeded.json()["result_available"] is True
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["reading_version_id"] == succeeded.json()["reading_version_id"]
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)) == 1


async def test_confirm_and_preview_persists_unrenderable_prepared_checkpoint_without_saving_profile(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    runtime = UnrenderableChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "unrenderable-profile-preview-v1",
        }
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        draft_id = draft.json()["draft_id"]
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft_id}/readings/preview"

        first = await atomic_client.post(endpoint, headers=headers, json=payload)
        replay = await atomic_client.post(endpoint, headers=headers, json=payload)
        listed_after_failure = await atomic_client.get("/api/v1/profiles")

    assert first.status_code == 503, first.text
    assert first.json()["code"] == "chart_view_model_projection_failed"
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "prepared"
    assert replay.json()["result_available"] is False
    assert replay.json()["poll_required"] is False
    assert replay.json()["profile_version_id"] is None
    assert runtime.calls == 1
    assert listed_after_failure.json() == {"profiles": []}
    async with database.sessions() as session:
        version = await session.scalar(select(ReadingVersion))
        assert version is not None
        assert version.state_token_ciphertext is not None
        assert version.state_token_fingerprint is not None
        assert version.prepare_has_state_token is False
        root = await session.scalar(select(ReadingRoot))
        assert root is not None
        assert root.profile_version_id is None
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)) == 1
        assert await session.scalar(select(func.count()).select_from(FactBrief)) == 1
        assert list(await session.scalars(select(ReadingVersion.status))) == ["prepared"]
        assert list(await session.scalars(select(ReadingJobRecord.status))) == ["complete"]


async def test_confirm_and_preview_persists_transport_unknown_without_saving_profile(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    runtime = TransportUnknownChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "transport-unknown-profile-preview-v1",
        }
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        draft_id = draft.json()["draft_id"]
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft_id}/readings/preview"

        first = await atomic_client.post(endpoint, headers=headers, json=payload)
        replay = await atomic_client.post(endpoint, headers=headers, json=payload)
        listed_after_failure = await atomic_client.get("/api/v1/profiles")

    assert first.status_code == 503, first.text
    assert first.json()["code"] == "chart_runtime_transport"
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "runtime_unknown"
    assert runtime.calls == 1
    assert listed_after_failure.json() == {"profiles": []}
    async with database.sessions() as session:
        root = await session.scalar(select(ReadingRoot))
        assert root is not None
        assert root.profile_version_id is None
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)) == 1
        assert list(await session.scalars(select(ReadingVersion.status))) == [
            "runtime_unknown"
        ]
        assert list(await session.scalars(select(ReadingJobRecord.status))) == [
            "runtime_unknown"
        ]


@pytest.mark.parametrize(
    "transport_fault",
    ["unbound-result", "result-decode", "unbound-idle"],
)
async def test_confirm_and_preview_quarantines_post_write_generic_stopped_and_replays(
    database: Any,
    test_settings: Any,
    transport_fault: str,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    runtime = PostWriteGenericStoppedChartRuntime(transport_fault)
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": f"post-write-{transport_fault}-preview-v1",
        }
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = (
            f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"
        )

        first = await atomic_client.post(endpoint, headers=headers, json=payload)
        replay = await atomic_client.post(endpoint, headers=headers, json=payload)
        listed_after_failure = await atomic_client.get("/api/v1/profiles")

    assert first.status_code == 503, first.text
    assert first.json()["code"] == "chart_runtime_transport"
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "runtime_unknown"
    assert replay.json()["profile_version_id"] is None
    assert runtime.calls == 1
    assert listed_after_failure.json() == {"profiles": []}
    async with database.sessions() as session:
        root = await session.scalar(select(ReadingRoot))
        assert root is not None
        assert root.profile_version_id is None
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert (
            await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey))
            == 1
        )
        assert list(await session.scalars(select(ReadingVersion.status))) == [
            "runtime_unknown"
        ]
        assert list(await session.scalars(select(ReadingJobRecord.status))) == [
            "runtime_unknown"
        ]


async def test_confirm_and_preview_quarantines_valid_result_when_audit_persistence_fails(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    runtime = AuditPersistenceFailureChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "audit-persistence-failure-preview-v1",
        }
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = (
            f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"
        )

        first = await atomic_client.post(endpoint, headers=headers, json=payload)
        replay = await atomic_client.post(endpoint, headers=headers, json=payload)
        listed_after_failure = await atomic_client.get("/api/v1/profiles")

    assert isinstance(runtime.result, Prepared)
    assert runtime.published_result_kind == "prepared"
    assert first.status_code == 503, first.text
    assert first.json()["code"] == "chart_runtime_transport"
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "runtime_unknown"
    assert replay.json()["profile_version_id"] is None
    assert runtime.calls == 1
    assert listed_after_failure.json() == {"profiles": []}
    async with database.sessions() as session:
        root = await session.scalar(select(ReadingRoot))
        assert root is not None
        assert root.profile_version_id is None
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert (
            await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey))
            == 1
        )
        assert list(await session.scalars(select(ReadingVersion.status))) == [
            "runtime_unknown"
        ]
        assert list(await session.scalars(select(ReadingJobRecord.status))) == [
            "runtime_unknown"
        ]


@pytest.mark.parametrize(
    ("runtime_fault", "expected_code"),
    [
        ("timeout", "chart_runtime_timeout"),
        ("eof", "chart_runtime_transport"),
        ("transport", "chart_runtime_transport"),
    ],
)
async def test_confirm_and_preview_claims_unknown_before_cross_process_runtime(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
    runtime_fault: str,
    expected_code: str,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    runtime = TransportUnknownChartRuntime(runtime_fault)
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    first_unknown_rolled_back = asyncio.Event()
    release_first_quarantine = asyncio.Event()
    quarantine_calls = 0
    original_quarantine = ReadingService._persist_runtime_unknown_quarantine

    async def expose_rollback_to_detached_claim_window(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        nonlocal quarantine_calls
        quarantine_calls += 1
        if quarantine_calls == 1:
            first_unknown_rolled_back.set()
            await release_first_quarantine.wait()
        await original_quarantine(service, *args, **kwargs)

    monkeypatch.setattr(
        ReadingService,
        "_persist_runtime_unknown_quarantine",
        expose_rollback_to_detached_claim_window,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as first_client:
        guest_headers = await create_guest(first_client)
        logged_in = await login_current_guest(first_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "cross-process-transport-unknown-v1",
        }
        draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
            cookies=first_client.cookies,
        ) as second_client:
            first_request = asyncio.create_task(
                first_client.post(endpoint, headers=headers, json=payload)
            )
            await first_unknown_rolled_back.wait()
            second = await second_client.post(endpoint, headers=headers, json=payload)
            release_first_quarantine.set()
            first = await first_request
            replay = await second_client.post(endpoint, headers=headers, json=payload)
            listed_after_failure = await second_client.get("/api/v1/profiles")

    assert first.status_code == 503, first.text
    assert first.json()["code"] == expected_code
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "input_ready"
    assert second.json()["result_available"] is False
    assert second.json()["poll_required"] is True
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "runtime_unknown"
    assert replay.json()["reading_version_id"] == second.json()["reading_version_id"]
    assert runtime.calls == 1
    assert listed_after_failure.json() == {"profiles": []}
    async with database.sessions() as session:
        root = await session.scalar(select(ReadingRoot))
        assert root is not None
        assert root.profile_version_id is None
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)) == 1
        assert list(await session.scalars(select(ReadingVersion.status))) == [
            "runtime_unknown"
        ]
        assert list(await session.scalars(select(ReadingJobRecord.status))) == [
            "runtime_unknown"
        ]


async def test_confirm_and_preview_abandoned_claim_expires_and_replays_after_restart(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    runtime = RenderableChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    claim_committed = asyncio.Event()
    hold_abandoned_owner = asyncio.Event()
    original_claim = ReadingService._claim_atomic_profile_preview

    async def abandon_after_durable_claim(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        result = await original_claim(service, *args, **kwargs)
        if result is None and service._atomic_profile_preview_claim is not None:
            claim_committed.set()
            await hold_abandoned_owner.wait()
        return result

    monkeypatch.setattr(
        ReadingService,
        "_claim_atomic_profile_preview",
        abandon_after_durable_claim,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as first_client:
        guest_headers = await create_guest(first_client)
        logged_in = await login_current_guest(first_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "abandoned-profile-preview-v1",
        }
        draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"

        abandoned = asyncio.create_task(
            first_client.post(endpoint, headers=headers, json=payload)
        )
        await claim_committed.wait()
        abandoned.cancel()
        await asyncio.gather(abandoned, return_exceptions=True)

        before_expiry = await first_client.post(endpoint, headers=headers, json=payload)
        assert before_expiry.status_code == 200, before_expiry.text
        assert before_expiry.json()["status"] == "input_ready"
        assert before_expiry.json()["result_available"] is False
        assert before_expiry.json()["poll_required"] is True
        assert await run_worker_once(database, test_settings, runtime=runtime) is False

        reading_version_id = before_expiry.json()["reading_version_id"]
        async with database.sessions() as session:
            job = await session.scalar(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == UUID(reading_version_id)
                )
            )
            assert job is not None
            assert job.status == "claim_pending"
            assert job.lease_owner == "profile-preview-direct"
            assert job.lease_token is not None
            assert job.lease_expires_at is not None
            job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()

        restarted = main.create_app(settings=test_settings, database=database)
        restarted_runtime = RenderableChartRuntime()
        restarted.state.chart_runtime = restarted_runtime
        restarted.dependency_overrides[
            profiles_api._serialize_draft_preview
        ] = bypass_process_local_lock
        async with AsyncClient(
            transport=ASGITransport(app=restarted),
            base_url="https://testserver",
            cookies=first_client.cookies,
        ) as restarted_client:
            summary_after_expiry = await restarted_client.get(
                f"/api/v1/readings/{reading_version_id}"
            )
            after_expiry = await restarted_client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            fetched = await restarted_client.get(
                f"/api/v1/readings/{reading_version_id}/result"
            )
            stable_replay = await restarted_client.post(
                endpoint,
                headers=headers,
                json=payload,
            )

    assert summary_after_expiry.status_code == 200, summary_after_expiry.text
    assert summary_after_expiry.json()["status"] == "runtime_unknown"
    assert after_expiry.status_code == 200, after_expiry.text
    assert after_expiry.json()["status"] == "runtime_unknown"
    assert after_expiry.json()["reading_version_id"] == reading_version_id
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["status"] == "runtime_unknown"
    assert stable_replay.status_code == 200, stable_replay.text
    assert stable_replay.json()["reading_version_id"] == reading_version_id
    assert runtime.calls == 0
    assert restarted_runtime.calls == 0
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        ) == 1
        job = await session.scalar(select(ReadingJobRecord))
        assert job is not None
        assert job.status == "runtime_unknown"
        assert job.lease_owner is None
        assert job.lease_token is None
        assert job.lease_expires_at is None


@pytest.mark.parametrize("expire_claim", [False, True], ids=["active", "expired"])
async def test_foreign_owner_reads_do_not_stabilize_atomic_profile_preview_claim(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
    expire_claim: bool,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    runtime = UnsupportedChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    claim_committed = asyncio.Event()
    release_winner = asyncio.Event()
    claimed_version_id: UUID | None = None
    original_claim = ReadingService._claim_atomic_profile_preview

    async def pause_after_durable_claim(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal claimed_version_id
        result = await original_claim(service, *args, **kwargs)
        claim = service._atomic_profile_preview_claim
        if result is None and claim is not None:
            claimed_version_id = claim.reading_version_id
            claim_committed.set()
            await release_winner.wait()
        return result

    monkeypatch.setattr(
        ReadingService,
        "_claim_atomic_profile_preview",
        pause_after_durable_claim,
    )

    async with (
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as owner_client,
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as foreign_client,
    ):
        owner_guest = await create_guest(owner_client)
        owner_login = await login_current_guest(
            owner_client,
            owner_guest,
            destination="13800138000",
        )
        owner_headers = {
            "X-CSRF-Token": owner_login["csrf_token"],
            "Idempotency-Key": "foreign-read-ownership-v1",
        }
        foreign_guest = await create_guest(foreign_client)
        await login_current_guest(
            foreign_client,
            foreign_guest,
            destination="13900139000",
        )
        draft = await owner_client.post(
            "/api/v1/profiles/drafts",
            headers=owner_headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"

        winner = asyncio.create_task(
            owner_client.post(endpoint, headers=owner_headers, json=payload)
        )
        await asyncio.wait_for(claim_committed.wait(), timeout=5)
        assert claimed_version_id is not None
        if expire_claim:
            async with database.sessions() as session:
                job = await session.scalar(
                    select(ReadingJobRecord).where(
                        ReadingJobRecord.reading_version_id == claimed_version_id
                    )
                )
                assert job is not None
                job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
                await session.commit()
        try:
            foreign_summary = await foreign_client.get(
                f"/api/v1/readings/{claimed_version_id}"
            )
            foreign_result = await foreign_client.get(
                f"/api/v1/readings/{claimed_version_id}/result"
            )
            async with database.sessions() as session:
                observed_generation = await session.scalar(
                    select(ReadingJobRecord.lease_generation).where(
                        ReadingJobRecord.reading_version_id == claimed_version_id
                    )
                )
                observed_job_status = await session.scalar(
                    select(ReadingJobRecord.status).where(
                        ReadingJobRecord.reading_version_id == claimed_version_id
                    )
                )
                observed_version_status = await session.scalar(
                    select(ReadingVersion.status).where(
                        ReadingVersion.id == claimed_version_id
                    )
                )
        finally:
            release_winner.set()
        failed = await asyncio.wait_for(winner, timeout=10)

    assert foreign_summary.status_code == 404, foreign_summary.text
    assert foreign_result.status_code == 404, foreign_result.text
    assert observed_generation == 1
    assert observed_job_status == "claim_pending"
    assert observed_version_status == "input_ready"
    assert failed.status_code == 503, failed.text
    async with database.sessions() as session:
        if expire_claim:
            assert failed.json()["code"] == "chart_runtime_transport"
            assert runtime.calls == 0
            assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
            assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
            assert await session.scalar(
                select(func.count()).select_from(ReadingJobRecord)
            ) == 1
            assert await session.scalar(
                select(func.count()).select_from(ReadingIdempotencyKey)
            ) == 1
            assert await session.scalar(select(ReadingVersion.status)) == "runtime_unknown"
            assert await session.scalar(select(ReadingJobRecord.status)) == "runtime_unknown"
        else:
            assert failed.json()["code"] == "chart_runtime_unsupported"
            assert runtime.calls == 1
            assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 0
            assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 0
            assert await session.scalar(
                select(func.count()).select_from(ReadingJobRecord)
            ) == 0
            assert await session.scalar(
                select(func.count()).select_from(ReadingIdempotencyKey)
            ) == 0


@pytest.mark.parametrize(
    "listing_path",
    ["/api/v1/readings", "/api/v1/account/history"],
    ids=["reading-summaries", "account-history"],
)
async def test_listing_provisional_preview_claim_keeps_returned_id_replayable(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
    listing_path: str,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    runtime = UnsupportedChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    claim_committed = asyncio.Event()
    release_winner = asyncio.Event()
    claimed_version_id: UUID | None = None
    original_claim = ReadingService._claim_atomic_profile_preview

    async def pause_after_durable_claim(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal claimed_version_id
        result = await original_claim(service, *args, **kwargs)
        claim = service._atomic_profile_preview_claim
        if result is None and claim is not None:
            claimed_version_id = claim.reading_version_id
            claim_committed.set()
            await release_winner.wait()
        return result

    monkeypatch.setattr(
        ReadingService,
        "_claim_atomic_profile_preview",
        pause_after_durable_claim,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        guest_headers = await create_guest(client)
        logged_in = await login_current_guest(client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": f"list-exposes-preview-{listing_path.rsplit('/', 1)[-1]}-v1",
        }
        draft = await client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"

        winner = asyncio.create_task(client.post(endpoint, headers=headers, json=payload))
        await asyncio.wait_for(claim_committed.wait(), timeout=5)
        assert claimed_version_id is not None
        try:
            listing = await client.get(listing_path)
            async with database.sessions() as session:
                observed_generation = await session.scalar(
                    select(ReadingJobRecord.lease_generation).where(
                        ReadingJobRecord.reading_version_id == claimed_version_id
                    )
                )
        finally:
            release_winner.set()
        failed = await asyncio.wait_for(winner, timeout=10)
        fetched = await client.get(f"/api/v1/readings/{claimed_version_id}")

    assert listing.status_code == 200, listing.text
    if listing_path == "/api/v1/readings":
        listed_version_ids = {
            item["reading_version_id"] for item in listing.json()["readings"]
        }
    else:
        listed_version_ids = {
            item["reading_version_id"]
            for root in listing.json()["roots"]
            for item in root["versions"]
        }
    assert str(claimed_version_id) in listed_version_ids
    assert observed_generation == 2
    assert failed.status_code == 503, failed.text
    assert failed.json()["code"] == "chart_runtime_unsupported"
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["reading_version_id"] == str(claimed_version_id)
    assert fetched.json()["status"] == "terminal_stopped"
    assert fetched.json()["poll_required"] is False
    assert runtime.calls == 1


async def test_confirm_and_preview_expired_claim_beats_late_winner(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    runtime = RenderableChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    claim_committed = asyncio.Event()
    release_late_winner = asyncio.Event()
    recovery_lock_orders: list[tuple[type[Any], ...]] = []
    original_claim = ReadingService._claim_atomic_profile_preview
    original_recover = ReadingService._recover_expired_atomic_profile_preview_claim

    async def pause_after_durable_claim(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        result = await original_claim(service, *args, **kwargs)
        if result is None and service._atomic_profile_preview_claim is not None:
            claim_committed.set()
            await release_late_winner.wait()
        return result

    monkeypatch.setattr(
        ReadingService,
        "_claim_atomic_profile_preview",
        pause_after_durable_claim,
    )

    async def record_recovery_lock_order(
        service: ReadingService,
        version_id: UUID,
    ) -> bool:
        locked_entities: list[type[Any]] = []
        original_scalar = service.session.scalar

        async def recording_scalar(statement: Any, *args: Any, **kwargs: Any) -> Any:
            if getattr(statement, "_for_update_arg", None) is not None:
                entity = statement.column_descriptions[0].get("entity")
                if entity in (ReadingVersion, ReadingJobRecord):
                    locked_entities.append(entity)
            return await original_scalar(statement, *args, **kwargs)

        service.session.scalar = recording_scalar  # type: ignore[method-assign]
        try:
            recovered = await original_recover(service, version_id)
        finally:
            service.session.scalar = original_scalar  # type: ignore[method-assign]
        if recovered:
            recovery_lock_orders.append(tuple(locked_entities))
        return recovered

    monkeypatch.setattr(
        ReadingService,
        "_recover_expired_atomic_profile_preview_claim",
        record_recovery_lock_order,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as first_client:
        guest_headers = await create_guest(first_client)
        logged_in = await login_current_guest(first_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "expired-late-winner-preview-v1",
        }
        draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
            cookies=first_client.cookies,
        ) as second_client:
            late_winner = asyncio.create_task(
                first_client.post(endpoint, headers=headers, json=payload)
            )
            await claim_committed.wait()
            provisional = await second_client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            reading_version_id = provisional.json()["reading_version_id"]
            async with database.sessions() as session:
                job = await session.scalar(select(ReadingJobRecord))
                assert job is not None
                job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
                await session.commit()

            recovered = await second_client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            release_late_winner.set()
            late = await late_winner
            stable = await second_client.post(endpoint, headers=headers, json=payload)

    assert provisional.status_code == 200, provisional.text
    assert provisional.json()["status"] == "input_ready"
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "runtime_unknown"
    assert recovered.json()["reading_version_id"] == reading_version_id
    assert late.status_code == 503, late.text
    assert late.json()["code"] == "chart_runtime_transport"
    assert stable.status_code == 200, stable.text
    assert stable.json()["reading_version_id"] == reading_version_id
    assert stable.json()["status"] == "runtime_unknown"
    assert runtime.calls == 0
    assert recovery_lock_orders == [(ReadingVersion, ReadingJobRecord)]
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        ) == 1
        assert list(await session.scalars(select(ReadingVersion.status))) == [
            "runtime_unknown"
        ]
        assert list(await session.scalars(select(ReadingJobRecord.status))) == [
            "runtime_unknown"
        ]


async def test_confirm_and_preview_late_winner_replay_survives_recovery_rollback(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    readings_service_module = __import__(
        "app.readings.service",
        fromlist=["_ATOMIC_PROFILE_PREVIEW_CLAIM_LEASE_SECONDS"],
    )
    repository_module = __import__(
        "app.readings.repository",
        fromlist=["SqlReadingRepository"],
    )
    runtime = RenderableChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    monkeypatch.setattr(
        readings_service_module,
        "_ATOMIC_PROFILE_PREVIEW_CLAIM_LEASE_SECONDS",
        1,
    )
    payload = confirm_and_preview_payload()
    winner_at_attach = asyncio.Event()
    release_late_winner = asyncio.Event()
    recovery_at_version_lock = asyncio.Event()
    release_recovery = asyncio.Event()
    claimed_version_id: UUID | None = None
    recovery_paused = False
    original_attach = repository_module.SqlReadingRepository.attach_start_claim_profile
    original_recover = ReadingService._recover_expired_atomic_profile_preview_claim

    async def pause_after_claim_validation(
        repository: Any,
        version_id: UUID,
        profile_version_id: UUID,
    ) -> Any:
        nonlocal claimed_version_id
        claimed_version_id = version_id
        winner_at_attach.set()
        await release_late_winner.wait()
        return await original_attach(repository, version_id, profile_version_id)

    monkeypatch.setattr(
        repository_module.SqlReadingRepository,
        "attach_start_claim_profile",
        pause_after_claim_validation,
    )

    async def pause_recovery_before_version_lock(
        service: ReadingService,
        version_id: UUID,
    ) -> bool:
        nonlocal recovery_paused
        original_scalar = service.session.scalar

        async def pausing_scalar(statement: Any, *args: Any, **kwargs: Any) -> Any:
            nonlocal recovery_paused
            entity = statement.column_descriptions[0].get("entity")
            if (
                not recovery_paused
                and getattr(statement, "_for_update_arg", None) is not None
                and entity is ReadingVersion
            ):
                recovery_paused = True
                recovery_at_version_lock.set()
                await release_recovery.wait()
            return await original_scalar(statement, *args, **kwargs)

        service.session.scalar = pausing_scalar  # type: ignore[method-assign]
        try:
            return await original_recover(service, version_id)
        finally:
            service.session.scalar = original_scalar  # type: ignore[method-assign]

    monkeypatch.setattr(
        ReadingService,
        "_recover_expired_atomic_profile_preview_claim",
        pause_recovery_before_version_lock,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as first_client:
        guest_headers = await create_guest(first_client)
        logged_in = await login_current_guest(first_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "expired-late-winner-rollback-v1",
        }
        draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"

        async with AsyncClient(
            transport=ASGITransport(app=application, raise_app_exceptions=False),
            base_url="https://testserver",
            cookies=first_client.cookies,
        ) as replay_client:
            late_winner = asyncio.create_task(
                first_client.post(endpoint, headers=headers, json=payload)
            )
            await asyncio.wait_for(winner_at_attach.wait(), timeout=5)
            assert claimed_version_id is not None
            await asyncio.sleep(1.1)

            replay_task = asyncio.create_task(
                replay_client.post(endpoint, headers=headers, json=payload)
            )
            try:
                await asyncio.wait_for(recovery_at_version_lock.wait(), timeout=5)
                release_late_winner.set()
                late = await asyncio.wait_for(late_winner, timeout=10)
            finally:
                release_late_winner.set()
                release_recovery.set()
            replay = await asyncio.wait_for(replay_task, timeout=10)

    assert late.status_code == 201, late.text
    assert late.json()["status"] == "prepared"
    assert replay.status_code == 200, replay.text
    assert replay.json()["reading_version_id"] == str(claimed_version_id)
    assert replay.json()["status"] == "prepared"
    assert runtime.calls == 1
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        ) == 1


async def test_confirm_and_preview_exposed_claim_keeps_terminal_failure_replayable(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    runtime = UnsupportedChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    claim_committed = asyncio.Event()
    release_winner = asyncio.Event()
    original_claim = ReadingService._claim_atomic_profile_preview

    async def pause_after_durable_claim(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        result = await original_claim(service, *args, **kwargs)
        if result is None and service._atomic_profile_preview_claim is not None:
            claim_committed.set()
            await release_winner.wait()
        return result

    monkeypatch.setattr(
        ReadingService,
        "_claim_atomic_profile_preview",
        pause_after_durable_claim,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as first_client:
        guest_headers = await create_guest(first_client)
        logged_in = await login_current_guest(first_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "exposed-terminal-failure-preview-v1",
        }
        draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
            cookies=first_client.cookies,
        ) as second_client:
            winner = asyncio.create_task(
                first_client.post(endpoint, headers=headers, json=payload)
            )
            await claim_committed.wait()
            provisional = await second_client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            reading_version_id = provisional.json()["reading_version_id"]
            release_winner.set()
            failed = await winner
            replay = await second_client.post(endpoint, headers=headers, json=payload)
            fetched = await second_client.get(
                f"/api/v1/readings/{reading_version_id}/result"
            )

    assert provisional.status_code == 200, provisional.text
    assert provisional.json()["status"] == "input_ready"
    assert failed.status_code == 503, failed.text
    assert failed.json()["code"] == "chart_runtime_unsupported"
    assert replay.status_code == 200, replay.text
    assert replay.json()["reading_version_id"] == reading_version_id
    assert replay.json()["status"] == "terminal_stopped"
    assert replay.json()["poll_required"] is False
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["status"] == "terminal_stopped"
    assert runtime.calls == 1
    async with database.sessions() as session:
        root = await session.scalar(select(ReadingRoot))
        job = await session.scalar(select(ReadingJobRecord))
        assert root is not None
        assert root.profile_version_id is None
        assert job is not None
        assert job.status == "stopped"
        assert job.lease_owner is None
        assert job.lease_token is None
        assert job.lease_expires_at is None
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        ) == 1


async def test_postgresql_late_identical_preview_replay_keeps_failure_stable(
    postgres_api_database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    runtime_started = asyncio.Event()
    release_runtime = asyncio.Event()
    runtime_returned = asyncio.Event()
    settlement_commit_started = asyncio.Event()
    release_settlement_commit = asyncio.Event()
    replay_intent_started = asyncio.Event()

    class BlockingUnsupportedChartRuntime:
        adapter_kind = "fake"

        def __init__(self) -> None:
            self.calls = 0

        async def execute(self, command: Any) -> Stopped:
            del command
            self.calls += 1
            runtime_started.set()
            await release_runtime.wait()
            runtime_returned.set()
            return Stopped(
                reason="unsupported",
                public_copy="当前排盘能力暂不可用。",
            )

    runtime = BlockingUnsupportedChartRuntime()
    application = main.create_app(settings=test_settings, database=postgres_api_database)
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    original_hold_intent = ReadingService._hold_atomic_profile_preview_replay_intent
    original_commit = AsyncSession.commit
    settlement_commit_paused = False

    async def observe_replay_intent(
        service: ReadingService,
        idempotency: Any,
    ) -> None:
        replay_intent_started.set()
        await original_hold_intent(service, idempotency)

    async def pause_settlement_commit(session: AsyncSession) -> None:
        nonlocal settlement_commit_paused
        if runtime_returned.is_set() and not settlement_commit_paused:
            settlement_commit_paused = True
            settlement_commit_started.set()
            await release_settlement_commit.wait()
        await original_commit(session)

    monkeypatch.setattr(
        ReadingService,
        "_hold_atomic_profile_preview_replay_intent",
        observe_replay_intent,
    )
    monkeypatch.setattr(
        AsyncSession,
        "commit",
        pause_settlement_commit,
    )
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as winner_client:
        guest_headers = await create_guest(winner_client)
        logged_in = await login_current_guest(winner_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "postgres-blocked-terminal-preview-v1",
        }
        draft = await winner_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(postgres_api_database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
            cookies=winner_client.cookies,
        ) as replay_client:
            winner_task = asyncio.create_task(
                winner_client.post(endpoint, headers=headers, json=payload)
            )
            await asyncio.wait_for(runtime_started.wait(), timeout=5)
            release_runtime.set()
            await asyncio.wait_for(settlement_commit_started.wait(), timeout=5)
            replay_task = asyncio.create_task(
                replay_client.post(endpoint, headers=headers, json=payload)
            )
            try:
                await asyncio.wait_for(replay_intent_started.wait(), timeout=5)
                await asyncio.sleep(0.1)
                assert not replay_task.done()
                release_settlement_commit.set()
                failed = await asyncio.wait_for(winner_task, timeout=10)
                replay = await asyncio.wait_for(replay_task, timeout=10)
            finally:
                release_runtime.set()
                release_settlement_commit.set()
            stable_replay = await replay_client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            assert runtime.calls == 1
            different_key_headers = {
                **headers,
                "Idempotency-Key": "postgres-different-terminal-preview-v1",
            }
            different_key_failed = await winner_client.post(
                endpoint,
                headers=different_key_headers,
                json=payload,
            )
            different_key_replay = await replay_client.post(
                endpoint,
                headers=different_key_headers,
                json=payload,
            )

    assert failed.status_code == 503, failed.text
    assert failed.json()["code"] == "chart_runtime_unsupported"
    assert settlement_commit_paused is True
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "terminal_stopped"
    assert replay.json()["poll_required"] is False
    assert stable_replay.status_code == 200, stable_replay.text
    assert stable_replay.json()["reading_version_id"] == replay.json()["reading_version_id"]
    assert stable_replay.json()["status"] == "terminal_stopped"
    assert different_key_failed.status_code == 503, different_key_failed.text
    assert different_key_failed.json()["code"] == "chart_runtime_unsupported"
    assert different_key_replay.status_code == 200, different_key_replay.text
    assert different_key_replay.json()["status"] == "terminal_stopped"
    assert (
        different_key_replay.json()["reading_version_id"]
        != replay.json()["reading_version_id"]
    )
    assert runtime.calls == 2
    async with postgres_api_database.sessions() as session:
        jobs = list(await session.scalars(select(ReadingJobRecord)))
        assert len(jobs) == 2
        assert all(job.status == "stopped" for job in jobs)
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 2
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 2
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 2
        assert await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        ) == 2


async def test_confirm_and_preview_preserves_need_input_and_rolls_back(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    runtime = NeedInputChartRuntime()
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = runtime
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "need-input-profile-preview-v1",
        }
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        draft_id = draft.json()["draft_id"]
        await seed_runtime_release(database, test_settings)
        async with database.sessions() as session:
            counts_before = (
                await session.scalar(select(func.count()).select_from(SubjectProfile)),
                await session.scalar(select(func.count()).select_from(ProfileVersion)),
                await session.scalar(select(func.count()).select_from(ReadingRoot)),
                await session.scalar(select(func.count()).select_from(ReadingVersion)),
                await session.scalar(
                    select(func.count()).select_from(ReadingIdempotencyKey)
                ),
            )

        need_input = await atomic_client.post(
            f"/api/v1/profiles/drafts/{draft_id}/readings/preview",
            headers=headers,
            json=payload,
        )
        replay = await atomic_client.post(
            f"/api/v1/profiles/drafts/{draft_id}/readings/preview",
            headers=headers,
            json=payload,
        )
        listed_after_failure = await atomic_client.get("/api/v1/profiles")

    assert need_input.status_code == 400, need_input.text
    assert need_input.json()["title"] == "Chart generation unavailable"
    assert need_input.json()["type"] == (
        "urn:mingli:problem:chart_runtime_need_input"
    )
    assert need_input.json()["detail"] == "chart_runtime_need_input"
    assert need_input.json()["code"] == "chart_runtime_need_input"
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "waiting_input"
    assert replay.json()["profile_version_id"] is None
    assert replay.json()["input_request"] == {
        "requirements": [
            {
                "any_of": [
                    {
                        "id": "missing_chart_input",
                        "label": "补充信息",
                        "type_id": "text",
                        "description": None,
                        "choices": [],
                    }
                ]
            }
        ]
    }
    assert runtime.calls == 1
    assert listed_after_failure.json() == {"profiles": []}
    async with database.sessions() as session:
        root = await session.scalar(select(ReadingRoot))
        version = await session.scalar(select(ReadingVersion))
        assert root is not None
        assert version is not None
        assert root.profile_version_id is None
        assert version.state_token_ciphertext is not None
        assert version.state_token_fingerprint is not None
        assert version.prepare_has_state_token is False
        counts_after = (
            await session.scalar(select(func.count()).select_from(SubjectProfile)),
            await session.scalar(select(func.count()).select_from(ProfileVersion)),
            await session.scalar(select(func.count()).select_from(ReadingRoot)),
            await session.scalar(select(func.count()).select_from(ReadingVersion)),
            await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)),
        )
        assert counts_after[:2] == counts_before[:2]
        assert counts_after[2:] == (1, 1, 1)
        assert (
            await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        )
        assert list(await session.scalars(select(ReadingVersion.status))) == [
            "waiting_input"
        ]
        assert list(await session.scalars(select(ReadingJobRecord.status))) == [
            "waiting_input"
        ]


async def test_confirm_and_preview_replays_a_concurrent_idempotent_request(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = RenderableChartRuntime()
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "concurrent-profile-preview-v1",
        }
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        draft_id = draft.json()["draft_id"]
        await seed_runtime_release(database, test_settings)
        endpoint = f"/api/v1/profiles/drafts/{draft_id}/readings/preview"

        first, second = await asyncio.gather(
            atomic_client.post(endpoint, headers=headers, json=payload),
            atomic_client.post(endpoint, headers=headers, json=payload),
        )
        conflicting_payload = confirm_and_preview_payload()
        conflicting_payload["profile"]["on_name_conflict"] = "overwrite"
        conflicting_payload["reading"]["dimension_ids"] = ["overview"]
        conflict = await atomic_client.post(
            endpoint,
            headers=headers,
            json=conflicting_payload,
        )

    assert sorted((first.status_code, second.status_code)) == [200, 201]
    assert first.json()["reading_version_id"] == second.json()["reading_version_id"]
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["title"] == "Idempotency-Key conflict"
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)) == 1


async def test_confirm_and_preview_replays_cross_process_overwrite_race(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    application = main.create_app(settings=test_settings, database=database)
    runtime = RenderableChartRuntime()
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    payload["profile"]["on_name_conflict"] = "overwrite"

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        csrf_headers = {"X-CSRF-Token": logged_in["csrf_token"]}
        existing = await create_confirmed_profile(atomic_client, csrf_headers)
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=csrf_headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)

        claim_committed = asyncio.Event()
        release_winner = asyncio.Event()
        original_claim = ReadingService._claim_atomic_profile_preview

        async def pause_winner_after_durable_claim(
            service: ReadingService,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            result = await original_claim(service, *args, **kwargs)
            if result is None and service._atomic_profile_preview_claim is not None:
                claim_committed.set()
                await release_winner.wait()
            return result

        monkeypatch.setattr(
            ReadingService,
            "_claim_atomic_profile_preview",
            pause_winner_after_durable_claim,
        )
        headers = {
            **csrf_headers,
            "Idempotency-Key": "cross-process-overwrite-preview-v1",
        }
        endpoint = (
            f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"
        )

        winner = asyncio.create_task(
            atomic_client.post(endpoint, headers=headers, json=payload)
        )
        await claim_committed.wait()
        second = await atomic_client.post(endpoint, headers=headers, json=payload)
        async with database.sessions() as session:
            provisional_root = await session.scalar(select(ReadingRoot))
            assert provisional_root is not None
            assert provisional_root.profile_version_id is None
            assert await session.scalar(
                select(func.count()).select_from(ReadingRoot)
            ) == 1
            assert await session.scalar(
                select(func.count()).select_from(ReadingVersion)
            ) == 1
            assert await session.scalar(
                select(func.count()).select_from(ReadingJobRecord)
            ) == 1
            assert await session.scalar(
                select(func.count()).select_from(ReadingIdempotencyKey)
            ) == 1
            assert list(await session.scalars(select(ReadingVersion.status))) == [
                "input_ready"
            ]
            assert list(await session.scalars(select(ReadingJobRecord.status))) == [
                "claim_pending"
            ]
        release_winner.set()
        first = await winner
        replay = await atomic_client.post(endpoint, headers=headers, json=payload)

    assert sorted((first.status_code, second.status_code)) == [200, 201]
    assert second.json()["status"] == "input_ready"
    assert second.json()["result_available"] is False
    assert second.json()["poll_required"] is True
    assert first.json()["reading_version_id"] == second.json()["reading_version_id"]
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "prepared"
    assert replay.json()["result_available"] is True
    assert replay.json()["reading_version_id"] == first.json()["reading_version_id"]
    assert runtime.calls == 1
    async with database.sessions() as session:
        profiles = list(await session.scalars(select(SubjectProfile)))
        assert [str(profile.id) for profile in profiles] == [existing["profile_id"]]
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingIdempotencyKey)) == 1


async def test_confirm_and_preview_discards_different_key_overwrite_loser_claim(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    application = main.create_app(settings=test_settings, database=database)
    runtime = RenderableChartRuntime()
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    payload["profile"]["on_name_conflict"] = "overwrite"
    claim_committed = [asyncio.Event(), asyncio.Event()]
    release_claim = [asyncio.Event(), asyncio.Event()]
    claim_index = 0
    original_claim = ReadingService._claim_atomic_profile_preview

    async def pause_after_each_durable_claim(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal claim_index
        result = await original_claim(service, *args, **kwargs)
        if result is None and service._atomic_profile_preview_claim is not None:
            index = claim_index
            claim_index += 1
            claim_committed[index].set()
            await release_claim[index].wait()
        return result

    monkeypatch.setattr(
        ReadingService,
        "_claim_atomic_profile_preview",
        pause_after_each_durable_claim,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as first_client:
        guest_headers = await create_guest(first_client)
        logged_in = await login_current_guest(first_client, guest_headers)
        csrf_headers = {"X-CSRF-Token": logged_in["csrf_token"]}
        existing = await create_confirmed_profile(first_client, csrf_headers)
        draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=csrf_headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = (
            f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"
        )
        winner_headers = {
            **csrf_headers,
            "Idempotency-Key": "different-key-overwrite-winner-v1",
        }
        loser_headers = {
            **csrf_headers,
            "Idempotency-Key": "different-key-overwrite-loser-v1",
        }

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
            cookies=first_client.cookies,
        ) as second_client:
            winner_request = asyncio.create_task(
                first_client.post(endpoint, headers=winner_headers, json=payload)
            )
            await claim_committed[0].wait()
            loser_request = asyncio.create_task(
                second_client.post(endpoint, headers=loser_headers, json=payload)
            )
            await claim_committed[1].wait()

            release_claim[0].set()
            winner = await winner_request
            release_claim[1].set()
            loser = await loser_request
            replay = await second_client.post(
                endpoint,
                headers=winner_headers,
                json=payload,
            )
            conflicting_payload = confirm_and_preview_payload()
            conflicting_payload["profile"]["on_name_conflict"] = "overwrite"
            conflicting_payload["reading"]["dimension_ids"] = ["overview"]
            conflict = await second_client.post(
                endpoint,
                headers=winner_headers,
                json=conflicting_payload,
            )

    assert winner.status_code == 201, winner.text
    assert loser.status_code == 404, loser.text
    assert loser.json()["code"] == "profile_not_found"
    assert replay.status_code == 200, replay.text
    assert replay.json()["reading_version_id"] == winner.json()["reading_version_id"]
    assert replay.json()["status"] == "prepared"
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["title"] == "Idempotency-Key conflict"
    assert runtime.calls == 1
    async with database.sessions() as session:
        profiles = list(await session.scalars(select(SubjectProfile)))
        assert [str(profile.id) for profile in profiles] == [existing["profile_id"]]
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 1
        assert await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        ) == 1


@pytest.mark.parametrize("expose_claim", [False, True], ids=["unexposed", "exposed"])
async def test_confirm_and_preview_cleans_claim_when_confirmation_loses_race(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
    expose_claim: bool,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    application = main.create_app(settings=test_settings, database=database)
    runtime = RenderableChartRuntime()
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    claim_committed = asyncio.Event()
    release_loser = asyncio.Event()
    original_claim = ReadingService._claim_atomic_profile_preview

    async def pause_after_durable_claim(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        result = await original_claim(service, *args, **kwargs)
        if result is None and service._atomic_profile_preview_claim is not None:
            claim_committed.set()
            await release_loser.wait()
        return result

    monkeypatch.setattr(
        ReadingService,
        "_claim_atomic_profile_preview",
        pause_after_durable_claim,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as first_client:
        guest_headers = await create_guest(first_client)
        logged_in = await login_current_guest(first_client, guest_headers)
        csrf_headers = {"X-CSRF-Token": logged_in["csrf_token"]}
        draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=csrf_headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)
        endpoint = (
            f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview"
        )
        combined_headers = {
            **csrf_headers,
            "Idempotency-Key": "losing-confirm-race-preview-v1",
        }

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
            cookies=first_client.cookies,
        ) as second_client:
            loser_request = asyncio.create_task(
                first_client.post(endpoint, headers=combined_headers, json=payload)
            )
            await claim_committed.wait()
            provisional = (
                await second_client.post(
                    endpoint,
                    headers=combined_headers,
                    json=payload,
                )
                if expose_claim
                else None
            )
            winner = await second_client.post(
                f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
                headers=csrf_headers,
                json=payload["profile"],
            )
            release_loser.set()
            loser = await loser_request
            retry = await second_client.post(
                endpoint,
                headers=combined_headers,
                json=payload,
            )

    assert winner.status_code == 201, winner.text
    assert runtime.calls == 0
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 1
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 1
        if expose_claim:
            assert provisional is not None
            reading_version_id = provisional.json()["reading_version_id"]
            assert provisional.status_code == 200, provisional.text
            assert provisional.json()["status"] == "input_ready"
            assert loser.status_code == 200, loser.text
            assert loser.json()["status"] == "terminal_stopped"
            assert loser.json()["reading_version_id"] == reading_version_id
            assert retry.status_code == 200, retry.text
            assert retry.json()["status"] == "terminal_stopped"
            assert retry.json()["reading_version_id"] == reading_version_id
            assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 1
            assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 1
            assert await session.scalar(
                select(func.count()).select_from(ReadingJobRecord)
            ) == 1
            assert await session.scalar(
                select(func.count()).select_from(ReadingIdempotencyKey)
            ) == 1
        else:
            assert provisional is None
            assert loser.status_code == 409, loser.text
            assert loser.json()["title"] == "Profile Draft is already confirmed"
            assert retry.status_code == 409, retry.text
            assert retry.json()["title"] == "Profile Draft is already confirmed"
            assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 0
            assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 0
            assert await session.scalar(
                select(func.count()).select_from(ReadingJobRecord)
            ) == 0
            assert await session.scalar(
                select(func.count()).select_from(ReadingIdempotencyKey)
            ) == 0


async def test_confirm_and_preview_cleans_claim_after_late_name_conflict(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    profiles_api = __import__("app.api.profiles", fromlist=["_serialize_draft_preview"])
    application = main.create_app(settings=test_settings, database=database)
    runtime = RenderableChartRuntime()
    application.state.chart_runtime = runtime

    async def bypass_process_local_lock() -> None:
        return None

    application.dependency_overrides[
        profiles_api._serialize_draft_preview
    ] = bypass_process_local_lock
    payload = confirm_and_preview_payload()
    claim_committed: dict[UUID, asyncio.Event] = {}
    release_claim: dict[UUID, asyncio.Event] = {}
    original_claim = ReadingService._claim_atomic_profile_preview

    async def pause_after_durable_claim(
        service: ReadingService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        result = await original_claim(service, *args, **kwargs)
        draft_id = kwargs["draft_id"]
        if result is None and service._atomic_profile_preview_claim is not None:
            claim_committed[draft_id].set()
            await release_claim[draft_id].wait()
        return result

    monkeypatch.setattr(
        ReadingService,
        "_claim_atomic_profile_preview",
        pause_after_durable_claim,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as first_client:
        guest_headers = await create_guest(first_client)
        logged_in = await login_current_guest(first_client, guest_headers)
        csrf_headers = {"X-CSRF-Token": logged_in["csrf_token"]}
        first_draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=csrf_headers,
            json={"label": "本人"},
        )
        second_draft = await first_client.post(
            "/api/v1/profiles/drafts",
            headers=csrf_headers,
            json={"label": "本人"},
        )
        assert first_draft.status_code == 201, first_draft.text
        assert second_draft.status_code == 201, second_draft.text
        await seed_runtime_release(database, test_settings)
        first_draft_id = UUID(first_draft.json()["draft_id"])
        second_draft_id = UUID(second_draft.json()["draft_id"])
        claim_committed = {
            first_draft_id: asyncio.Event(),
            second_draft_id: asyncio.Event(),
        }
        release_claim = {
            first_draft_id: asyncio.Event(),
            second_draft_id: asyncio.Event(),
        }

        async with (
            AsyncClient(
                transport=ASGITransport(app=application),
                base_url="https://testserver",
                cookies=first_client.cookies,
            ) as second_client,
            AsyncClient(
                transport=ASGITransport(app=application),
                base_url="https://testserver",
                cookies=first_client.cookies,
            ) as confirm_client,
        ):
            first_headers = {
                **csrf_headers,
                "Idempotency-Key": "late-name-conflict-first-v1",
            }
            second_headers = {
                **csrf_headers,
                "Idempotency-Key": "late-name-conflict-second-v1",
            }
            first_endpoint = (
                f"/api/v1/profiles/drafts/{first_draft_id}/readings/preview"
            )
            second_endpoint = (
                f"/api/v1/profiles/drafts/{second_draft_id}/readings/preview"
            )
            first_request = asyncio.create_task(
                first_client.post(first_endpoint, headers=first_headers, json=payload)
            )
            await claim_committed[first_draft_id].wait()
            second_request = asyncio.create_task(
                second_client.post(second_endpoint, headers=second_headers, json=payload)
            )
            await claim_committed[second_draft_id].wait()

            confirmed = await confirm_client.post(
                f"/api/v1/profiles/drafts/{first_draft_id}/confirm",
                headers=csrf_headers,
                json=payload["profile"],
            )
            assert confirmed.status_code == 201, confirmed.text

            release_claim[first_draft_id].set()
            already_confirmed = await first_request
            release_claim[second_draft_id].set()
            name_conflict = await second_request
            replay = await confirm_client.post(
                second_endpoint,
                headers=second_headers,
                json=payload,
            )

    assert already_confirmed.status_code == 409, already_confirmed.text
    assert already_confirmed.json()["title"] == "Profile Draft is already confirmed"
    assert name_conflict.status_code == 409, name_conflict.text
    assert name_conflict.json()["code"] == "profile_name_conflict"
    assert replay.status_code == 409, replay.text
    assert replay.json()["code"] == "profile_name_conflict"
    assert runtime.calls == 0
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(SubjectProfile)) == 2
        assert await session.scalar(select(func.count()).select_from(ProfileVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(ReadingRoot)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(ReadingJobRecord)) == 0
        assert await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        ) == 0


async def test_confirm_and_preview_timing_includes_final_commit(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = RenderableChartRuntime()
    payload = confirm_and_preview_payload()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as atomic_client:
        guest_headers = await create_guest(atomic_client)
        logged_in = await login_current_guest(atomic_client, guest_headers)
        headers = {
            "X-CSRF-Token": logged_in["csrf_token"],
            "Idempotency-Key": "profile-preview-timing-v1",
        }
        draft = await atomic_client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        await seed_runtime_release(database, test_settings)

        original_commit = AsyncSession.commit
        commit_delay_seconds = 0.05

        async def delayed_commit(session: AsyncSession) -> None:
            await asyncio.sleep(commit_delay_seconds)
            await original_commit(session)

        monkeypatch.setattr(AsyncSession, "commit", delayed_commit)
        response = await atomic_client.post(
            f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/readings/preview",
            headers=headers,
            json=payload,
        )

    assert response.status_code == 201, response.text
    timing = response.json()["fast_path_timing"]
    minimum_commit_ms = commit_delay_seconds * 1000 * 0.8
    assert timing["db_persistence_ms"] >= minimum_commit_ms
    assert timing["total_ms"] >= minimum_commit_ms
    server_timing = {
        item.split(";dur=", maxsplit=1)[0]: float(item.split(";dur=", maxsplit=1)[1])
        for item in response.headers["Server-Timing"].split(", ")
        if ";dur=" in item
    }
    assert server_timing["chart-db"] == pytest.approx(
        timing["db_persistence_ms"],
        abs=0.001,
    )
    assert server_timing["chart-direct"] == pytest.approx(
        timing["total_ms"],
        abs=0.001,
    )


@pytest.mark.parametrize(
    ("endpoint", "product_id", "request_fields"),
    (
        (
            "/api/v1/readings/bazi-relationship",
            "bazi-relationship",
            {"relationship_type": "romantic"},
        ),
        (
            "/api/v1/readings/chart-similarity",
            "chart-similarity",
            {"dimension_ids": ["state"]},
        ),
    ),
)
async def test_latest_profile_reading_finds_secondary_participant(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    endpoint: str,
    product_id: str,
    request_fields: dict[str, Any],
) -> None:
    from test_relationship_readings import RelationshipFakeRuntime

    guest_headers = await create_guest(client)
    first = await create_confirmed_profile(client, guest_headers, label="本人甲")
    second = await create_confirmed_profile(
        client,
        guest_headers,
        label="本人乙",
        location="上海市浦东新区",
    )
    logged_in = await login_current_guest(client, guest_headers)
    headers = {"X-CSRF-Token": logged_in["csrf_token"]}
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        endpoint,
        headers=headers,
        json={
            "profile_version_ids": [
                first["profile_version_id"],
                second["profile_version_id"],
            ],
            **request_fields,
        },
    )
    assert started.status_code == 201, started.text
    assert await run_worker_once(
        database,
        test_settings,
        runtime=RelationshipFakeRuntime(),
    ) is True

    latest = await client.get(
        f"/api/v1/profiles/{second['profile_id']}/readings/latest",
        params={"product_id": product_id},
    )

    assert latest.status_code == 200, latest.text
    assert latest.json()["profile_version_id"] == second["profile_version_id"]
    assert latest.json()["reading_root_id"] == started.json()["reading_root_id"]
    assert latest.json()["reading_version_id"] == started.json()["reading_version_id"]
    assert latest.json()["product_id"] == product_id
    assert latest.json()["result_available"] is True


async def test_latest_profile_reading_crosses_versions_and_ignores_history_limit(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    guest_headers = await create_guest(client)
    first_profile = await create_confirmed_profile(client, guest_headers)
    logged_in = await login_current_guest(client, guest_headers)
    headers = {"X-CSRF-Token": logged_in["csrf_token"]}
    await seed_runtime_release(database, test_settings)
    first = await start_preview(
        client,
        headers,
        first_profile["profile_version_id"],
        idempotency_key="latest-profile-first-v1",
    )
    appended = await client.post(
        f"/api/v1/profiles/{first_profile['profile_id']}/versions",
        headers=headers,
        json={
            **confirm_and_preview_payload()["profile"],
            "birth_datetime": "1994-04-30T06:05:00+08:00",
            "difference_acknowledged": True,
        },
    )
    assert appended.status_code == 201, appended.text
    latest = await start_preview(
        client,
        headers,
        appended.json()["profile_version_id"],
        idempotency_key="latest-profile-second-v1",
    )
    await replace_prepared_brief(
        database,
        test_settings,
        version_id=first["reading_version_id"],
        brief=_bazi_chart_brief(f"profile-version:{first_profile['profile_version_id']}"),
    )
    await replace_prepared_brief(
        database,
        test_settings,
        version_id=latest["reading_version_id"],
        brief=_bazi_chart_brief(f"profile-version:{appended.json()['profile_version_id']}"),
    )

    readings = __import__(
        "app.readings.repository",
        fromlist=["SqlReadingRepository"],
    )
    cipher = EnvelopeCipher.from_settings(test_settings)
    async with database.sessions() as session:
        first_version = await session.get(
            ReadingVersion,
            UUID(first["reading_version_id"]),
        )
        latest_version = await session.get(
            ReadingVersion,
            UUID(latest["reading_version_id"]),
        )
        assert first_version is not None
        assert latest_version is not None
        tied_created_at = datetime.now(UTC) - timedelta(days=1)
        first_version.created_at = tied_created_at
        latest_version.created_at = tied_created_at
        expected_reading = max(
            (first, latest),
            key=lambda item: UUID(item["reading_version_id"]),
        )
        expected_profile_version_id = (
            first_profile["profile_version_id"]
            if expected_reading is first
            else appended.json()["profile_version_id"]
        )
        expected_latest_created_at = tied_created_at.replace(tzinfo=None).isoformat()
        repository = readings.SqlReadingRepository(session, cipher)
        prepare = await repository.load_prepare(latest_version.id)
        for _ in range(51):
            root = await repository.create_root(
                capability_id="bazi",
                owner_user_id=UUID(logged_in["user_id"]),
                profile_version_id=UUID(appended.json()["profile_version_id"]),
            )
            await repository.create_version(
                reading_root_id=root.id,
                runtime_release_id=latest_version.runtime_release_id,
                prepare_command=prepare,
            )
        await session.commit()

    async with database.sessions() as session:
        before = (
            await session.scalar(select(func.count()).select_from(SubjectProfile)),
            await session.scalar(select(func.count()).select_from(ProfileVersion)),
            await session.scalar(select(func.count()).select_from(ReadingRoot)),
            await session.scalar(select(func.count()).select_from(ReadingVersion)),
        )
    response = await client.get(
        f"/api/v1/profiles/{first_profile['profile_id']}/readings/latest",
        params={"product_id": "bazi"},
    )
    async with database.sessions() as session:
        after = (
            await session.scalar(select(func.count()).select_from(SubjectProfile)),
            await session.scalar(select(func.count()).select_from(ProfileVersion)),
            await session.scalar(select(func.count()).select_from(ReadingRoot)),
            await session.scalar(select(func.count()).select_from(ReadingVersion)),
        )

    assert response.status_code == 200, response.text
    assert_private_headers(response)
    assert response.json() == {
        "profile_id": first_profile["profile_id"],
        "profile_version_id": expected_profile_version_id,
        "reading_root_id": expected_reading["reading_root_id"],
        "reading_version_id": expected_reading["reading_version_id"],
        "capability_id": "bazi",
        "product_id": "bazi",
        "status": "prepared",
        "result_available": True,
        "created_at": expected_latest_created_at,
    }
    assert before == after


async def test_latest_profile_reading_returns_stable_reasons_and_hides_ownership(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=test_settings, database=database)
    application.state.chart_runtime = RenderableChartRuntime()
    async with (
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as first_client,
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as second_client,
    ):
        first_guest = await create_guest(first_client)
        never_profile = await create_confirmed_profile(
            first_client,
            first_guest,
            label="未排盘",
        )
        successful_profile = await create_confirmed_profile(
            first_client,
            first_guest,
            label="已有八字",
            birth_datetime="2001-07-12T09:30:00+08:00",
        )
        unrenderable_profile = await create_confirmed_profile(
            first_client,
            first_guest,
            label="无可渲染结果",
            birth_datetime="2002-08-13T10:40:00+08:00",
        )
        logged_in = await login_current_guest(first_client, first_guest)
        headers = {"X-CSRF-Token": logged_in["csrf_token"]}
        await seed_runtime_release(database, test_settings)
        await start_preview(
            first_client,
            headers,
            successful_profile["profile_version_id"],
            idempotency_key="latest-profile-incompatible-v1",
        )
        unrenderable = await start_preview(
            first_client,
            headers,
            unrenderable_profile["profile_version_id"],
            idempotency_key="latest-profile-unrenderable-v1",
        )
        async with database.sessions() as session:
            brief = await session.scalar(
                select(FactBrief).where(
                    FactBrief.reading_version_id
                    == UUID(unrenderable["reading_version_id"]),
                )
            )
            assert brief is not None
            await session.delete(brief)
            await session.commit()

        never = await first_client.get(
            f"/api/v1/profiles/{never_profile['profile_id']}/readings/latest",
            params={"product_id": "bazi"},
        )
        unrenderable_only = await first_client.get(
            f"/api/v1/profiles/{unrenderable_profile['profile_id']}/readings/latest",
            params={"product_id": "bazi"},
        )
        incompatible = await first_client.get(
            f"/api/v1/profiles/{successful_profile['profile_id']}/readings/latest",
            params={"product_id": "ziwei"},
        )
        await create_guest(second_client)
        forbidden = await second_client.get(
            f"/api/v1/profiles/{successful_profile['profile_id']}/readings/latest",
            params={"product_id": "bazi"},
        )
        absent = await second_client.get(
            f"/api/v1/profiles/{uuid4()}/readings/latest",
            params={"product_id": "bazi"},
        )

    assert never.status_code == 409, never.text
    assert never.json()["code"] == "never_succeeded"
    assert unrenderable_only.status_code == 409, unrenderable_only.text
    assert unrenderable_only.json()["code"] == "never_succeeded"
    assert incompatible.status_code == 409, incompatible.text
    assert incompatible.json()["code"] == "unavailable_or_incompatible"
    assert forbidden.status_code == absent.status_code == 404
    assert forbidden.json()["code"] == absent.json()["code"] == "profile_not_found"
    assert forbidden.json()["title"] == absent.json()["title"]


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
            headers={**first_headers, "Idempotency-Key": "owner-scope-preview"},
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
        headers={**headers, "Idempotency-Key": "declared-choices-liuyao"},
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


async def test_liuyao_need_input_supply_finishes_on_the_direct_runtime_lane(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/liuyao",
        headers={**headers, "Idempotency-Key": "need-input-direct-liuyao"},
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

    async with database.sessions() as session:
        waiting_jobs = list(
            await session.scalars(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == UUID(version_id),
                )
            )
        )
        assert len(waiting_jobs) == 1
        waiting_job_id = waiting_jobs[0].id
        assert waiting_jobs[0].status == "waiting_input"

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
    assert supplied.json()["status"] == "prepared"
    assert supplied.json()["input_request"] is None
    assert supplied.json()["fast_path_timing"]["execution_lane"] == "direct_runtime"

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
                select(ReadingJobRecord).where(ReadingJobRecord.reading_version_id == version.id)
            )
        )
        assert len(jobs) == 1
        assert jobs[0].id == waiting_job_id
        assert jobs[0].status == "complete"
        cipher = EnvelopeCipher.from_settings(test_settings)
        readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
        repository = readings.SqlReadingRepository(session, cipher)
        supplied_job = jobs[0]
        loaded = await repository.load_job(str(supplied_job.id))
        assert loaded.prepare_command.state_token is not None
        assert loaded.prepare_command.transition == "correct"
        subject_ref = str(loaded.prepare_command.intent["subject_refs"][0])
        supplied_facts = loaded.prepare_command.facts[subject_ref]
        assert supplied_facts["cast"] == (8, 7, 8, 7, 8, 7)
        assert supplied_facts["event_datetime"] == "2026-08-10T12:00:00+08:00"
        assert supplied_facts["location"] == "北京市朝阳区"
        assert "prior_answer" not in supplied_facts

    processed = await run_worker_once(database, test_settings, runtime=TokenEchoRuntime())
    assert processed is False
    advanced = await client.get(f"/api/v1/readings/{version_id}")
    assert advanced.status_code == 200
    assert advanced.json()["status"] in {"prepared", "completing", "accepted"}


async def test_liuyao_outcome_dimension_finishes_without_worker_or_model(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/liuyao",
        headers={**headers, "Idempotency-Key": "outcome-direct-liuyao"},
        json={
            "cast": [7, 8, 6, 9, 7, 8],
            "event_datetime": "2026-08-10T12:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
            "dimension_ids": ["outcome"],
        },
    )

    assert started.status_code == 201, started.text
    version_id = started.json()["reading_version_id"]

    async with database.sessions() as session:
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == UUID(version_id)
            )
        )
        assert job is not None
        assert job.output_contract["required_dimension_ids"] == ["outcome"]

    runtime = TokenEchoRuntime()
    assert await run_worker_once(database, test_settings, runtime=runtime) is False
    finished = await client.get(f"/api/v1/readings/{version_id}")
    assert finished.status_code == 200
    assert finished.json()["status"] == "prepared"


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
            narrative_policy_version="policy-v1",
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


async def test_supply_input_after_waiting_timeout_is_rejected(
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
    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        version.waiting_input_at = datetime.now(UTC) - timedelta(days=7)
        await session.commit()

    assert await run_worker_once(database, test_settings) is False
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
    assert response.json()["title"] == "Reading is not waiting for input"


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
        headers={**headers, "Idempotency-Key": "accepted-verification-preview"},
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
    assert body["document"] is None
    assert body["fact_panel"]["facts"][0]["display_text"] == (
        "这是 Fake Runtime 合同事实，不是命理结果。"
    )
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
                select(ReadingJobRecord).where(ReadingJobRecord.reading_version_id == version.id)
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
            await session.scalars(select(ReadingVersion).order_by(ReadingVersion.version))
        )
        roots = list(await session.scalars(select(ReadingRoot)))
        assert len(roots) == 1
        assert [version.version for version in versions] == [1, 2]
        assert (
            len(
                list(
                    await session.scalars(
                        select(ReadingJobRecord).where(
                            ReadingJobRecord.reading_version_id == versions[1].id
                        )
                    )
                )
            )
            == 1
        )
        cipher = EnvelopeCipher.from_settings(test_settings)
        readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
        repository = readings.SqlReadingRepository(session, cipher)
        job = await session.scalar(
            select(ReadingJobRecord).where(ReadingJobRecord.reading_version_id == versions[1].id)
        )
        loaded = await repository.load_job(str(job.id))
        assert loaded.prepare_command.facts[subject_ref]["prior_answer"] == ACCEPTED_COPY
        assert loaded.prepare_command.state_token is not None
        assert loaded.prepare_command.transition is None


async def test_recast_creates_a_new_root_from_an_accepted_reading(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.readings.service._profile_default_preview_year",
        lambda _profile: 2032,
    )
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    source = await start_preview(
        client,
        headers,
        confirmed["profile_version_id"],
        idempotency_key="recast-source-v1",
    )
    await advance_to_accepted(
        database,
        test_settings,
        version_id=source["reading_version_id"],
        subject_ref=f"profile-version:{confirmed['profile_version_id']}",
    )

    recast = await client.post(
        f"/api/v1/readings/{source['reading_version_id']}/recast",
        headers={**headers, "Idempotency-Key": "recast-request-v1"},
        json={
            "action": "profile_preview",
            "profile_version_id": confirmed["profile_version_id"],
            "query": "改看长期结构中的职业主线",
            "dimension_ids": ["career"],
        },
    )

    assert recast.status_code == 201, recast.text
    body = recast.json()
    assert body["version"] == 1
    assert body["reading_root_id"] != source["reading_root_id"]
    assert body["profile_version_id"] == confirmed["profile_version_id"]
    assert body["capability_id"] == "bazi"
    assert body["horizon"] == {
        "kind_id": "year",
        "start": "2032",
        "end": "2032",
    }

    replayed = await client.post(
        f"/api/v1/readings/{source['reading_version_id']}/recast",
        headers={**headers, "Idempotency-Key": "recast-request-v1"},
        json={
            "action": "profile_preview",
            "profile_version_id": confirmed["profile_version_id"],
            "query": "改看长期结构中的职业主线",
            "dimension_ids": ["career"],
        },
    )
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["reading_version_id"] == body["reading_version_id"]

    async with database.sessions() as session:
        roots = list(await session.scalars(select(ReadingRoot)))
        assert len(roots) == 2
        assert {str(root.id) for root in roots} >= {
            source["reading_root_id"],
            body["reading_root_id"],
        }


async def test_recast_requires_accepted_source_and_owner_scope(
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
        source = await start_preview(
            first,
            first_headers,
            confirmed["profile_version_id"],
            idempotency_key="recast-not-ready-v1",
        )

        not_ready = await first.post(
            f"/api/v1/readings/{source['reading_version_id']}/recast",
            headers={**first_headers, "Idempotency-Key": "recast-not-ready-request"},
            json={
                "action": "profile_preview",
                "profile_version_id": confirmed["profile_version_id"],
            },
        )
        assert not_ready.status_code == 409

        second_headers = await create_guest(second)
        cross_owner = await second.post(
            f"/api/v1/readings/{source['reading_version_id']}/recast",
            headers={**second_headers, "Idempotency-Key": "recast-cross-owner"},
            json={
                "action": "profile_preview",
                "profile_version_id": confirmed["profile_version_id"],
            },
        )

    assert cross_owner.status_code == 404


async def test_recast_liuyao_uses_a_structured_event_request(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    source = await start_preview(
        client,
        headers,
        confirmed["profile_version_id"],
        idempotency_key="recast-liuyao-source",
    )
    await advance_to_accepted(
        database,
        test_settings,
        version_id=source["reading_version_id"],
        subject_ref=f"profile-version:{confirmed['profile_version_id']}",
    )

    recast = await client.post(
        f"/api/v1/readings/{source['reading_version_id']}/recast",
        headers={**headers, "Idempotency-Key": "recast-liuyao-request"},
        json={
            "action": "liuyao_one_question",
            "cast": [6, 7, 8, 9, 6, 7],
            "event_datetime": "2026-08-14T10:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "query": "换一个具体事件重新判断",
            "dimension_ids": ["outcome"],
        },
    )

    assert recast.status_code == 201, recast.text
    body = recast.json()
    assert body["version"] == 1
    assert body["reading_root_id"] != source["reading_root_id"]
    assert body["profile_version_id"] is None
    assert body["capability_id"] == "liuyao"
    assert body["dimension_ids"] == ["outcome"]


async def test_follow_up_enforces_snapshot_expiry_count_and_linear_active_child(
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
        idempotency_key="follow-up-contract-base",
    )
    version_id = started["reading_version_id"]
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    await advance_to_accepted(
        database,
        test_settings,
        version_id=version_id,
        subject_ref=subject_ref,
    )

    async with database.sessions() as session:
        root = await session.get(ReadingRoot, UUID(started["reading_root_id"]))
        assert root is not None
        root.follow_up_count_snapshot = 1
        root.follow_up_window_seconds_snapshot = 3_600
        root.follow_up_started_at = datetime.now(UTC)
        await session.commit()

    first = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-contract-first"},
        json={"query": "继续看这条主线"},
    )
    assert first.status_code == 201
    first_child_id = first.json()["reading_version_id"]

    active_branch = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-contract-branch"},
        json={"query": "从旧版再开一个问题"},
    )
    assert active_branch.status_code == 409

    await advance_to_accepted(
        database,
        test_settings,
        version_id=first_child_id,
        subject_ref=subject_ref,
    )
    exhausted = await client.post(
        f"/api/v1/readings/{first_child_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-contract-exhausted"},
        json={"query": "再问一次"},
    )
    assert exhausted.status_code == 409


async def test_follow_up_rejects_an_expired_product_snapshot(
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
        idempotency_key="follow-up-contract-expired-base",
    )
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    await advance_to_accepted(
        database,
        test_settings,
        version_id=started["reading_version_id"],
        subject_ref=subject_ref,
    )

    async with database.sessions() as session:
        root = await session.get(ReadingRoot, UUID(started["reading_root_id"]))
        assert root is not None
        root.follow_up_count_snapshot = 1
        root.follow_up_window_seconds_snapshot = 60
        root.follow_up_started_at = datetime.now(UTC) - timedelta(minutes=2)
        await session.commit()

    expired = await client.post(
        f"/api/v1/readings/{started['reading_version_id']}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-contract-expired"},
        json={"query": "已过期的问题"},
    )
    assert expired.status_code == 409


async def test_result_fact_panel_strips_raw_inputs_and_dependent_refs(
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
        idempotency_key="input-leak-base",
    )
    version_id = started["reading_version_id"]
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    leak_brief = brief_payload(subject_ref, {"kind_id": "life", "start": None, "end": None})
    raw_location_ref = f"fact:{subject_ref}/input/location"
    chart_ref = "fact:career-structure"
    leak_brief["facts"] = [
        {
            "ref": raw_location_ref,
            "subject_ref": subject_ref,
            "kind_id": "kind.structure",
            "value": "上海市",
            "display_text": "出生地点：上海市",
        },
        {
            "ref": chart_ref,
            "subject_ref": subject_ref,
            "kind_id": "kind.structure",
            "value": {"fixture": "stable"},
            "display_text": "当前结构更支持持续积累。",
        },
    ]
    leak_brief["evidence"][0]["supports_fact_refs"] = [raw_location_ref, chart_ref]
    leak_brief["findings"][0]["fact_refs"] = [raw_location_ref, chart_ref]
    leak_brief["claim_scopes"][0]["fact_refs"] = [raw_location_ref, chart_ref]
    readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
    cipher = EnvelopeCipher.from_settings(test_settings)
    async with database.sessions() as session:
        repository = readings.SqlReadingRepository(session, cipher)
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version.id,
            )
        )
        assert job is not None
        existing_brief = await session.scalar(
            select(FactBrief).where(FactBrief.reading_version_id == version.id)
        )
        assert existing_brief is not None
        await session.delete(existing_brief)
        await session.flush()
        state_token = await repository.load_state_token(version.id)
        now = datetime.now(UTC)
        await repository.record_prepared(
            str(job.id),
            Prepared(
                state_token=state_token or "api-test-token",
                brief=ReadingBrief.from_dict(leak_brief),
            ),
            now,
        )
        await repository.record_accepted(
            str(job.id),
            Accepted(
                state_token=state_token or "api-test-token",
                public_copy=ACCEPTED_COPY,
            ),
            now,
        )
        await session.commit()

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "accepted"
    panel = body["fact_panel"]
    assert "上海市" not in result.text
    assert "/input/" not in result.text
    assert [fact["ref"] for fact in panel["facts"]] == [chart_ref]
    assert panel["evidence"][0]["supports_fact_refs"] == [chart_ref]
    assert panel["findings"][0]["fact_refs"] == [chart_ref]
    assert panel["claim_scopes"][0]["fact_refs"] == [chart_ref]


async def test_follow_up_requires_accepted_reading(
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
        idempotency_key="follow-up-not-ready",
    )
    version_id = started["reading_version_id"]
    response = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers=headers,
        json={"query": "再往下看事业节奏"},
    )
    assert response.status_code == 409


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
    for index in range(10):
        response = await client.post(
            "/api/v1/readings/preview",
            headers={**headers, "Idempotency-Key": f"rate-limit-{index:02d}"},
            json={
                "profile_version_id": confirmed["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )
        responses.append(response.status_code)
    limited = await client.post(
        "/api/v1/readings/preview",
        headers={**headers, "Idempotency-Key": "rate-limit-overflow"},
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
        headers={**user_headers, "Idempotency-Key": "claimed-user-preview"},
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
        guest = await session.scalar(select(GuestSession).order_by(GuestSession.created_at.desc()))
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
        "product_id",
        "runtime_capability_ids",
        "version",
        "status",
        "object_id",
        "dimension_ids",
        "horizon",
        "prior_answer",
        "input_request",
        "created_at",
        "delivery_state",
        "result_available",
        "poll_required",
        "poll_after_seconds",
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
    assert [item["reading_version_id"] for item in listed_a.json()["readings"]] == [version_a]

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
    assert [item["reading_version_id"] for item in listed_b.json()["readings"]] == [version_b]

    # After guest B claims a User account, the same session must still see only
    # its own readings: guest A's Version must never leak across owners.
    logged_in = await login_current_guest(client, guest_b)
    claimed = await client.get("/api/v1/readings")
    claimed_ids = [item["reading_version_id"] for item in claimed.json()["readings"]]
    assert claimed_ids == [version_b]
    assert str(logged_in["user_id"])
    assert version_a not in claimed_ids


@pytest.mark.parametrize(
    (
        "path",
        "payload",
        "expected_capability",
        "expected_product",
        "expected_horizon",
        "needs_profile",
    ),
    [
        (
            "/api/v1/readings/luming-nayin",
            {"dimension_ids": ["state", "career"]},
            "luming-nayin",
            "luming-nayin",
            "life",
            True,
        ),
        (
            "/api/v1/readings/five-elements-facts",
            {"dimension_ids": ["state"]},
            "bazi",
            "five-elements-facts",
            "life",
            True,
        ),
        (
            "/api/v1/readings/rhythm",
            {"dimension_ids": ["state"]},
            "luming-nayin",
            "rhythm",
            "life",
            True,
        ),
        (
            "/api/v1/readings/taiyi",
            {
                "event_datetime": "2026-08-14T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "dimension_ids": ["outcome", "timing"],
            },
            "taiyi",
            "taiyi",
            "year",
            False,
        ),
        (
            "/api/v1/readings/selection",
            {
                "event_profile": "business_opening_transaction",
                "requested_actions": ["开市"],
                "date_range_start": "2026-09-01",
                "date_range_end": "2026-09-03",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "dimension_ids": ["timing", "state"],
            },
            "selection",
            "selection",
            "year",
            False,
        ),
        (
            "/api/v1/readings/fengshui",
            {
                "fengshui_spec": {
                    "schema_version": "mingli-fengshui-input-v1",
                    "property_scope": "residential",
                    "subprofiles": ["liqi"],
                    "requested_form_variables": [],
                    "liqi": {
                        "selected_school": "bazhai",
                        "origin_basis": "door_trigram",
                        "origin_node_id": "door-1",
                    },
                    "building": {},
                    "assets": [],
                    "observations": [],
                    "compass_measurements": [
                        {
                            "measurement_id": "m-door",
                            "method": "synthetic-compass",
                            "source_ref": "synthetic-compass-1",
                            "source_type": "user_measurement",
                            "north_reference": "true",
                            "facing_degrees": 180,
                            "correction_degrees": 0,
                            "uncertainty_degrees": 0,
                            "quality": "good",
                        }
                    ],
                    "declared_orientation": {},
                    "layout_graph": {
                        "nodes": [
                            {
                                "node_id": "door-1",
                                "kind": "door",
                                "direction_measurement": "m-door",
                            }
                        ],
                        "edges": [],
                    },
                },
                "dimension_ids": ["current_state", "direction"],
            },
            "fengshui",
            "fengshui",
            "instant",
            False,
        ),
    ],
)
async def test_guest_can_start_each_remaining_core_product(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    path: str,
    payload: dict[str, Any],
    expected_capability: str,
    expected_product: str,
    expected_horizon: str,
    needs_profile: bool,
) -> None:
    headers = await create_guest(client)
    if needs_profile:
        profile = await create_confirmed_profile(client, headers)
        payload = {**payload, "profile_version_id": profile["profile_version_id"]}
    await seed_runtime_release(database, test_settings)

    started = await client.post(
        path,
        headers={**headers, "Idempotency-Key": f"internal-core-{expected_capability}"},
        json=payload,
    )

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["capability_id"] == expected_capability
    assert body["product_id"] == expected_product
    assert body["horizon"]["kind_id"] == expected_horizon
    assert body["status"] == "input_ready"
    assert_private_headers(started)


async def test_guest_result_exposes_all_supported_bazi_layers_without_billing_state(
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
        idempotency_key="entitlement-guest-bazi",
    )
    version_id = started["reading_version_id"]
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    await replace_prepared_brief(
        database,
        test_settings,
        version_id=version_id,
        brief=_bazi_chart_brief(subject_ref, include_year=True, include_month=True),
    )

    result = await client.get(f"/api/v1/readings/{version_id}/result")

    assert result.status_code == 200
    body = result.json()
    entitlement = body["time_layer_entitlement"]
    restored = TimeLayerEntitlementV1.from_dict(entitlement)
    layers = _entitlement_by_id(entitlement)
    view_layers = body["view_model"]["time_layers"]
    public_facts = {
        item["ref"].rsplit("/", 1)[-1]: item["display_text"]
        for item in body["fact_panel"]["facts"]
    }
    month_capability = next(item for item in view_layers if item["layer_id"] == "month")
    assert entitlement["schema_version"] == TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION
    assert restored.capability_id == "bazi"
    assert entitlement["resolution"] == "granted"
    assert entitlement["free_year_set"] == [2026]
    assert layers["life"]["access"] == "readable"
    assert layers["year"]["access"] == "readable"
    assert layers["year"]["upgrade_cta"] is None
    assert layers["month"]["access"] == "readable"
    assert layers["month"]["upgrade_cta"] is None
    assert layers["hour"]["access"] == "unavailable"
    assert layers["hour"]["upgrade_cta"] is None
    assert month_capability["available"] is True
    assert "tier" not in month_capability
    assert "access" not in month_capability
    assert public_facts["four_pillars"] == (
        "四柱：年柱甲戌、月柱戊辰、日柱丙戌、时柱辛卯。"
    )
    assert public_facts["year_layers"].startswith("流年：2026年丙午")
    assert public_facts["month_layers"].startswith("流月：2026-08")
    assert body["view_model"]["core_facts"]["month_layers"] is not None
    assert all("{" not in text for text in public_facts.values())
    assert_private_headers(result)


async def test_fortune_result_keeps_runtime_text_outside_humanized_guarantee(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/today",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    assert started.status_code == 201, started.text
    version_id = started.json()["reading_version_id"]
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    fallback_payload = brief_payload(
        subject_ref,
        {"kind_id": "day", "start": "2026-08-31", "end": "2026-08-31"},
    )
    runtime_text = '{"schema_version":"fortune-result/v1","engine":"fixture"}'
    fallback_payload["facts"][0]["display_text"] = runtime_text
    fallback_payload["request_view"]["capability_ids"] = ["fortune"]
    fallback_payload["request_view"]["object_id"] = "today"
    await replace_prepared_brief(
        database,
        test_settings,
        version_id=version_id,
        brief=ReadingBrief.from_dict(fallback_payload),
    )
    await advance_to_accepted(
        database,
        test_settings,
        version_id=version_id,
        subject_ref=subject_ref,
    )

    result = await client.get(f"/api/v1/readings/{version_id}/result")

    assert result.status_code == 200
    body = result.json()
    assert body["view_model"] is None
    assert body["fact_panel"]["facts"][0]["display_text"] == runtime_text
    assert_private_headers(result)


async def test_user_result_and_delivery_expose_supported_layers_without_grants(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guest_headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, guest_headers)
    await seed_runtime_release(database, test_settings)
    logged_in = await login_current_guest(client, guest_headers)
    user_headers = {"X-CSRF-Token": logged_in["csrf_token"]}
    bazi_started = await start_preview(
        client,
        user_headers,
        confirmed["profile_version_id"],
        idempotency_key="entitlement-user-bazi",
    )
    ziwei_started = await client.post(
        "/api/v1/readings/ziwei",
        headers={**user_headers, "Idempotency-Key": "entitlement-user-ziwei"},
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    assert ziwei_started.status_code == 201, ziwei_started.text
    bazi_subject = f"profile-version:{confirmed['profile_version_id']}"
    bazi_brief = _bazi_chart_brief(
        bazi_subject,
        include_year=True,
        include_month=True,
    )
    ziwei_brief = _ziwei_chart_brief(bazi_subject, include_month=True)
    await replace_prepared_brief(
        database,
        test_settings,
        version_id=bazi_started["reading_version_id"],
        brief=bazi_brief,
    )
    await replace_prepared_brief(
        database,
        test_settings,
        version_id=ziwei_started.json()["reading_version_id"],
        brief=ziwei_brief,
    )
    bazi_public_ref = f"fact:{bazi_subject}/calculated/bazi/four_pillars"
    bazi_time_ref = f"fact:{bazi_subject}/calculated/bazi/month_layers"
    ziwei_public_ref = f"fact:{bazi_subject}/calculated/ziwei/palaces"
    ziwei_time_ref = (
        f"fact:{bazi_subject}/calculated/ziwei/monthly_layers"
    )
    await save_fact_referencing_document(
        database,
        test_settings,
        version_id=bazi_started["reading_version_id"],
        subject_ref=bazi_subject,
        product_id="bazi",
        brief=bazi_brief,
        public_fact_ref=bazi_public_ref,
        supported_time_fact_ref=bazi_time_ref,
    )
    await save_fact_referencing_document(
        database,
        test_settings,
        version_id=ziwei_started.json()["reading_version_id"],
        subject_ref=bazi_subject,
        product_id="ziwei",
        brief=ziwei_brief,
        public_fact_ref=ziwei_public_ref,
        supported_time_fact_ref=ziwei_time_ref,
    )

    bazi_result = await client.get(
        f"/api/v1/readings/{bazi_started['reading_version_id']}/result"
    )
    ziwei_result = await client.get(
        f"/api/v1/readings/{ziwei_started.json()['reading_version_id']}/result"
    )

    assert bazi_result.status_code == 200
    assert ziwei_result.status_code == 200
    bazi_payload = bazi_result.json()
    ziwei_payload = ziwei_result.json()
    bazi_entitlement = bazi_payload["time_layer_entitlement"]
    ziwei_entitlement = ziwei_payload["time_layer_entitlement"]
    ziwei_public_facts = ziwei_payload["fact_panel"]["facts"]
    TimeLayerEntitlementV1.from_dict(bazi_entitlement)
    TimeLayerEntitlementV1.from_dict(ziwei_entitlement)
    bazi_layers = _entitlement_by_id(bazi_entitlement)
    ziwei_layers = _entitlement_by_id(ziwei_entitlement)
    assert bazi_entitlement["resolution"] == "granted"
    assert ziwei_entitlement["resolution"] == "granted"
    assert ziwei_entitlement["capability_id"] == "ziwei"
    assert bazi_layers["month"]["access"] == "readable"
    assert bazi_layers["month"]["upgrade_cta"] is None
    assert ziwei_layers["life"]["access"] == "readable"
    assert ziwei_layers["year"]["access"] == "unavailable"
    assert ziwei_layers["year"]["upgrade_cta"] is None
    assert ziwei_layers["month"]["access"] == "readable"
    assert ziwei_layers["month"]["upgrade_cta"] is None
    assert ziwei_public_facts[0]["display_text"].startswith(
        "十二宫：命宫（甲子）主星紫微；"
    )
    for payload, time_ref in (
        (bazi_payload, bazi_time_ref),
        (ziwei_payload, ziwei_time_ref),
    ):
        public_fact_refs = {
            item["ref"] for item in payload["fact_panel"]["facts"]
        }
        document = payload["document"]
        assert document is not None
        assert all(
            set(claim["fact_refs"]) <= public_fact_refs
            for claim in document["claims"]
        )
        assert all(
            set(evidence["supports_fact_refs"]) <= public_fact_refs
            for evidence in document["evidence"]
        )
        assert [claim["claim_id"] for claim in document["claims"]] == [
            "claim:time-layer",
            "claim:fact-closure",
            "claim:limit-only",
            "claim:empty-dependency",
        ]
        assert [evidence["evidence_ref"] for evidence in document["evidence"]] == [
            "evidence:fact-closure",
            "evidence:time-layer",
        ]
        assert document["answer_summary"] == (
            "受支持流月事实形成的结论应保持引用闭包。"
        )
        assert "MIXED-CLAIM-MUST-DROP" not in str(document)
        assert "MIXED-EVIDENCE-MUST-DROP" not in str(document)
        assert payload["accepted_copy"] == "\n\n".join(
            (
                "受支持流月事实形成的结论应保持引用闭包。",
                "公开结果必须保持事实引用闭包。",
                "公开边界可独立支撑这条结论。",
                "这条公开说明没有事实依赖。",
                "本解读仅供传统文化参考，不构成现实决策保证。",
            )
        )
        assert "MIXED-CLAIM-MUST-DROP" not in payload["accepted_copy"]
        assert time_ref in public_fact_refs
        assert time_ref in str(document)
    assert bazi_payload["document"]["view_model"]["core_facts"]["month_layers"]
    assert ziwei_payload["document"]["view_model"]["core_facts"]["monthly_layers"]

    export_documents: list[ReadingDocumentV1] = []

    def capture_export(document: ReadingDocumentV1, export_format: str) -> Any:
        exports = importlib.import_module("app.readings.export")
        export_documents.append(document)
        return exports.RenderedExport(
            format=export_format,
            content_type="application/pdf",
            file_name="reading.pdf",
            payload=b"%PDF-public-projection",
        )

    monkeypatch.setattr(
        "app.readings.export.render_reading_export",
        capture_export,
    )
    version_ids = (
        bazi_started["reading_version_id"],
        ziwei_started.json()["reading_version_id"],
    )
    for version_id in version_ids:
        exported = await client.post(
            f"/api/v1/readings/{version_id}/export",
            headers=user_headers,
            json={"format": "pdf", "ttl_seconds": 300},
        )
        assert exported.status_code == 201, exported.text
        shared = await client.post(
            f"/api/v1/readings/{version_id}/share",
            headers=user_headers,
            json={"ttl_seconds": 300},
        )
        assert shared.status_code == 201, shared.text
        bearer = await client.get(f"/api/v1/share/{shared.json()['token']}")
        assert bearer.status_code == 200, bearer.text
        bearer_document = bearer.json()["document"]
        assert bearer_document["answer_summary"] == (
            "受支持流月事实形成的结论应保持引用闭包。"
        )
        assert "流月事实依据" in str(bearer_document)
        assert "claim:limit-only" in str(bearer_document)
        assert "claim:empty-dependency" in str(bearer_document)
        assert "MIXED-CLAIM-MUST-DROP" not in str(bearer_document)
        assert "MIXED-EVIDENCE-MUST-DROP" not in str(bearer_document)
    assert len(export_documents) == 2
    assert all(
        document.answer_summary == "受支持流月事实形成的结论应保持引用闭包。"
        and "流月事实依据" in str(document)
        and "claim:limit-only" in str(document)
        and "claim:empty-dependency" in str(document)
        and "MIXED-CLAIM-MUST-DROP" not in str(document)
        and "MIXED-EVIDENCE-MUST-DROP" not in str(document)
        for document in export_documents
    )

async def test_result_without_session_is_401_and_omits_entitlement(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/api/v1/readings/{uuid4()}/result")

    assert response.status_code == 401
    assert "time_layer_entitlement" not in response.json()


async def test_request_failed_result_keeps_supported_bazi_layers_readable(
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
        idempotency_key="entitlement-request-failed",
    )
    version_id = started["reading_version_id"]
    subject_ref = f"profile-version:{confirmed['profile_version_id']}"
    await replace_prepared_brief(
        database,
        test_settings,
        version_id=version_id,
        brief=_bazi_chart_brief(subject_ref, include_year=True, include_month=True),
    )
    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(version_id))
        assert version is not None
        version.status = "terminal_stopped"
        await session.commit()

    result = await client.get(f"/api/v1/readings/{version_id}/result")

    assert result.status_code == 200
    entitlement = result.json()["time_layer_entitlement"]
    layers = _entitlement_by_id(entitlement)
    TimeLayerEntitlementV1.from_dict(entitlement)
    assert entitlement["resolution"] == "granted"
    assert layers["year"]["access"] == "readable"
    assert layers["month"]["access"] == "readable"
    assert layers["month"]["upgrade_cta"] is None
    assert layers["hour"]["access"] == "unavailable"
    public_refs = {
        item["ref"].rsplit("/", 1)[-1]
        for item in result.json()["fact_panel"]["facts"]
    }
    assert "month_layers" in public_refs


async def test_liuyao_result_does_not_invent_time_layer_entitlement(
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

    result = await client.get(f"/api/v1/readings/{version_id}/result")

    assert result.status_code == 200
    body = result.json()
    assert body["time_layer_entitlement"] is None
    assert body.get("view_model") is None or body["view_model"]["schema_version"] != (
        "bazi-chart/v1"
    )
