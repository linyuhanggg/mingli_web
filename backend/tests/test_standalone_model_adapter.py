import asyncio
import base64
import hashlib
import json
import traceback
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import httpx
import pytest
from app.adapters.model import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_CHAT_COMPLETIONS_PATH,
    DEEPSEEK_MODEL_ID,
    DEEPSEEK_MODEL_PROFILE_ID,
    DeepSeekStandaloneModelAdapter,
    ModelCallAudit,
    ModelPriceSnapshot,
    build_deepseek_model_adapter,
)
from app.config import Settings
from app.readings.errors import NarrativeGenerationError
from app.readings.narrative_contracts import NarrativeRequest, OutputContract
from app.readings.runtime_contracts import ReadingBrief
from pydantic import SecretStr, ValidationError


def _brief() -> ReadingBrief:
    return ReadingBrief.from_dict(
        {
            "question": "事业上最该先抓住哪条主线？",
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


def _narrative_request() -> NarrativeRequest:
    return NarrativeRequest(
        brief=_brief(),
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
        self.records: list[ModelCallAudit] = []

    async def record(self, record: ModelCallAudit) -> None:
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
        candidate = await adapter.generate(_narrative_request())
    finally:
        await adapter.aclose()

    assert candidate.to_dict() == _candidate_payload()
    assert len(requests) == 1
    assert len(audits.records) == 1
    audit = audits.records[0]
    assert audit.model_profile_id == DEEPSEEK_MODEL_PROFILE_ID
    assert audit.provider == "deepseek"
    assert audit.provider_model_version == DEEPSEEK_MODEL_ID
    assert audit.provider_request_id == "provider-request-fixture"
    assert audit.request_fingerprint == hashlib.sha256(requests[0].content).hexdigest()
    assert audit.usage.input_tokens == 3
    assert audit.usage.output_tokens == 7
    assert audit.usage.total_tokens == 10
    assert audit.cost.currency == "CNY"
    assert audit.cost.microunits == 34
    assert audit.cost.price_snapshot_version == "fixture-price-v1"
    assert audit.latency_ms == 125


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

    adapter = _adapter(httpx.MockTransport(handler))
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
    assert audits.records == []


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
    assert settings.model_base_url == DEEPSEEK_BASE_URL
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
    assert "provider-request-safe" in rendered
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

    assert audits.records == []


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
        assert events == ["worker-build"]

    assert events == ["worker-build", "model-close", "database-close"]


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
    assert str(adapter._client.base_url) == "https://api.deepseek.com"  # noqa: SLF001
    assert adapter._client.follow_redirects is False  # noqa: SLF001
    assert adapter._client._trust_env is False  # noqa: SLF001
    await adapter.aclose()
