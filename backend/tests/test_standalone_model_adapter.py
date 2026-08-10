import asyncio
import base64
import hashlib
import json
import logging
import traceback
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import httpx
import pytest
from app.adapters.model import (
    DEEPSEEK_CHAT_COMPLETIONS_PATH,
    DEEPSEEK_MODEL_ID,
    DEEPSEEK_MODEL_PROFILE_ID,
    DeepSeekStandaloneModelAdapter,
    ModelCallReceipt,
    ModelPriceSnapshot,
    build_deepseek_model_adapter,
)
from app.config import Settings
from app.observability import configure_logging
from app.readings.errors import NarrativeGenerationError
from app.readings.model_contracts import ModelCost, ModelPriceReceipt, ModelTokenUsage
from app.readings.narrative_contracts import NarrativeRequest, OutputContract
from app.readings.runtime_contracts import ReadingBrief
from pydantic import SecretStr, ValidationError


def _brief(question: str = "事业上最该先抓住哪条主线？") -> ReadingBrief:
    return ReadingBrief.from_dict(
        {
            "question": question,
            "vocabulary": [],
            "facts": [
                {
                    "ref": "fact:fixture-1",
                    "subject_ref": "subject:fixture-1",
                    "kind_id": "kind.structure",
                    "value": {"fixture": True},
                    "display_text": "测试事实。",
                }
            ],
            "evidence": [],
            "findings": [],
            "claim_scopes": [
                {
                    "subject_ref": "subject:fixture-1",
                    "dimension_id": "career",
                    "allowed_kind_ids": ["kind.tendency"],
                    "certainty_ceiling_id": "certainty.tendency",
                    "fact_refs": ["fact:fixture-1"],
                    "evidence_refs": [],
                }
            ],
            "limits": [],
            "prior_answer": None,
            "request_view": None,
        }
    )


def _narrative_request(question: str = "事业上最该先抓住哪条主线？") -> NarrativeRequest:
    return NarrativeRequest(
        brief=_brief(question),
        narrative_policy_version="policy-v1",
        output_contract=OutputContract(
            contract_id="preview-v1",
            language="zh-CN",
            min_blocks=1,
            max_blocks=4,
            max_output_chars=1200,
            required_dimension_ids=("career",),
            required_limit_kind_ids=(),
            disclosure_text="AI 辅助生成，仅供传统文化参考。",
        ),
        language="zh-CN",
        max_output_chars=1200,
    )


def _candidate_payload() -> dict[str, Any]:
    return {
        "schema_version": "mingli-narrative-candidate-v1",
        "blocks": [
            {
                "block_id": "b1",
                "block_type": "claim",
                "text": "先抓住可持续积累。",
                "subject_ref": "subject:fixture-1",
                "dimension_id": "career",
                "claim_kind_id": "kind.tendency",
                "certainty_id": "certainty.tendency",
                "fact_refs": ["fact:fixture-1"],
                "finding_refs": [],
                "evidence_refs": [],
                "limit_kind_ids": [],
            }
        ],
    }


def _provider_response(
    *,
    content: object | None = None,
    usage: Mapping[str, object] | None = None,
    finish_reason: str = "stop",
) -> dict[str, object]:
    return {
        "id": "provider-body-id",
        "model": DEEPSEEK_MODEL_ID,
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(content or _candidate_payload(), ensure_ascii=False),
                },
            }
        ],
        "usage": dict(
            usage
            or {
                "prompt_tokens": 3,
                "completion_tokens": 7,
                "total_tokens": 10,
            }
        ),
    }


class RecordingAuditSink:
    def __init__(self) -> None:
        self.records: list[ModelCallReceipt] = []

    async def record(self, record: ModelCallReceipt) -> None:
        self.records.append(record)


def _production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "production",
        "cookie_secure": True,
        "otp_adapter": "disabled",
        "identity_hash_key": "production-identity-key",
        "content_encryption_key_b64": base64.b64encode(b"p" * 32).decode(),
        "content_encryption_key_id": "production-content-v1",
        "runtime_adapter": "one-shot",
        "runtime_launcher_path": "/opt/mingli-master/scripts/run_reading_transaction.sh",
        "runtime_python_path": "/opt/mingli-runtime/venv/bin/python",
        "runtime_release_root": "/opt/mingli-master",
        "runtime_state_root": "/var/lib/mingli",
        "runtime_expected_manifest_digest": (
            "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
        ),
        "runtime_expected_capability_shape_sha256": (
            "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
        ),
        "model_adapter": "deepseek",
        "deepseek_api_key": "test-only-obviously-not-a-real-key",
        "model_price_snapshot_version": "deployment-price-fixture-v1",
        "model_input_price_microunits_per_million_tokens": 2_000_000,
        "model_output_price_microunits_per_million_tokens": 4_000_000,
    }
    values.update(overrides)
    return Settings(**values)


def _adapter(
    transport: httpx.AsyncBaseTransport,
    *,
    audits: RecordingAuditSink | None = None,
    **overrides: object,
) -> DeepSeekStandaloneModelAdapter:
    return DeepSeekStandaloneModelAdapter(
        api_key=SecretStr("test-only-obviously-not-a-real-key"),
        price_snapshot=ModelPriceSnapshot(
            version="fixture-price-v1",
            currency="CNY",
            input_microunits_per_million_tokens=2_000_000,
            output_microunits_per_million_tokens=4_000_000,
        ),
        audit_sink=audits or RecordingAuditSink(),
        transport=transport,
        **overrides,
    )


async def test_successful_call_returns_candidate_and_auditable_integer_cost() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=_provider_response(),
            headers={"X-Request-ID": "provider-request-fixture"},
        )

    audits = RecordingAuditSink()
    clock_values = iter((10.0, 10.125))
    adapter = DeepSeekStandaloneModelAdapter(
        api_key=SecretStr("test-only-obviously-not-a-real-key"),
        price_snapshot=ModelPriceSnapshot(
            version="fixture-price-v1",
            currency="CNY",
            input_microunits_per_million_tokens=2_000_000,
            output_microunits_per_million_tokens=4_000_000,
        ),
        audit_sink=audits,
        transport=httpx.MockTransport(handler),
        clock=lambda: next(clock_values),
    )

    try:
        generation = await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert generation.candidate.to_dict() == _candidate_payload()
    assert generation.receipt is audits.records[0]
    assert len(requests) == 1
    assert len(audits.records) == 1
    audit = audits.records[0]
    assert audit.model_profile_id == DEEPSEEK_MODEL_PROFILE_ID
    assert audit.provider == "deepseek"
    assert audit.provider_model_version == DEEPSEEK_MODEL_ID
    assert (
        audit.provider_request_fingerprint
        == hashlib.sha256(b"provider-request-fixture").hexdigest()
    )
    assert audit.request_fingerprint == hashlib.sha256(requests[0].content).hexdigest()
    assert audit.usage.input_tokens == 3
    assert audit.usage.output_tokens == 7
    assert audit.usage.total_tokens == 10
    assert audit.cost.currency == "CNY"
    assert audit.cost.microunits == 34
    assert audit.cost.price_snapshot_version == "fixture-price-v1"
    assert audit.cost.price_snapshot_digest == adapter._price_snapshot.snapshot_digest  # noqa: SLF001
    assert audit.cost.input_microunits_per_million_tokens == 2_000_000
    assert audit.cost.output_microunits_per_million_tokens == 4_000_000
    assert audit.latency_ms == 125


async def test_two_concurrent_jobs_receive_their_own_explicit_receipts() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        prompt = json.loads(body["messages"][1]["content"])
        question = prompt["prepared_brief"]["question"]
        if question == "job-a-question":
            await asyncio.sleep(0.01)
            request_id = "provider-request-job-a"
        else:
            request_id = "provider-request-job-b"
        return httpx.Response(
            200,
            json=_provider_response(),
            headers={"X-Request-ID": request_id},
        )

    adapter = _adapter(httpx.MockTransport(handler))
    try:
        first, second = await asyncio.gather(
            adapter.generate(_narrative_request("job-a-question")),
            adapter.generate(_narrative_request("job-b-question")),
        )
    finally:
        await adapter.aclose()

    assert (
        first.receipt.provider_request_fingerprint
        == hashlib.sha256(b"provider-request-job-a").hexdigest()
    )
    assert (
        second.receipt.provider_request_fingerprint
        == hashlib.sha256(b"provider-request-job-b").hexdigest()
    )
    assert first.receipt.request_fingerprint != second.receipt.request_fingerprint
    assert first.receipt is not second.receipt


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (302, "model_redirect_forbidden"),
        (429, "model_rate_limited"),
        (500, "model_upstream_error"),
        (503, "model_upstream_error"),
        (400, "model_http_error"),
    ],
)
async def test_http_failures_are_single_shot_and_do_not_expose_error_bodies(
    status_code: int,
    expected_code: str,
) -> None:
    request_count = 0
    sensitive_error = "provider-error user@example.com leaked-secret-value"

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            status_code,
            json={"error": {"message": sensitive_error}},
            headers={"Location": "https://evil.invalid/capture"} if status_code == 302 else {},
        )

    audits = RecordingAuditSink()
    adapter = _adapter(httpx.MockTransport(handler), audits=audits)
    try:
        with pytest.raises(NarrativeGenerationError) as captured:
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert request_count == 1
    assert str(captured.value) == expected_code
    assert sensitive_error not in repr(captured.value)
    assert "api.deepseek.com" not in repr(captured.value)
    assert "evil.invalid" not in repr(captured.value)
    assert len(audits.records) == 1
    assert audits.records[0].outcome == "failed"
    assert audits.records[0].error_code == expected_code
    assert audits.records[0].usage_known is False
    assert audits.records[0].cost is None
    assert audits.records[0].price_snapshot.version == "fixture-price-v1"


@pytest.mark.parametrize(
    ("case", "expected_code"),
    [
        ("non_json", "model_invalid_response"),
        ("missing_choices", "model_invalid_response"),
        ("multiple_choices", "model_invalid_response"),
        ("empty_content", "model_invalid_response"),
        ("array_content", "model_invalid_response"),
        ("multiple_json_objects", "model_invalid_response"),
        ("schema_mismatch", "model_invalid_response"),
        ("finish_reason", "model_invalid_response"),
        ("model_mismatch", "model_unapproved_response"),
        ("missing_usage", "model_usage_invalid"),
        ("negative_usage", "model_usage_invalid"),
        ("inconsistent_usage", "model_usage_invalid"),
    ],
)
async def test_malformed_responses_fail_closed_after_exactly_one_request(
    case: str,
    expected_code: str,
) -> None:
    request_count = 0
    payload = _provider_response()
    if case == "missing_choices":
        payload.pop("choices")
    elif case == "multiple_choices":
        payload["choices"] = [*payload["choices"], *payload["choices"]]  # type: ignore[misc]
    elif case == "empty_content":
        payload["choices"][0]["message"]["content"] = ""  # type: ignore[index]
    elif case == "array_content":
        payload["choices"][0]["message"]["content"] = "[]"  # type: ignore[index]
    elif case == "multiple_json_objects":
        encoded = json.dumps(_candidate_payload(), ensure_ascii=False)
        payload["choices"][0]["message"]["content"] = f"{encoded}\n{encoded}"  # type: ignore[index]
    elif case == "schema_mismatch":
        payload["choices"][0]["message"]["content"] = "{}"  # type: ignore[index]
    elif case == "finish_reason":
        payload["choices"][0]["finish_reason"] = "length"  # type: ignore[index]
    elif case == "model_mismatch":
        payload["model"] = "provider-silent-fallback"
    elif case == "missing_usage":
        payload.pop("usage")
    elif case == "negative_usage":
        payload["usage"] = {
            "prompt_tokens": -1,
            "completion_tokens": 7,
            "total_tokens": 6,
        }
    elif case == "inconsistent_usage":
        payload["usage"] = {
            "prompt_tokens": 3,
            "completion_tokens": 7,
            "total_tokens": 11,
        }

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if case == "non_json":
            return httpx.Response(200, content=b"not-json", headers={"X-Request-ID": "fixture"})
        return httpx.Response(200, json=payload, headers={"X-Request-ID": "fixture"})

    audits = RecordingAuditSink()
    adapter = _adapter(httpx.MockTransport(handler), audits=audits)
    try:
        with pytest.raises(NarrativeGenerationError) as captured:
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert request_count == 1
    assert str(captured.value) == expected_code
    assert captured.value.__context__ is None
    assert len(audits.records) == 1
    audit = audits.records[0]
    assert audit.outcome == "failed"
    assert audit.error_code == expected_code
    if case == "schema_mismatch":
        assert audit.usage is not None
        assert audit.usage.total_tokens == 10
        assert audit.cost is not None
    if case == "model_mismatch":
        assert audit.usage is not None
        assert audit.usage.total_tokens == 10
        assert audit.cost is None
        assert audit.to_dict()["cost_unknown_reason"] == "price_snapshot_model_mismatch"


async def test_traceback_locals_never_retain_the_key_prompt_or_authorized_request() -> None:
    sensitive_prompt = "事业上最该先抓住哪条主线？"
    api_key = "test-only-obviously-not-a-real-key"

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("provider transport failed", request=request)

    adapter = _adapter(httpx.MockTransport(handler))
    try:
        with pytest.raises(NarrativeGenerationError) as captured:
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    frames: list[str] = []
    current = captured.value.__traceback__
    while current is not None:
        if current.tb_frame.f_code.co_filename.endswith("/app/adapters/model.py"):
            frames.append(repr(current.tb_frame.f_locals))
        current = current.tb_next
    rendered_locals = "\n".join(frames)
    assert api_key not in rendered_locals
    assert sensitive_prompt not in rendered_locals
    assert "authorization" not in rendered_locals.lower()


async def test_external_cancellation_carries_a_safe_receipt_without_sensitive_frames() -> None:
    sensitive_prompt = "事业上最该先抓住哪条主线？"
    api_key = "test-only-obviously-not-a-real-key"
    request_started = asyncio.Event()
    never_complete = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        request_started.set()
        await never_complete.wait()
        raise AssertionError("unreachable")

    audits = RecordingAuditSink()
    adapter = _adapter(httpx.MockTransport(handler), audits=audits)
    task = asyncio.create_task(adapter.generate(_narrative_request(sensitive_prompt)))
    try:
        await request_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError) as captured:
            await task
    finally:
        await adapter.aclose()

    receipt = getattr(captured.value, "receipt", None)
    assert receipt is audits.records[0]
    assert receipt.outcome == "failed"
    assert receipt.error_code == "model_cancelled"
    frames: list[str] = []
    current = captured.value.__traceback__
    while current is not None:
        if current.tb_frame.f_code.co_filename.endswith("/app/adapters/model.py"):
            frames.append(repr(current.tb_frame.f_locals))
        current = current.tb_next
    rendered_locals = "\n".join(frames)
    assert api_key not in rendered_locals
    assert sensitive_prompt not in rendered_locals
    assert "authorization" not in rendered_locals.lower()
    assert "body_bytes" not in rendered_locals


class CountingByteStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.yielded = 0

    async def __aiter__(self):  # type: ignore[no-untyped-def]
        for chunk in self.chunks:
            self.yielded += 1
            yield chunk


async def test_content_length_over_cap_is_rejected_before_reading_the_body() -> None:
    stream = CountingByteStream([b"{}"])

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Length": "1000"},
            stream=stream,
        )

    adapter = _adapter(httpx.MockTransport(handler), max_response_bytes=100)
    try:
        with pytest.raises(NarrativeGenerationError, match="model_response_too_large"):
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert stream.yielded == 0


async def test_streaming_response_stops_reading_as_soon_as_the_cap_is_crossed() -> None:
    stream = CountingByteStream([b" " * 60, b" " * 60, b"must-not-be-read"])

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    adapter = _adapter(httpx.MockTransport(handler), max_response_bytes=100)
    try:
        with pytest.raises(NarrativeGenerationError, match="model_response_too_large"):
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert stream.yielded == 2


async def test_compressed_provider_response_is_rejected_without_decompression() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            stream=CountingByteStream([b"compressed-provider-bytes"]),
            headers={"Content-Encoding": "gzip", "X-Request-ID": "fixture"},
        )

    adapter = _adapter(httpx.MockTransport(handler))
    try:
        with pytest.raises(NarrativeGenerationError, match="model_encoding_forbidden"):
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert len(requests) == 1
    assert requests[0].headers["accept-encoding"] == "identity"


async def test_usage_is_bounded_by_the_frozen_profile() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json=_provider_response(
                usage={
                    "prompt_tokens": 3,
                    "completion_tokens": 4097,
                    "total_tokens": 4100,
                }
            ),
            headers={"X-Request-ID": "fixture"},
        )

    audits = RecordingAuditSink()
    adapter = _adapter(httpx.MockTransport(handler), audits=audits, max_output_tokens=4096)
    try:
        with pytest.raises(NarrativeGenerationError, match="model_usage_invalid"):
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert len(audits.records) == 1
    assert audits.records[0].usage is not None
    assert audits.records[0].usage.output_tokens == 4097
    assert audits.records[0].cost is not None
    assert audits.records[0].to_dict()["usage_known"] is True
    assert audits.records[0].to_dict()["cost_known"] is True


@pytest.mark.parametrize("failure_kind", ["connect", "read", "overall"])
async def test_transport_timeouts_are_single_shot_and_strip_sensitive_exception_chains(
    failure_kind: str,
) -> None:
    request_count = 0

    class ReadTimeoutStream(httpx.AsyncByteStream):
        async def __aiter__(self):  # type: ignore[no-untyped-def]
            raise httpx.ReadTimeout("leaked-secret-value")
            yield b""  # pragma: no cover

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if failure_kind == "connect":
            raise httpx.ConnectTimeout("leaked-secret-value", request=request)
        if failure_kind == "read":
            return httpx.Response(200, stream=ReadTimeoutStream())
        await asyncio.sleep(0.05)
        return httpx.Response(200, json=_provider_response())

    adapter = _adapter(
        httpx.MockTransport(handler),
        overall_timeout_seconds=0.01 if failure_kind == "overall" else 1.0,
    )
    try:
        with pytest.raises(NarrativeGenerationError) as captured:
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert request_count == 1
    assert str(captured.value) == "model_timeout"
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    rendered_traceback = "".join(
        traceback.format_exception(
            type(captured.value), captured.value, captured.value.__traceback__
        )
    )
    assert "leaked-secret-value" not in repr(captured.value)
    assert "test-only-obviously-not-a-real-key" not in repr(captured.value)
    assert "leaked-secret-value" not in rendered_traceback
    assert "test-only-obviously-not-a-real-key" not in rendered_traceback


async def test_non_timeout_transport_error_is_detached_from_authorized_request() -> None:
    request_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        raise httpx.ConnectError("leaked-secret-value", request=request)

    adapter = _adapter(httpx.MockTransport(handler))
    try:
        with pytest.raises(NarrativeGenerationError) as captured:
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert request_count == 1
    assert str(captured.value) == "model_transport_error"
    assert captured.value.__context__ is None
    assert "leaked-secret-value" not in repr(captured.value)
    assert "test-only-obviously-not-a-real-key" not in repr(captured.value)


async def test_unapproved_policy_is_rejected_before_transport_without_sensitive_context() -> None:
    request_count = 0
    sensitive_policy = "unapproved-policy-leaked-secret-value"

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json=_provider_response())

    adapter = _adapter(httpx.MockTransport(handler))
    try:
        with pytest.raises(NarrativeGenerationError) as captured:
            await adapter.generate(
                replace(_narrative_request(), narrative_policy_version=sensitive_policy)
            )
    finally:
        await adapter.aclose()

    assert request_count == 0
    assert str(captured.value) == "model_policy_not_approved"
    assert captured.value.__context__ is None
    assert sensitive_policy not in repr(captured.value)


async def test_untrusted_output_contract_id_is_rejected_before_transport() -> None:
    request_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json=_provider_response())

    request = replace(
        _narrative_request(),
        output_contract=replace(
            _narrative_request().output_contract,
            contract_id="customer@example.com secret contract",
        ),
    )
    adapter = _adapter(httpx.MockTransport(handler))
    try:
        with pytest.raises(
            NarrativeGenerationError,
            match="model_output_contract_not_approved",
        ):
            await adapter.generate(request)
    finally:
        await adapter.aclose()

    assert request_count == 0


def test_exact_deployment_secret_name_is_loaded_without_prefixed_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("MINGLI_DEEPSEEK_API_KEY", "must-not-be-accepted")

    with pytest.raises(ValidationError, match="DeepSeek API key"):
        Settings(
            model_adapter="deepseek",
            model_price_snapshot_version="fixture-v1",
            model_input_price_microunits_per_million_tokens=1,
            model_output_price_microunits_per_million_tokens=1,
        )

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-obviously-not-a-real-key")
    settings = Settings(
        model_adapter="deepseek",
        model_price_snapshot_version="fixture-v1",
        model_input_price_microunits_per_million_tokens=1,
        model_output_price_microunits_per_million_tokens=1,
    )

    assert settings.deepseek_api_key is not None
    assert settings.deepseek_api_key.get_secret_value() == "test-only-obviously-not-a-real-key"
    assert "test-only-obviously-not-a-real-key" not in repr(settings)


@pytest.mark.parametrize("wrong_name", ["deepseek_api_key", "DeepSeek_Api_Key"])
def test_deepseek_secret_environment_name_is_case_sensitive(
    monkeypatch: pytest.MonkeyPatch,
    wrong_name: str,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv(wrong_name, "must-not-be-accepted")

    with pytest.raises(ValidationError, match="DeepSeek API key"):
        Settings(
            model_adapter="deepseek",
            model_price_snapshot_version="fixture-v1",
            model_input_price_microunits_per_million_tokens=1,
            model_output_price_microunits_per_million_tokens=1,
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"model_adapter": "fake"}, "Fake Model"),
        ({"model_profile_id": "unknown-profile"}, "model profile"),
        ({"model_id": "deepseek-v4-flsh"}, "model ID"),
        ({"model_base_url": "http://api.deepseek.com"}, "base URL"),
        ({"model_base_url": "https://evil.invalid"}, "base URL"),
        ({"model_endpoint_path": "/other"}, "endpoint path"),
        ({"deepseek_api_key": None}, "API key"),
        ({"model_price_snapshot_version": None}, "price snapshot"),
        ({"model_price_snapshot_version": "unsafe snapshot\nsecret"}, "price snapshot"),
        ({"model_input_price_microunits_per_million_tokens": None}, "token prices"),
        ({"model_connect_timeout_seconds": float("inf")}, "connect timeout"),
        ({"model_read_timeout_seconds": 0}, "read timeout"),
        ({"model_overall_timeout_seconds": 1000}, "overall timeout"),
        ({"model_max_response_bytes": 0}, "response body"),
        ({"model_temperature": 0.3}, "model profile"),
        ({"model_max_output_tokens": 4095}, "model profile"),
        ({"model_max_output_tokens": 100_000}, "output tokens"),
    ],
)
def test_production_model_configuration_fails_closed(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        _production_settings(**overrides)


def test_production_model_configuration_freezes_one_deepseek_profile() -> None:
    settings = _production_settings()

    assert settings.model_adapter == "deepseek"
    assert settings.model_profile_id == DEEPSEEK_MODEL_PROFILE_ID
    assert settings.model_id == DEEPSEEK_MODEL_ID
    assert settings.model_base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert settings.model_endpoint_path == DEEPSEEK_CHAT_COMPLETIONS_PATH
    assert settings.model_thinking_mode == "not-sent-p0-v1"


def test_price_snapshot_identifier_is_safe_to_emit_as_audit_metadata() -> None:
    with pytest.raises(ValueError, match="snapshot version"):
        ModelPriceSnapshot(
            version="unsafe snapshot\nsecret",
            currency="CNY",
            input_microunits_per_million_tokens=1,
            output_microunits_per_million_tokens=1,
        )


def test_price_snapshot_digest_binds_version_currency_and_integer_rates() -> None:
    first = ModelPriceSnapshot(
        version="fixture-price-v1",
        currency="CNY",
        input_microunits_per_million_tokens=1,
        output_microunits_per_million_tokens=2,
    )
    changed_rate = ModelPriceSnapshot(
        version="fixture-price-v1",
        currency="CNY",
        input_microunits_per_million_tokens=1,
        output_microunits_per_million_tokens=3,
    )

    assert first.snapshot_digest != changed_rate.snapshot_digest
    assert len(first.snapshot_digest) == 64


def test_receipt_recomputes_price_snapshot_digest_and_integer_cost() -> None:
    snapshot = ModelPriceSnapshot(
        version="fixture-price-v1",
        currency="CNY",
        input_microunits_per_million_tokens=2_000_000,
        output_microunits_per_million_tokens=4_000_000,
    )
    with pytest.raises(ValueError, match="price receipt digest"):
        ModelPriceReceipt(
            version=snapshot.version,
            currency=snapshot.currency,
            snapshot_digest="0" * 64,
            input_microunits_per_million_tokens=(snapshot.input_microunits_per_million_tokens),
            output_microunits_per_million_tokens=(snapshot.output_microunits_per_million_tokens),
        )

    usage = ModelTokenUsage(input_tokens=3, output_tokens=7, total_tokens=10)
    price_receipt = ModelPriceReceipt(
        version=snapshot.version,
        currency=snapshot.currency,
        snapshot_digest=snapshot.snapshot_digest,
        input_microunits_per_million_tokens=snapshot.input_microunits_per_million_tokens,
        output_microunits_per_million_tokens=snapshot.output_microunits_per_million_tokens,
    )
    with pytest.raises(ValueError, match="computed model cost"):
        ModelCallReceipt(
            outcome="succeeded",
            error_code=None,
            model_profile_id=DEEPSEEK_MODEL_PROFILE_ID,
            model_profile_snapshot_digest="a" * 64,
            provider="deepseek",
            provider_model_version=DEEPSEEK_MODEL_ID,
            provider_request_fingerprint="b" * 64,
            request_fingerprint="c" * 64,
            latency_ms=1,
            narrative_policy_version="policy-v1",
            output_contract_id="preview-v1",
            price_snapshot=price_receipt,
            usage=usage,
            cost=ModelCost(
                currency="CNY",
                microunits=35,
                price_snapshot_version=snapshot.version,
                price_snapshot_digest=snapshot.snapshot_digest,
                input_microunits_per_million_tokens=(snapshot.input_microunits_per_million_tokens),
                output_microunits_per_million_tokens=(
                    snapshot.output_microunits_per_million_tokens
                ),
            ),
        )


async def test_safe_audit_log_excludes_api_key_prompt_and_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adapters import model as model_module

    messages: list[str] = []

    class LoggerFixture:
        def info(self, message: str) -> None:
            messages.append(message)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_provider_response(),
            headers={"X-Request-ID": "provider-request-safe"},
        )

    monkeypatch.setattr(model_module, "_logger", LoggerFixture())
    adapter = DeepSeekStandaloneModelAdapter(
        api_key=SecretStr("test-only-obviously-not-a-real-key"),
        price_snapshot=ModelPriceSnapshot(
            version="fixture-price-v1",
            currency="CNY",
            input_microunits_per_million_tokens=1,
            output_microunits_per_million_tokens=1,
        ),
        transport=httpx.MockTransport(handler),
    )
    try:
        await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    rendered = "\n".join(messages)
    assert "standalone_model_call" in rendered
    assert hashlib.sha256(b"provider-request-safe").hexdigest() in rendered
    assert "provider-request-safe" not in rendered
    for forbidden in (
        "test-only-obviously-not-a-real-key",
        "事业上最该先抓住哪条主线",
        "测试事实",
        "先抓住可持续积累",
        "authorization",
        "prepared_brief",
        "messages",
    ):
        assert forbidden not in rendered.lower()
    assert "test-only-obviously-not-a-real-key" not in repr(adapter)


async def test_untrusted_provider_request_id_cannot_inject_sensitive_audit_text() -> None:
    injected = "provider-id leaked-secret-value\nprepared_brief=full-prompt"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_provider_response(),
            headers={"X-Request-ID": injected},
        )

    audits = RecordingAuditSink()
    adapter = _adapter(httpx.MockTransport(handler), audits=audits)
    try:
        with pytest.raises(NarrativeGenerationError, match="model_invalid_response"):
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert len(audits.records) == 1
    assert audits.records[0].outcome == "failed"
    assert (
        audits.records[0].provider_request_fingerprint
        == hashlib.sha256(b"provider-body-id").hexdigest()
    )
    assert injected not in repr(audits.records[0])


@pytest.mark.parametrize("echo_field", ["request_id", "model"])
async def test_provider_metadata_can_never_echo_the_api_key_into_a_receipt(
    echo_field: str,
) -> None:
    api_key = "test-only-obviously-not-a-real-key"
    payload = _provider_response()
    headers = {"X-Request-ID": "provider-request-safe"}
    if echo_field == "request_id":
        headers["X-Request-ID"] = api_key
    else:
        payload["model"] = api_key

    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json=payload, headers=headers)

    audits = RecordingAuditSink()
    adapter = _adapter(httpx.MockTransport(handler), audits=audits)
    try:
        if echo_field == "model":
            with pytest.raises(NarrativeGenerationError, match="model_unapproved_response"):
                await adapter.generate(_narrative_request())
        else:
            await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert len(audits.records) == 1
    assert api_key not in repr(audits.records[0])
    assert api_key not in json.dumps(audits.records[0].to_dict(), sort_keys=True)


def test_root_debug_never_enables_raw_model_transport_header_logging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    echoed_key = "sk-test-only-obviously-not-a-real-key"
    caplog.set_level(logging.DEBUG)
    configure_logging("DEBUG")
    caplog.clear()

    for logger_name in ("httpx", "httpcore", "h2", "hpack"):
        transport_logger = logging.getLogger(logger_name)
        transport_logger.debug(
            "receive_response_headers headers=%r",
            [(b"x-request-id", echoed_key.encode())],
        )
        assert transport_logger.getEffectiveLevel() >= logging.WARNING

    assert echoed_key not in caplog.text


async def test_configured_worker_builds_and_closes_the_selected_model_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from worker import readings

    events: list[str] = []
    built_worker = object()

    class DatabaseFixture:
        sessions = object()

        def __init__(self, database_url: str) -> None:
            del database_url

        async def dispose(self) -> None:
            events.append("database-close")

    class ModelFixture:
        async def aclose(self) -> None:
            events.append("model-close")

    model = ModelFixture()
    settings = Settings(
        environment="test",
        model_adapter="deepseek",
        deepseek_api_key="test-only-obviously-not-a-real-key",
        model_price_snapshot_version="fixture-v1",
        model_input_price_microunits_per_million_tokens=1,
        model_output_price_microunits_per_million_tokens=1,
    )

    def build_worker_fixture(**kwargs: object) -> object:
        assert kwargs["model"] is model
        events.append("worker-build")
        return built_worker

    monkeypatch.setattr(readings, "get_settings", lambda: settings)
    monkeypatch.setattr(
        readings,
        "configure_logging",
        lambda level: events.append(f"logging:{level}"),
    )
    monkeypatch.setattr(readings, "Database", DatabaseFixture)
    monkeypatch.setattr(
        readings,
        "build_deepseek_model_adapter",
        lambda _settings: model,
        raising=False,
    )
    monkeypatch.setattr(readings, "build_reading_worker", build_worker_fixture)

    async with readings.configured_reading_worker() as worker:
        assert worker is built_worker
        assert events == ["logging:INFO", "worker-build"]

    assert events == ["logging:INFO", "worker-build", "model-close", "database-close"]


async def test_worker_disposes_database_even_when_model_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from worker import readings

    events: list[str] = []

    class DatabaseFixture:
        sessions = object()

        def __init__(self, database_url: str) -> None:
            del database_url

        async def dispose(self) -> None:
            events.append("database-close")

    class ModelFixture:
        async def aclose(self) -> None:
            events.append("model-close")
            raise RuntimeError("close failed")

    settings = Settings(
        environment="test",
        model_adapter="deepseek",
        deepseek_api_key="test-only-obviously-not-a-real-key",
        model_price_snapshot_version="fixture-v1",
        model_input_price_microunits_per_million_tokens=1,
        model_output_price_microunits_per_million_tokens=1,
    )
    monkeypatch.setattr(readings, "get_settings", lambda: settings)
    monkeypatch.setattr(readings, "Database", DatabaseFixture)
    monkeypatch.setattr(readings, "build_deepseek_model_adapter", lambda _settings: ModelFixture())
    monkeypatch.setattr(readings, "build_reading_worker", lambda **kwargs: object())

    with pytest.raises(RuntimeError, match="close failed"):
        async with readings.configured_reading_worker():
            pass

    assert events == ["model-close", "database-close"]


async def test_factory_maps_only_server_settings_into_the_adapter() -> None:
    settings = Settings(
        environment="test",
        model_adapter="deepseek",
        deepseek_api_key="test-only-obviously-not-a-real-key",
        model_price_snapshot_version="fixture-v1",
        model_input_price_microunits_per_million_tokens=2,
        model_output_price_microunits_per_million_tokens=4,
    )

    adapter = build_deepseek_model_adapter(
        settings,
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )

    assert isinstance(adapter, DeepSeekStandaloneModelAdapter)
    assert str(adapter._client.base_url).rstrip("/") == "https://dashscope.aliyuncs.com/compatible-mode/v1"  # noqa: SLF001
    assert adapter._client.follow_redirects is False  # noqa: SLF001
    assert adapter._client._trust_env is False  # noqa: SLF001
    await adapter.aclose()
