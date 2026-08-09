from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from test_narrative_guard import build_brief, load_candidate


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 9, 12, 0, tzinfo=UTC)


class ScriptedRuntime:
    def __init__(self, script: list[object], events: list[str] | None = None) -> None:
        self.script = list(script)
        self.commands: list[Any] = []
        self.events = events if events is not None else []

    async def execute(self, command: Any) -> Any:
        self.commands.append(command)
        self.events.append(f"runtime:{command.kind}")
        if not self.script:
            raise AssertionError("runtime script exhausted")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item(command)
        return item


class ScriptedModel:
    def __init__(self, script: list[object], events: list[str] | None = None) -> None:
        self.script = list(script)
        self.requests: list[Any] = []
        self.events = events if events is not None else []

    async def generate(self, request: Any) -> Any:
        self.requests.append(request)
        self.events.append("model:generate")
        if not self.script:
            raise AssertionError("model script exhausted")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        narrative = __import__(
            "app.readings.narrative_contracts",
            fromlist=["NarrativeCandidate"],
        )
        if isinstance(item, narrative.NarrativeCandidate):
            model_contracts = __import__(
                "app.readings.model_contracts",
                fromlist=["ModelGenerationResult"],
            )
            return model_contracts.ModelGenerationResult(
                candidate=item,
                receipt=make_model_receipt(request),
            )
        return item


class ScriptedGuard:
    def __init__(self, results: list[Any], events: list[str] | None = None) -> None:
        self.results = list(results)
        self.events = events if events is not None else []
        self.calls = 0

    def validate(self, candidate: Any, brief: Any, output_contract: Any) -> Any:
        del candidate, brief, output_contract
        self.calls += 1
        self.events.append("guard:validate")
        if not self.results:
            raise AssertionError("guard script exhausted")
        return self.results.pop(0)


class MemoryRepository:
    def __init__(self, orchestrator: Any, job: Any, events: list[str] | None = None) -> None:
        self.orchestrator = orchestrator
        self.job = job
        self.events = events if events is not None else []
        self.checkpoint = orchestrator.ReadingCheckpoint()
        self.attempts: list[tuple[int, tuple[str, ...]]] = []
        self.model_receipts: list[Any] = []

    async def load_job(self, job_id: str) -> Any:
        assert job_id == self.job.id
        return self.job

    async def load_checkpoint(self, job_id: str) -> Any:
        assert job_id == self.job.id
        return self.checkpoint

    async def record_waiting_input(self, job_id: str, stopped: Any, at: datetime) -> None:
        del at
        assert job_id == self.job.id
        self.events.append("repo:waiting_input")
        self.checkpoint = replace(
            self.checkpoint,
            status=self.orchestrator.ReadingStatus.WAITING_INPUT,
            waiting_input=stopped,
        )

    async def record_terminal_stopped(self, job_id: str, stopped: Any, at: datetime) -> None:
        del at
        assert job_id == self.job.id
        self.events.append("repo:terminal_stopped")
        self.checkpoint = replace(
            self.checkpoint,
            status=self.orchestrator.ReadingStatus.TERMINAL_STOPPED,
            terminal_stopped=stopped,
        )

    async def record_prepared(self, job_id: str, prepared: Any, at: datetime) -> None:
        del at
        assert job_id == self.job.id
        self.events.append("repo:prepared")
        self.checkpoint = replace(
            self.checkpoint,
            status=self.orchestrator.ReadingStatus.PREPARED,
            prepared=prepared,
        )

    async def record_generation_attempt(
        self,
        job_id: str,
        attempt_number: int,
        candidate: Any,
        guard_errors: tuple[str, ...],
        at: datetime,
        *,
        model_receipt: Any = None,
    ) -> None:
        del candidate, at
        assert job_id == self.job.id
        self.events.append(f"repo:attempt:{attempt_number}")
        self.attempts.append((attempt_number, guard_errors))
        self.model_receipts.append(model_receipt)
        self.checkpoint = replace(self.checkpoint, attempt_count=attempt_number)

    async def record_completion_intent(
        self,
        job_id: str,
        public_copy: str,
        at: datetime,
    ) -> None:
        del at
        assert job_id == self.job.id
        self.events.append("repo:completion_intent")
        self.checkpoint = replace(
            self.checkpoint,
            status=self.orchestrator.ReadingStatus.COMPLETING,
            completion_copy=public_copy,
        )

    async def record_successful_attempt(
        self,
        job_id: str,
        attempt_number: int,
        candidate: Any,
        public_copy: str,
        at: datetime,
        *,
        model_receipt: Any = None,
    ) -> None:
        del candidate, at
        assert job_id == self.job.id
        self.events.append(f"repo:successful_attempt:{attempt_number}")
        self.attempts.append((attempt_number, ()))
        self.model_receipts.append(model_receipt)
        self.checkpoint = replace(
            self.checkpoint,
            status=self.orchestrator.ReadingStatus.COMPLETING,
            attempt_count=attempt_number,
            completion_copy=public_copy,
        )

    async def record_accepted(self, job_id: str, accepted: Any, at: datetime) -> Any:
        del at
        assert job_id == self.job.id
        self.events.append("repo:accepted")
        self.checkpoint = replace(
            self.checkpoint,
            status=self.orchestrator.ReadingStatus.ACCEPTED,
            accepted=accepted,
        )
        return accepted

    async def mark_delayed(self, job_id: str, at: datetime) -> None:
        del at
        assert job_id == self.job.id
        self.events.append("repo:delayed")
        self.checkpoint = replace(
            self.checkpoint,
            status=self.orchestrator.ReadingStatus.DELAYED,
        )

    async def mark_runtime_unknown(self, job_id: str, at: datetime) -> None:
        del at
        assert job_id == self.job.id
        self.events.append("repo:runtime_unknown")
        self.checkpoint = replace(
            self.checkpoint,
            status=self.orchestrator.ReadingStatus.RUNTIME_UNKNOWN,
        )


def make_prepare(contracts: Any, *, state_token: str | None = None, facts: bool = True) -> Any:
    return contracts.Prepare(
        query="事业上最该先抓住哪条主线？",
        intent={
            "subject_refs": ["profile-version:test"],
            "object_id": "natal",
            "dimension_ids": ["career"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
            "capability_id": "bazi",
            "comparisons": [],
        },
        facts=(
            {"profile-version:test": {"birth_datetime_or_four_pillars": "fixture"}} if facts else {}
        ),
        state_token=state_token,
    )


def make_prepared(contracts: Any) -> Any:
    return contracts.Prepared(
        state_token="fake-opaque-state",
        brief=build_brief(),
    )


def make_candidate(narrative: Any) -> Any:
    return narrative.NarrativeCandidate.from_dict(load_candidate())


def make_model_receipt(request: Any) -> Any:
    contracts = __import__(
        "app.readings.model_contracts",
        fromlist=["ModelCallReceipt"],
    )
    usage = contracts.ModelTokenUsage(input_tokens=0, output_tokens=0, total_tokens=0)
    price_digest = contracts.model_price_snapshot_digest(
        version="fake-model-price-v1",
        currency="CNY",
        input_microunits_per_million_tokens=0,
        output_microunits_per_million_tokens=0,
    )
    return contracts.ModelCallReceipt(
        outcome="succeeded",
        error_code=None,
        model_profile_id="fake-model-p0-v1",
        model_profile_snapshot_digest=hashlib.sha256(b"fake-model-p0-v1").hexdigest(),
        provider="fake",
        provider_model_version="fake-model-v1",
        provider_request_fingerprint=hashlib.sha256(b"fake-request-v1").hexdigest(),
        request_fingerprint=hashlib.sha256(
            json.dumps(request.to_dict(), sort_keys=True).encode()
        ).hexdigest(),
        latency_ms=0,
        narrative_policy_version=request.narrative_policy_version,
        output_contract_id=request.output_contract.contract_id,
        price_snapshot=contracts.ModelPriceReceipt(
            version="fake-model-price-v1",
            currency="CNY",
            snapshot_digest=price_digest,
            input_microunits_per_million_tokens=0,
            output_microunits_per_million_tokens=0,
        ),
        usage=usage,
        cost=contracts.ModelCost(
            currency="CNY",
            microunits=0,
            price_snapshot_version="fake-model-price-v1",
            price_snapshot_digest=price_digest,
            input_microunits_per_million_tokens=0,
            output_microunits_per_million_tokens=0,
        ),
    )


def make_output_contract(narrative: Any) -> Any:
    return narrative.OutputContract(
        contract_id="orchestrator-test-v1",
        language="zh-CN",
        min_blocks=1,
        max_blocks=4,
        max_output_chars=1200,
        required_dimension_ids=("career",),
        required_limit_kind_ids=("limit:traditional",),
        disclosure_text="AI 辅助生成，仅供传统文化参考。",
    )


def make_job(
    orchestrator: Any, contracts: Any, narrative: Any, *, prepare: Any | None = None
) -> Any:
    return orchestrator.ReadingJob(
        id="job:test",
        prepare_command=prepare or make_prepare(contracts),
        narrative_policy_version="policy-v1",
        output_contract=make_output_contract(narrative),
        language="zh-CN",
        max_output_chars=1200,
        max_attempts=2,
    )
