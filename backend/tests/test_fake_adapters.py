import importlib
from uuid import uuid4


async def test_fake_payment_never_reports_real_settlement() -> None:
    payment = importlib.import_module("app.adapters.payment")
    gateway = payment.FakePaymentGateway()

    checkout = await gateway.create_checkout(
        order_id=uuid4(),
        amount_minor=2990,
        currency="CNY",
    )
    notification = await gateway.verify_notification(b"untrusted callback")
    queried = await gateway.query_payment(attempt_id=uuid4())
    refund = await gateway.request_refund(
        payment_id=uuid4(),
        amount_minor=2990,
        reason="test-only",
    )
    queried_refund = await gateway.query_refund(refund_id=uuid4())

    assert checkout.channel == "fake"
    assert checkout.status == "unavailable"
    assert checkout.redirect_url is None
    assert notification.verified is False
    assert notification.payment_succeeded is False
    assert queried.status == "unavailable"
    assert queried.payment_succeeded is False
    assert refund.status == "unavailable"
    assert refund.refund_succeeded is False
    assert queried_refund.status == "unavailable"
    assert queried_refund.refund_succeeded is False


async def test_fake_model_returns_traceable_candidate_without_acceptance_state() -> None:
    model = importlib.import_module("app.adapters.model")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    runtime = importlib.import_module("app.readings.runtime_contracts")
    gateway = model.FakeModelGateway()
    brief = runtime.ReadingBrief.from_dict(
        {
            "question": "事业主线是什么？",
            "vocabulary": [],
            "facts": [
                {
                    "ref": "fact:fake-1",
                    "subject_ref": "profile-version:test",
                    "kind_id": "kind.structure",
                    "value": {"fixture": True},
                    "display_text": "这是合同测试事实。",
                }
            ],
            "evidence": [],
            "findings": [
                {
                    "ref": "finding:fake-1",
                    "subject_ref": "profile-version:test",
                    "dimension_ids": ["career"],
                    "kind_id": "kind.tendency",
                    "data": {"fixture": True},
                    "fact_refs": ["fact:fake-1"],
                    "evidence_refs": [],
                    "limit_kind_ids": ["limit:fake"],
                    "support_mode": "exact",
                }
            ],
            "claim_scopes": [
                {
                    "subject_ref": "profile-version:test",
                    "dimension_id": "career",
                    "allowed_kind_ids": ["kind.tendency"],
                    "certainty_ceiling_id": "certainty.tendency",
                    "fact_refs": ["fact:fake-1"],
                    "evidence_refs": [],
                }
            ],
            "limits": [
                {
                    "kind_id": "limit:fake",
                    "public_text": "这是合同测试边界。",
                    "scope_refs": ["profile-version:test"],
                    "detail_ids": [],
                }
            ],
            "prior_answer": None,
            "request_view": None,
        }
    )
    output_contract = narrative.OutputContract.from_dict(
        {
            "schema_version": "mingli-output-contract-v1",
            "contract_id": "preview-v1",
            "language": "zh-CN",
            "min_blocks": 1,
            "max_blocks": 4,
            "max_output_chars": 1200,
            "required_dimension_ids": ["career"],
            "required_limit_kind_ids": ["limit:fake"],
            "disclosure_text": "AI 辅助生成，仅供传统文化参考。",
        }
    )
    request = narrative.NarrativeRequest(
        brief=brief,
        narrative_policy_version="policy-v1",
        output_contract=output_contract,
        language="zh-CN",
        max_output_chars=1200,
    )

    generation = await gateway.generate(request)
    candidate = generation.candidate
    payload = candidate.to_dict()

    assert payload["blocks"][0]["fact_refs"] == ["fact:fake-1"]
    assert payload["blocks"][0]["finding_refs"] == ["finding:fake-1"]
    assert payload["blocks"][0]["limit_kind_ids"] == ["limit:fake"]
    assert "accepted" not in payload
    assert not hasattr(candidate, "accepted")


async def test_fake_runtime_is_explicitly_non_production() -> None:
    runtime = importlib.import_module("app.adapters.runtime")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    adapter = runtime.FakeMingliRuntimeAdapter()

    description = await adapter.execute(contracts.Describe())

    assert adapter.production_ready is False
    assert description.protocol_version == "mingli-portable-interface-v2"
    assert tuple(capability["id"] for capability in description.capabilities) == (
        "bazi",
        "fengshui",
        "fortune",
        "liuren",
        "liuyao",
        "luming-nayin",
        "meihua",
        "physiognomy",
        "qimen",
        "selection",
        "taiyi",
        "xingming",
        "ziwei",
    )


async def test_fake_runtime_does_not_apply_the_p0_product_allowlist() -> None:
    runtime = importlib.import_module("app.adapters.runtime")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    adapter = runtime.FakeMingliRuntimeAdapter()

    result = await adapter.execute(
        contracts.Prepare(
            query="验证未公开能力仍由完整 Runtime 承载",
            intent={
                "subject_refs": ["fixture:test"],
                "object_id": "fixture_object",
                "dimension_ids": ["overview"],
                "horizon": {"kind_id": "fixture", "start": None, "end": None},
                "capability_id": "ziwei",
                "comparisons": [],
            },
            facts={"fixture:test": {"fixture_input": "test-only"}},
        )
    )

    assert isinstance(result, contracts.Prepared)
    assert result.brief.to_dict()["request_view"]["capability_ids"] == ["ziwei"]


async def test_fake_runtime_can_stop_prepare_and_accept_first_copy_only() -> None:
    runtime = importlib.import_module("app.adapters.runtime")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    adapter = runtime.FakeMingliRuntimeAdapter()
    intent = {
        "subject_refs": ["profile-version:test"],
        "object_id": "natal",
        "dimension_ids": ["overview"],
        "horizon": {"kind_id": "life", "start": None, "end": None},
        "capability_id": "bazi",
        "comparisons": [],
    }

    stopped = await adapter.execute(
        contracts.Prepare(
            query="看一下这个八字",
            intent=intent,
            facts={},
        )
    )
    prepared = await adapter.execute(
        contracts.Prepare(
            query="看一下这个八字",
            intent=intent,
            facts={
                "profile-version:test": {
                    "birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00"
                }
            },
        )
    )
    first = await adapter.execute(
        contracts.Complete(
            state_token=prepared.state_token,
            public_copy="第一次提交的测试正文。",
        )
    )
    replay = await adapter.execute(
        contracts.Complete(
            state_token=prepared.state_token,
            public_copy="第二次不应覆盖的正文。",
        )
    )

    assert stopped.reason == "need_input"
    assert stopped.state_token == "fake-opaque-state"
    assert prepared.state_token == "fake-opaque-state"
    assert first.public_copy == "第一次提交的测试正文。"
    assert replay.public_copy == first.public_copy
