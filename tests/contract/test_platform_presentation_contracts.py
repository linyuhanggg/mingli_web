import copy
import json
from functools import lru_cache
from pathlib import Path

import pytest
from app.charts.contracts import (
    FORTUNE_JIEQI_NAMES,
    FORTUNE_SOLAR_TERM_TRIPLES,
    VIEW_MODEL_TYPES,
    FortuneFactsViewV1,
    FortuneSolarTerm,
    parse_view_model,
)
from app.charts.projectors import project_view_model
from app.readings.presentation import (
    PresentationContract,
    PresentationSection,
    ReadingDocumentV1,
    build_reading_document,
)
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "contracts" / "schemas"

VIEW_SCHEMAS = (
    "bazi-chart-v1.schema.json",
    "fortune-facts-view-v1.schema.json",
    "ziwei-chart-v1.schema.json",
    "qizheng-chart-v1.schema.json",
    "liuyao-chart-v1.schema.json",
    "meihua-chart-v1.schema.json",
    "luming-nayin-chart-v1.schema.json",
    "rhythm-facts-view-v1.schema.json",
    "taiyi-chart-v1.schema.json",
    "selection-chart-v1.schema.json",
    "fengshui-view-v1.schema.json",
    "qimen-chart-v1.schema.json",
    "daliuren-chart-v1.schema.json",
    "physiognomy-view-v1.schema.json",
    "bazi-relationship-v1.schema.json",
    "ziwei-relationship-v1.schema.json",
    "qizheng-relationship-v1.schema.json",
    "hecan-view-v1.schema.json",
    "wenshi-view-v1.schema.json",
    "canwen-view-v1.schema.json",
)


@lru_cache(maxsize=1)
def _schema_registry() -> Registry:
    resources: list[tuple[str, Resource[object]]] = []
    for path in SCHEMA_ROOT.rglob("*.json"):
        with path.open(encoding="utf-8") as stream:
            contents = json.load(stream)
        schema_id = contents.get("$id")
        if isinstance(schema_id, str) and schema_id:
            resources.append((schema_id, Resource.from_contents(contents)))
    return Registry().with_resources(resources)


def _schema(path: Path) -> dict[str, object]:
    assert path.is_file(), f"missing frozen contract: {path}"
    with path.open(encoding="utf-8") as stream:
        schema = json.load(stream)
    Draft202012Validator.check_schema(schema)
    return schema


def _draft_validator(schema: dict[str, object]) -> Draft202012Validator:
    return Draft202012Validator(schema, registry=_schema_registry())


def _bazi_payload() -> dict[str, object]:
    return {
        "schema_version": "bazi-chart/v1",
        "subject_ref": "profile-version:alice-v1",
        "pillars": [
            {"position": "year", "stem": "甲", "branch": "子"},
            {"position": "month", "stem": "乙", "branch": "丑"},
            {"position": "day", "stem": "丙", "branch": "寅"},
            {"position": "hour", "stem": "丁", "branch": "卯"},
        ],
        "element_balance": [
            {"element": "wood", "value": 2, "display_text": "木二"}
        ],
        "time_layers": [
            {
                "layer_id": "life",
                "label": "本命",
                "available": True,
                "unavailable_reason": None,
            }
        ],
    }


def _bazi_calendar_normalization_payload() -> dict[str, object]:
    return {
        "status": "calculated",
        "algorithm_version": "calendar-v53",
        "time_basis": {
            "policy": "local_apparent_solar-v1",
            "standard_meridian_degrees": None,
            "longitude_correction_seconds": None,
            "equation_of_time_seconds": None,
            "total_correction_seconds": None,
            "algorithm": {
                "id": None,
                "version": None,
                "source": None,
                "uncertainty_seconds": None,
            },
            "boundary": {
                "distance_seconds": None,
                "correction_changes_hour_branch": None,
                "within_uncertainty": None,
            },
        },
        "true_solar_time": {
            "status": "apparent_solar_applied",
            "policy": None,
            "longitude_correction_seconds": None,
            "equation_of_time_seconds": None,
            "total_correction_seconds": None,
        },
        "calendar_convention": {
            "id": None,
            "version": None,
            "year_boundary": None,
            "month_boundary": None,
            "day_rollover": None,
            "hour_basis": None,
            "zi_hour_policy": None,
        },
        "effective_datetime": "1985-03-01T23:33:00+08:00",
        "day_boundary": {
            "correction_crossed_date": True,
            "zi_policy_advanced_day_pillar": False,
        },
        "changed_pillars": ["day", "hour"],
        "solar_terms": {
            "previous": {
                "name": "雨水",
                "index": 2,
                "is_month_boundary_jie": False,
                "datetime": "1985-02-19T06:00:00+08:00",
                "instant_utc": "1985-02-18T22:00:00Z",
            },
            "next": {
                "name": "惊蛰",
                "index": 3,
                "is_month_boundary_jie": True,
                "datetime": "1985-03-05T17:00:00+08:00",
                "instant_utc": "1985-03-05T09:00:00Z",
            },
            "month_switch_policy": "exact_jie_instant",
        },
    }


def _fortune_calendar_normalization_payload() -> dict[str, object]:
    payload = copy.deepcopy(_bazi_calendar_normalization_payload())
    solar_terms = payload["solar_terms"]
    assert isinstance(solar_terms, dict)
    previous = solar_terms["previous"]
    nxt = solar_terms["next"]
    assert isinstance(previous, dict)
    assert isinstance(nxt, dict)
    previous["index"] = 4
    previous["is_month_boundary_jie"] = False
    nxt["index"] = 5
    nxt["is_month_boundary_jie"] = True
    return payload


def _fortune_payload() -> dict[str, object]:
    return {
        "schema_version": "fortune-facts-view/v1",
        "subject_ref": "profile-version:alice-v1",
        "natal_pillars": {
            "year": "甲戌",
            "month": "戊辰",
            "day": "丙戌",
            "hour": "辛卯",
        },
        "day_master": {"stem": "丙", "element": "fire", "polarity": "阳"},
        "month_command": {
            "branch": "辰",
            "label": "辰月",
            "main_qi": "戊",
            "main_qi_element": "earth",
        },
        "active_luck_cycle": "乙丑",
        "target_day": "2026-08-14",
        "target_period": {
            "kind": "day",
            "start": "2026-08-14",
            "end": "2026-08-14",
        },
        "available_periods": ["2026-08-14"],
        "period_markers": [
            {
                "date": "2026-08-14",
                "day_pillar": "甲子",
                "day_role": "日运",
                "active_luck_cycle": "乙丑",
                "primary_mechanism_ids": ["fortune.day_pillar"],
                "decisive_mechanism_ids": [],
                "relations": [],
                "specific_event_policy": "事实标记，不推出具体事件",
                "unresolved_boundaries": [],
            }
        ],
        "calendar_normalization": _fortune_calendar_normalization_payload(),
    }


def _rhythm_payload() -> dict[str, object]:
    return {
        "schema_version": "rhythm-facts-view/v1",
        "subject_ref": "profile-version:alice-v1",
        "pillars": [
            {"position": "year", "stem": "甲", "branch": "戌", "nayin": "山头火"},
            {"position": "month", "stem": "戊", "branch": "辰", "nayin": "大林木"},
            {"position": "day", "stem": "丙", "branch": "戌", "nayin": "屋上土"},
            {"position": "hour", "stem": "辛", "branch": "卯", "nayin": "松柏木"},
        ],
        "independent_lineage": "early-luming-nayin",
        "fact_scope": "early_luming_natal_facts",
        "interpretation_status": "facts_only",
        "source_boundary": "只展示 Runtime 四柱纳音事实。",
    }


def _reading_document_payload() -> dict[str, object]:
    return {
        "schema_version": "reading-document/v1",
        "document_id": "reading-version:1",
        "reading_version_id": "reading-version:1",
        "accepted_copy_ref": "accepted-copy:1",
        "product_version": "bazi-deep/v1",
        "presentation_contract_version": "bazi-deep-presentation/v1",
        "view_model": _bazi_payload(),
        "answer_summary": "先稳住长期积累。",
        "subject_summaries": [
            {"subject_ref": "profile-version:alice-v1", "label": "本人"}
        ],
        "themes": [{"theme_id": "career", "label": "事业"}],
        "claims": [
            {
                "claim_id": "claim:1",
                "section_id": "overview",
                "text": "先稳住长期积累。",
                "subject_ref": "profile-version:alice-v1",
                "dimension_id": "career",
                "claim_kind_id": "kind.tendency",
                "certainty_id": "certainty.tendency",
                "fact_refs": ["fact:1"],
                "finding_refs": ["finding:1"],
                "evidence_refs": ["evidence:1"],
                "limit_refs": ["limit:1"],
                "verification": {"enabled": True},
            }
        ],
        "evidence": [
            {
                "evidence_ref": "evidence:1",
                "title": "依据",
                "supports_fact_refs": ["fact:1"],
            }
        ],
        "boundaries": [{"limit_ref": "limit:1", "text": "仅供个人参考。"}],
        "actions": {
            "correction": {"enabled": True},
            "follow_up": {"enabled": True},
            "export": {"enabled": False},
            "share": {"enabled": False},
        },
        "versions": {
            "runtime_release": "runtime:v1",
            "view_model_schema": "bazi-chart/v1",
            "reading_document_schema": "reading-document/v1",
        },
    }


def _qizheng_reading_document_payload() -> dict[str, object]:
    payload = _reading_document_payload()
    payload["product_version"] = "qizheng-reading/v1"
    payload["presentation_contract_version"] = "qizheng-reading-presentation/v1"
    payload["view_model"] = {
        "schema_version": "qizheng-chart/v1",
        "subject_ref": "profile-version:alice-v1",
        "planets": [
            {
                "planet_id": "Sun",
                "sign_id": "白羊",
                "house_id": "1",
                "longitude": 12.5,
            }
        ],
        "houses": [
            {"house_id": "1", "sign_id": "白羊", "cusp_longitude": 0.0}
        ],
        "aspects": [],
        "time_layers": [
            {
                "layer_id": "natal",
                "label": "本命",
                "available": True,
                "unavailable_reason": None,
            }
        ],
        "core_facts": {
            "ephemeris": {
                "schema_version": "mingli-ephemeris-v1",
                "engine": {
                    "name": "astronomy-engine",
                    "version": "2.1.19",
                    "license": "MIT",
                },
                "coordinate_convention": {
                    "frame": "geocentric_true_ecliptic_of_date",
                    "zodiac": "tropical",
                    "aberration": True,
                    "precession": "equinox_of_date_by_astronomy_engine",
                },
            },
            "conventions": {},
            "classical_bodies": [
                {
                    "body_id": "Sun",
                    "classical_name": "太阳",
                    "longitude": 12.5,
                    "latitude_degrees": 0.1,
                    "degree_in_zodiac_sign": 12.5,
                    "house_id": "1",
                    "house_degree": 12.5,
                    "motion_state": "direct",
                    "fact_status": "calculated_not_interpreted",
                    "point_kind": "observed_ephemeris_body",
                    "observed_body": True,
                    "source_dependency_id": "xingming.ephemeris.seven-luminaries",
                    "trace": {"engine": "astronomy-engine"},
                }
            ],
            "ming_shen": None,
            "major_limits": None,
            "transformations": None,
            "source_conditioned_patterns": [
                {
                    "rule_id": "QX-P01",
                    "local_rule_id": "QX-P01",
                    "title": "合成来源谓词",
                    "source_pack": "xingming-fixture",
                    "source_anchor": "fixture#P01",
                    "status": "predicate_matched_not_verdict",
                    "fact_paths": ["/classical_bodies/0/longitude"],
                    "predicate_audit": ["longitude_present"],
                }
            ],
            "annual_transformations": None,
            "requested_limit_layers": None,
        },
    }
    payload["versions"] = {
        **payload["versions"],
        "view_model_schema": "qizheng-chart/v1",
    }
    return payload


def _interpretive_candidates_payload() -> dict[str, object]:
    return {
        "strength": {
            "status": "evidence_only",
            "hard_verdict": None,
            "day_element": "fire",
            "month_command_element": "earth",
            "seasonal_state": "休",
            "seasonal_state_source_rule_id": "bazi/sanming-tonghui#R-02-04",
            "same_element_occurrences": 2,
            "resource_element": "wood",
            "resource_occurrences": 1,
            "all_element_occurrences": [
                {"element": "fire", "value": 2},
                {"element": "wood", "value": 1},
            ],
            "month_order_adjudication": {
                "status": "adjudicated_month_order_state",
                "decision_scope": "bazi_month_order_seasonal_state",
                "day_master_element": "fire",
                "month_command_element": "earth",
                "seasonal_state": "休",
                "whole_chart_strength_verdict": None,
                "useful_god_verdict": None,
                "source_ref": {
                    "pack": "bazi/sanming-tonghui",
                    "rule_id": "R-02-04",
                    "source_anchor": (
                        "references/books/bazi/sanming-tonghui/"
                        "rules.md#R-02-04"
                    ),
                    "verification_status": "verified",
                    "binding_digest": (
                        "77b387e17e65b50c7cbcdba3cc8ef5b170499c6d5c07461856b710d5aa50759e"
                    ),
                },
                "unresolved_checks": ["全局根气、生扶、克泄与合化"],
            },
            "boundary": "机械证据，不作强弱裁定。",
        },
        "structure": {
            "status": "candidate_only",
            "hard_verdict": None,
            "month_main_qi": "己",
            "month_main_qi_ten_god": "伤官",
            "main_qi_visible": False,
            "visible_positions": [],
            "boundary": "仅为候选，不作格局裁定。",
        },
        "following_and_transformation": {
            "status": "requires_classical_adjudication",
            "hard_verdict": None,
            "stem_combination_candidates": [],
            "branch_formation_candidates": [],
            "boundary": "需按古法进一步裁定。",
        },
        "salience_signals": [],
    }


def _reading_document_with_candidates(view_kind: str) -> dict[str, object]:
    payload = _reading_document_payload()
    candidates = _interpretive_candidates_payload()
    if view_kind == "bazi":
        payload["view_model"]["core_facts"] = {
            "interpretive_candidates": candidates,
        }
        return payload

    payload["view_model"] = {
        "schema_version": "five-elements-facts-view/v1",
        "subject_ref": "profile-version:alice-v1",
        "day_master": None,
        "month_command": None,
        "seasonal_profile": None,
        "tiaohou_markers": None,
        "element_inventory": None,
        "interpretive_candidates": candidates,
        "source_identity": None,
        "active_source_rule_ids": [],
        "source_dependency_ids": [],
        "source_status": "unavailable",
        "source_gaps": [],
        "limitations": [],
    }
    payload["versions"]["view_model_schema"] = "five-elements-facts-view/v1"
    return payload


@pytest.mark.parametrize("schema_name", VIEW_SCHEMAS)
def test_p5_publishes_each_versioned_view_schema(schema_name: str) -> None:
    schema = _schema(SCHEMA_ROOT / "views" / schema_name)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"].endswith("/v1")


def test_chart_contract_rejects_unknown_fields_and_unknown_versions() -> None:
    payload = _bazi_payload()
    parsed = parse_view_model(payload)
    assert parsed.schema_version == "bazi-chart/v1"
    assert "bazi-chart/v1" in VIEW_MODEL_TYPES

    with pytest.raises(ValidationError):
        parse_view_model({**payload, "raw": {"day_master": "丙"}})
    with pytest.raises(ValueError, match="unsupported view model schema_version"):
        parse_view_model({**payload, "schema_version": "bazi-chart/v999"})


def test_rhythm_facts_view_model_is_strict_and_parseable() -> None:
    payload = _rhythm_payload()
    parsed = parse_view_model(payload)

    assert parsed.schema_version == "rhythm-facts-view/v1"
    assert parsed.independent_lineage == "early-luming-nayin"
    assert len(parsed.pillars) == 4

    with pytest.raises(ValidationError):
        parse_view_model({**payload, "sound_score": 1})


def test_projector_requires_a_typed_supported_view_model() -> None:
    projected = project_view_model(parse_view_model(_bazi_payload()))
    assert projected["schema_version"] == "bazi-chart/v1"

    with pytest.raises(TypeError, match="typed view model"):
        project_view_model(_bazi_payload())


def test_view_models_reject_missing_layer_reasons_duplicate_subjects_and_arts() -> None:
    unavailable = _bazi_payload()
    unavailable["time_layers"][0] = {
        "layer_id": "year",
        "label": "流年",
        "available": False,
        "unavailable_reason": None,
    }
    with pytest.raises(ValidationError):
        parse_view_model(unavailable)

    subject = {
        "subject_ref": "profile-version:alice-v1",
        "profile_version_id": "alice-v1",
        "label": "甲方",
    }
    with pytest.raises(ValidationError):
        parse_view_model(
            {
                "schema_version": "bazi-relationship/v1",
                "subjects": [subject, {**subject, "label": "乙方"}],
                "relationship_type": "friend",
                "signals": [],
            }
        )

    with pytest.raises(ValidationError):
        parse_view_model(
            {
                "schema_version": "hecan-view/v1",
                "subject_ref": "profile-version:alice-v1",
                "selected_art_ids": ["bazi", "bazi"],
                "dimensions": [
                    {
                        "dimension_id": "career",
                        "signals": [],
                        "convergence": [],
                        "disagreements": [],
                        "missing_art_ids": ["ziwei", "qizheng"],
                    }
                ],
            }
        )


def test_reading_document_schema_validates_standalone_without_registry() -> None:
    schema = _schema(SCHEMA_ROOT / "reading-document-v1.schema.json")
    Draft202012Validator(schema).validate(_reading_document_payload())


def test_reading_document_is_closed_and_embeds_only_known_view_models() -> None:
    schema = _schema(SCHEMA_ROOT / "reading-document-v1.schema.json")
    payload = _reading_document_payload()
    _draft_validator(schema).validate(payload)

    unknown = copy.deepcopy(payload)
    unknown["raw"] = {"provider_payload": True}
    assert tuple(_draft_validator(schema).iter_errors(unknown))

    unknown_view = copy.deepcopy(payload)
    unknown_view["view_model"]["schema_version"] = "unknown-view/v1"
    with pytest.raises(ValidationError):
        ReadingDocumentV1.model_validate(unknown_view)


def test_bazi_calendar_g3_fields_are_shared_by_view_and_document_schemas() -> None:
    calendar = _bazi_calendar_normalization_payload()
    view_payload = _bazi_payload()
    view_payload["core_facts"] = {"calendar_normalization": calendar}

    view_schema = _schema(SCHEMA_ROOT / "views" / "bazi-chart-v1.schema.json")
    _draft_validator(view_schema).validate(view_payload)

    document_payload = _reading_document_payload()
    document_payload["view_model"] = view_payload
    document_schema = _schema(SCHEMA_ROOT / "reading-document-v1.schema.json")
    _draft_validator(document_schema).validate(document_payload)
    document = ReadingDocumentV1.model_validate(document_payload)
    assert document.view_model.core_facts is not None
    normalized = document.view_model.core_facts.calendar_normalization
    assert normalized is not None
    assert normalized.changed_pillars == ("day", "hour")
    assert normalized.solar_terms is not None
    assert normalized.solar_terms.next is not None
    assert normalized.solar_terms.next.name == "惊蛰"

    invalid = copy.deepcopy(document_payload)
    invalid["view_model"]["core_facts"]["calendar_normalization"][
        "changed_pillars"
    ] = ["day", "week"]
    assert tuple(_draft_validator(document_schema).iter_errors(invalid))


def test_fortune_calendar_additive_fields_are_typed_in_view_and_document() -> None:
    view_payload = _fortune_payload()
    view_schema = _schema(
        SCHEMA_ROOT / "views" / "fortune-facts-view-v1.schema.json"
    )
    _draft_validator(view_schema).validate(view_payload)

    document_payload = _reading_document_payload()
    document_payload["view_model"] = view_payload
    document_payload["versions"]["view_model_schema"] = "fortune-facts-view/v1"
    document_schema = _schema(SCHEMA_ROOT / "reading-document-v1.schema.json")
    _draft_validator(document_schema).validate(document_payload)
    document = ReadingDocumentV1.model_validate(document_payload)
    normalized = document.view_model.calendar_normalization
    assert normalized.effective_datetime == "1985-03-01T23:33:00+08:00"
    assert normalized.changed_pillars == ("day", "hour")
    assert normalized.solar_terms is not None
    assert normalized.solar_terms.next is not None
    assert normalized.solar_terms.next.name == "惊蛰"
    assert normalized.solar_terms.next.index == 5
    assert normalized.solar_terms.next.is_month_boundary_jie is True
    assert normalized.solar_terms.previous is not None
    assert normalized.solar_terms.previous.name == "雨水"
    assert normalized.solar_terms.previous.index == 4
    assert normalized.solar_terms.previous.is_month_boundary_jie is False

    invalid = copy.deepcopy(document_payload)
    invalid["view_model"]["calendar_normalization"]["solar_terms"][
        "raw_runtime_payload"
    ] = {}
    assert tuple(_draft_validator(document_schema).iter_errors(invalid))
    with pytest.raises(ValidationError):
        ReadingDocumentV1.model_validate(invalid)


@pytest.mark.parametrize("index", range(24))
def test_fortune_schema_and_model_accept_every_frozen_solar_term_triple(
    index: int,
) -> None:
    view_schema = _schema(
        SCHEMA_ROOT / "views" / "fortune-facts-view-v1.schema.json"
    )
    validator = _draft_validator(view_schema)
    name, expected_index, is_month_boundary_jie = FORTUNE_SOLAR_TERM_TRIPLES[index]
    term = {
        "name": name,
        "index": expected_index,
        "is_month_boundary_jie": is_month_boundary_jie,
        "datetime": "1985-02-19T06:00:00+08:00",
        "instant_utc": "1985-02-18T22:00:00Z",
    }
    payload = _fortune_payload()
    calendar = payload["calendar_normalization"]
    assert isinstance(calendar, dict)
    solar_terms = calendar["solar_terms"]
    assert isinstance(solar_terms, dict)
    solar_terms["previous"] = term
    validator.validate(payload)
    parsed = parse_view_model(payload)
    assert isinstance(parsed, FortuneFactsViewV1)
    assert parsed.calendar_normalization.solar_terms is not None
    previous = parsed.calendar_normalization.solar_terms.previous
    assert previous is not None
    assert previous.name == name
    assert previous.index == expected_index
    assert previous.is_month_boundary_jie is is_month_boundary_jie
    FortuneSolarTerm.model_validate(term)


def test_fortune_solar_term_schema_matches_frozen_contract_table() -> None:
    schema = _schema(SCHEMA_ROOT / "views" / "fortune-facts-view-v1.schema.json")
    defs = schema["$defs"]
    assert isinstance(defs, dict)
    solar_term = defs["solarTerm"]
    assert isinstance(solar_term, dict)
    properties = solar_term["properties"]
    assert isinstance(properties, dict)
    name_schema = properties["name"]
    index_schema = properties["index"]
    assert isinstance(name_schema, dict)
    assert isinstance(index_schema, dict)
    assert name_schema["enum"] == list(FORTUNE_JIEQI_NAMES)
    assert index_schema == {"type": "integer", "minimum": 0, "maximum": 23}
    one_of = solar_term["oneOf"]
    assert isinstance(one_of, list)
    triples: list[tuple[str, int, bool]] = []
    for branch in one_of:
        assert isinstance(branch, dict)
        branch_properties = branch["properties"]
        assert isinstance(branch_properties, dict)
        name = branch_properties["name"]
        index = branch_properties["index"]
        boundary = branch_properties["is_month_boundary_jie"]
        assert isinstance(name, dict)
        assert isinstance(index, dict)
        assert isinstance(boundary, dict)
        triples.append((name["const"], index["const"], boundary["const"]))
    assert tuple(triples) == FORTUNE_SOLAR_TERM_TRIPLES


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(
            lambda term: {**term, "name": "谷雨", "index": 23, "is_month_boundary_jie": True},
            id="review-mismatch",
        ),
        pytest.param(
            lambda term: {**term, "is_month_boundary_jie": True},
            id="boundary-mismatch",
        ),
        pytest.param(lambda term: {**term, "index": -1}, id="index-underflow"),
        pytest.param(lambda term: {**term, "index": 24}, id="index-overflow"),
        pytest.param(lambda term: {**term, "index": "8"}, id="index-str"),
        pytest.param(lambda term: {**term, "index": True}, id="index-bool"),
        pytest.param(lambda term: {**term, "index": 8.0}, id="index-float"),
        pytest.param(
            lambda term: {k: v for k, v in term.items() if k != "name"},
            id="missing-name",
        ),
        pytest.param(
            lambda term: {k: v for k, v in term.items() if k != "index"},
            id="missing-index",
        ),
        pytest.param(
            lambda term: {k: v for k, v in term.items() if k != "is_month_boundary_jie"},
            id="missing-boundary",
        ),
    ],
)
def test_fortune_solar_term_fail_closed_isomorphic_across_layers(
    mutator: object,
) -> None:
    view_schema = _schema(
        SCHEMA_ROOT / "views" / "fortune-facts-view-v1.schema.json"
    )
    validator = _draft_validator(view_schema)
    payload = _fortune_payload()
    calendar = payload["calendar_normalization"]
    assert isinstance(calendar, dict)
    solar_terms = calendar["solar_terms"]
    assert isinstance(solar_terms, dict)
    original = solar_terms["previous"]
    assert isinstance(original, dict)
    mutated = mutator(original)  # type: ignore[operator]
    solar_terms["previous"] = mutated

    assert tuple(validator.iter_errors(payload))
    with pytest.raises(ValidationError):
        parse_view_model(payload)
    with pytest.raises(ValueError):
        FortuneSolarTerm.model_validate(mutated)


@pytest.mark.parametrize("view_kind", ["bazi", "five_elements"])
def test_reading_document_accepts_strict_interpretive_candidates(
    view_kind: str,
) -> None:
    schema = _schema(SCHEMA_ROOT / "reading-document-v1.schema.json")
    payload = _reading_document_with_candidates(view_kind)

    _draft_validator(schema).validate(payload)


@pytest.mark.parametrize("view_kind", ["bazi", "five_elements"])
@pytest.mark.parametrize("invalid_case", ["missing", "status", "extra"])
def test_reading_document_rejects_invalid_interpretive_candidates(
    view_kind: str,
    invalid_case: str,
) -> None:
    schema = _schema(SCHEMA_ROOT / "reading-document-v1.schema.json")
    payload = _reading_document_with_candidates(view_kind)
    if view_kind == "bazi":
        candidates = payload["view_model"]["core_facts"]["interpretive_candidates"]
    else:
        candidates = payload["view_model"]["interpretive_candidates"]

    if invalid_case == "missing":
        del candidates["structure"]
    elif invalid_case == "status":
        candidates["strength"]["status"] = "adjudicated"
    else:
        candidates["unexpected"] = True

    assert tuple(_draft_validator(schema).iter_errors(payload))


@pytest.mark.parametrize(
    ("schema_version", "view_model"),
    [
        (
            "meihua-chart/v1",
            {
                "schema_version": "meihua-chart/v1",
                "subject_ref": "meihua:fixture",
                "question": "这件事如何推进？",
                "casting_method": "time",
                "primary_hexagram": {
                    "name": "风雷益",
                    "upper_trigram": "巽",
                    "lower_trigram": "震",
                },
                "mutual_hexagram": None,
                "changed_hexagram": None,
                "moving_lines": [2],
                "body_use": {
                    "body": {"position": "upper", "trigram": "巽", "element": "木"},
                    "use": {"position": "lower", "trigram": "震", "element": "木"},
                    "relation": "比和",
                    "status": "calculated_relation_not_verdict",
                },
            },
        ),
        (
            "luming-nayin-chart/v1",
            {
                "schema_version": "luming-nayin-chart/v1",
                "subject_ref": "profile-version:fixture",
                "pillars": [
                    {"position": "year", "stem": "甲", "branch": "子", "nayin": "海中金"},
                    {"position": "month", "stem": "乙", "branch": "丑", "nayin": "海中金"},
                    {"position": "day", "stem": "丙", "branch": "寅", "nayin": "炉中火"},
                    {"position": "hour", "stem": "丁", "branch": "卯", "nayin": "炉中火"},
                ],
                "three_yuan_profiles": {"year": {"name": "上元"}},
                "taiyuan": None,
                "relations": [
                    {
                        "category": "lu",
                        "relation": "干禄",
                        "anchor": "year",
                        "anchor_pillar": "甲子",
                        "status": "calculated_relation_not_verdict",
                        "target_branch": None,
                        "candidates": [],
                        "matched_positions": [],
                        "recension": None,
                    }
                ],
            },
        ),
        (
            "rhythm-facts-view/v1",
            {
                "schema_version": "rhythm-facts-view/v1",
                "subject_ref": "profile-version:fixture",
                "pillars": [
                    {"position": "year", "stem": "甲", "branch": "子", "nayin": "海中金"},
                    {"position": "month", "stem": "乙", "branch": "丑", "nayin": "海中金"},
                    {"position": "day", "stem": "丙", "branch": "寅", "nayin": "炉中火"},
                    {"position": "hour", "stem": "丁", "branch": "卯", "nayin": "炉中火"},
                ],
                "independent_lineage": "early-luming-nayin",
                "fact_scope": "early_luming_natal_facts",
                "interpretation_status": "facts_only",
                "source_boundary": "只展示 Runtime 四柱纳音事实。",
            },
        ),
        (
            "chart-similarity-view/v1",
            {
                "schema_version": "chart-similarity-view/v1",
                "left_subject_ref": "profile-version:left",
                "right_subject_ref": "profile-version:right",
                "basis": "bazi.four_pillars.exact",
                "left_fact_ref": "fact:left/calculated/bazi/four_pillars",
                "right_fact_ref": "fact:right/calculated/bazi/four_pillars",
                "comparisons": [
                    {
                        "position": "year",
                        "left": {"position": "year", "stem": "甲", "branch": "子"},
                        "right": {"position": "year", "stem": "甲", "branch": "子"},
                        "exact_match": True,
                    },
                    {
                        "position": "month",
                        "left": {"position": "month", "stem": "乙", "branch": "丑"},
                        "right": {"position": "month", "stem": "乙", "branch": "丑"},
                        "exact_match": True,
                    },
                    {
                        "position": "day",
                        "left": {"position": "day", "stem": "丙", "branch": "寅"},
                        "right": {"position": "day", "stem": "丙", "branch": "寅"},
                        "exact_match": True,
                    },
                    {
                        "position": "hour",
                        "left": {"position": "hour", "stem": "丁", "branch": "卯"},
                        "right": {"position": "hour", "stem": "戊", "branch": "辰"},
                        "exact_match": False,
                    },
                ],
                "exact_match": False,
                "matched_positions": ["year", "month", "day"],
                "differing_positions": ["hour"],
                "limitations": ["只比较四柱原值，不生成百分比评分。"],
            },
        ),
        (
            "taiyi-chart/v1",
            {
                "schema_version": "taiyi-chart/v1",
                "subject_ref": "taiyi:fixture",
                "calendar": {
                    "annual_boundary": "lunar_new_year",
                    "lunar_year": 2026,
                    "year_ganzhi": "丙午",
                },
                "epoch": {
                    "accumulated_year": 1,
                    "anchor_accumulated_year": 1,
                    "anchor_lunar_year_ce": 1,
                    "derived_ce_offset": 0,
                    "one_based": True,
                    "profile_id": "fixture",
                    "source_anchor": "fixture",
                },
                "cycle": {
                    "bureau": 1,
                    "governance": "理天",
                    "ji": 1,
                    "position_360": 1,
                    "year_in_ji": 1,
                    "year_in_zi_yuan": 1,
                    "zi_yuan": 1,
                    "zi_yuan_head": "甲子",
                },
                "board": {
                    "heshen": "子",
                    "jishen": "丑",
                    "shiji": "寅",
                    "taisui": "卯",
                    "taiyi_position": "辰",
                    "tianmu_wenchang": {"name": "文昌", "position": "巳"},
                },
                "host_guest": {},
                "four_generals": {
                    "guest_assistant": 1,
                    "guest_major": 2,
                    "host_assistant": 3,
                    "host_major": 4,
                },
                "long_cycle_deities": [],
                "board_predicates": [],
                "scope_contract": {
                    "declared_scope": "annual",
                    "interpretation_policy": "facts_only",
                    "supported_horizons": ["year"],
                    "supported_objects": ["macro_historical"],
                    "unsupported_scopes": ["personal_event"],
                },
            },
        ),
        (
            "selection-chart/v1",
            {
                "schema_version": "selection-chart/v1",
                "subject_ref": "selection:fixture",
                "event_profile": "business_opening_transaction",
                "eligible_candidates": [],
                "eligible_date_time_candidates": [],
                "eliminations": [],
                "ranking": {
                    "component_order": [],
                    "eligible_candidate_ids": [],
                    "eligible_date_time_candidate_ids": [],
                    "folk_affects_rank": False,
                    "method": "explainable_lexicographic_v1",
                    "opaque_numeric_score": False,
                    "ordered_candidate_ids": [],
                    "ordered_date_time_candidate_ids": [],
                },
                "lineage_policy": {
                    "folk": "folk",
                    "folk_priority": "comparison_only",
                    "merge_verdicts": False,
                    "official": "official",
                    "official_priority": "primary",
                    "preserve_disagreement": True,
                },
                "no_valid_candidate": True,
                "basis_projection": {},
            },
        ),
        (
            "fengshui-view/v1",
            {
                "schema_version": "fengshui-view/v1",
                "subject_ref": "fengshui:fixture",
                "active_subprofiles": ["liqi"],
                "observation_provenance": {},
                "compass": {},
                "building_chronology": {},
                "layout_graph": {},
                "form": {},
                "liqi": {},
                "active_source_rule_ids": [],
                "conflicts": [],
                "uncertainties": [],
                "critical_missing": [],
            },
        ),
    ],
)
def test_reading_document_accepts_the_recent_art_view_models(
    schema_version: str,
    view_model: dict[str, object],
) -> None:
    schema = _schema(SCHEMA_ROOT / "reading-document-v1.schema.json")
    payload = _reading_document_payload()
    payload["view_model"] = view_model
    payload["versions"] = {
        **payload["versions"],
        "view_model_schema": schema_version,
    }
    _draft_validator(schema).validate(payload)
    document = ReadingDocumentV1.model_validate(payload)
    assert document.view_model.schema_version == schema_version


def test_reading_document_accepts_qizheng_provenance_fields() -> None:
    payload = _qizheng_reading_document_payload()
    schema = _schema(SCHEMA_ROOT / "reading-document-v1.schema.json")
    _draft_validator(schema).validate(payload)
    document = ReadingDocumentV1.model_validate(payload)
    assert document.view_model.schema_version == "qizheng-chart/v1"
    assert document.view_model.core_facts is not None
    assert document.view_model.core_facts.classical_bodies is not None
    body = document.view_model.core_facts.classical_bodies[0]
    assert body.point_kind == "observed_ephemeris_body"
    assert body.source_dependency_id == "xingming.ephemeris.seven-luminaries"


def test_presentation_contract_controls_order_slots_disclosures_and_renderer() -> None:
    contract = PresentationContract(
        contract_version="bazi-deep-presentation/v1",
        product_version="bazi-deep/v1",
        renderer="bazi-reading/v1",
        sections=(
            PresentationSection(
                section_id="overview",
                title="总览",
                min_claims=1,
                max_claims=1,
                max_chars_per_claim=40,
                allowed_claim_kind_ids=("kind.tendency",),
            ),
        ),
        fixed_disclosures=("仅供个人参考。",),
    )
    document = build_reading_document(contract, _reading_document_payload())
    assert document.presentation_contract_version == contract.contract_version

    too_many = copy.deepcopy(_reading_document_payload())
    too_many["claims"].append(copy.deepcopy(too_many["claims"][0]))
    too_many["claims"][1]["claim_id"] = "claim:2"
    with pytest.raises(ValueError, match="claim slots"):
        build_reading_document(contract, too_many)

    disallowed = copy.deepcopy(_reading_document_payload())
    disallowed["claims"][0]["claim_kind_id"] = "kind.guarantee"
    with pytest.raises(ValueError, match="claim kind"):
        build_reading_document(contract, disallowed)


def test_models_do_not_offer_raw_or_unknown_fallback_fields() -> None:
    forbidden = {"raw", "payload", "unknown", "fallback"}
    for model in (*VIEW_MODEL_TYPES.values(), ReadingDocumentV1, PresentationContract):
        assert forbidden.isdisjoint(model.model_fields)
        assert model.model_config.get("extra") == "forbid"
