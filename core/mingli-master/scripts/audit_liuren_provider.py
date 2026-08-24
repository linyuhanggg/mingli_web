#!/usr/bin/env python3
"""Machine-readable Task 7H completeness audit for deterministic Daliuren."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

import audit_algorithm_sources
from audit_provider_preflight import provider_preflight_failure
import adapter_validate
import build_evidence_index
import liuren_calc
import liuren_fact_adapter
from reading_engine import calendar_core
from reading_engine.contracts import ReadingRequest, canonical_digest
from reading_engine.providers import PROVIDER_CAPABILITIES, LiurenProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "liuren-v51.yaml"
MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
SOURCE_TABLE = ROOT / "references" / "matrices" / "liuren-source-tables-v1.yaml"
SOURCE_SAMPLES = ROOT / "references" / "fixtures" / "algorithm-source-samples-v51.yaml"
EXPECTED_FIXTURE_SHA256 = (
    "791640f102d54c857e64a33bc405135125a7a20fb1959f90f1c7c489c3d69960"
)
EXPECTED_PROVIDER_ID = "mingli-master.liuren.v8"
EXPECTED_PROVIDER_VERSION = "mingli-liuren-pipeline-v6-runtime-contract"
SHARED_CALENDAR_DEPENDENCY_ID = "liuren.calendar.shared-sxtwl-four-pillars"
SHARED_CALENDAR_DEPENDENCY_VERSION = (
    "sxtwl-2.0.7/exact-jie-boundary-v1.2/"
    "east-asian-civil-jieqi-v1@1.0.2/five-rat-strict"
)
LINE_ANCHOR_RE = re.compile(r"^L(?P<start>\d+)(?:-L(?P<end>\d+))?$")
REQUIRED_PRIMARY_METHODS = {
    "元首", "重审", "比用", "涉害", "遥克", "昴星", "别责", "八专", "伏吟", "反吟",
}
REQUIRED_SOURCE_LABELS = {
    "见机", "察微", "缀瑕", "蒿矢", "弹射", "虎视", "自任", "自信", "杜传", "井栏射",
}
REQUIRED_DIMENSIONS = {
    "outcome", "timing", "state", "location", "relationship", "work", "money",
}
REQUIRED_EVIDENCE_ROLES = {
    "casting_rule", "imagery_correspondence", "issue_specific_judgment_rule", "timing_rule",
}
EXPECTED_TERM_TO_MONTH_GENERAL = {
    "雨水": "亥", "惊蛰": "亥", "春分": "戌", "清明": "戌",
    "谷雨": "酉", "立夏": "酉", "小满": "申", "芒种": "申",
    "夏至": "未", "小暑": "未", "大暑": "午", "立秋": "午",
    "处暑": "巳", "白露": "巳", "秋分": "辰", "寒露": "辰",
    "霜降": "卯", "立冬": "卯", "小雪": "寅", "大雪": "寅",
    "冬至": "丑", "小寒": "丑", "大寒": "子", "立春": "子",
}
EXPECTED_SOLAR_TERM_CYCLE = (
    "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满",
    "芒种", "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至", "小寒", "大寒",
)
EXPECTED_MONTH_GENERAL_TRANSITIONS = (
    ("雨水", "亥", "雨水前日卯初刻，太陽入衛用登明亥。"),
    ("春分", "戌", "春分後二巳一刻，入魯河魁作將明戌。"),
    ("谷雨", "酉", "穀雨後四亥初刻，入趙從魁用可稱酉。"),
    ("小满", "申", "小滿後五酉三刻，入晉還須傳送興申。"),
    ("夏至", "未", "夏至後四未一刻，入秦小吉用其名未。"),
    ("大暑", "午", "大暑後三巳一亥，入周先用勝光靈午。"),
    ("处暑", "巳", "處暑後三巳二刻，入楚還當太乙迎巳。"),
    ("秋分", "辰", "秋分後七寅三刻，入鄭天罡用去亨辰。"),
    ("霜降", "卯", "霜降後九醜三刻，太衝運動宋州城卯。"),
    ("小雪", "寅", "小雪後七戌一刻，功曹將領入燕京寅。"),
    ("冬至", "丑", "冬至後四刻一刻，入吳大吉便休停醜。"),
    ("大寒", "子", "大寒當日酉三刻，入齊神後歲功成子。"),
)


def _finding(findings: list[str], condition: bool, message: str) -> None:
    if not condition:
        findings.append(message)


def _month_general_oracle_ready(
    *,
    source_table: dict[str, Any],
    research_root: Path | None,
) -> bool:
    """Bind the 24-term runtime oracle to a fixed classical source excerpt.

    This is a release-time source verification: without an explicit research
    root there is no fulltext to bind against, so it reports not-ready rather
    than raising.
    """

    if research_root is None:
        return False
    contract = source_table.get("month_general_solar_term_mapping")
    profiles = source_table.get("source_profiles")
    if not isinstance(contract, dict) or not isinstance(profiles, dict):
        return False
    profile = profiles.get(str(contract.get("source_profile") or ""))
    mapping = contract.get("terms")
    transitions = contract.get("source_transitions")
    if (
        not isinstance(profile, dict)
        or not isinstance(mapping, dict)
        or not isinstance(transitions, dict)
    ):
        return False
    expected_transitions = {
        term: phrase for term, _branch, phrase in EXPECTED_MONTH_GENERAL_TRANSITIONS
    }
    if transitions != expected_transitions:
        return False
    if liuren_fact_adapter.TERM_TO_MONTH_GENERAL != EXPECTED_TERM_TO_MONTH_GENERAL:
        return False
    anchor = str(contract.get("source_anchor") or "")
    anchors = profile.get("anchors")
    if not isinstance(anchors, dict) or anchors.get("month_general_cycle") != anchor:
        return False
    source_path = research_root / str(profile.get("normalized_path") or "")
    try:
        if not source_path.is_file() or _sha256(source_path) != profile.get("sha256"):
            return False
        excerpt = _source_slice(source_path.read_text(encoding="utf-8"), anchor)
    except (OSError, UnicodeError, ValueError):
        return False
    excerpt_digest = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    if excerpt_digest != contract.get("source_excerpt_sha256"):
        return False
    if not all(phrase in excerpt for phrase in expected_transitions.values()):
        return False
    derived_mapping: dict[str, str] = {}
    for term, branch, _phrase in EXPECTED_MONTH_GENERAL_TRANSITIONS:
        index = EXPECTED_SOLAR_TERM_CYCLE.index(term)
        derived_mapping[term] = branch
        derived_mapping[EXPECTED_SOLAR_TERM_CYCLE[(index + 1) % 24]] = branch
    return mapping == derived_mapping == EXPECTED_TERM_TO_MONTH_GENERAL


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_slice(text: str, anchor: str) -> str:
    match = LINE_ANCHOR_RE.fullmatch(anchor)
    if match is None:
        raise ValueError(f"invalid Liuren source anchor: {anchor}")
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    lines = text.splitlines()
    if start < 1 or end < start or end > len(lines):
        raise ValueError(f"Liuren source anchor out of range: {anchor}")
    return "\n".join(lines[start - 1 : end])


def _lessons(output: dict[str, Any]) -> list[list[str]]:
    return [[str(row["upper"]), str(row["lower"])] for row in output["four_lessons"]]


def _transmissions(output: dict[str, Any]) -> str:
    return "".join(str(row["branch"]) for row in output["three_transmissions"])


def _anchor_supports_transmissions(anchored: str, expected: str) -> bool:
    compact = "".join(anchored.split())
    if expected in compact:
        return True
    heads: list[str] = []
    for line in anchored.splitlines()[1:]:
        normalized = "".join(line.split())
        if not normalized or normalized[0] not in liuren_fact_adapter.BRANCHES:
            continue
        # Transmission rows contain one branch plus its heavenly general. Four-
        # lesson and plate rows contain several branches and are excluded here.
        if sum(character in liuren_fact_adapter.BRANCHES for character in normalized) != 1:
            continue
        heads.append(normalized[0])
        if len(heads) == 3:
            break
    return "".join(heads) == expected


def _source_complete_plate(anchored: str) -> dict[str, Any]:
    stems = re.escape(liuren_fact_adapter.STEMS)
    branches = re.escape(liuren_fact_adapter.BRANCHES)
    header = re.search(
        rf"(?P<day>[{stems}][{branches}])日"
        rf"(?P<hour>[{branches}])[时時]"
        rf"(?P<general>[{branches}])[将將]",
        anchored,
    )
    if header is None:
        raise ValueError("complete Liuren source plate has no cast header")

    lines = anchored.splitlines()
    transmission_rows: list[str] = []
    transmission_end = -1
    for index, line in enumerate(lines):
        normalized = "".join(line.split())
        source_symbols = re.findall(rf"[{stems}{branches}]", normalized)
        if (
            normalized
            and normalized[0] in liuren_fact_adapter.BRANCHES
            and len(source_symbols) == 1
        ):
            transmission_rows.append(source_symbols[0])
            if len(transmission_rows) == 3:
                transmission_end = index
                break
    if len(transmission_rows) != 3:
        raise ValueError("complete Liuren source plate has no three transmissions")

    upper_row: list[str] | None = None
    lower_row: list[str] | None = None
    day_stem = header.group("day")[0]
    for line in lines[transmission_end + 1 :]:
        source_symbols = re.findall(rf"[{stems}{branches}]", line)
        if len(source_symbols) != 4:
            continue
        if upper_row is None:
            upper_row = source_symbols
            continue
        if source_symbols[-1] == day_stem:
            lower_row = source_symbols
            break
    if upper_row is None or lower_row is None:
        raise ValueError("complete Liuren source plate has no four-lesson diagram")
    four_lessons = [
        [upper, lower]
        for upper, lower in reversed(list(zip(upper_row, lower_row)))
    ]
    return {
        "day": header.group("day"),
        "hour_branch": header.group("hour"),
        "month_general": header.group("general"),
        "transmissions": "".join(transmission_rows),
        "four_lessons": four_lessons,
    }


def _provider_datetime_for_classical_input(
    supplied: dict[str, Any],
) -> str:
    """Find a real civil instant with the fixture's day/hour/general tuple."""

    day_ganzhi = str(supplied["day"])
    hour_ganzhi = str(supplied["hour"])
    month_general = str(supplied["month_general"])
    hour_branch = hour_ganzhi[1]
    local_hour = liuren_fact_adapter.BRANCHES.index(hour_branch) * 2
    start = datetime(2000, 1, 1, local_hour, 0, 0)
    first_matching_day: datetime | None = None
    for offset in range(60):
        candidate = start + timedelta(days=offset)
        calendar = calendar_core.normalize_calendar(
            candidate.isoformat(timespec="seconds"),
            timezone_name="Asia/Shanghai",
            location="上海",
            zi_hour_policy="midnight",
        )
        ganzhi = calendar.get("ganzhi") or {}
        if ganzhi.get("day") == day_ganzhi and ganzhi.get("hour") == hour_ganzhi:
            first_matching_day = candidate
            break
    if first_matching_day is None:
        raise ValueError(
            f"classical day/hour tuple is not calendar-valid: {day_ganzhi}/{hour_ganzhi}"
        )

    for cycle in range(220):
        candidate = first_matching_day + timedelta(days=60 * cycle)
        calendar = calendar_core.normalize_calendar(
            candidate.isoformat(timespec="seconds"),
            timezone_name="Asia/Shanghai",
            location="上海",
            zi_hour_policy="midnight",
        )
        previous_term = (calendar.get("solar_terms") or {}).get("previous") or {}
        active_general = liuren_fact_adapter.TERM_TO_MONTH_GENERAL.get(
            str(previous_term.get("name") or "")
        )
        if active_general == month_general:
            return candidate.isoformat(timespec="seconds")
    raise ValueError(
        "no real civil instant realizes classical tuple: "
        f"{day_ganzhi}/{hour_ganzhi}/{month_general}"
    )


def audit_liuren_provider(
    *, fixture_path: Path = FIXTURE, research_root: Path | None = None
) -> dict[str, Any]:
    preflight = provider_preflight_failure(
        system="liuren",
        schema_version="mingli-liuren-completeness-audit-v1",
        provider_class=LiurenProvider,
        expected_mode="calculation",
        expected_provider_id=EXPECTED_PROVIDER_ID,
        expected_provider_version=EXPECTED_PROVIDER_VERSION,
    )
    if preflight is not None:
        return preflight
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    matrix = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    source_table = yaml.safe_load(SOURCE_TABLE.read_text(encoding="utf-8"))
    source_samples = yaml.safe_load(SOURCE_SAMPLES.read_text(encoding="utf-8"))["cases"]
    cases = list(fixture.get("classical_cases") or ())
    boundaries = list(fixture.get("calendar_boundaries") or ())
    findings: list[str] = []
    liuren_dependencies = {
        str(row.get("id") or ""): row
        for row in ((matrix.get("providers") or {}).get("liuren") or {}).get(
            "dependencies", ()
        )
        if isinstance(row, dict)
    }
    calendar_dependency = liuren_dependencies.get(
        SHARED_CALENDAR_DEPENDENCY_ID
    ) or {}
    live_calendar_dependencies = {
        dependency.id: dependency.version
        for dependency in PROVIDER_CAPABILITIES["liuren"].algorithm_dependencies
    }
    runtime_binding = calendar_dependency.get("runtime_binding") or {}
    _finding(
        findings,
        bool(calendar_dependency),
        "Liuren shared calendar dependency manifest declaration missing",
    )
    _finding(
        findings,
        live_calendar_dependencies.get(SHARED_CALENDAR_DEPENDENCY_ID)
        == SHARED_CALENDAR_DEPENDENCY_VERSION,
        "Liuren live shared calendar dependency declaration missing",
    )
    _finding(
        findings,
        calendar_dependency.get("version") == SHARED_CALENDAR_DEPENDENCY_VERSION,
        "Liuren shared calendar dependency version drift",
    )
    _finding(
        findings,
        runtime_binding.get("calendar_algorithm_version")
        == calendar_core.ALGORITHM_VERSION,
        "Liuren shared calendar algorithm identity drift",
    )
    _finding(
        findings,
        runtime_binding.get("calendar_convention_id")
        == calendar_core.CONVENTION_ID
        and str(runtime_binding.get("calendar_convention_version"))
        == calendar_core.CONVENTION_VERSION,
        "Liuren shared calendar convention identity drift",
    )
    runtime_engine_version = importlib.metadata.version("sxtwl")
    _finding(
        findings,
        runtime_binding.get("engine") == "sxtwl"
        and str(runtime_binding.get("engine_version"))
        == runtime_engine_version
        == calendar_core.ENGINE_VERSION,
        "Liuren shared calendar engine identity drift",
    )
    _finding(
        findings,
        set(runtime_binding.get("zi_hour_policies") or ())
        == calendar_core.ZI_HOUR_POLICIES
        and runtime_binding.get("hour_stem_rule") == "five-rat-strict",
        "Liuren shared calendar Zi-hour/five-rat declaration drift",
    )
    five_rat_known_answers: dict[str, dict[str, str]] = {}
    for zi_hour_policy in sorted(calendar_core.ZI_HOUR_POLICIES):
        known_calendar = calendar_core.normalize_calendar(
            "2024-01-15T23:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            zi_hour_policy=zi_hour_policy,
        )
        known_ganzhi = known_calendar["ganzhi"]
        five_rat_known_answers[zi_hour_policy] = {
            "day": str(known_ganzhi["day"]),
            "hour": str(known_ganzhi["hour"]),
        }
    _finding(
        findings,
        five_rat_known_answers
        == {
            "midnight": {"day": "戊寅", "hour": "壬子"},
            "late-zi-next-day": {"day": "己卯", "hour": "甲子"},
        },
        "Liuren shared calendar five-rat known answer drift",
    )
    calendar_identity = {
        "dependency_id": SHARED_CALENDAR_DEPENDENCY_ID,
        "algorithm_version": calendar_core.ALGORITHM_VERSION,
        "convention_id": calendar_core.CONVENTION_ID,
        "convention_version": calendar_core.CONVENTION_VERSION,
        "engine": "sxtwl",
        "engine_version": runtime_engine_version,
        "zi_hour_policies": sorted(calendar_core.ZI_HOUR_POLICIES),
        "five_rat_known_answers": five_rat_known_answers,
    }
    fixture_sha256 = _sha256(fixture_path)
    _finding(
        findings,
        LiurenProvider.provider_id == EXPECTED_PROVIDER_ID
        and LiurenProvider.provider_version == EXPECTED_PROVIDER_VERSION,
        "Liuren provider identity drift",
    )
    _finding(
        findings,
        fixture_sha256 == EXPECTED_FIXTURE_SHA256,
        "Liuren fixture artifact hash mismatch",
    )
    _finding(
        findings,
        PROVIDER_CAPABILITIES["liuren"].mode == "calculation",
        "Liuren provider capability mode is not calculation",
    )

    imagery_contract = source_table["structured_excerpt_indexes"][
        "general_landing_imagery"
    ]
    imagery_path = ROOT / str(imagery_contract["path"])
    imagery_payload = json.loads(imagery_path.read_text(encoding="utf-8"))
    imagery_pairs = {
        f"{general}/{branch}"
        for general, profile in imagery_payload["generals"].items()
        for branch in (profile.get("by_branch") or {})
    }
    all_imagery_pairs = {
        f"{general}/{branch}"
        for general in liuren_fact_adapter.HEAVENLY_GENERAL_ORDER
        for branch in liuren_fact_adapter.BRANCHES
    }
    missing_imagery_pairs = all_imagery_pairs - imagery_pairs

    _finding(findings, fixture.get("schema_version") == "mingli-liuren-fixtures-v51", "unexpected fixture schema")
    _finding(findings, len(cases) >= 30, "fixture requires at least 30 classical/reference cases")
    _finding(findings, len(cases) == len({case.get("id") for case in cases}), "classical case ids are not unique")
    _finding(findings, len(boundaries) >= 8, "fixture requires at least eight calendar boundaries")
    _finding(
        findings,
        _sha256(imagery_path) == imagery_contract["sha256"],
        "Liuren imagery index hash mismatch",
    )
    _finding(
        findings,
        len(imagery_pairs) == imagery_contract["exact_pair_count"],
        "Liuren imagery exact-pair count mismatch",
    )
    _finding(
        findings,
        missing_imagery_pairs == set(imagery_contract["missing_exact_pairs"]),
        "Liuren imagery missing-pair declaration mismatch",
    )
    categories = Counter(str(case.get("category") or "") for case in boundaries)
    for category, minimum in {"solar_term_boundary": 2, "day_rollover": 2, "leap_month": 1, "timezone_boundary": 2}.items():
        _finding(findings, categories[category] >= minimum, f"calendar boundary category {category} requires {minimum} cases")

    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(matrix, ROOT)
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    source_identity = dict(fixture.get("source") or {})
    source_text = ""
    if resolved_research_root is not None:
        source_path = resolved_research_root / str(source_identity.get("path") or "")
        try:
            _finding(
                source_verification.setdefault("findings", []),
                source_path.is_file(),
                "Liuren normalized source is missing",
            )
            if source_path.is_file():
                _finding(
                    source_verification.setdefault("findings", []),
                    _sha256(source_path) == source_identity.get("sha256"),
                    "Liuren normalized source hash mismatch",
                )
                source_text = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            source_verification.setdefault("findings", []).append(
                f"Liuren normalized source failed: {exc}"
            )

    observed_methods: set[str] = set()
    observed_labels: set[str] = set()
    complete_plates = 0
    complete_plate_ids: set[str] = set()
    qualifying_cases = 0
    provider_calculations = 0
    provider_extensions = 0
    determinism_checks = 0
    executed_horizons: set[str] = set()
    resolved_datetimes: dict[tuple[str, str, str], str] = {}
    for case_index, case in enumerate(cases):
        identifier = str(case.get("id") or "")
        case_finding_start = len(findings)
        try:
            expected = case["expected"]
            supplied = case["input"]
            source_plate = None
            if resolved_research_root is not None and source_text:
                # Source-anchor verification is a release-time gate: it runs
                # only when an explicit research root supplies the fulltext.
                anchored = _source_slice(source_text, str(case["source_anchor"]))
                source_verification_findings = source_verification.setdefault(
                    "findings", []
                )
                _finding(
                    source_verification_findings,
                    str(supplied["day"]) in anchored,
                    f"source anchor omits day: {identifier}",
                )
                _finding(
                    source_verification_findings,
                    str(expected["source_method_label"]) in anchored,
                    f"source anchor omits method label: {identifier}",
                )
                _finding(
                    source_verification_findings,
                    _anchor_supports_transmissions(
                        anchored, str(expected["transmissions"])
                    ),
                    f"source anchor omits transmissions: {identifier}",
                )
                if expected.get("four_lessons"):
                    source_plate = _source_complete_plate(anchored)
                    _finding(
                        source_verification_findings,
                        source_plate["day"] == supplied["day"]
                        and source_plate["hour_branch"]
                        == str(supplied["hour"])[1]
                        and source_plate["month_general"]
                        == supplied["month_general"],
                        f"source-derived cast input mismatch: {identifier}",
                    )
                    _finding(
                        source_verification_findings,
                        source_plate["transmissions"]
                        == expected["transmissions"],
                        f"source-derived transmissions mismatch: {identifier}",
                    )
                    _finding(
                        source_verification_findings,
                        source_plate["four_lessons"]
                        == expected["four_lessons"],
                        f"source-derived four-lessons mismatch: {identifier}",
                    )
            facts = liuren_fact_adapter.build_from_chart(
                day_ganzhi=str(supplied["day"]),
                hour_ganzhi=str(supplied["hour"]),
                month_general=str(supplied["month_general"]),
                question="fixture",
                location="fixture",
            )
            output = facts["output"]
            method = str(output["transmission_method"]["primary"])
            observed_methods.add(method)
            observed_labels.add(str(expected["source_method_label"]))
            _finding(findings, method == expected["primary_method"], f"method mismatch: {identifier}")
            _finding(findings, _transmissions(output) == expected["transmissions"], f"transmission mismatch: {identifier}")
            if expected.get("four_lessons"):
                complete_plates += 1
                complete_plate_ids.add(identifier)
                _finding(findings, _lessons(output) == expected["four_lessons"], f"four-lessons mismatch: {identifier}")
                if resolved_research_root is not None:
                    _finding(
                        source_verification.setdefault("findings", []),
                        source_plate is not None
                        and _lessons(output) == source_plate["four_lessons"],
                        f"provider four-lessons disagree with source: {identifier}",
                    )
            if expected.get("documented_label_variant"):
                variants = output["transmission_method"].get("source_label_variants") or []
                _finding(
                    findings,
                    any(row.get("source_label") == expected["source_method_label"] for row in variants if isinstance(row, dict)),
                    f"source-label variant not retained: {identifier}",
                )

            input_key = (
                str(supplied["day"]),
                str(supplied["hour"]),
                str(supplied["month_general"]),
            )
            event_datetime = resolved_datetimes.get(input_key)
            if event_datetime is None:
                event_datetime = _provider_datetime_for_classical_input(supplied)
                resolved_datetimes[input_key] = event_datetime
            request = ReadingRequest(
                query=f"Task 7N Liuren provider replay {identifier}",
                action="new",
                system="liuren",
                event_datetime=event_datetime,
                timezone="Asia/Shanghai",
                location="上海",
            )
            first = LiurenProvider(ROOT).calculate(request)
            second = LiurenProvider(ROOT).calculate(request)
            provider_calculations += 2
            for result in (first, second):
                if (
                    result.system != "liuren"
                    or result.provider_id != LiurenProvider.provider_id
                    or result.provider_version != LiurenProvider.provider_version
                ):
                    raise ValueError("live provider identity mismatch")
                live_facts = result.facts["chart_facts"]
                live_output = live_facts["output"]
                live_calendar = live_facts["calendar_normalization"]
                if (
                    live_calendar["ganzhi"]["day"] != supplied["day"]
                    or live_calendar["ganzhi"]["hour"] != supplied["hour"]
                    or live_output["month_general"]["branch"]
                    != supplied["month_general"]
                    or live_output["transmission_method"]["primary"]
                    != expected["primary_method"]
                    or _transmissions(live_output) != expected["transmissions"]
                    or (
                        bool(expected.get("four_lessons"))
                        and _lessons(live_output) != expected["four_lessons"]
                    )
                ):
                    raise ValueError("live provider result differs from classical oracle")
            if (
                first.result_hash != second.result_hash
                or first.input_hash != second.input_hash
                or canonical_digest(first.facts) != canonical_digest(second.facts)
            ):
                raise ValueError("live provider calculation is nondeterministic")
            determinism_checks += 1

            horizon_kind = PROVIDER_CAPABILITIES["liuren"].horizons[
                case_index % len(PROVIDER_CAPABILITIES["liuren"].horizons)
            ]
            executed_horizons.add(horizon_kind)
            horizon = {"kind": horizon_kind}
            if horizon_kind != "instant":
                civil_date = event_datetime[:10]
                bound = {
                    "day": civil_date,
                    "month": civil_date[:7],
                    "year": civil_date[:4],
                }[horizon_kind]
                horizon.update({"start": bound, "end": bound})
            dimensions = tuple(PROVIDER_CAPABILITIES["liuren"].dimensions)
            first_extended = LiurenProvider(ROOT).extend(
                first, dimensions, horizon
            )
            second_extended = LiurenProvider(ROOT).extend(
                second, dimensions, horizon
            )
            provider_extensions += 2
            first_extension = first_extended.fact_extension
            second_extension = second_extended.fact_extension
            if (
                first_extension is None
                or second_extension is None
                or first_extension.status != "complete"
                or second_extension.status != "complete"
                or first_extension.extension_digest
                != second_extension.extension_digest
                or canonical_digest(first_extension.facts)
                != canonical_digest(second_extension.facts)
            ):
                raise ValueError("live provider extension is incomplete or nondeterministic")
            determinism_checks += 1
            if len(findings) == case_finding_start:
                qualifying_cases += 1
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"classical case failed: {identifier}: {exc}")
    _finding(findings, REQUIRED_PRIMARY_METHODS <= observed_methods, "classical cases do not cover every primary method")
    _finding(findings, REQUIRED_SOURCE_LABELS <= observed_labels, "classical cases do not cover every required special method label")
    declared_complete_plate_ids = {
        str(identifier)
        for identifier in (source_table.get("complete_source_plate_ids") or ())
    }
    _finding(
        findings,
        complete_plate_ids == declared_complete_plate_ids,
        "complete source plate id set mismatch",
    )

    seen_variant_inputs: set[tuple[str, str, str]] = set()
    for variant in source_table.get("method_label_variants") or ():
        variant_input = variant.get("input") or {}
        key = (
            str(variant_input.get("day") or ""),
            str(variant_input.get("hour_branch") or ""),
            str(variant_input.get("month_general") or ""),
        )
        _finding(
            findings,
            key not in seen_variant_inputs,
            f"duplicate method-label variant input: {'/'.join(key)}",
        )
        seen_variant_inputs.add(key)
        matches = [
            case
            for case in cases
            if str((case.get("input") or {}).get("day") or "") == key[0]
            and str((case.get("input") or {}).get("hour") or "")[1:2] == key[1]
            and str((case.get("input") or {}).get("month_general") or "") == key[2]
        ]
        identifier = str(matches[0].get("id") or "") if len(matches) == 1 else "/".join(key)
        _finding(
            findings,
            len(matches) == 1,
            f"method-label variant fixture match mismatch: {identifier}",
        )
        if len(matches) != 1:
            continue
        case = matches[0]
        expected = case.get("expected") or {}
        expected_anchor = (
            "daliuren-daquan "
            + str(case.get("source_anchor") or "").split("-", 1)[0]
        )
        anchored = ""
        if resolved_research_root is not None and source_text:
            anchored = _source_slice(
                source_text, str(case.get("source_anchor") or "")
            )
        facts = liuren_fact_adapter.build_from_chart(
            day_ganzhi=str((case.get("input") or {})["day"]),
            hour_ganzhi=str((case.get("input") or {})["hour"]),
            month_general=str((case.get("input") or {})["month_general"]),
            question="fixture",
            location="fixture",
        )
        method = facts["output"]["transmission_method"]
        _finding(
            findings,
            variant.get("calculated_label") == method.get("primary") == expected.get("primary_method"),
            f"method-label variant calculated label mismatch: {identifier}",
        )
        if resolved_research_root is not None:
            source_verification_findings = source_verification.setdefault(
                "findings", []
            )
            _finding(
                source_verification_findings,
                variant.get("source_label") == expected.get("source_method_label")
                and str(variant.get("source_label") or "") in anchored,
                f"method-label variant source label mismatch: {identifier}",
            )
            _finding(
                source_verification_findings,
                variant.get("source_anchor") == expected_anchor,
                f"method-label variant source anchor mismatch: {identifier}",
            )
        _finding(
            findings,
            variant.get("transmissions") == expected.get("transmissions") == _transmissions(facts["output"]),
            f"method-label variant transmissions mismatch: {identifier}",
        )
        runtime_variants = method.get("source_label_variants") or ()
        _finding(
            findings,
            any(
                isinstance(row, dict)
                and all(
                    row.get(field) == variant.get(field)
                    for field in (
                        "source_label",
                        "calculated_label",
                        "transmissions",
                        "source_anchor",
                        "resolution",
                    )
                )
                for row in runtime_variants
            ),
            f"method-label variant runtime metadata mismatch: {identifier}",
        )

    classical_sample = source_samples["liuren-classical-method-source-plates"]
    _finding(
        findings,
        int(classical_sample["expected"]["case_count"]) == len(cases),
        "independent method sample case count diverges from fixture",
    )
    _finding(
        findings,
        set(classical_sample["expected"]["primary_methods"]) == observed_methods,
        "independent method sample primary methods diverge from provider coverage",
    )

    direction_sample = source_samples["liuren-branch-direction-correspondence"]
    expected_directions = [
        source_table["branch_directions"][str(branch)]["chinese"]
        for branch in direction_sample["input"]
    ]
    _finding(
        findings,
        expected_directions == direction_sample["expected"]["directions"],
        "independent branch-direction sample diverges from source table",
    )
    _finding(
        findings,
        direction_sample["expected"]["role"] == "symbolic_direction_candidate_only",
        "independent branch-direction sample lost its symbolic-only boundary",
    )

    relation_sample = source_samples["liuren-outcome-relation-projection"]
    relation_input = relation_sample["input"]
    expected_relation = liuren_calc._directed_element_relation(
        "day_stem",
        str(relation_input["day_stem"]),
        "day_branch",
        str(relation_input["day_branch"]),
    )
    transmission_relations = [
        liuren_calc._directed_element_relation(
            "transmission_branch",
            str(branch),
            "day_stem",
            str(relation_input["day_stem"]),
        )
        for branch in relation_input["transmissions"]
    ]
    _finding(
        findings,
        expected_relation["relation"] == relation_sample["expected"]["subject_object_relation"],
        "independent outcome relation sample diverges from directed provider relation",
    )
    _finding(
        findings,
        bool(transmission_relations) == relation_sample["expected"]["transmission_relations_are_separate"],
        "independent outcome sample does not preserve separate transmission relations",
    )
    _finding(
        findings,
        relation_sample["expected"]["target_relative_requires_caller_domain"] is True
        and relation_sample["expected"]["verdict"] == "none",
        "independent outcome sample lost its target/verdict stop conditions",
    )

    imagery_sample = source_samples["liuren-general-landing-correspondence"]
    imagery_input = imagery_sample["input"]
    imagery_row = liuren_calc._general_landing_correspondences(
        [
            {
                "stage": "initial",
                "branch": imagery_input["landing_branch"],
                "heavenly_general": imagery_input["heavenly_general"],
            }
        ]
    )[0]
    _finding(
        findings,
        imagery_row["source_text"] == imagery_sample["expected"]["source_text"],
        "independent general-landing source text diverges from structured index",
    )
    _finding(
        findings,
        imagery_row["source_rule"] == imagery_sample["expected"]["source_rule"]
        and imagery_row["role"] == imagery_sample["expected"]["role"],
        "independent general-landing role or rule diverges from provider",
    )

    boundary_provider_calculations = 0
    boundary_provider_determinism_checks = 0
    for case in boundaries:
        identifier = str(case.get("id") or "")
        try:
            facts = liuren_fact_adapter.build_from_datetime(
                str(case["datetime"]),
                timezone_name=str(case["timezone"]),
                location="fixture",
                question="fixture",
                zi_hour_policy=str(case["zi_hour_policy"]),
            )
            output = facts["output"]
            calendar = facts["calendar_normalization"]
            _finding(findings, [calendar["ganzhi"][key] for key in ("year", "month", "day", "hour")] == case["expected_pillars"], f"calendar pillars mismatch: {identifier}")
            _finding(findings, output["month_general"]["branch"] == case["expected_general"], f"month-general mismatch: {identifier}")
            _finding(findings, output["transmission_method"]["primary"] == case["expected_method"], f"boundary method mismatch: {identifier}")
            _finding(findings, _transmissions(output) == case["expected_transmissions"], f"boundary transmissions mismatch: {identifier}")
            request = ReadingRequest(
                query=f"Task 7N Liuren boundary replay {identifier}",
                action="new",
                system="liuren",
                event_datetime=str(case["datetime"]),
                timezone=str(case["timezone"]),
                location="fixture",
                metadata={"zi_hour_policy": str(case["zi_hour_policy"])},
            )
            first = LiurenProvider(ROOT).calculate(request)
            second = LiurenProvider(ROOT).calculate(request)
            boundary_provider_calculations += 2
            _finding(
                findings,
                first.input_hash == second.input_hash
                and first.result_hash == second.result_hash
                and canonical_digest(first.facts) == canonical_digest(second.facts),
                f"boundary provider replay is nondeterministic: {identifier}",
            )
            boundary_provider_determinism_checks += 1
            live_output = first.facts["chart_facts"]["output"]
            live_calendar = first.facts["chart_facts"]["calendar_normalization"]
            _finding(
                findings,
                [
                    live_calendar["ganzhi"][key]
                    for key in ("year", "month", "day", "hour")
                ]
                == case["expected_pillars"]
                and live_calendar["zi_hour_policy"] == case["zi_hour_policy"]
                and live_output["transmission_method"]["primary"]
                == case["expected_method"]
                and _transmissions(live_output) == case["expected_transmissions"],
                f"boundary provider result mismatch: {identifier}",
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"calendar boundary failed: {identifier}: {exc}")

    representative = liuren_fact_adapter.build_from_datetime(
        "2026-07-10T14:00:00",
        timezone_name="Asia/Shanghai",
        location="上海",
        question="fixture",
    )
    extension = liuren_calc.extend_liuren_facts(
        representative,
        requested_dimensions=tuple(sorted(REQUIRED_DIMENSIONS)),
        horizon={"kind": "day", "start": "2026-07-10", "end": "2026-07-31"},
    )
    dimension_facts = extension.get("dimension_facts") or {}
    _finding(findings, set(dimension_facts) == REQUIRED_DIMENSIONS, "provider does not expose all required dimensions")
    expected_outputs = source_table["dimension_profiles"]
    for dimension in REQUIRED_DIMENSIONS:
        expected_keys = set(expected_outputs[dimension]["deterministic_outputs"])
        actual = dimension_facts.get(dimension) or {}
        _finding(findings, expected_keys <= set(actual), f"dimension {dimension} omits deterministic outputs")
        _finding(findings, actual.get("status") == "calculated_facts_not_verdict", f"dimension {dimension} lacks non-verdict boundary")
    rendered_dimensions = {
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for value in dimension_facts.values()
    }
    _finding(findings, len(rendered_dimensions) == len(REQUIRED_DIMENSIONS), "dimension projections are identical clones")

    closure_source = liuren_fact_adapter.build_from_datetime(
        "2024-01-15T12:30:00",
        timezone_name="Asia/Shanghai",
        location="上海",
        question="calendar/month-general closure audit",
        zi_hour_policy="midnight",
    )
    actual_general = closure_source["output"]["month_general"]["branch"]
    wrong_general = "子" if actual_general != "子" else "丑"
    forged_general = liuren_fact_adapter.build_from_chart(
        day_ganzhi=closure_source["output"]["day_hour"]["day"],
        hour_ganzhi=closure_source["output"]["day_hour"]["hour"],
        month_general=wrong_general,
        question="calendar/month-general closure audit",
        location="上海",
    )
    for field in (
        "civil_datetime",
        "timezone",
        "zi_hour_policy",
        "longitude",
        "latitude",
        "coordinate_source",
    ):
        forged_general["input"][field] = closure_source["input"][field]
    forged_general["calendar_normalization"] = copy.deepcopy(
        closure_source["calendar_normalization"]
    )
    wrong_general_report = adapter_validate.validate_payload(
        "liuren", forged_general
    )
    forged_name = copy.deepcopy(closure_source)
    forged_name["output"]["month_general"]["name"] = "伪造月将名"
    wrong_name_report = adapter_validate.validate_payload("liuren", forged_name)
    forged_shape = liuren_fact_adapter.build_from_chart(
        day_ganzhi="己未",
        hour_ganzhi="庚午",
        month_general="亥",
        question="supplied shape closure audit",
        location="上海",
    )
    forged_shape["input"]["normalized_chart_input"]["year"] = "甲子"
    wrong_shape_report = adapter_validate.validate_payload("liuren", forged_shape)
    whitespace_payload = liuren_fact_adapter.build_from_datetime(
        "2024-01-15T12:30:00",
        timezone_name="Asia/Shanghai",
        location=" 上海 ",
        question="location normalization closure audit",
        zi_hour_policy="midnight",
    )
    whitespace_report = adapter_validate.validate_payload(
        "liuren", whitespace_payload
    )
    _finding(
        findings,
        "liuren_calendar_month_general_mismatch"
        in wrong_general_report["codes"]
        and "liuren_month_general_name_mismatch" in wrong_name_report["codes"]
        and "liuren_supplied_input_shape_mismatch" in wrong_shape_report["codes"]
        and whitespace_report["ok"] is True
        and whitespace_payload["input"]["location"] == "上海"
        and whitespace_payload["calendar_normalization"]["location"]["name"]
        == "上海",
        "calendar/month-general adversarial closure failed",
    )
    if resolved_research_root is not None:
        _finding(
            source_verification.setdefault("findings", []),
            _month_general_oracle_ready(
                source_table=source_table,
                research_root=resolved_research_root,
            ),
            "calendar/month-general oracle source binding failed",
        )
    calendar_month_general_closure_ready = (
        "liuren_calendar_month_general_mismatch"
        in wrong_general_report["codes"]
        and "liuren_month_general_name_mismatch" in wrong_name_report["codes"]
        and "liuren_supplied_input_shape_mismatch" in wrong_shape_report["codes"]
        and whitespace_report["ok"] is True
        and whitespace_payload["input"]["location"] == "上海"
        and whitespace_payload["calendar_normalization"]["location"]["name"]
        == "上海"
    )

    roles_by_pack = source_table["evidence_roles"]
    expected_role_by_rule: dict[tuple[str, str], str] = {}
    for pack, roles in roles_by_pack.items():
        for role, local_ids in roles.items():
            for local_id in local_ids:
                key = (pack, str(local_id))
                if key in expected_role_by_rule:
                    findings.append(f"source role duplicate: {pack}#{local_id}")
                expected_role_by_rule[key] = str(role)
    records = [record for record in build_evidence_index.compile_evidence_rules() if record["system"] == "liuren"]
    observed_roles: set[str] = set()
    for record in records:
        key = (str(record["source_pack"]), str(record["local_rule_id"]))
        expected_role = expected_role_by_rule.get(key)
        _finding(findings, expected_role is not None, f"Liuren rule is absent from evidence-role matrix: {record['rule_id']}")
        _finding(findings, record.get("evidence_role") == expected_role, f"Liuren evidence role mismatch: {record['rule_id']}")
        if record.get("evidence_role"):
            observed_roles.add(str(record["evidence_role"]))
    _finding(findings, observed_roles == REQUIRED_EVIDENCE_ROLES, "evidence index does not separate all four Liuren roles")
    _finding(
        findings,
        qualifying_cases >= 30,
        "live Liuren provider replay requires at least 30 qualifying cases",
    )
    _finding(
        findings,
        qualifying_cases == len(cases),
        "one or more route-owned Liuren cases did not qualify",
    )
    _finding(
        findings,
        provider_calculations == 2 * len(cases),
        "not every route-owned Liuren case ran through the provider twice",
    )
    _finding(
        findings,
        executed_horizons == set(PROVIDER_CAPABILITIES["liuren"].horizons),
        "live Liuren replay does not cover every declared horizon",
    )

    source_report = audit_algorithm_sources.audit_matrix(
        matrix,
        root=ROOT,
        systems=("liuren",),
    )
    findings.extend(f"source audit: {item}" for item in source_report["findings"])

    if resolved_research_root is not None:
        source_verification["ok"] = not source_verification.get("findings")
        source_verification["status"] = (
            "verified" if source_verification["ok"] else "failed"
        )

    return {
        "schema_version": "mingli-liuren-completeness-audit-v1",
        "system": "liuren",
        "status": "pass" if not findings else "fail",
        "provider_ready": not findings,
        "source_verification": source_verification,
        "provider": {
            "provider_id": LiurenProvider.provider_id,
            "provider_version": LiurenProvider.provider_version,
            "capability_mode": PROVIDER_CAPABILITIES["liuren"].mode,
        },
        "calendar_identity": calendar_identity,
        "calendar_month_general_closure_ready": (
            calendar_month_general_closure_ready
        ),
        "route_owned_case_ids": [str(case.get("id") or "") for case in cases],
        "fixture": {
            "path": str(fixture_path),
            "sha256": fixture_sha256,
            "expected_sha256": EXPECTED_FIXTURE_SHA256,
        },
        "fixture_sha256": fixture_sha256,
        "fixture_artifacts": {
            "route_fixture_sha256": fixture_sha256,
            "expected_route_fixture_sha256": EXPECTED_FIXTURE_SHA256,
            "qualifying_artifact_hashes": {
                "liuren_route_fixture": fixture_sha256,
            },
        },
        "counts": {
            "qualifying_cases": qualifying_cases,
            "route_owned_cases": len(cases),
            "provider_calculations": provider_calculations,
            "provider_extensions": provider_extensions,
            "determinism_checks": determinism_checks,
            "boundary_case_count": len(boundaries),
            "classical_cases": len(cases),
            "complete_source_plates": complete_plates,
            "calendar_boundaries": len(boundaries),
            "boundary_provider_calculations": boundary_provider_calculations,
            "boundary_provider_determinism_checks": (
                boundary_provider_determinism_checks
            ),
            "primary_methods": len(observed_methods),
            "special_source_labels": len(observed_labels & REQUIRED_SOURCE_LABELS),
            "dimensions": len(dimension_facts),
            "evidence_roles": len(observed_roles),
            "algorithm_dependencies": source_report["dependency_count"],
            "imagery_exact_pairs": len(imagery_pairs),
            "imagery_missing_pairs": len(missing_imagery_pairs),
        },
        "boundary_categories": sorted(
            (
                {str(case.get("category") or "") for case in boundaries}
                | {"classical_source_plate", *executed_horizons}
            )
            - {""}
        ),
        "source_table": {"path": SOURCE_TABLE.relative_to(ROOT).as_posix(), "sha256": _sha256(SOURCE_TABLE)},
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args()
    report = audit_liuren_provider(fixture_path=args.fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
