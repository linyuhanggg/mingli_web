from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Never, Protocol, cast, runtime_checkable

import httpx
from pydantic import SecretStr

from app.config import Settings
from app.readings.errors import NarrativeGenerationCancelled, NarrativeGenerationError
from app.readings.model_contracts import (
    ModelCallReceipt,
    ModelCost,
    ModelGenerationResult,
    ModelPriceReceipt,
    ModelTokenUsage,
    model_price_snapshot_digest,
)
from app.readings.narrative_contracts import (
    CANDIDATE_SCHEMA,
    NarrativeCandidate,
    NarrativeRequest,
)

DEEPSEEK_PROVIDER = "deepseek"
DEEPSEEK_MODEL_ID = "deepseek-v4-flash"
DEEPSEEK_MODEL_PROFILE_ID = "deepseek-v4-flash-p0-v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_CHAT_COMPLETIONS_PATH = "/chat/completions"
NARRATIVE_POLICY_INSTRUCTIONS = {
    "policy-v1": (
        "只使用 Prepared Brief 中的事实、发现、证据、范围和限制来撰写自然中文；"
        "不得补造事实、提高确定性、暴露内部结构或改写引用；"
        "只返回一个符合 Candidate JSON Schema 的 JSON object。"
    )
}
_SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "contracts" / "schemas"
_logger = logging.getLogger("mingli.model")
_SAFE_PROVIDER_METADATA = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_MAX_MODEL_USAGE_TOKENS = 10_000_000
_FROZEN_TEMPERATURE = 0.2
_FROZEN_MAX_OUTPUT_TOKENS = 4096


@runtime_checkable
class NarrativeModel(Protocol):
    async def generate(self, request: NarrativeRequest) -> ModelGenerationResult: ...


@dataclass(frozen=True, slots=True)
class ModelPriceSnapshot:
    version: str
    currency: str
    input_microunits_per_million_tokens: int
    output_microunits_per_million_tokens: int

    def __post_init__(self) -> None:
        if not _SAFE_PROVIDER_METADATA.fullmatch(self.version):
            raise ValueError("model price snapshot version must be a bounded safe identifier")
        if self.currency != "CNY":
            raise ValueError("P0 model price snapshot currency must be CNY")
        if (
            min(
                self.input_microunits_per_million_tokens,
                self.output_microunits_per_million_tokens,
            )
            < 0
        ):
            raise ValueError("model token prices must not be negative")

    @property
    def snapshot_digest(self) -> str:
        return model_price_snapshot_digest(
            version=self.version,
            currency=self.currency,
            input_microunits_per_million_tokens=(self.input_microunits_per_million_tokens),
            output_microunits_per_million_tokens=(self.output_microunits_per_million_tokens),
        )


@dataclass(frozen=True, slots=True)
class _ProviderObservation:
    model_version: str | None = None
    request_fingerprint: str | None = None
    usage: ModelTokenUsage | None = None


@dataclass(frozen=True, slots=True)
class _ModelCallOutcome:
    result: ModelGenerationResult | None
    error_code: str | None
    receipt: ModelCallReceipt | None
    cancelled: bool = False


class ModelAuditSink(Protocol):
    async def record(self, receipt: ModelCallReceipt) -> None: ...


class SafeModelAuditLogger:
    """Emits only bounded billing/transport metadata, never request or response bodies."""

    async def record(self, receipt: ModelCallReceipt) -> None:
        _logger.info(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")))


@lru_cache(maxsize=1)
def _candidate_json_schema() -> dict[str, Any]:
    with (_SCHEMA_ROOT / CANDIDATE_SCHEMA).open(encoding="utf-8") as stream:
        return cast(dict[str, Any], json.load(stream))


def _canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class DeepSeekStandaloneModelAdapter:
    """One-shot DeepSeek JSON-object transport with no retry, tools or fallback."""

    production_ready = True

    def __init__(
        self,
        *,
        api_key: SecretStr,
        price_snapshot: ModelPriceSnapshot,
        audit_sink: ModelAuditSink | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 60.0,
        overall_timeout_seconds: float = 75.0,
        max_response_bytes: int = 256 * 1024,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        if not api_key.get_secret_value().strip():
            raise ValueError("DeepSeek API key is required")
        if min(connect_timeout_seconds, read_timeout_seconds, overall_timeout_seconds) <= 0:
            raise ValueError("model timeouts must be positive")
        if max_response_bytes < 1 or max_output_tokens < 1:
            raise ValueError("model response and output limits must be positive")
        if not 0 <= temperature <= 2:
            raise ValueError("model temperature must be between zero and two")
        self._api_key = api_key
        self._price_snapshot = price_snapshot
        self._audit_sink = audit_sink or SafeModelAuditLogger()
        self._overall_timeout_seconds = overall_timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._clock = clock
        self._client = httpx.AsyncClient(
            base_url=DEEPSEEK_BASE_URL,
            transport=transport,
            timeout=httpx.Timeout(
                connect=connect_timeout_seconds,
                read=read_timeout_seconds,
                write=connect_timeout_seconds,
                pool=connect_timeout_seconds,
            ),
            follow_redirects=False,
            trust_env=False,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate(self, request: NarrativeRequest) -> ModelGenerationResult:
        outcome = await self._perform_call(request)
        del request
        if outcome.cancelled:
            receipt = outcome.receipt
            del outcome
            self._raise_cancelled_sanitized(receipt)
        if outcome.error_code is not None:
            self._raise_sanitized(outcome.error_code, outcome.receipt)
        if outcome.result is None:
            self._raise_sanitized("model_invalid_response", outcome.receipt)
        return outcome.result

    async def _perform_call(self, request: NarrativeRequest) -> _ModelCallOutcome:
        if not _SAFE_PROVIDER_METADATA.fullmatch(request.output_contract.contract_id):
            return _ModelCallOutcome(
                result=None,
                error_code="model_output_contract_not_approved",
                receipt=None,
            )
        try:
            body_bytes = _canonical_json(self._provider_request(request))
        except NarrativeGenerationError as error:
            return _ModelCallOutcome(result=None, error_code=str(error), receipt=None)
        request_fingerprint = hashlib.sha256(body_bytes).hexdigest()
        profile_digest = self._model_profile_snapshot_digest()
        policy_version = request.narrative_policy_version
        output_contract_id = request.output_contract.contract_id
        started = self._clock()
        sent = False
        candidate: NarrativeCandidate | None = None
        observation = _ProviderObservation()
        error_code: str | None = None
        cancelled = False
        try:
            async with asyncio.timeout(self._overall_timeout_seconds):
                sent = True
                async with self._client.stream(
                    "POST",
                    DEEPSEEK_CHAT_COMPLETIONS_PATH,
                    content=body_bytes,
                    headers={
                        "Authorization": f"Bearer {self._api_key.get_secret_value()}",
                        "Accept": "application/json",
                        "Accept-Encoding": "identity",
                        "Content-Type": "application/json",
                        "User-Agent": "FateRadar-ModelPort/1",
                    },
                ) as response:
                    observation = self._observe_provider(None, response.headers)
                    if 300 <= response.status_code < 400:
                        raise NarrativeGenerationError("model_redirect_forbidden")
                    if response.status_code == 429:
                        raise NarrativeGenerationError("model_rate_limited")
                    if response.status_code >= 500:
                        raise NarrativeGenerationError("model_upstream_error")
                    if response.status_code != 200:
                        raise NarrativeGenerationError("model_http_error")
                    content_encoding = response.headers.get("content-encoding")
                    if content_encoding not in {None, "", "identity"}:
                        raise NarrativeGenerationError("model_encoding_forbidden")
                    raw = await self._read_bounded(response)
                    response_payload = json.loads(raw)
                    observation = self._observe_provider(response_payload, response.headers)
                    candidate, model_version, provider_request_fingerprint, usage = (
                        self._parse_response(
                            response_payload,
                            response.headers,
                        )
                    )
                    observation = _ProviderObservation(
                        model_version=model_version,
                        request_fingerprint=provider_request_fingerprint,
                        usage=usage,
                    )
        except asyncio.CancelledError:
            error_code = "model_cancelled"
            cancelled = True
        except NarrativeGenerationError as error:
            error_code = str(error)
        except (TimeoutError, httpx.TimeoutException):
            error_code = "model_timeout"
        except httpx.HTTPError:
            error_code = "model_transport_error"
        except (UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            error_code = "model_invalid_response"
        except Exception:
            error_code = "model_transport_error"

        if not sent:
            return _ModelCallOutcome(result=None, error_code=error_code, receipt=None)
        latency_ms = max(0, round((self._clock() - started) * 1000))
        receipt = ModelCallReceipt(
            outcome="succeeded" if error_code is None else "failed",
            error_code=error_code,
            model_profile_id=DEEPSEEK_MODEL_PROFILE_ID,
            model_profile_snapshot_digest=profile_digest,
            provider=DEEPSEEK_PROVIDER,
            provider_model_version=observation.model_version,
            provider_request_fingerprint=observation.request_fingerprint,
            request_fingerprint=request_fingerprint,
            latency_ms=latency_ms,
            narrative_policy_version=policy_version,
            output_contract_id=output_contract_id,
            price_snapshot=self._price_receipt(),
            usage=observation.usage,
            cost=(
                self._cost(observation.usage)
                if observation.usage is not None and observation.model_version == DEEPSEEK_MODEL_ID
                else None
            ),
        )
        try:
            await self._audit_sink.record(receipt)
        except asyncio.CancelledError:
            cancelled = True
            error_code = "model_cancelled"
            if receipt.outcome != "failed":
                receipt = replace(receipt, outcome="failed", error_code=error_code)
        except Exception:
            _logger.error('{"event":"standalone_model_audit_sink_failed"}')
        if cancelled:
            return _ModelCallOutcome(
                result=None,
                error_code=error_code,
                receipt=receipt,
                cancelled=True,
            )
        if error_code is not None or candidate is None:
            return _ModelCallOutcome(result=None, error_code=error_code, receipt=receipt)
        return _ModelCallOutcome(
            result=ModelGenerationResult(candidate=candidate, receipt=receipt),
            error_code=None,
            receipt=receipt,
        )

    @staticmethod
    def _raise_sanitized(code: str, receipt: ModelCallReceipt | None) -> Never:
        raise NarrativeGenerationError(code, receipt=receipt) from None

    @staticmethod
    def _raise_cancelled_sanitized(receipt: ModelCallReceipt | None) -> Never:
        if receipt is None:
            raise asyncio.CancelledError from None
        raise NarrativeGenerationCancelled(receipt=receipt) from None

    async def _read_bounded(self, response: httpx.Response) -> bytes:
        content_length = response.headers.get("content-length")
        if content_length is not None:
            declared_length = int(content_length)
            if declared_length < 0:
                raise ValueError("negative Content-Length")
            if declared_length > self._max_response_bytes:
                raise NarrativeGenerationError("model_response_too_large")
        chunks = bytearray()
        async for chunk in response.aiter_bytes():
            if len(chunks) + len(chunk) > self._max_response_bytes:
                raise NarrativeGenerationError("model_response_too_large")
            chunks.extend(chunk)
        return bytes(chunks)

    def _provider_request(self, request: NarrativeRequest) -> dict[str, object]:
        policy_instructions = NARRATIVE_POLICY_INSTRUCTIONS.get(request.narrative_policy_version)
        if policy_instructions is None:
            raise NarrativeGenerationError("model_policy_not_approved")
        prompt = {
            "narrative_policy": {
                "version": request.narrative_policy_version,
                "instructions": policy_instructions,
            },
            "output_contract": {
                "contract": request.output_contract.to_dict(),
                "candidate_json_schema": _candidate_json_schema(),
            },
            "prepared_brief": request.brief.to_dict(),
            "generation": {
                "language": request.language,
                "max_output_chars": request.max_output_chars,
            },
        }
        return {
            "model": DEEPSEEK_MODEL_ID,
            "messages": [
                {
                    "role": "system",
                    "content": "Render one closed-world narrative Candidate JSON object.",
                },
                {
                    "role": "user",
                    "content": _canonical_json(prompt).decode("utf-8"),
                },
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_output_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }

    def _parse_response(
        self,
        payload: object,
        headers: httpx.Headers,
    ) -> tuple[NarrativeCandidate, str, str, ModelTokenUsage]:
        if not isinstance(payload, Mapping):
            raise NarrativeGenerationError("model_invalid_response")
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise NarrativeGenerationError("model_invalid_response")
        choice = choices[0]
        if not isinstance(choice, Mapping) or choice.get("finish_reason") != "stop":
            raise NarrativeGenerationError("model_invalid_response")
        message = choice.get("message")
        if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
            raise NarrativeGenerationError("model_invalid_response")
        content = json.loads(message["content"])
        if not isinstance(content, Mapping):
            raise NarrativeGenerationError("model_invalid_response")
        candidate = NarrativeCandidate.from_dict(content)
        model_version = payload.get("model")
        if not isinstance(model_version, str) or not model_version.strip():
            raise NarrativeGenerationError("model_invalid_response")
        if model_version != DEEPSEEK_MODEL_ID:
            raise NarrativeGenerationError("model_unapproved_response")
        provider_request_fingerprint = self._provider_request_fingerprint(
            headers.get("x-request-id") or payload.get("id")
        )
        if provider_request_fingerprint is None:
            raise NarrativeGenerationError("model_invalid_response")
        raw_usage = payload.get("usage")
        if not isinstance(raw_usage, Mapping):
            raise NarrativeGenerationError("model_usage_invalid")
        usage = self._parse_usage(raw_usage)
        return candidate, model_version, provider_request_fingerprint, usage

    def _observe_provider(
        self,
        payload: object | None,
        headers: httpx.Headers,
    ) -> _ProviderObservation:
        request_fingerprint = self._provider_request_fingerprint(headers.get("x-request-id"))
        if not isinstance(payload, Mapping):
            return _ProviderObservation(request_fingerprint=request_fingerprint)
        model_value = payload.get("model")
        model_version = DEEPSEEK_MODEL_ID if model_value == DEEPSEEK_MODEL_ID else None
        if request_fingerprint is None:
            request_fingerprint = self._provider_request_fingerprint(payload.get("id"))
        usage: ModelTokenUsage | None = None
        raw_usage = payload.get("usage")
        if isinstance(raw_usage, Mapping):
            with suppress(NarrativeGenerationError):
                usage = self._parse_observed_usage(raw_usage)
        return _ProviderObservation(
            model_version=model_version,
            request_fingerprint=request_fingerprint,
            usage=usage,
        )

    @staticmethod
    def _provider_request_fingerprint(value: object) -> str | None:
        if not isinstance(value, str) or not _SAFE_PROVIDER_METADATA.fullmatch(value):
            return None
        return hashlib.sha256(value.encode()).hexdigest()

    def _parse_usage(self, raw_usage: Mapping[str, object]) -> ModelTokenUsage:
        usage = self._parse_observed_usage(raw_usage)
        if usage.output_tokens > self._max_output_tokens:
            raise NarrativeGenerationError("model_usage_invalid")
        return usage

    def _parse_observed_usage(self, raw_usage: Mapping[str, object]) -> ModelTokenUsage:
        input_tokens = self._token_count(raw_usage.get("prompt_tokens"))
        output_tokens = self._token_count(raw_usage.get("completion_tokens"))
        total_tokens = self._token_count(raw_usage.get("total_tokens"))
        if (
            total_tokens != input_tokens + output_tokens
            or max(input_tokens, output_tokens, total_tokens) > _MAX_MODEL_USAGE_TOKENS
        ):
            raise NarrativeGenerationError("model_usage_invalid")
        return ModelTokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    @staticmethod
    def _token_count(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise NarrativeGenerationError("model_usage_invalid")
        return value

    def _cost(self, usage: ModelTokenUsage) -> ModelCost:
        numerator = Decimal(
            usage.input_tokens * self._price_snapshot.input_microunits_per_million_tokens
            + usage.output_tokens * self._price_snapshot.output_microunits_per_million_tokens
        )
        microunits = int((numerator / Decimal(1_000_000)).quantize(Decimal(1), ROUND_HALF_UP))
        return ModelCost(
            currency=self._price_snapshot.currency,
            microunits=microunits,
            price_snapshot_version=self._price_snapshot.version,
            price_snapshot_digest=self._price_snapshot.snapshot_digest,
            input_microunits_per_million_tokens=(
                self._price_snapshot.input_microunits_per_million_tokens
            ),
            output_microunits_per_million_tokens=(
                self._price_snapshot.output_microunits_per_million_tokens
            ),
        )

    def _price_receipt(self) -> ModelPriceReceipt:
        return ModelPriceReceipt(
            version=self._price_snapshot.version,
            currency=self._price_snapshot.currency,
            snapshot_digest=self._price_snapshot.snapshot_digest,
            input_microunits_per_million_tokens=(
                self._price_snapshot.input_microunits_per_million_tokens
            ),
            output_microunits_per_million_tokens=(
                self._price_snapshot.output_microunits_per_million_tokens
            ),
        )

    def _model_profile_snapshot_digest(self) -> str:
        return hashlib.sha256(
            _canonical_json(
                {
                    "base_url": DEEPSEEK_BASE_URL,
                    "endpoint_path": DEEPSEEK_CHAT_COMPLETIONS_PATH,
                    "max_output_tokens": self._max_output_tokens,
                    "model_id": DEEPSEEK_MODEL_ID,
                    "model_profile_id": DEEPSEEK_MODEL_PROFILE_ID,
                    "provider": DEEPSEEK_PROVIDER,
                    "response_format": {"type": "json_object"},
                    "stream": False,
                    "temperature": self._temperature,
                    "thinking_mode": "not-sent-p0-v1",
                }
            )
        ).hexdigest()


def build_deepseek_model_adapter(
    settings: Settings,
    *,
    audit_sink: ModelAuditSink | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> DeepSeekStandaloneModelAdapter:
    if settings.model_adapter != "deepseek":
        raise ValueError("DeepSeek adapter requires the approved model profile")
    if settings.deepseek_api_key is None:
        raise ValueError("DeepSeek API key is required")
    if settings.model_price_snapshot_version is None:
        raise ValueError("model price snapshot is required")
    input_price = settings.model_input_price_microunits_per_million_tokens
    output_price = settings.model_output_price_microunits_per_million_tokens
    if input_price is None or output_price is None:
        raise ValueError("model token prices are required")
    return DeepSeekStandaloneModelAdapter(
        api_key=settings.deepseek_api_key,
        price_snapshot=ModelPriceSnapshot(
            version=settings.model_price_snapshot_version,
            currency=settings.model_price_currency,
            input_microunits_per_million_tokens=input_price,
            output_microunits_per_million_tokens=output_price,
        ),
        audit_sink=audit_sink,
        transport=transport,
        connect_timeout_seconds=settings.model_connect_timeout_seconds,
        read_timeout_seconds=settings.model_read_timeout_seconds,
        overall_timeout_seconds=settings.model_overall_timeout_seconds,
        max_response_bytes=settings.model_max_response_bytes,
        temperature=settings.model_temperature,
        max_output_tokens=settings.model_max_output_tokens,
    )


def _objects(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, tuple):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        return ()
    return tuple(str(item) for item in value)


class FakeModelGateway:
    """Deterministic schema Fake; it has no tools, memory, network or acceptance role."""

    async def generate(self, request: NarrativeRequest) -> ModelGenerationResult:
        scopes = _objects(request.brief.get("claim_scopes"))
        scope = scopes[0] if scopes else {}
        subject_ref = str(scope.get("subject_ref", "fixture:subject"))
        dimension_id = str(scope.get("dimension_id", "overview"))
        allowed_kinds = _strings(scope.get("allowed_kind_ids"))
        findings = _objects(request.brief.get("findings"))
        limit_ids = tuple(item for item in request.output_contract.required_limit_kind_ids if item)

        candidate = NarrativeCandidate.from_dict(
            {
                "schema_version": "mingli-narrative-candidate-v1",
                "blocks": [
                    {
                        "block_id": "fake-block-1",
                        "block_type": "claim",
                        "text": "这是合同测试候选稿，不是正式命理解读。",
                        "subject_ref": subject_ref,
                        "dimension_id": dimension_id,
                        "claim_kind_id": (allowed_kinds[0] if allowed_kinds else "kind.fixture"),
                        "certainty_id": str(scope.get("certainty_ceiling_id", "certainty.fixture")),
                        "fact_refs": list(_strings(scope.get("fact_refs"))),
                        "finding_refs": [
                            str(item["ref"])
                            for item in findings
                            if item.get("subject_ref") == subject_ref
                            and dimension_id in _strings(item.get("dimension_ids"))
                        ],
                        "evidence_refs": list(_strings(scope.get("evidence_refs"))),
                        "limit_kind_ids": list(limit_ids),
                    }
                ],
            }
        )
        usage = ModelTokenUsage(input_tokens=0, output_tokens=0, total_tokens=0)
        price_snapshot = ModelPriceSnapshot(
            version="fake-model-price-v1",
            currency="CNY",
            input_microunits_per_million_tokens=0,
            output_microunits_per_million_tokens=0,
        )
        receipt = ModelCallReceipt(
            outcome="succeeded",
            error_code=None,
            model_profile_id="fake-model-p0-v1",
            model_profile_snapshot_digest=hashlib.sha256(b"fake-model-p0-v1").hexdigest(),
            provider="fake",
            provider_model_version="fake-model-v1",
            provider_request_fingerprint=hashlib.sha256(b"fake-request-v1").hexdigest(),
            request_fingerprint=hashlib.sha256(_canonical_json(request.to_dict())).hexdigest(),
            latency_ms=0,
            narrative_policy_version=request.narrative_policy_version,
            output_contract_id=request.output_contract.contract_id,
            price_snapshot=ModelPriceReceipt(
                version=price_snapshot.version,
                currency=price_snapshot.currency,
                snapshot_digest=price_snapshot.snapshot_digest,
                input_microunits_per_million_tokens=0,
                output_microunits_per_million_tokens=0,
            ),
            usage=usage,
            cost=ModelCost(
                currency="CNY",
                microunits=0,
                price_snapshot_version=price_snapshot.version,
                price_snapshot_digest=price_snapshot.snapshot_digest,
                input_microunits_per_million_tokens=0,
                output_microunits_per_million_tokens=0,
            ),
        )
        return ModelGenerationResult(candidate=candidate, receipt=receipt)
