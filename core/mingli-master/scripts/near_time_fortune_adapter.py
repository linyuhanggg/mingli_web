#!/usr/bin/env python3
"""Build a source-family-aware near-time Bazi fact contract.

The adapter deliberately stops before concrete event prediction. It validates a
complete natal chart, finds the active major-luck cycle, calculates target
calendar facts, and groups dependent transit signals so repeated probes cannot
masquerade as independent evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import bazi_fact_adapter as bazi
from bazi_reasoning_tools import compile_bazi_reasoning_tools
from reading_engine import calendar_core


CONTRACT_VERSION = "fortune-public-v6-mechanism-stack"
FACT_STATUS = "near_time_bazi_transit_facts"
ADAPTER_NAME = "mingli-master.near_time_fortune_adapter"
ADAPTER_VERSION = "2.2.1"
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
POSITIONS = ("year", "month", "day", "hour")
POSITION_LABELS = {"year": "年支", "month": "月支", "day": "日支", "hour": "时支"}

LIUHE = {
    frozenset(pair) for pair in ("子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未")
}
CHONG = {
    frozenset(pair) for pair in ("子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥")
}
HAI = {
    frozenset(pair) for pair in ("子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌")
}
PO = {
    frozenset(pair) for pair in ("子酉", "卯午", "辰丑", "戌未", "寅亥", "巳申")
}
SELF_XING = set("辰午酉亥")
TRIPLE_FORMATIONS = {
    "三合": {
        "申子辰": "水",
        "亥卯未": "木",
        "寅午戌": "火",
        "巳酉丑": "金",
    },
    "三会": {
        "寅卯辰": "木",
        "巳午未": "火",
        "申酉戌": "金",
        "亥子丑": "水",
    },
    "三刑": {
        "寅巳申": None,
        "丑戌未": None,
    },
}


def _ensure_sxtwl() -> Any:
    return calendar_core.load_sxtwl()


def _parse_datetime(value: str, timezone: ZoneInfo) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def _parse_window(value: str, timezone: ZoneInfo) -> list[datetime]:
    match = re.fullmatch(
        r"\s*(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})\s*[-–—到至]\s*"
        r"(?:(\d{4}-\d{2}-\d{2})\s+)?(\d{1,2}):(\d{2})\s*",
        value,
    )
    if not match:
        raise ValueError("invalid window: expected 'YYYY-MM-DD HH:MM-YYYY-MM-DD HH:MM'")
    start = datetime.combine(
        date.fromisoformat(match.group(1)),
        datetime.min.time().replace(hour=int(match.group(2)), minute=int(match.group(3))),
        tzinfo=timezone,
    )
    end = datetime.combine(
        date.fromisoformat(match.group(4) or match.group(1)),
        datetime.min.time().replace(hour=int(match.group(5)), minute=int(match.group(6))),
        tzinfo=timezone,
    )
    if end <= start:
        raise ValueError("invalid window: end must be after start")
    midpoint = start + (end - start) / 2
    probes = []
    for item in (start, midpoint, end):
        normalized = item.replace(second=0, microsecond=0)
        if normalized not in probes:
            probes.append(normalized)
    if len(probes) < 2:
        raise ValueError("invalid window: at least two distinct probes are required")
    return probes


def _phase_name(value: datetime) -> str:
    if value.hour < 12:
        return "morning"
    if value.hour < 18:
        return "afternoon"
    return "evening"


def _ganzhi(value: Any) -> str:
    return STEMS[value.tg] + BRANCHES[value.dz]


def _branch_relation_types(transit: str, natal: str) -> list[str]:
    pair = frozenset((transit, natal))
    relations = []
    if transit == natal:
        relations.append("同支")
        if transit in SELF_XING:
            relations.append("自刑")
    if pair in LIUHE:
        relations.append("六合")
    if pair in CHONG:
        relations.append("六冲")
    if pair in HAI:
        relations.append("六害")
    if pair in PO:
        relations.append("六破")
    return relations


def _relations_to_natal(branch: str, natal_pillars: dict[str, str]) -> list[dict[str, str]]:
    relations = []
    for position in POSITIONS:
        natal_branch = natal_pillars[position][1]
        for relation in _branch_relation_types(branch, natal_branch):
            relations.append({
                "transit_branch": branch,
                "natal_position": position,
                "natal_position_label": POSITION_LABELS[position],
                "natal_branch": natal_branch,
                "relation": relation,
            })
    return relations


def _snapshot(
    value: datetime,
    *,
    day_master: str,
    natal_pillars: dict[str, str],
    location: str = "unspecified",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
    zi_hour_policy: str = "midnight",
) -> dict[str, Any]:
    calendar = calendar_core.normalize_calendar(
        value.isoformat(),
        timezone_name=str(getattr(value.tzinfo, "key", None) or value.tzname() or "UTC"),
        location=location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
        zi_hour_policy=zi_hour_policy,
    )
    ganzhi = dict(calendar["ganzhi"])
    ten_gods = {
        layer: bazi._ten_god(day_master, pillar[0])
        for layer, pillar in ganzhi.items()
    }
    day_relations = _relations_to_natal(ganzhi["day"][1], natal_pillars)
    hour_relations = _relations_to_natal(ganzhi["hour"][1], natal_pillars)
    return {
        "at": value.isoformat(),
        "solar_date": value.date().isoformat(),
        "lunar_date": dict(calendar["lunar_date"]),
        "ganzhi": ganzhi,
        "calendar_normalization": calendar,
        "ten_gods": ten_gods,
        "day_branch_relations": day_relations,
        "hour_branch_relations": hour_relations,
    }


def _age_years(birth: datetime, target: datetime) -> float:
    return (target - birth).total_seconds() / (365.2425 * 24 * 60 * 60)


def _active_luck_cycle(natal: dict[str, Any], birth: datetime, target: datetime) -> dict[str, Any]:
    age = _age_years(birth, target)
    cycles = natal["output"]["luck_cycles"]["cycles"]
    for cycle in cycles:
        if cycle["start_age_years"] <= age < cycle["end_age_years"]:
            return {**cycle, "age_at_target": round(age, 6)}
    raise ValueError("target date falls outside calculated major-luck cycles")


def _transit_layer(
    name: str,
    pillar: str,
    *,
    day_master: str,
    natal_pillars: dict[str, str],
) -> dict[str, Any]:
    return {
        "layer": name,
        "pillar": pillar,
        "stem": pillar[0],
        "branch": pillar[1],
        "stem_ten_god": bazi._ten_god(day_master, pillar[0]),
        "branch_hidden_ten_gods": [
            {
                "stem": stem,
                "ten_god": bazi._ten_god(day_master, stem),
            }
            for stem in bazi.HIDDEN_STEMS[pillar[1]]
        ],
        "branch_relations_to_natal": _relations_to_natal(pillar[1], natal_pillars),
    }


def _element_role_family(day_master: str, target_element: str | None) -> str | None:
    if not target_element:
        return None
    day_element = bazi.STEM_ELEMENT[day_master]
    day_index = bazi.ELEMENTS.index(day_element)
    target_index = bazi.ELEMENTS.index(target_element)
    if day_index == target_index:
        return "比劫"
    if target_index == (day_index + 1) % 5:
        return "食伤"
    if target_index == (day_index + 2) % 5:
        return "财"
    if day_index == (target_index + 1) % 5:
        return "印"
    return "官杀"


def _target_day_multi_branch_formations(
    natal_pillars: dict[str, str],
    transit_layers: dict[str, dict[str, Any]],
    *,
    day_master: str,
) -> list[dict[str, Any]]:
    target_branch = transit_layers["day"]["branch"]
    occurrences: dict[str, list[dict[str, str]]] = {branch: [] for branch in BRANCHES}
    for layer in ("day", "month", "year", "major_luck"):
        branch = transit_layers[layer]["branch"]
        occurrences[branch].append({
            "scope": "transit",
            "layer": layer,
            "branch": branch,
        })
    for position in POSITIONS:
        branch = natal_pillars[position][1]
        occurrences[branch].append({
            "scope": "natal",
            "position": position,
            "position_label": POSITION_LABELS[position],
            "branch": branch,
        })

    formations: list[dict[str, Any]] = []
    for relation, patterns in TRIPLE_FORMATIONS.items():
        for pattern, nominal_element in patterns.items():
            branches = list(pattern)
            if target_branch not in branches or any(not occurrences[branch] for branch in branches):
                continue
            members = []
            for branch in branches:
                if branch == target_branch:
                    day_member = next(
                        (
                            item
                            for item in occurrences[branch]
                            if item.get("scope") == "transit" and item.get("layer") == "day"
                        ),
                        None,
                    )
                    members.append(day_member or occurrences[branch][0])
                else:
                    members.append(occurrences[branch][0])
            formations.append({
                "id": f"day-multi-formation-{len(formations) + 1:02d}",
                "relation": relation,
                "branches": branches,
                "nominal_element": nominal_element,
                "nominal_element_role_family": _element_role_family(
                    day_master,
                    nominal_element,
                ),
                "branch_set_status": (
                    "complete_branch_set_present_across_natal_and_timing_layers"
                ),
                "transformation_status": (
                    "unadjudicated_requires_classical_conditions"
                    if nominal_element else "not_applicable"
                ),
                "members": members,
                "target_day_involved": True,
                "scope": "cross_natal_and_active_timing_layers_not_specific_event",
            })
    return formations


def _assert_mechanism_scopes_are_symbolic(
    decisive: list[dict[str, Any]],
    formations: list[dict[str, Any]],
) -> None:
    """Fail-fast guard: every emitted mechanism must be scoped as symbolic, not event-specific.

    Section 2 of the accuracy-first refactor: prevents future adapter changes
    from silently promoting a mechanism into a life-scene claim. Any scope that
    does not end in `_not_specific_event` is treated as a bug and rejected.
    """
    permitted_suffix = "_not_specific_event"
    for item in decisive:
        scope = item.get("scope")
        if not isinstance(scope, str) or not scope.endswith(permitted_suffix):
            raise ValueError(
                f"decisive mechanism {item.get('id')!r} has non-symbolic scope {scope!r};"
                f" the fortune adapter must not emit specific-event scopes"
            )
    for formation in formations:
        scope = formation.get("scope")
        if not isinstance(scope, str) or not scope.endswith(permitted_suffix):
            raise ValueError(
                f"multi-branch formation {formation.get('id')!r} has non-symbolic scope {scope!r}"
            )


def _mechanism_stack(
    *,
    day_layer: dict[str, Any],
    transit_layers: dict[str, dict[str, Any]],
    natal_output: dict[str, Any],
    strength_evidence: dict[str, Any],
) -> dict[str, Any]:
    natal_pillars = natal_output["four_pillars"]
    day_master = natal_output["day_master"]["stem"]
    decisive = [{
        "id": "day-stem-ten-god",
        "category": "stem_ten_god",
        "source_family": "transit_day_stem",
        "layer": "day",
        "stem": day_layer["stem"],
        "ten_god": day_layer["stem_ten_god"],
        "scope": "traditional_symbolic_relation_not_specific_event",
    }]
    relation_ids = []
    for index, relation in enumerate(day_layer["branch_relations_to_natal"], start=1):
        mechanism_id = f"day-branch-relation-{index:02d}"
        relation_ids.append(mechanism_id)
        decisive.append({
            "id": mechanism_id,
            "category": "branch_relation",
            "source_family": "transit_day_branch_relations",
            "layer": "day",
            **relation,
            "scope": "structural_relation_not_specific_event",
        })

    formations = _target_day_multi_branch_formations(
        natal_pillars,
        transit_layers,
        day_master=day_master,
    )
    for formation in formations:
        decisive.append({
            **formation,
            "category": "multi_branch_formation",
            "source_family": "transit_day_multi_branch_formations",
            "layer": "day_cross_layer",
        })
    formation_ids = [item["id"] for item in formations]
    if formation_ids:
        resolution_level = "cross_layer_formation"
        primary_ids = formation_ids
    elif relation_ids:
        resolution_level = "day_branch_relation"
        primary_ids = relation_ids
    else:
        resolution_level = "symbolic_low"
        primary_ids = ["day-stem-ten-god"]

    _assert_mechanism_scopes_are_symbolic(decisive, formations)

    return {
        "natal_baseline": {
            "day_master": natal_output["day_master"],
            "month_command": natal_output["month_command"],
            "seasonal_profile": natal_output["seasonal_profile"],
            "tiaohou_markers": natal_output["tiaohou_markers"],
            "element_inventory": natal_output["element_inventory"],
            "strength_evidence": strength_evidence,
        },
        "target_day": {
            "pillar": day_layer["pillar"],
            "stem": day_layer["stem"],
            "branch": day_layer["branch"],
            "stem_ten_god": day_layer["stem_ten_god"],
            "branch_hidden_ten_gods": day_layer["branch_hidden_ten_gods"],
            "relations_to_natal": day_layer["branch_relations_to_natal"],
        },
        "active_layer_order": ["major_luck", "year", "month", "day"],
        "active_layers": transit_layers,
        "multi_branch_formations": formations,
        "decisive_mechanisms": decisive,
        "judgment_resolution": {
            "level": resolution_level,
            "primary_mechanism_ids": primary_ids,
            "direction_status": "requires_classical_interpretive_adjudication",
            "specific_life_event_status": "unsupported_without_user_context",
            # Fourth-acceptance P0-1: the fact adapter runs BEFORE source plan
            # and evidence bundle. It cannot know which records will be
            # selected, whether classical rules conflict, or whether
            # applicable conditions are met. Therefore it MUST NOT emit any
            # `resolution_reason` here. The reason is bound to real records
            # and conditions during evidence-bundle compilation.
        },
        "dependency_groups": [
            {
                "id": "transit-day-stem",
                "mechanism_ids": ["day-stem-ten-god"],
                "independent_family_count": 1,
            },
            {
                "id": "transit-day-branch-relations",
                "mechanism_ids": relation_ids,
                "independent_family_count": 1,
            },
            {
                "id": "transit-day-multi-branch-formations",
                "mechanism_ids": formation_ids,
                "independent_family_count": 1,
            },
        ],
        "active_layer_metadata": {
            "id": "active-timing-layers",
            "layers": ["major_luck", "year", "month", "day"],
            "independent_family_count": None,
            "note": "traditional layers are compared structurally, not counted as empirical votes",
        },
        "unresolved_boundaries": [
            "favorable_or_unfavorable_use_requires_classical_interpretive_adjudication",
            "specific_life_event_cannot_be_determined_from_transit_symbols_alone",
        ],
        "empirical_independence_claimed": False,
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    _ensure_sxtwl()
    timezone = ZoneInfo(args.timezone)
    generated_at = _parse_datetime(args.at, timezone) if args.at != "now" else datetime.now(timezone)
    probes = _parse_window(args.window, timezone)
    period_dates = sorted({probe.date().isoformat() for probe in probes})
    if len(period_dates) != 1:
        raise ValueError("Fortune bounded view must stay within one civil day")
    target_date = period_dates[0]
    if generated_at.date().isoformat() == target_date:
        selected_at = generated_at
        selection_basis = "reference_datetime"
    else:
        selected_at = probes[0]
        selection_basis = "target_window_start_reference_outside_period"
    expected = args.expected_pillars or None
    natal, conflict = bazi.build_from_birth(
        args.birth_datetime,
        timezone_name=args.timezone,
        location=args.location,
        gender=args.gender,
        expected_pillars=expected,
        zi_hour_policy=args.zi_hour_policy,
        longitude=args.longitude,
        latitude=args.latitude,
        coordinate_source=args.coordinate_source,
        coordinate_accuracy_meters=getattr(args, "coordinate_accuracy_meters", None),
        time_basis_policy=getattr(args, "time_basis_policy", "civil"),
    )
    if conflict or natal["fact_layer_status"] != "calculated_natal_chart_from_birth_datetime":
        raise ValueError("birth facts conflict with expected pillars")

    natal_pillars = natal["output"]["four_pillars"]
    day_master = natal["output"]["day_master"]["stem"]
    snapshots = [
        _snapshot(
            probe,
            day_master=day_master,
            natal_pillars=natal_pillars,
            location=args.location,
            longitude=args.longitude,
            latitude=args.latitude,
            coordinate_source=args.coordinate_source,
            zi_hour_policy=args.zi_hour_policy,
        )
        for probe in probes
    ]
    active_luck = _active_luck_cycle(
        natal,
        _parse_datetime(args.birth_datetime, timezone),
        selected_at,
    )
    target_snapshot = _snapshot(
        selected_at,
        day_master=day_master,
        natal_pillars=natal_pillars,
        location=args.location,
        longitude=args.longitude,
        latitude=args.latitude,
        coordinate_source=args.coordinate_source,
        zi_hour_policy=args.zi_hour_policy,
    )
    day_ten_god = target_snapshot["ten_gods"]["day"]
    day_relations = target_snapshot["day_branch_relations"]

    hour_profiles = []
    for snapshot in snapshots:
        hour_ten_god = snapshot["ten_gods"]["hour"]
        hour_profiles.append({
            "phase": _phase_name(datetime.fromisoformat(snapshot["at"])),
            "at": snapshot["at"],
            "hour_ganzhi": snapshot["ganzhi"]["hour"],
            "hour_stem_ten_god": hour_ten_god,
            "source_family": "transit_hour_stem",
            "hour_branch_relations": snapshot["hour_branch_relations"],
        })
    hour_signals = []
    seen_hour_stems = set()
    for item in hour_profiles:
        hour_stem = item["hour_ganzhi"][0]
        if hour_stem in seen_hour_stems:
            continue
        seen_hour_stems.add(hour_stem)
        hour_signals.append({
            "at": item["at"],
            "hour_stem": hour_stem,
            "ten_god": item["hour_stem_ten_god"],
        })

    transit_layers = {}
    for name, pillar in (
        ("major_luck", active_luck["pillar"]),
        ("year", target_snapshot["ganzhi"]["year"]),
        ("month", target_snapshot["ganzhi"]["month"]),
        ("day", target_snapshot["ganzhi"]["day"]),
    ):
        transit_layers[name] = _transit_layer(
            name,
            pillar,
            day_master=day_master,
            natal_pillars=natal_pillars,
        )
    strength_evidence = compile_bazi_reasoning_tools(
        natal,
        {"domains": []},
    )["strength_evidence"]
    mechanism_stack = _mechanism_stack(
        day_layer=transit_layers["day"],
        transit_layers=transit_layers,
        natal_output=natal["output"],
        strength_evidence=strength_evidence,
    )
    natal_digest = bazi.natal_fact_digest(natal)
    bazi_day_fact_layer = bazi.build_day_fact_extensions(
        natal,
        start_date=target_date,
        end_date=target_date,
        target_time_basis_policy="civil",
    )[target_date]
    selected_instant = datetime.fromisoformat(target_snapshot["at"])
    selected_bazi_segment = next(
        segment
        for segment in bazi_day_fact_layer["ganzhi_segments"]
        if datetime.fromisoformat(segment["start_inclusive"])
        <= selected_instant
        < datetime.fromisoformat(segment["end_exclusive"])
    )
    for layer in ("year", "month", "day"):
        if (
            selected_bazi_segment["active_transits"][layer]
            != target_snapshot["ganzhi"][layer]
        ):
            raise ValueError(
                f"Fortune {layer} layer diverges from the authoritative Bazi day facts"
            )

    payload = {
        "schema_version": "mingli-near-time-fortune-v2",
        "fact_layer_status": FACT_STATUS,
        "source_tool": "fortune_calc.py" if args.source_tool == "fortune_calc.py" else Path(__file__).name,
        "contract_version": CONTRACT_VERSION,
        "adapter": {
            "name": ADAPTER_NAME,
            "version": ADAPTER_VERSION,
            "rule_profile": "full-birth/transit-mechanism-stack-v5",
            "generated_at": generated_at.isoformat(timespec="seconds"),
        },
        "window_status": "ok",
        "target_date": probes[0].date().isoformat(),
        "target_window": args.window,
        "probe_times": [probe.isoformat(timespec="minutes") for probe in probes],
        "reference_selection": {
            "requested_at": generated_at.isoformat(),
            "selected_at": selected_instant.isoformat(),
            "basis": selection_basis,
        },
        "bounded_view": {
            "base_system": "bazi",
            "natal_fact_digest": natal_digest,
            "period_kind": "civil_day",
            "periods": period_dates,
            "period_count": len(period_dates),
            "base_fact_layer": "bazi_day_fact_extension",
            "scope": "verified natal facts plus the explicitly requested near-time window",
        },
        "calendar_normalization": target_snapshot["calendar_normalization"],
        "bazi_day_fact_layer": bazi_day_fact_layer,
        "selected_bazi_day_segment": selected_bazi_segment,
        "birth_fact_layer": {
            "status": natal["fact_layer_status"],
            "adapter": natal["adapter"],
            "calendar_normalization": natal["calendar_normalization"],
            "natal_fact_digest": natal_digest,
            "natal_pillars": natal_pillars,
            "four_pillars": natal_pillars,
            "day_master": natal["output"]["day_master"],
            "month_command": natal["output"]["month_command"],
            "hidden_stems": natal["output"]["hidden_stems"],
            "ten_gods": natal["output"]["ten_gods"],
            "element_inventory": natal["output"]["element_inventory"],
            "seasonal_profile": natal["output"]["seasonal_profile"],
            "tiaohou_markers": natal["output"]["tiaohou_markers"],
            "interpretive_candidates": natal["output"]["interpretive_candidates"],
            "shensha_auxiliary": natal["output"]["shensha_auxiliary"],
            "strength_evidence": strength_evidence,
            "active_luck_cycle": active_luck["pillar"],
            "active_luck_cycle_detail": active_luck,
        },
        "shensha_auxiliary": {
            **selected_bazi_segment["shensha_auxiliary"],
            "temporal_scope": "bounded_near_time_view",
        },
        "transit_layers": transit_layers,
        "mechanism_stack": mechanism_stack,
        "hour_profiles": hour_profiles,
        "source_family_evidence": {
            "transit_day_stem": {
                "independent_family_count": 1,
                "signals": [{
                    "mechanism_id": "day-stem-ten-god",
                    "stem": target_snapshot["ganzhi"]["day"][0],
                    "ten_god": day_ten_god,
                }],
                "temporal_scope": "day",
            },
            "transit_day_branch_relations": {
                "independent_family_count": 1,
                "signals": day_relations,
                "temporal_scope": "day",
                "primary_eligible": False,
            },
            "transit_day_multi_branch_formations": {
                "independent_family_count": 1,
                "signals": mechanism_stack["multi_branch_formations"],
                "temporal_scope": "day_cross_natal_and_active_layers",
                "primary_eligible": bool(mechanism_stack["multi_branch_formations"]),
            },
            "transit_hour_stem": {
                "independent_family_count": 1,
                "distinct_signal_count": len(hour_signals),
                "signals": hour_signals,
                "temporal_scope": "queried_hours",
            },
        },
        "public_claim_contract": {
            "decisive_mechanism_ids": [
                item["id"] for item in mechanism_stack["decisive_mechanisms"]
            ],
            "primary_mechanism_ids": mechanism_stack["judgment_resolution"][
                "primary_mechanism_ids"
            ],
            "require_phase_narrative": False,
            "user_selected_domains_only": True,
            "supported_specific_events": [],
            "exact_event_claims": [],
            "required_coverage": [
                "time_basis",
                "direct_judgment",
                "mechanism_explanation",
            ],
            "specificity_policy": "no specific event, amount, or domain without user context or supporting facts",
            "wording_policy": "free natural prose; no required phases, feelings, actions, score, or sentence order",
        },
        "dialogue_contract": {
            "mode": "answer_then_optional_probe",
            "question_required": False,
            "maximum_follow_up_questions": 1,
            "question_allowed_when": [
                "missing_decisive_input",
                "two_supported_hypotheses_need_disambiguation",
                "user_requests_refinement",
            ],
            "probe_must_change": ["route", "event_context", "time_horizon", "fact_layer"],
            "prohibited_question_styles": [
                "question_only_deferral",
                "leading_confirmation",
                "repeat_known_birth_data",
                "multi_question_intake",
            ],
            "repair_after_user_dissatisfaction": {
                "mode": "recalculate_answer_then_one_open_probe",
                "question_required": True,
                "maximum_follow_up_questions": 1,
                "prohibited_responses": [
                    "meta_explanation_only",
                    "domain_menu",
                    "leading_confirmation",
                ],
            },
            "after_user_answers_probe": {
                "mode": "continue_from_user_event_context",
                "reuse_validated_baseline": True,
                "treat_reply_as_chart_proof": False,
            },
        },
        "evidence_resolution": {
            "level": "traditional_structural_medium",
            "empirically_calibrated": False,
            "limitations": [
                "traditional Bazi associations are not statistically validated event predictions",
                "branch relations produced by one transit branch remain one dependent evidence family",
                "queried hours are optional facts and do not require a public phase narrative",
            ],
        },
    }
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--birth-datetime", required=True)
    parser.add_argument("--timezone", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--coordinate-source")
    parser.add_argument("--coordinate-accuracy-meters", type=float)
    parser.add_argument("--gender", required=True)
    parser.add_argument("--expected-pillars", nargs=4)
    parser.add_argument("--window", required=True)
    parser.add_argument("--at", default="now")
    parser.add_argument("--zi-hour-policy", choices=("midnight", "late-zi-next-day"), default="midnight")
    parser.add_argument("--time-basis-policy", default="civil")
    parser.add_argument("--source-tool", choices=("adapter", "fortune_calc.py"), default="adapter")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        payload = build_contract(args)
    except (AssertionError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
