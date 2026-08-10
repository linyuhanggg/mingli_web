import inspect
import json
from pathlib import Path
from typing import Any

import httpx
import yaml
from app.adapters.model import (
    DEEPSEEK_MODEL_ID,
    DeepSeekStandaloneModelAdapter,
    ModelPriceSnapshot,
)
from app.readings.narrative_contracts import NarrativeRequest, OutputContract
from app.readings.runtime_contracts import ReadingBrief
from pydantic import SecretStr

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "openapi" / "internal-model-v1.yaml"
)


def _boundary_request() -> NarrativeRequest:
    return NarrativeRequest(
        brief=ReadingBrief.from_dict(
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
                "claim_scopes": [],
                "limits": [],
                "prior_answer": None,
                "request_view": None,
            }
        ),
        narrative_policy_version="policy-v1",
        output_contract=OutputContract(
            contract_id="preview-v1",
            language="zh-CN",
            min_blocks=1,
            max_blocks=4,
            max_output_chars=1200,
            required_dimension_ids=(),
            required_limit_kind_ids=(),
            disclosure_text="AI 辅助生成，仅供传统文化参考。",
        ),
        language="zh-CN",
        max_output_chars=1200,
    )


def _boundary_provider_response() -> dict[str, object]:
    candidate = {
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
    return {
        "id": "provider-body-id",
        "model": DEEPSEEK_MODEL_ID,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(candidate, ensure_ascii=False),
                },
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 7, "total_tokens": 10},
    }


class NoopAuditSink:
    async def record(self, audit: object) -> None:
        del audit


def _property_names(value: object) -> set[str]:
    if isinstance(value, dict):
        names = (
            set(value.get("properties", {})) if isinstance(value.get("properties"), dict) else set()
        )
        return names | set().union(*(_property_names(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_property_names(item) for item in value), set())
    return set()


def test_internal_model_contract_is_closed_and_agent_free() -> None:
    document: dict[str, Any] = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    operation = document["paths"]["/internal/model/v1/generations"]["post"]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert request_schema == {"$ref": "#/components/schemas/ModelGenerationRequest"}
    assert response_schema == {"$ref": "#/components/schemas/ModelGenerationResponse"}
    assert set(document["components"]["schemas"]["ModelGenerationRequest"]["properties"]) == {
        "model_profile_id",
        "narrative_policy",
        "output_contract",
        "prepared_brief",
        "generation",
        "idempotency",
    }
    assert set(document["components"]["schemas"]["ModelGenerationResponse"]["properties"]) == {
        "candidate",
        "usage",
        "latency_ms",
        "provider_model_version",
        "provider_request_fingerprint",
        "request_fingerprint",
        "model_profile_snapshot_digest",
        "cost",
    }
    schemas = document["components"]["schemas"]
    assert schemas["ModelGenerationRequest"]["properties"]["model_profile_id"]["enum"] == [
        "deepseek-v4-flash-p0-v1"
    ]
    assert schemas["NarrativePolicy"]["properties"]["version"]["enum"] == ["policy-v1"]
    assert schemas["GenerationLimits"]["properties"]["max_output_tokens"]["maximum"] == 8192
    assert schemas["ModelGenerationResponse"]["properties"]["provider_model_version"]["enum"] == [
        "deepseek-v4-flash"
    ]
    assert schemas["ModelGenerationResponse"]["properties"]["provider_request_fingerprint"] == {
        "type": "string",
        "description": (
            "SHA-256 of the untrusted provider request identifier; the raw ID is never stored."
        ),
        "pattern": "^[0-9a-f]{64}$",
    }
    assert schemas["ModelCost"]["properties"]["price_snapshot_version"] == {
        "type": "string",
        "pattern": "^[A-Za-z0-9._:-]{1,128}$",
        "maxLength": 128,
    }
    assert schemas["ModelCost"]["properties"]["price_snapshot_digest"] == {
        "type": "string",
        "pattern": "^[0-9a-f]{64}$",
    }
    assert all(
        schema.get("additionalProperties") is False
        for schema in document["components"]["schemas"].values()
        if schema.get("type") == "object"
    )
    forbidden = {
        "tools",
        "tool_choice",
        "functions",
        "function_call",
        "memory",
        "retrieval",
        "rag",
        "agent_run_id",
        "state_token",
        "user_id",
        "order_id",
        "entitlement_id",
        "reading_id",
        "job_id",
        "provider_request_id",
    }
    assert _property_names(document).isdisjoint(forbidden)


async def test_real_outbound_request_contains_only_the_closed_narrative_boundary() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json=_boundary_provider_response(),
            headers={"X-Request-ID": "provider-request-boundary"},
        )

    api_key = "test-only-obviously-not-a-real-key"
    adapter = DeepSeekStandaloneModelAdapter(
        api_key=SecretStr(api_key),
        price_snapshot=ModelPriceSnapshot(
            version="fixture-price-v1",
            currency="CNY",
            input_microunits_per_million_tokens=1,
            output_microunits_per_million_tokens=1,
        ),
        audit_sink=NoopAuditSink(),
        transport=httpx.MockTransport(handler),
    )
    try:
        generation = await adapter.generate(_boundary_request())
    finally:
        await adapter.aclose()

    assert len(captured) == 1
    outbound = captured[0]
    assert outbound.method == "POST"
    assert str(outbound.url) == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert outbound.headers["authorization"] == f"Bearer {api_key}"
    assert outbound.headers["accept"] == "application/json"
    assert outbound.headers["accept-encoding"] == "identity"
    assert outbound.headers["content-type"] == "application/json"
    assert outbound.headers["user-agent"] == "FateRadar-ModelPort/1"
    for forbidden_header in ("cookie", "x-api-key", "x-user-id", "x-reading-id"):
        assert forbidden_header not in outbound.headers

    body = json.loads(outbound.content)
    assert set(body) == {
        "model",
        "messages",
        "temperature",
        "max_tokens",
        "response_format",
        "stream",
        "enable_thinking",
    }
    assert body["model"] == DEEPSEEK_MODEL_ID
    assert body["response_format"] == {"type": "json_object"}
    assert body["stream"] is False
    assert body["enable_thinking"] is False
    assert [message["role"] for message in body["messages"]] == ["system", "user"]
    prompt = json.loads(body["messages"][1]["content"])
    assert set(prompt) == {
        "narrative_policy",
        "output_contract",
        "prepared_brief",
        "generation",
    }
    assert set(prompt["narrative_policy"]) == {"version", "instructions"}
    assert set(prompt["output_contract"]) == {"contract", "candidate_json_schema"}
    assert prompt["prepared_brief"] == _boundary_request().brief.to_dict()
    assert prompt["output_contract"]["contract"] == _boundary_request().output_contract.to_dict()

    serialized_body = json.dumps(body, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in (
        "state_token",
        "user_id",
        "order_id",
        "entitlement_id",
        "reading_id",
        "job_id",
        "raw_db_row",
        "cookie",
        "otp",
        "payment_secret",
        "api_key",
        "authorization",
        "test-only-obviously-not-a-real-key",
        '"tools"',
        '"functions"',
        '"memory"',
        '"retrieval"',
        '"rag"',
        '"network"',
        '"browser"',
        '"thinking"',
        '"agent_run_id"',
    ):
        assert forbidden not in serialized_body

    serialized_receipt = json.dumps(
        generation.receipt.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    for forbidden in (
        "事业上最该先抓住哪条主线",
        "测试事实",
        api_key.lower(),
        "state_token",
        "user_id",
        "order_id",
        "entitlement_id",
        "reading_id",
        "job_id",
        "prepared_brief",
        "messages",
    ):
        assert forbidden not in serialized_receipt


def test_callers_cannot_supply_a_model_or_endpoint_to_the_adapter() -> None:
    parameters = inspect.signature(DeepSeekStandaloneModelAdapter).parameters

    assert "model" not in parameters
    assert "model_id" not in parameters
    assert "provider" not in parameters
    # base_url is allowlisted server config only; free-form url/endpoint remain forbidden.
    assert "url" not in parameters
    assert "endpoint" not in parameters
    assert "endpoint_path" not in parameters
    assert parameters["base_url"].default == "https://dashscope.aliyuncs.com/compatible-mode/v1"
