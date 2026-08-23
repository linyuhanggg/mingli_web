#!/usr/bin/env python3
"""Private deterministic fact calculator used by the portable provider."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

import liuren_fact_adapter
from reading_engine.liuren_contract import (
    LIUREN_RULES_SHA256,
    build_runtime_core_facts,
)
from runtime_python import runtime_command


CALCULATION_CONTRACT = "mingli-liuren-pipeline-v6-runtime-contract"
RUNTIME_FILES = (
    "scripts/liuren_calc.py",
    "scripts/runtime_python.py",
    "scripts/liuren_fact_adapter.py",
    "scripts/data/liuren-miben-general-imagery.json",
    "scripts/reading_engine/calendar_core.py",
    "scripts/reading_engine/liuren_contract.py",
    "scripts/adapter_validate.py",
    "references/matrices/liuren-source-tables-v1.yaml",
    "references/inference/liuren-rules-v1.json",
)
MAX_QUERY_CHARS = 500
MAX_LOCATION_CHARS = 100
DEFAULT_CIVIL_CHINA_LOCATION = "中国（民用北京时间；城市未提供）"
LIUREN_STEMS = "甲乙丙丁戊己庚辛壬癸"
LIUREN_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
LIUREN_SEXAGENARY_CYCLE = tuple(
    LIUREN_STEMS[index % 10] + LIUREN_BRANCHES[index % 12]
    for index in range(60)
)
LIUREN_INITIAL_TIMING_ANCHOR = {
    "寅": "辰",
    "卯": "辰",
    "辰": "未",
    "巳": "未",
    "午": "未",
    "未": "戌",
    "申": "戌",
    "酉": "戌",
    "戌": "丑",
    "亥": "丑",
    "子": "丑",
    "丑": "辰",
}
LIUREN_ELEMENT = dict(zip("子丑寅卯辰巳午未申酉戌亥", "水土木木土火火土金金土水"))
LIUREN_MONTH_SEASON = {
    **dict.fromkeys("寅卯", "spring"),
    **dict.fromkeys("巳午", "summer"),
    **dict.fromkeys("申酉", "autumn"),
    **dict.fromkeys("亥子", "winter"),
    **dict.fromkeys("辰未戌丑", "earth"),
}
LIUREN_SEASONAL_STRENGTH = {
    "spring": dict(zip("木火水金土", "旺相休囚死")),
    "summer": dict(zip("火土木水金", "旺相休囚死")),
    "autumn": dict(zip("金水土火木", "旺相休囚死")),
    "winter": dict(zip("水木金土火", "旺相休囚死")),
    "earth": dict(zip("土金火木水", "旺相休囚死")),
}
LIUREN_SOURCE_TABLE_RELPATH = Path("references/matrices/liuren-source-tables-v1.yaml")
LIUREN_SOURCE_TABLE_SHA256 = "49095999aaef2b16000e201969f5ca5b1a02bf5c3e340ae0770d95f3cfe27415"
LIUREN_IMAGERY_RELPATH = Path("scripts/data/liuren-miben-general-imagery.json")
LIUREN_IMAGERY_SHA256 = "da5cead70490e0769cb60ed44de07e8b106960d964f8616a7ad384380f13d996"
LIUREN_RULES_RELPATH = Path("references/inference/liuren-rules-v1.json")
LIUREN_DIMENSION_ALIASES = {
    "outcome": "outcome",
    "timing": "timing",
    "state": "state",
    "current_state": "state",
    "location": "location",
    "location_direction": "location",
    "relationship": "relationship",
    "work": "work",
    "career": "work",
    "money": "money",
}
LIUREN_TARGET_RELATIVES = ("兄弟", "子孙", "妻财", "官鬼", "父母")
LIUREN_TARGET_RELATIVE_SET = frozenset(LIUREN_TARGET_RELATIVES)
LIUREN_DIMENSION_DEPENDENCIES = {
    "outcome": ("liuren.dimension-specific-calculated-facts",),
    "timing": (
        "liuren.timing.initial-group-seasonal-upper",
        "liuren.dimension-specific-calculated-facts",
    ),
    "state": (
        "liuren.dimension-specific-calculated-facts",
        "liuren.imagery.general-landing-correspondence",
    ),
    "location": ("liuren.location.branch-direction-correspondence",),
    "relationship": ("liuren.dimension-specific-calculated-facts",),
    "work": ("liuren.dimension-specific-calculated-facts",),
    "money": (
        "liuren.dimension-specific-calculated-facts",
        "liuren.imagery.general-landing-correspondence",
    ),
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def _liuren_source_tables() -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    source_table_path = root / LIUREN_SOURCE_TABLE_RELPATH
    imagery_path = root / LIUREN_IMAGERY_RELPATH
    if _sha256_file(source_table_path) != LIUREN_SOURCE_TABLE_SHA256:
        raise ValueError("Liuren source table hash mismatch")
    if _sha256_file(imagery_path) != LIUREN_IMAGERY_SHA256:
        raise ValueError("Liuren imagery index hash mismatch")
    source_table = yaml.safe_load(source_table_path.read_text(encoding="utf-8"))
    imagery = json.loads(imagery_path.read_text(encoding="utf-8"))
    if source_table.get("schema_version") != "mingli-liuren-source-tables-v1":
        raise ValueError("unsupported Liuren source table schema")
    if imagery.get("schema_version") != "liuren-miben-general-imagery-v1":
        raise ValueError("unsupported Liuren imagery index schema")
    return source_table, imagery


@lru_cache(maxsize=1)
def _liuren_rule_catalog() -> dict[str, dict[str, Any]]:
    """Load the source-bound rule definitions used by the evidence layer."""

    root = Path(__file__).resolve().parents[1]
    path = root / LIUREN_RULES_RELPATH
    if _sha256_file(path) != LIUREN_RULES_SHA256:
        raise ValueError("Liuren rule catalog hash mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "mingli-liuren-executable-rules-v1":
        raise ValueError("unsupported Liuren rule catalog schema")
    rules = payload.get("rules")
    if not isinstance(rules, dict) or not rules:
        raise ValueError("Liuren rule catalog is empty")
    return {
        str(key): copy.deepcopy(value)
        for key, value in rules.items()
        if isinstance(value, dict)
    }


def _directed_element_relation(
    left_label: str,
    left_value: str,
    right_label: str,
    right_value: str,
) -> dict[str, Any]:
    left_element = liuren_fact_adapter.ELEMENT[left_value]
    right_element = liuren_fact_adapter.ELEMENT[right_value]
    if left_element == right_element:
        relation = "same_element"
    elif liuren_fact_adapter.GENERATES[left_element] == right_element:
        relation = "subject_generates_object"
    elif liuren_fact_adapter.GENERATES[right_element] == left_element:
        relation = "object_generates_subject"
    elif liuren_fact_adapter.OVERCOMES[left_element] == right_element:
        relation = "subject_overcomes_object"
    elif liuren_fact_adapter.OVERCOMES[right_element] == left_element:
        relation = "object_overcomes_subject"
    else:  # pragma: no cover - the complete five-phase graph is exhaustive
        raise ValueError("unresolved five-phase relation")
    return {
        "subject": left_label,
        "subject_value": left_value,
        "subject_element": left_element,
        "object": right_label,
        "object_value": right_value,
        "object_element": right_element,
        "relation": relation,
    }


def _stage_status(transmissions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "stage": row["stage"],
            "branch": row["branch"],
            "six_relative": row["six_relative"],
            "heavenly_general": row["heavenly_general"],
            "season_strength": row["season_strength"],
            "is_xunkong": row["is_xunkong"],
        }
        for row in transmissions
    ]


def _liuren_rule_record(
    rule_key: str,
    *,
    status: str,
    fact_paths: tuple[str, ...],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    catalog = _liuren_rule_catalog()
    definition = catalog.get(rule_key)
    if definition is None:
        raise ValueError(f"unknown Liuren rule key: {rule_key}")
    record = {
        "rule_key": rule_key,
        "activation_id": str(definition["activation_id"]),
        "rule_id": str(definition["rule_id"]),
        "status": status,
        "polarity": str(definition["polarity"]),
        "weight_class": str(definition["weight_class"]),
        "dependency_group": str(definition["dependency_group"]),
        "source_refs": copy.deepcopy(definition.get("source_refs") or ()),
        "fact_paths": list(fact_paths),
        "observation": copy.deepcopy(dict(observation)),
    }
    if definition.get("confidence_ceiling") is not None:
        record["confidence_ceiling"] = str(definition["confidence_ceiling"])
    if definition.get("stop_conditions"):
        record["stop_conditions"] = copy.deepcopy(definition["stop_conditions"])
    return record


def _liuren_rule_evidence(
    canonical: str,
    *,
    projected: Mapping[str, Any],
    transmissions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compile only directly observable source-rule activations.

    This is intentionally an evidence layer.  It never aggregates support and
    opposition into a directional answer, because the source packages do not
    define a complete school-neutral adjudication procedure here.
    """

    catalog = _liuren_rule_catalog()

    matched: list[dict[str, Any]] = []
    scope_boundaries: list[dict[str, Any]] = []
    not_evaluated: list[dict[str, Any]] = []

    def add_match(
        rule_key: str,
        *,
        fact_paths: tuple[str, ...],
        observation: Mapping[str, Any],
    ) -> None:
        matched.append(
            _liuren_rule_record(
                rule_key,
                status="matched",
                fact_paths=fact_paths,
                observation=observation,
            )
        )

    def add_scope(
        rule_key: str,
        *,
        fact_paths: tuple[str, ...],
        observation: Mapping[str, Any],
    ) -> None:
        scope_boundaries.append(
            _liuren_rule_record(
                rule_key,
                status="scope_boundary",
                fact_paths=fact_paths,
                observation=observation,
            )
        )

    if canonical == "outcome":
        subject_relation = str(
            (projected.get("subject_object_relation") or {}).get("relation") or ""
        )
        relation_paths = ("dimension_facts.outcome.subject_object_relation",)
        if subject_relation == "subject_overcomes_object":
            add_match(
                "day_stem_overcomes_branch",
                fact_paths=relation_paths,
                observation={"relation": subject_relation},
            )
        elif subject_relation == "object_overcomes_subject":
            add_match(
                "day_branch_overcomes_stem",
                fact_paths=relation_paths,
                observation={"relation": subject_relation},
            )

        transmission_relations = [
            str(row.get("relation") or "")
            for row in projected.get("transmissions_to_day") or ()
            if isinstance(row, Mapping)
        ]
        transmission_paths = ("dimension_facts.outcome.transmissions_to_day",)
        if transmission_relations and all(
            relation == "subject_generates_object" for relation in transmission_relations
        ):
            add_match(
                "transmissions_generate_day",
                fact_paths=transmission_paths,
                observation={"relations": transmission_relations},
            )
        elif transmission_relations and all(
            relation == "subject_overcomes_object" for relation in transmission_relations
        ):
            add_match(
                "transmissions_overcome_day",
                fact_paths=transmission_paths,
                observation={"relations": transmission_relations},
            )

        initial_final_relation = str(
            (projected.get("initial_final_relation") or {}).get("relation") or ""
        )
        initial_final_paths = ("dimension_facts.outcome.initial_final_relation",)
        if initial_final_relation == "subject_overcomes_object":
            add_match(
                "initial_overcomes_final",
                fact_paths=initial_final_paths,
                observation={"relation": initial_final_relation},
            )
        elif initial_final_relation == "object_overcomes_subject":
            add_match(
                "final_overcomes_initial",
                fact_paths=initial_final_paths,
                observation={"relation": initial_final_relation},
            )

        middle = next(
            (
                row
                for row in transmissions
                if str(row.get("stage") or "") == "middle"
            ),
            None,
        )
        if isinstance(middle, Mapping) and bool(middle.get("is_xunkong")):
            add_match(
                "middle_void_process",
                fact_paths=("dimension_facts.outcome.stage_status",),
                observation={
                    "stage": "middle",
                    "branch": middle.get("branch"),
                    "is_xunkong": True,
                },
            )

        for rule_key in (
            "message_target_present",
            "message_target_strong",
            "message_target_weak",
            "message_target_void",
        ):
            definition = catalog[rule_key]
            not_evaluated.append(
                {
                    "rule_key": rule_key,
                    "activation_id": str(definition["activation_id"]),
                    "rule_id": str(definition["rule_id"]),
                    "status": "required_fact_missing",
                    "reason": "no_message_target_fact_in_current_liuren_contract",
                    "source_refs": copy.deepcopy(definition.get("source_refs") or ()),
                }
            )
    elif canonical == "money":
        wealth_present = bool(projected.get("wealth_presence"))
        wealth_paths = ("dimension_facts.money.wealth_presence",)
        if wealth_present:
            observation = {
                "wealth_presence": True,
                "wealth_stages": copy.deepcopy(projected.get("wealth_stage_strength") or ()),
            }
            add_match("wealth_present_miben", fact_paths=wealth_paths, observation=observation)
            void_rows = [
                row
                for row in projected.get("wealth_void_status") or ()
                if isinstance(row, Mapping) and bool(row.get("is_xunkong"))
            ]
            if void_rows:
                void_observation = {
                    "wealth_void_rows": copy.deepcopy(void_rows),
                }
                add_match(
                    "wealth_void_miben",
                    fact_paths=("dimension_facts.money.wealth_void_status",),
                    observation=void_observation,
                )
        else:
            add_scope(
                "wealth_absent_scope",
                fact_paths=wealth_paths,
                observation={"wealth_presence": False},
            )

        middle = next(
            (
                row
                for row in transmissions
                if str(row.get("stage") or "") == "middle"
            ),
            None,
        )
        if isinstance(middle, Mapping) and bool(middle.get("is_xunkong")):
            add_match(
                "middle_void_process",
                fact_paths=("dimension_facts.money.stage_status",),
                observation={
                    "stage": "middle",
                    "branch": middle.get("branch"),
                    "is_xunkong": True,
                },
            )

    elif canonical == "timing":
        candidate_branch = projected.get("candidate_branch")
        if isinstance(candidate_branch, Mapping) and candidate_branch.get("branch"):
            add_match(
                "timing_candidate_branch",
                fact_paths=("dimension_facts.timing.candidate_branch",),
                observation={
                    "candidate_branch": copy.deepcopy(dict(candidate_branch)),
                    "candidate_date": copy.deepcopy(projected.get("candidate_date")),
                    "relative_speed": projected.get("relative_speed"),
                },
            )

    elif canonical == "state":
        matched_correspondences = [
            row
            for row in projected.get("general_landing_correspondences") or ()
            if isinstance(row, Mapping)
            and row.get("status") == "source_correspondence_matched"
        ]
        if matched_correspondences:
            add_match(
                "state_general_landing_correspondence",
                fact_paths=("dimension_facts.state.general_landing_correspondences",),
                observation={
                    "matched_count": len(matched_correspondences),
                    "stages": [str(row.get("stage") or "") for row in matched_correspondences],
                    "correspondences": copy.deepcopy(matched_correspondences),
                },
            )

    elif canonical == "relationship":
        subject_relation = str(
            (projected.get("subject_object_relation") or {}).get("relation") or ""
        )
        relation_paths = ("dimension_facts.relationship.subject_object_relation",)
        if subject_relation == "subject_overcomes_object":
            add_match(
                "relationship_day_stem_overcomes_branch",
                fact_paths=relation_paths,
                observation={"relation": subject_relation},
            )
        elif subject_relation == "object_overcomes_subject":
            add_match(
                "relationship_day_branch_overcomes_stem",
                fact_paths=relation_paths,
                observation={"relation": subject_relation},
            )

    elif canonical == "work":
        target_relative = str(projected.get("target_relative") or "")
        target_paths = (
            "dimension_facts.work.target_relative",
            "dimension_facts.work.target_presence",
        )
        target_presence = projected.get("target_presence") is True
        if target_relative and target_presence:
            add_match(
                "work_target_present",
                fact_paths=target_paths,
                observation={
                    "target_relative": target_relative,
                    "target_strength": copy.deepcopy(projected.get("target_strength") or ()),
                    "target_general_modifier": copy.deepcopy(
                        projected.get("target_general_modifier") or ()
                    ),
                },
            )
        elif target_relative:
            add_scope(
                "work_target_present",
                fact_paths=target_paths,
                observation={
                    "target_relative": target_relative,
                    "target_presence": False,
                    "target_contract_status": str(
                        projected.get("target_contract_status") or "bound"
                    ),
                },
            )
        else:
            definition = catalog["work_target_present"]
            not_evaluated.append(
                {
                    "rule_key": "work_target_present",
                    "activation_id": str(definition["activation_id"]),
                    "rule_id": str(definition["rule_id"]),
                    "status": "required_fact_missing",
                    "reason": "work_target_relative_not_supplied",
                    "source_refs": copy.deepcopy(definition.get("source_refs") or ()),
                }
            )

    if matched:
        status = "matched_evidence"
    elif scope_boundaries:
        status = "scope_boundary"
    elif canonical in {"outcome", "money"}:
        status = "not_calculated"
    else:
        status = "not_bound"
    return {
        "status": status,
        "hard_verdict": None,
        "requires_school_adjudication": True,
        "matched": matched,
        "scope_boundaries": scope_boundaries,
        "not_evaluated": not_evaluated,
        "catalog_schema": "mingli-liuren-executable-rules-v1",
    }


def _general_landing_correspondences(
    transmissions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    _, imagery = _liuren_source_tables()
    generals = imagery.get("generals") or {}
    rows: list[dict[str, Any]] = []
    for transmission in transmissions:
        general = str(transmission["heavenly_general"])
        branch = str(transmission["branch"])
        general_profile = generals.get(general)
        if not isinstance(general_profile, dict):
            raise ValueError(f"unknown Liuren heavenly general: {general}")
        entry = ((general_profile.get("by_branch") or {}).get(branch))
        row = {
            "stage": transmission["stage"],
            "heavenly_general": general,
            "landing_branch": branch,
            "source_pack": "san-shi/liuren-miben",
            "source_rule": "LM-R01",
            "role": "imagery_correspondence_not_observed_activity",
        }
        if not isinstance(entry, dict):
            rows.append({**row, "status": "no_exact_source_correspondence"})
            continue
        if not entry.get("source_text") or not entry.get("source_anchor"):
            raise ValueError(f"incomplete Liuren source correspondence: {general}/{branch}")
        rows.append(
            {
                **row,
                "status": "source_correspondence_matched",
                "source_text": str(entry["source_text"]),
                "source_anchor": str(entry["source_anchor"]),
            }
        )
    return rows


def _stage_branch_directions(
    transmissions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_table, _ = _liuren_source_tables()
    directions = source_table.get("branch_directions") or {}
    rows: list[dict[str, Any]] = []
    for transmission in transmissions:
        branch = str(transmission["branch"])
        direction = directions.get(branch)
        if not isinstance(direction, dict):
            raise ValueError(f"missing Liuren branch direction: {branch}")
        rows.append(
            {
                "stage": transmission["stage"],
                "branch": branch,
                "direction": direction["direction"],
                "direction_chinese": direction["chinese"],
                "declared_source_anchor": direction["source_anchor"],
                "source_binding_status": "unverified_source_excerpt_not_in_release",
                "scope": "symbolic_direction_candidate_only",
            }
        )
    return rows


def _horizon_boundary(value: Any, *, end: bool) -> date | None:
    text = str(value or "")[:10]
    if not text:
        return None
    try:
        if len(text) == 4:
            return date(int(text), 12 if end else 1, 31 if end else 1)
        if len(text) == 7:
            year, month = (int(part) for part in text.split("-"))
            if end:
                next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
                return next_month - timedelta(days=1)
            return date(year, month, 1)
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def _timing_projection(
    facts: dict[str, Any],
    output: dict[str, Any],
    transmissions: list[dict[str, Any]],
    horizon: dict[str, Any],
) -> dict[str, Any]:
    initial_branch = str(transmissions[0]["branch"])
    anchor_earth = LIUREN_INITIAL_TIMING_ANCHOR.get(initial_branch)
    raw_candidate_branch = _liuren_heaven_above(output, anchor_earth) if anchor_earth else None
    start = _horizon_boundary(horizon.get("start"), end=False)
    end = _horizon_boundary(horizon.get("end"), end=True)
    kind = str(horizon.get("kind") or "instant")
    civil_datetime = str((facts.get("calendar_normalization") or {}).get("civil_datetime") or "")
    try:
        datetime.fromisoformat(civil_datetime)
        calendar_ready = True
    except ValueError:
        calendar_ready = False
    bounded = kind in {"day", "month"} and start is not None and end is not None and start <= end
    candidate_branch = raw_candidate_branch if calendar_ready and bounded else None
    candidates: list[dict[str, Any]] = []
    if candidate_branch and calendar_ready and bounded:
        candidate = _liuren_next_branch_date(facts, candidate_branch)
        if candidate is not None:
            candidate_date = date.fromisoformat(candidate["solar_date"])
            if start <= candidate_date <= end:
                candidates.append(
                    {
                        "id": "initial_group_upper_candidate",
                        "role": "event_response_candidate",
                        "anchor_earth_branch": anchor_earth,
                        **candidate,
                        "source_pack": "san-shi/liuren-miben",
                        "source_rule": "LM-R21",
                        "candidate_not_guarantee": True,
                    }
                )
    strength = transmissions[0].get("season_strength")
    if not calendar_ready:
        status = "missing_calendar_precondition"
    elif not bounded:
        status = "unbounded_horizon_no_exact_date"
    else:
        status = "traditional_candidates" if candidates else "no_candidate_in_horizon"
    return {
        "requested_horizon": dict(horizon),
        "candidate_branch": (
            {
                "branch": candidate_branch,
                "anchor_earth_branch": anchor_earth,
                "source_rule": "LM-R21",
            }
            if candidate_branch
            else None
        ),
        "candidates": candidates,
        "status": status,
        "initial_strength": strength,
        "relative_speed": (
            "relatively_faster"
            if strength in {"旺", "相"}
            else "relatively_slower"
            if strength in {"休", "囚", "死"}
            else "unresolved"
        ),
        "rule_trace": [
            *(
                [
                    {
                        "rule_id": "LM-R21",
                        "source_dependency_id": "liuren.timing.initial-group-seasonal-upper",
                        "source_pack": "san-shi/liuren-miben",
                        "operation": "initial transmission group -> earth anchor -> heaven-plate upper -> next matching branch day when calendar and horizon are bounded",
                    }
                ]
                if candidate_branch
                else []
            ),
            *(
                [
                    {
                        "rule_id": "DLR-16",
                        "source_dependency_id": "liuren.dimension-specific-calculated-facts",
                        "source_pack": "san-shi/daliuren-daquan",
                        "operation": "calculated initial strength -> relative speed only",
                    }
                ]
                if strength in {"旺", "相", "休", "囚", "死"}
                else []
            ),
        ],
        "boundary": "traditional candidates are deterministic rule applications, not guaranteed event dates",
    }


def _activated_dimension_rule_ids(
    *,
    canonical: str,
    eligible_rule_ids: list[str],
    projected: dict[str, Any],
    output: dict[str, Any],
    transmissions_to_day: list[dict[str, Any]],
    initial_final: dict[str, Any],
    stage_flow: list[dict[str, Any]],
) -> list[str]:
    """Return only source rules whose stated deterministic preconditions fired."""

    active: set[str] = set()
    directional_overcome = {
        "subject_overcomes_object",
        "object_overcomes_subject",
    }
    if canonical in {"outcome", "relationship"}:
        relation = str((projected.get("subject_object_relation") or {}).get("relation") or "")
        if relation in directional_overcome:
            active.add("LR-17")

    if canonical == "outcome":
        transmission_relations = [str(row.get("relation") or "") for row in transmissions_to_day]
        initial_final_relation = str(initial_final.get("relation") or "")
        if (
            transmission_relations
            and (
                all(value == "subject_generates_object" for value in transmission_relations)
                or all(value == "subject_overcomes_object" for value in transmission_relations)
                or initial_final_relation in directional_overcome
            )
        ):
            active.add("LR-18")
        if (
            len(stage_flow) == 2
            and transmission_relations
            and all(
                str(row.get("relation") or "") == "subject_generates_object"
                for row in stage_flow
            )
            and transmission_relations[-1]
            in {"subject_generates_object", "subject_overcomes_object"}
        ):
            active.add("DLR-17")

    elif canonical == "timing":
        relative_speed = str(projected.get("relative_speed") or "")
        if relative_speed in {"relatively_faster", "relatively_slower"}:
            active.add("DLR-16")
        if projected.get("candidate_branch") is not None:
            active.add("LM-R21")
        method = str((output.get("transmission_method") or {}).get("primary") or "")
        if method in {"元首", "重审"} and relative_speed in {
            "relatively_faster",
            "relatively_slower",
        }:
            active.add("LR-16")

    elif canonical == "state":
        correspondences = projected.get("general_landing_correspondences") or ()
        if any(
            isinstance(row, dict)
            and row.get("status") == "source_correspondence_matched"
            for row in correspondences
        ):
            active.add("LM-R01")
        if len(projected.get("stage_status") or ()) == 3:
            active.add("LR-09")

    elif canonical == "location":
        # The branch-to-direction table is a deterministic structural helper,
        # not a verified LM-R01/LR-09 interpretation rule.  The release does
        # not ship the cited source excerpt, so location must remain a
        # candidate projection until that binding is audited.
        pass

    elif canonical == "money":
        # Selecting the money dimension supplies the question domain; the
        # complete transmission relatives allow the verified LM-R20 rule to
        # establish presence or absence. LR-15 is source-located but still
        # inactive_unverified, and LR-19 still lacks a target-relative
        # evidence contract here, so neither may be advertised as active.
        active.add("LM-R20")

    elif canonical == "work":
        if projected.get("target_presence") is True:
            active.add("LR-19")

    return [rule_id for rule_id in eligible_rule_ids if rule_id in active]


def _skill_candidates() -> list[Path]:
    configured = os.environ.get("MINGLI_SKILL_DIR")
    if configured:
        return [Path(configured).expanduser().resolve()]
    # A copied portable artifact remains self-contained when its legacy CLI
    # is called directly. It must never discover a host-specific install.
    return [Path(__file__).resolve().parents[1]]


def _find_skill_dir() -> Path:
    for candidate in _skill_candidates():
        if all((candidate / relpath).is_file() for relpath in RUNTIME_FILES):
            return candidate
    if os.environ.get("MINGLI_SKILL_DIR"):
        raise RuntimeError(
            "MINGLI_SKILL_DIR does not point to one complete mingli-master skill"
        )
    raise RuntimeError("mingli-master runtime is incomplete")


def _resolve_datetime(value: str, timezone_name: str) -> str:
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"invalid --timezone: {timezone_name}") from exc
    if value == "now":
        resolved = datetime.now(timezone)
    else:
        try:
            resolved = datetime.fromisoformat(value)
        except ValueError as exc:
            raise RuntimeError(f"invalid --datetime: {value}") from exc
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=timezone)
        else:
            resolved = resolved.astimezone(timezone)
    return resolved.isoformat(timespec="seconds")


def _liuren_heaven_above(output: dict[str, Any], earth_branch: str) -> str | None:
    for item in output.get("heaven_plate") or ():
        if isinstance(item, dict) and item.get("earth") == earth_branch:
            heaven = str(item.get("heaven") or "")
            return heaven if heaven in LIUREN_BRANCHES else None
    return None


def _liuren_next_branch_date(
    facts: dict[str, Any],
    branch: str,
) -> dict[str, Any] | None:
    calendar = facts.get("calendar_normalization") or {}
    output = facts.get("output") or {}
    civil_datetime = str(calendar.get("civil_datetime") or "")
    day_ganzhi = str((output.get("day_hour") or {}).get("day") or "")
    if branch not in LIUREN_BRANCHES or day_ganzhi not in LIUREN_SEXAGENARY_CYCLE:
        return None
    try:
        cast_date = datetime.fromisoformat(civil_datetime).date()
    except ValueError:
        return None
    current = LIUREN_SEXAGENARY_CYCLE.index(day_ganzhi)
    for offset in range(1, 13):
        candidate_ganzhi = LIUREN_SEXAGENARY_CYCLE[(current + offset) % 60]
        if candidate_ganzhi[1] == branch:
            return {
                "branch": branch,
                "solar_date": (cast_date + timedelta(days=offset)).isoformat(),
                "day_ganzhi": candidate_ganzhi,
                "days_after_cast": offset,
            }
    return None


def extend_liuren_facts(
    facts: dict[str, Any],
    *,
    requested_dimensions: tuple[str, ...],
    horizon: dict[str, Any],
    target_relative: str | None = None,
) -> dict[str, Any]:
    """Project only dimension-specific calculated facts and bounded candidates."""

    output = facts.get("output") or {}
    month_ganzhi = str(
        ((facts.get("calendar_normalization") or {}).get("ganzhi") or {}).get(
            "month"
        )
        or ""
    )
    month_branch = month_ganzhi[1:2]
    season = LIUREN_MONTH_SEASON.get(month_branch)
    strength_by_element = LIUREN_SEASONAL_STRENGTH.get(season or "", {})
    empty_branches = set((output.get("xunkong") or {}).get("branches") or ())
    transmissions = [
        {
            **{
                key: item.get(key)
                for key in (
                    "stage",
                    "branch",
                    "six_relative",
                    "heavenly_general",
                )
            },
            "season_strength": strength_by_element.get(
                LIUREN_ELEMENT.get(str(item.get("branch") or ""), "")
            ),
            "is_xunkong": item.get("branch") in empty_branches,
        }
        for item in output.get("three_transmissions") or ()
        if isinstance(item, dict)
    ]
    if len(transmissions) != 3:
        raise ValueError("Liuren extension requires three calculated transmissions")
    day_ganzhi = str((output.get("day_hour") or {}).get("day") or "")
    if day_ganzhi not in LIUREN_SEXAGENARY_CYCLE:
        raise ValueError("Liuren extension requires a calculated day pillar")
    day_stem, day_branch = day_ganzhi
    subject_object = _directed_element_relation("day_stem", day_stem, "day_branch", day_branch)
    transmissions_to_day = [
        {
            "stage": row["stage"],
            **_directed_element_relation(
                "transmission_branch",
                str(row["branch"]),
                "day_stem",
                day_stem,
            ),
        }
        for row in transmissions
    ]
    stage_flow = [
        {
            "from_stage": left["stage"],
            "to_stage": right["stage"],
            **_directed_element_relation(
                "from_branch",
                str(left["branch"]),
                "to_branch",
                str(right["branch"]),
            ),
        }
        for left, right in zip(transmissions, transmissions[1:])
    ]
    initial_final = _directed_element_relation(
        "initial_branch",
        str(transmissions[0]["branch"]),
        "final_branch",
        str(transmissions[-1]["branch"]),
    )
    status_rows = _stage_status(transmissions)
    six_relative_stages = [
        {key: row[key] for key in ("stage", "branch", "six_relative")}
        for row in transmissions
    ]
    correspondences = _general_landing_correspondences(transmissions)
    timing = _timing_projection(facts, output, transmissions, horizon)
    source_table, _ = _liuren_source_tables()
    profiles = source_table.get("dimension_profiles") or {}

    normalized_target_relative = str(target_relative or "").strip() or None
    if (
        normalized_target_relative is not None
        and normalized_target_relative not in LIUREN_TARGET_RELATIVE_SET
    ):
        raise ValueError(
            "Liuren target_relative must be one of "
            + ", ".join(LIUREN_TARGET_RELATIVES)
        )
    target_rows = [
        row
        for row in status_rows
        if normalized_target_relative is not None
        and row["six_relative"] == normalized_target_relative
    ]
    target_stages = {str(row["stage"]) for row in target_rows}
    target_general_modifier = [
        {**row, "six_relative": normalized_target_relative}
        for row in correspondences
        if row["stage"] in target_stages
    ]

    canonical_requested: list[tuple[str, str]] = []
    for requested in dict.fromkeys(requested_dimensions):
        canonical = LIUREN_DIMENSION_ALIASES.get(str(requested))
        if canonical is None:
            raise ValueError(f"unsupported Liuren dimension: {requested}")
        canonical_requested.append((str(requested), canonical))

    dimension_facts: dict[str, dict[str, Any]] = {}
    for requested, canonical in canonical_requested:
        profile = profiles.get(canonical) or {}
        base = {
            "requested_dimension": requested,
            "canonical_dimension": canonical,
            "status": "calculated_facts_not_verdict",
        }
        if canonical == "outcome":
            projected = {
                "subject_object_relation": subject_object,
                "transmissions_to_day": transmissions_to_day,
                "initial_final_relation": initial_final,
                "stage_flow": stage_flow,
            }
        elif canonical == "timing":
            projected = {
                "relative_speed": timing["relative_speed"],
                "candidate_branch": timing["candidate_branch"],
                "candidate_date": timing["candidates"][0] if timing["candidates"] else None,
            }
        elif canonical == "state":
            projected = {
                "stage_status": status_rows,
                "general_landing_correspondences": correspondences,
            }
        elif canonical == "location":
            projected = {"stage_branch_directions": _stage_branch_directions(transmissions)}
        elif canonical == "relationship":
            projected = {
                "six_relative_stages": six_relative_stages,
                "subject_object_relation": subject_object,
                "stage_flow": stage_flow,
            }
        elif canonical == "work":
            projected = {
                "six_relative_stages": six_relative_stages,
                "stage_status": status_rows,
                "subject_object_relation": subject_object,
                "target_relative": normalized_target_relative,
                "target_contract_status": (
                    "bound" if normalized_target_relative else "missing_target_relative"
                ),
                "target_presence": bool(target_rows),
                "target_strength": [
                    {
                        key: row[key]
                        for key in (
                            "stage",
                            "branch",
                            "six_relative",
                            "season_strength",
                            "is_xunkong",
                        )
                    }
                    for row in target_rows
                ],
                "target_general_modifier": target_general_modifier,
            }
        elif canonical == "money":
            wealth = [row for row in status_rows if row["six_relative"] == "妻财"]
            wealth_stages = {row["stage"] for row in wealth}
            projected = {
                "wealth_presence": bool(wealth),
                "wealth_stage_strength": [
                    {key: row[key] for key in ("stage", "branch", "six_relative", "season_strength")}
                    for row in wealth
                ],
                "wealth_void_status": [
                    {key: row[key] for key in ("stage", "branch", "six_relative", "is_xunkong")}
                    for row in wealth
                ],
                "wealth_general_modifier": [
                    {**row, "six_relative": "妻财"}
                    for row in correspondences
                    if row["stage"] in wealth_stages
                ],
            }
        else:  # pragma: no cover - aliases are exhaustively validated above
            raise ValueError(f"unimplemented Liuren dimension: {canonical}")
        expected_outputs = set(profile.get("deterministic_outputs") or ())
        if set(projected) != expected_outputs:
            raise ValueError(f"Liuren dimension source contract mismatch: {canonical}")
        source_rule_ids = _activated_dimension_rule_ids(
            canonical=canonical,
            eligible_rule_ids=[
                str(rule_id) for rule_id in (profile.get("eligible_rule_ids") or ())
            ],
            projected=projected,
            output=output,
            transmissions_to_day=transmissions_to_day,
            initial_final=initial_final,
            stage_flow=stage_flow,
        )
        rule_evidence = _liuren_rule_evidence(
            canonical,
            projected=projected,
            transmissions=transmissions,
        )
        dimension_facts[requested] = {
            **base,
            "source_rule_ids": source_rule_ids,
            "rule_evidence": rule_evidence,
            **copy.deepcopy(projected),
        }

    dependency_ids = tuple(
        dict.fromkeys(
            dependency
            for _, canonical in canonical_requested
            for dependency in LIUREN_DIMENSION_DEPENDENCIES[canonical]
        )
    )
    result: dict[str, Any] = {
        "dimension_facts": dimension_facts,
        "rule_traces": [
            {
                "source_dependency_id": dependency,
                "role": "deterministic_dimension_projection_without_event_verdict",
            }
            for dependency in dependency_ids
        ],
    }
    timing_requested = any(
        canonical == "timing" for _, canonical in canonical_requested
    )
    if timing_requested:
        result["timing"] = timing
        result["runtime_core_facts"] = build_runtime_core_facts(
            output,
            dimension_facts,
            timing_candidates=timing["candidates"],
        )
    else:
        result["runtime_core_facts"] = build_runtime_core_facts(
            output,
            dimension_facts,
        )
    return result


def _run_adapter(
    skill_dir: Path,
    args: argparse.Namespace,
    question: str,
    civil_datetime: str,
) -> dict[str, Any]:
    command = [
        *runtime_command(),
        str(skill_dir / "scripts" / "liuren_fact_adapter.py"),
        "cast",
        "--datetime",
        civil_datetime,
        "--timezone",
        args.timezone,
        "--location",
        args.location,
        "--question",
        question,
        "--guiren-profile",
        args.guiren_profile,
        "--day-night-profile",
        args.day_night_profile,
        "--zi-hour-policy",
        args.zi_hour_policy,
        "--biezhe-profile",
        args.biezhe_profile,
        "--time-basis-policy",
        str(getattr(args, "time_basis_policy", None) or "civil"),
    ]
    if getattr(args, "longitude", None) is not None:
        command.extend(["--longitude", str(args.longitude)])
    if getattr(args, "latitude", None) is not None:
        command.extend(["--latitude", str(args.latitude)])
    if getattr(args, "coordinate_source", None):
        command.extend(["--coordinate-source", str(args.coordinate_source)])
    if getattr(args, "coordinate_accuracy_meters", None) is not None:
        command.extend(["--coordinate-accuracy-meters", str(args.coordinate_accuracy_meters)])
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Da Liu Ren adapter failed")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Da Liu Ren adapter returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Da Liu Ren adapter returned a non-object")
    return payload


def _import_skill_module(skill_dir: Path, name: str) -> Any:
    scripts_dir = str(skill_dir / "scripts")
    sys.path.insert(0, scripts_dir)
    try:
        return importlib.import_module(name)
    finally:
        try:
            sys.path.remove(scripts_dir)
        except ValueError:
            pass


def _validate_facts(skill_dir: Path, facts: dict[str, Any]) -> None:
    module = _import_skill_module(skill_dir, "adapter_validate")
    result = module.validate_payload("liuren", facts)
    if not result.get("ok"):
        codes = ", ".join(result.get("codes") or ["unknown_validation_error"])
        raise RuntimeError("Da Liu Ren fact validation failed: " + codes)



def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    question = parser.add_mutually_exclusive_group(required=True)
    question.add_argument("--question")
    question.add_argument("--question-file")
    parser.add_argument("--datetime", default="now", dest="civil_datetime")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--location", default=DEFAULT_CIVIL_CHINA_LOCATION)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--coordinate-source")
    parser.add_argument("--coordinate-accuracy-meters", type=float)
    parser.add_argument("--guiren-profile", default="official-corrected")
    parser.add_argument("--day-night-profile", default="civil-double-hour")
    parser.add_argument("--zi-hour-policy", default="midnight")
    parser.add_argument("--biezhe-profile", default="daliuren-daquan-body-branch")
    parser.add_argument("--time-basis-policy", default="civil")
    parser.add_argument("--output")
    return parser


def _read_question(args: argparse.Namespace) -> str:
    question = args.question
    if args.question_file:
        question = Path(args.question_file).read_text(encoding="utf-8")
    question = (question or "").strip()
    if not question:
        raise RuntimeError("question must not be blank")
    if len(question) > MAX_QUERY_CHARS:
        raise RuntimeError(f"question is too long; maximum is {MAX_QUERY_CHARS} chars")
    return question


def _validate_inputs(args: argparse.Namespace) -> None:
    args.location = (args.location or "").strip()
    if not args.location:
        raise RuntimeError("location must not be blank")
    if len(args.location) > MAX_LOCATION_CHARS:
        raise RuntimeError(f"location is too long; maximum is {MAX_LOCATION_CHARS} chars")
    allowed = {
        "guiren_profile": {"official-corrected", "traditional-uncorrected"},
        "day_night_profile": {"civil-double-hour"},
        "zi_hour_policy": {"midnight", "late-zi-next-day"},
        "biezhe_profile": {
            "daliuren-daquan-body-branch",
            "wyg-stem-lodge-upper",
        },
    }
    for field, choices in allowed.items():
        value = getattr(args, field)
        if value not in choices:
            raise RuntimeError(f"invalid --{field.replace('_', '-')}: {value}")


def main() -> int:
    args = _parser().parse_args()
    try:
        question = _read_question(args)
        _validate_inputs(args)
        civil_datetime = _resolve_datetime(args.civil_datetime, args.timezone)
        skill_dir = _find_skill_dir()
        facts = _run_adapter(skill_dir, args, question, civil_datetime)
        _validate_facts(skill_dir, facts)
        rendered = json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
