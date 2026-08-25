import importlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from mingli_paths import MINGLI_CORE_ROOT, MINGLI_CORE_SCRIPTS


def prepare_payload() -> dict[str, Any]:
    return {
        "kind": "prepare",
        "query": "看一下这个八字",
        "intent": {
            "subject_refs": ["profile-version:test"],
            "object_id": "natal",
            "dimension_ids": ["overview"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
            "capability_id": "bazi",
            "comparisons": [],
        },
        "facts": {
            "profile-version:test": {"birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00"}
        },
        "state_token": None,
        "transition": None,
    }


def brief_payload() -> dict[str, Any]:
    return {
        "question": "看一下这个八字",
        "vocabulary": [],
        "facts": [],
        "evidence": [],
        "findings": [],
        "claim_scopes": [],
        "limits": [],
        "prior_answer": None,
        "request_view": None,
    }


def test_bazi_public_core_facts_are_declared_by_runtime_manifest() -> None:
    """Facts consumed by the Bazi ViewModels must retain Runtime provenance."""

    root = Path(__file__).parents[2]
    provider = json.loads(
        (root / ".runtime/v51-release/resources/runtime/providers/bazi.json").read_text(
            encoding="utf-8"
        )
    )
    runtime = provider["runtime_capability"]
    bindings = {
        item["name"]: tuple(item["json_pointers"])
        for item in runtime["output_bindings"]
    }
    expected = {
        "seasonal_profile",
        "tiaohou_markers",
        "element_inventory",
        "branch_relations",
        "shensha_auxiliary",
        "nayin",
        "interpretive_candidates",
    }

    assert expected <= set(bindings)
    for name in expected:
        assert bindings[name] == (f"/facts/chart_facts/output/{name}",)


def test_v53_bazi_declares_calendar_normalization_public_fact() -> None:
    provider = json.loads(
        (
            MINGLI_CORE_ROOT
            / "resources/runtime/providers/bazi.json"
        ).read_text(encoding="utf-8")
    )
    bindings = {
        item["name"]: tuple(item["json_pointers"])
        for item in provider["runtime_capability"]["output_bindings"]
    }
    assert bindings["calendar_normalization"] == (
        "/facts/chart_facts/public_calendar_normalization",
    )
    assert "calendar_normalization" in provider["runtime_capability"]["outputs"]


def test_v53_fortune_declares_calendar_normalization_public_fact() -> None:
    """Fortune must publish time-basis evidence without reproducing profile input."""

    provider = json.loads(
        (
            MINGLI_CORE_ROOT
            / "resources/runtime/providers/fortune.json"
        ).read_text(encoding="utf-8")
    )
    bindings = {
        item["name"]: tuple(item["json_pointers"])
        for item in provider["runtime_capability"]["output_bindings"]
    }
    assert bindings["calendar_normalization"] == (
        "/facts/chart_facts/public_calendar_normalization",
    )
    assert "calendar_normalization" in provider["runtime_capability"]["outputs"]


def test_v53_bazi_declares_xunkong_public_fact() -> None:
    provider = json.loads(
        (
            MINGLI_CORE_ROOT
            / "resources/runtime/providers/bazi.json"
        ).read_text(encoding="utf-8")
    )
    runtime = provider["runtime_capability"]
    bindings = {
        item["name"]: tuple(item["json_pointers"])
        for item in runtime["output_bindings"]
    }
    assert bindings["xunkong"] == ("/facts/chart_facts/output/xunkong",)
    assert "xunkong" in runtime["outputs"]


def test_v53_bazi_declares_san_yuan_public_fact() -> None:
    provider = json.loads(
        (
            MINGLI_CORE_ROOT
            / "resources/runtime/providers/bazi.json"
        ).read_text(encoding="utf-8")
    )
    runtime = provider["runtime_capability"]
    bindings = {
        item["name"]: tuple(item["json_pointers"])
        for item in runtime["output_bindings"]
    }
    assert bindings["san_yuan"] == ("/facts/chart_facts/output/san_yuan",)
    assert "san_yuan" in runtime["outputs"]


def test_v53_liuren_declares_runtime_core_facts_extension_binding() -> None:
    provider = json.loads(
        (
            MINGLI_CORE_ROOT
            / "resources/runtime/providers/liuren.json"
        ).read_text(encoding="utf-8")
    )
    runtime = provider["runtime_capability"]
    extension_bindings = {
        item["name"]: tuple(item["json_pointers"])
        for item in runtime["extension_output_bindings"]
    }
    assert extension_bindings["runtime_core_facts"] == (
        "/fact_extension/facts/runtime_core_facts",
    )
    assert "runtime_core_facts" in runtime["extension_outputs"]


@pytest.mark.parametrize("provider_id", ["bazi", "fengshui", "liuyao", "meihua"])
def test_v53_source_conditioned_patterns_are_manifest_bound(provider_id: str) -> None:
    """Every V53 source-conditioned core output must survive the public contract."""

    provider = json.loads(
        (
            MINGLI_CORE_ROOT
            / "resources/runtime/providers"
            / f"{provider_id}.json"
        ).read_text(encoding="utf-8")
    )
    runtime = provider["runtime_capability"]
    bindings = {
        item["name"]: tuple(item["json_pointers"])
        for item in runtime["output_bindings"]
    }

    assert bindings["source_conditioned_patterns"] == (
        "/facts/chart_facts/output/source_conditioned_patterns",
    )
    assert "source_conditioned_patterns" in runtime["outputs"]


def test_v53_bazi_san_yuan_matches_recovered_chart_engine_formula() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(MINGLI_CORE_SCRIPTS)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPYCACHEPREFIX"] = "/dev/null"
    completed = subprocess.run(
        [
            sys.executable,
            str(MINGLI_CORE_SCRIPTS / "bazi_fact_adapter.py"),
            "pillars",
            "--pillars",
            "甲戌",
            "戊辰",
            "丙戌",
            "辛卯",
            "--gender",
            "male",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    payload = json.loads(completed.stdout)
    assert payload["output"]["san_yuan"] == {
        "tai_yuan": "己未",
        "ming_gong": "甲戌",
        "shen_gong": "庚午",
        "source": "lunar-typescript-auxiliary",
        "source_dependency_id": "bazi.chart.san-yuan-lunar-typescript-v1",
        "boundary": "胎元、命宫、身宫位置事实；不能单独推出格局、旺衰、吉凶或事件结论",
    }


def test_v53_provider_inventory_has_a_typed_view_contract_for_each_chart_provider() -> None:
    """A Runtime Provider must not stop at Accepted with no public view contract."""

    catalog = json.loads(
        (
            MINGLI_CORE_ROOT
            / "resources/runtime/catalog-v1.json"
        ).read_text(encoding="utf-8")
    )
    provider_ids = {
        json.loads(
            (
                MINGLI_CORE_ROOT
                / "resources/runtime"
                / entry
            ).read_text(encoding="utf-8")
        )["id"]
        for entry in catalog["providers"]
    }

    from app.charts.contracts import VIEW_MODEL_TYPES
    from app.charts.projectors import RUNTIME_PROVIDER_VIEW_MODEL_SCHEMAS
    from app.readings.capability_policy import V53_TIME_CHECK_RELEASE_CAPABILITY_IDS

    assert provider_ids == set(V53_TIME_CHECK_RELEASE_CAPABILITY_IDS)
    assert set(RUNTIME_PROVIDER_VIEW_MODEL_SCHEMAS) == provider_ids
    assert set(RUNTIME_PROVIDER_VIEW_MODEL_SCHEMAS.values()) <= set(VIEW_MODEL_TYPES)
    assert RUNTIME_PROVIDER_VIEW_MODEL_SCHEMAS["fortune"] == "fortune-facts-view/v1"


def test_fortune_solar_term_table_matches_runtime_producer() -> None:
    scripts = str(MINGLI_CORE_SCRIPTS)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from app.charts.contracts import (
        FORTUNE_JIEQI_NAMES,
        FORTUNE_MONTH_BOUNDARY_JIE,
        FORTUNE_SOLAR_TERM_TRIPLES,
    )
    from reading_engine.calendar_core import JIEQI_NAMES, MONTH_BOUNDARY_JIE

    assert FORTUNE_JIEQI_NAMES == JIEQI_NAMES
    assert FORTUNE_MONTH_BOUNDARY_JIE == MONTH_BOUNDARY_JIE
    assert tuple(
        (name, index, index in MONTH_BOUNDARY_JIE)
        for index, name in enumerate(JIEQI_NAMES)
    ) == FORTUNE_SOLAR_TERM_TRIPLES


@pytest.mark.parametrize(
    "payload, expected_type",
    [
        ({"kind": "describe"}, "Describe"),
        (prepare_payload(), "Prepare"),
        (
            {
                "kind": "complete",
                "state_token": "fake-opaque-state",
                "public_copy": "合同测试正文。",
            },
            "Complete",
        ),
    ],
)
def test_command_dtos_validate_and_round_trip_public_json(
    payload: dict[str, Any],
    expected_type: str,
) -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")

    command = contracts.command_from_dict(payload)

    assert type(command).__name__ == expected_type
    assert command.to_dict() == payload


@pytest.mark.parametrize(
    "payload, expected_type",
    [
        (
            {
                "kind": "described",
                "protocol_version": "mingli-portable-interface-v2",
                "manifest_digest": "0" * 64,
                "capabilities": [],
            },
            "Described",
        ),
        (
            {
                "kind": "prepared",
                "state_token": "fake-opaque-state",
                "brief": brief_payload(),
            },
            "Prepared",
        ),
        (
            {
                "kind": "accepted",
                "state_token": "fake-opaque-state",
                "public_copy": "合同测试正文。",
            },
            "Accepted",
        ),
        (
            {
                "kind": "stopped",
                "reason": "error",
                "public_copy": "测试运行时停止。",
                "state_token": None,
                "input_request": None,
            },
            "Stopped",
        ),
    ],
)
def test_result_dtos_validate_and_round_trip_public_json(
    payload: dict[str, Any],
    expected_type: str,
) -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")

    result = contracts.result_from_dict(payload)

    assert type(result).__name__ == expected_type
    assert result.to_dict() == payload


def test_protocol_boundary_rejects_extra_or_legacy_fields() -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")
    malformed = prepare_payload()
    malformed["legacy_system"] = "bazi"

    with pytest.raises(contracts.ContractValidationError):
        contracts.command_from_dict(malformed)


def test_prepared_brief_is_deeply_immutable() -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")
    payload = {
        "kind": "prepared",
        "state_token": "fake-opaque-state",
        "brief": brief_payload(),
    }
    payload["brief"]["facts"] = [
        {
            "ref": "fact:fake",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fixture",
            "value": {"nested": [1, 2]},
            "display_text": "合同测试事实。",
        }
    ]

    prepared = contracts.result_from_dict(payload)
    fact = prepared.brief["facts"][0]

    assert isinstance(prepared.brief, Mapping)
    assert prepared.to_dict() == payload
    with pytest.raises(TypeError):
        fact["value"]["nested"][0] = 9


def test_narrative_request_has_only_the_closed_model_boundary() -> None:
    runtime = importlib.import_module("app.readings.runtime_contracts")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    brief = runtime.ReadingBrief.from_dict(brief_payload())
    output_contract = narrative.OutputContract.from_dict(
        {
            "schema_version": "mingli-output-contract-v1",
            "contract_id": "preview-v1",
            "language": "zh-CN",
            "min_blocks": 1,
            "max_blocks": 4,
            "max_output_chars": 1200,
            "required_dimension_ids": [],
            "required_limit_kind_ids": [],
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

    payload = request.to_dict()

    assert set(payload) == {
        "brief",
        "narrative_policy_version",
        "output_contract",
        "language",
        "max_output_chars",
    }
    serialized = repr(payload).lower()
    for forbidden in ("state_token", "user_id", "order_id", "entitlement"):
        assert forbidden not in serialized
