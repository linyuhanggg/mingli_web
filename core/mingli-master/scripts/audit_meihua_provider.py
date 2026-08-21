#!/usr/bin/env python3
"""Machine-readable Task 7G completeness audit for deterministic Meihua."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import yaml

import audit_algorithm_sources
from audit_provider_preflight import provider_preflight_failure
from reading_engine import calendar_core, meihua
from reading_engine.contracts import ReadingRequest
from reading_engine.providers import PROVIDER_CAPABILITIES, MeihuaProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "meihua-v51.yaml"
FIXTURE_SHA256 = "4d791d72356a7b4d63d7f4e4083726611dc1b845d3bb5ce78fdb6efe74ad9a25"
EXPECTED_PROVIDER_ID = "mingli-master.meihua.v1"
EXPECTED_PROVIDER_VERSION = "1.1.0"
MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
ANCHOR_RE = re.compile(r"L(?P<start>\d+)-L(?P<end>\d+)")
REQUIRED_CALENDAR_COUNTS = {
    "solar_term_boundary": 2,
    "day_rollover": 2,
    "leap_month": 1,
    "timezone_boundary": 2,
}
LIVE_REMAINDER_METHODS = {
    "trigram_remainder": "time",
    "moving_remainder": "observation",
}
CLASSICAL_TOTAL_PATTERNS = {
    "classical-guanmei": {
        "upper_total": r"共(?P<number>三十四)數",
        "lower_total": r"總得(?P<number>四十三)數",
        "moving_total": r"又上下總(?P<number>四十三)數",
    },
    "classical-mudan": {
        "upper_total": r"總得(?P<number>二十五)數",
        "lower_total": r"共得(?P<number>二十九)數",
        "moving_total": r"又以總計(?P<number>二十九)數",
    },
    "classical-knock-door": {
        "upper_total": r"以(?P<number>一)聲屬乾為上卦",
        "lower_total": r"以(?P<number>五)聲屬巽為下卦",
        "moving_total": r"共得(?P<number>十六)數",
    },
    "classical-today-motion": {
        "upper_total": r"共(?P<number>八)數，得坤為上卦",
        "lower_total": r"共(?P<number>五)數，得巽",
        "moving_total": r"八五總為(?P<number>十三)數",
    },
    "classical-xilin-sign": {
        "upper_total": r"以西字(?P<number>七)畫為艮",
        "lower_total": r"以林(?P<number>八)畫為坤",
        "moving_total": r"總(?P<number>十五)畫",
    },
    "classical-elder": {
        "upper_total": r"乾(?P<number>一)巽五之數",
        "lower_total": r"乾一巽(?P<number>五)之數",
        "moving_total": r"總(?P<number>十)數",
    },
    "classical-youth": {
        "upper_total": r"以艮(?P<number>七)離三",
        "lower_total": r"以艮七離(?P<number>三)",
        "moving_total": r"總(?P<number>十七)數",
    },
    "classical-cow": {
        "upper_total": r"坎六坤(?P<number>八)",
        "lower_total": r"坎(?P<number>六)坤八",
        "moving_total": r"共(?P<number>二十一)數",
    },
    "classical-chicken": {
        "upper_total": r"以巽(?P<number>五)乾一",
        "lower_total": r"以巽五乾(?P<number>一)",
        "moving_total": r"總(?P<number>十)數",
    },
    "classical-fallen-branch": {
        "upper_total": r"以兌二離(?P<number>三)",
        "lower_total": r"以兌(?P<number>二)離三",
        "moving_total": r"總(?P<number>十)數",
    },
}
CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def _finding(findings: list[str], condition: bool, message: str) -> None:
    if not condition:
        findings.append(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_slice(text: str, anchor: str) -> str:
    match = ANCHOR_RE.search(anchor)
    if match is None:
        raise ValueError(f"invalid Meihua source anchor: {anchor}")
    start = int(match.group("start"))
    end = int(match.group("end"))
    lines = text.splitlines()
    if start < 1 or end < start or end > len(lines):
        raise ValueError(f"Meihua source anchor out of range: {anchor}")
    return "\n".join(lines[start - 1 : end])


def _source_heading(anchor: str) -> str:
    match = ANCHOR_RE.search(anchor)
    if match is None:
        return ""
    return anchor[match.end() :].strip()


def _parse_chinese_integer(token: str) -> int:
    if token in CHINESE_DIGITS:
        return CHINESE_DIGITS[token]
    if "十" not in token or token.count("十") != 1:
        raise ValueError(f"unsupported classical Chinese integer: {token}")
    tens, ones = token.split("十")
    tens_value = 1 if not tens else CHINESE_DIGITS[tens]
    ones_value = 0 if not ones else CHINESE_DIGITS[ones]
    return tens_value * 10 + ones_value


def _source_derived_input(identifier: str, anchored: str) -> dict[str, int]:
    patterns = CLASSICAL_TOTAL_PATTERNS.get(identifier)
    if patterns is None:
        raise ValueError(f"missing classical source parser: {identifier}")
    derived: dict[str, int] = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, anchored)
        if match is None:
            raise ValueError(f"classical source pattern not found: {identifier}: {field}")
        derived[field] = _parse_chinese_integer(match.group("number"))
    return derived


def _reference_plate(
    source_input: Mapping[str, int], source_table: Mapping[str, Any]
) -> dict[str, Any]:
    trigrams = source_table["trigrams"]
    names = source_table["hexagram_names"]
    by_bits = {
        str(profile["bits_bottom_up"]): str(profile["name"])
        for profile in trigrams.values()
    }

    def trigram(total: int) -> tuple[str, list[int]]:
        profile = trigrams[(int(total) - 1) % 8 + 1]
        return str(profile["name"]), [int(bit) for bit in profile["bits_bottom_up"]]

    def hexagram(bits: list[int]) -> str:
        lower = by_bits["".join(str(bit) for bit in bits[:3])]
        upper = by_bits["".join(str(bit) for bit in bits[3:])]
        return str(names[f"{upper}/{lower}"])

    upper_name, upper_bits = trigram(source_input["upper_total"])
    lower_name, lower_bits = trigram(source_input["lower_total"])
    primary_bits = lower_bits + upper_bits
    primary = str(names[f"{upper_name}/{lower_name}"])
    moving_line = (source_input["moving_total"] - 1) % 6 + 1
    changed_bits = list(primary_bits)
    changed_bits[moving_line - 1] = 1 - changed_bits[moving_line - 1]
    mutual_source = changed_bits if primary in {"乾为天", "坤为地"} else primary_bits
    mutual_bits = mutual_source[1:4] + mutual_source[2:5]
    return {
        "primary": primary,
        "mutual": hexagram(mutual_bits),
        "changed": hexagram(changed_bits),
        "moving_line": moving_line,
    }


def _anchor_supports_case(case: dict[str, Any], anchored: str) -> bool:
    category = str(case.get("category") or "")
    identifier = str(case.get("id") or "")
    if category == "classical_case":
        heading = _source_heading(str(case.get("source_anchor") or ""))
        return bool(heading) and heading in anchored
    if category == "trigram_remainder":
        return "卦以八除" in anchored and "餘數作卦" in anchored
    if category == "moving_remainder":
        return "爻以六除" in anchored and "餘數作動爻" in anchored
    if identifier.startswith("supplied-number"):
        return "物數占例" in anchored and "時數配作下卦" in anchored
    if identifier.startswith("sound-count"):
        return "聲音占例" in anchored and "加時數配作下卦" in anchored
    if identifier.startswith("observation"):
        return "物卦起例" in anchored and "加時數以取動爻" in anchored
    return False


def _trigram_name(source_table: Mapping[str, Any], total: int) -> str:
    number = (int(total) - 1) % 8 + 1
    return str(source_table["trigrams"][number]["name"])


def _provider_request(
    case: Mapping[str, Any],
    replay: Mapping[str, Any],
    source_table: Mapping[str, Any],
) -> ReadingRequest:
    identifier = str(case.get("id") or "")
    source_input = dict(case["input"])
    exact_methods = replay.get("exact_method_cases")
    if not isinstance(exact_methods, Mapping):
        raise ValueError("Meihua provider replay exact_method_cases is missing")
    exact = exact_methods.get(identifier)
    event_datetime = str(replay.get("event_datetime") or "")
    provenance = {
        "kind": "source_anchored_totals",
        "fixture_id": identifier,
        "source_anchor": str(case.get("source_anchor") or ""),
        "source_input_totals": source_input,
    }
    if exact is None:
        chart_data = {
            "casting_method": "supplied_hexagram",
            "upper_trigram": _trigram_name(
                source_table, int(source_input["upper_total"])
            ),
            "lower_trigram": _trigram_name(
                source_table, int(source_input["lower_total"])
            ),
            "moving_line": (int(source_input["moving_total"]) - 1) % 6 + 1,
            "provenance": provenance,
        }
    else:
        if not isinstance(exact, Mapping):
            raise ValueError(f"Meihua provider replay case is invalid: {identifier}")
        method = str(exact.get("casting_method") or "")
        event_datetime = str(exact.get("event_datetime") or "")
        if (
            str(case.get("category") or "") in LIVE_REMAINDER_METHODS
            and method == "supplied_hexagram"
        ):
            raise ValueError(
                f"live remainder boundary cannot use supplied_hexagram: {identifier}"
            )
        if method == "time":
            chart_data = {"casting_method": method}
        elif method == "supplied_number":
            chart_data = {
                "casting_method": method,
                "number": int(source_input["upper_total"]),
                "provenance": provenance,
            }
        elif method == "sound_count":
            chart_data = {
                "casting_method": method,
                "count": int(source_input["upper_total"]),
                "observation_source": provenance,
            }
        elif method == "observation":
            chart_data = {
                "casting_method": method,
                "upper_trigram": str(exact.get("upper_trigram") or "")
                or _trigram_name(source_table, int(source_input["upper_total"])),
                "lower_trigram": str(exact.get("lower_trigram") or "")
                or _trigram_name(source_table, int(source_input["lower_total"])),
                "observation_source": provenance,
            }
        else:
            raise ValueError(
                f"Meihua provider replay method is unsupported: {identifier}: {method}"
            )
    return ReadingRequest(
        query=f"Task 7N Meihua replay {identifier}",
        action="new",
        system="meihua",
        event_datetime=event_datetime,
        timezone=str(replay.get("timezone") or ""),
        location=str(replay.get("location") or ""),
        chart_data=chart_data,
        metadata={
            "zi_hour_policy": str(replay.get("zi_hour_policy") or "")
        },
    )


def _calendar_boundary_request(case: Mapping[str, Any]) -> ReadingRequest:
    return ReadingRequest(
        query=f"Task 7N Meihua calendar replay {case.get('id')}",
        action="new",
        system="meihua",
        event_datetime=str(case.get("datetime") or ""),
        timezone=str(case.get("timezone") or ""),
        location=str(case.get("location") or ""),
        chart_data={"casting_method": "time"},
        metadata={
            "zi_hour_policy": str(case.get("zi_hour_policy") or "")
        },
    )


def audit_meihua_provider(
    *, fixture_path: Path = FIXTURE, research_root: Path | None = None
) -> dict[str, Any]:
    preflight = provider_preflight_failure(
        system="meihua",
        schema_version="mingli-meihua-completeness-audit-v1",
        provider_class=MeihuaProvider,
        expected_mode="calculation",
        expected_provider_id=EXPECTED_PROVIDER_ID,
        expected_provider_version=EXPECTED_PROVIDER_VERSION,
    )
    if preflight is not None:
        return preflight
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    fixture_sha256 = _sha256(fixture_path)
    examples = list(fixture.get("source_examples") or ())
    boundary_cases = list(fixture.get("calendar_boundaries") or ())
    findings: list[str] = []
    qualifying_cases = 0
    provider_calculations = 0
    boundary_provider_cases = 0
    determinism_checks = 0
    provider_mismatches = 0
    determinism_mismatches = 0
    validator_checks = 0
    independent_formula_cases = 0
    independent_formula_mismatches = 0
    qualifying_casting_methods: Counter[str] = Counter()
    live_remainder_boundary_counts: Counter[str] = Counter()
    live_remainder_casting_methods: Counter[str] = Counter()
    _finding(
        findings,
        MeihuaProvider.provider_id == EXPECTED_PROVIDER_ID
        and MeihuaProvider.provider_version == EXPECTED_PROVIDER_VERSION,
        "Meihua provider identity drift",
    )
    _finding(
        findings,
        fixture_sha256 == FIXTURE_SHA256,
        "Meihua fixture artifact hash mismatch",
    )
    catalog = meihua.build_hexagram_catalog()
    categories = Counter(str(case.get("category") or "") for case in examples)
    replay = fixture.get("provider_replay")
    if not isinstance(replay, Mapping):
        findings.append("Meihua provider replay profile must be a structured object")
        replay = {}
    direct_total_method_ids = {
        "supplied-number-9-zi",
        "supplied-number-8-hai",
        "sound-count-5-you",
        "sound-count-6-mao",
        "observation-qian-xun-mao",
        "observation-kun-kan-wu",
    }
    remainder_case_ids = {
        str(case.get("id") or "")
        for case in examples
        if str(case.get("category") or "") in LIVE_REMAINDER_METHODS
    }
    expected_exact_method_ids = direct_total_method_ids | remainder_case_ids
    _finding(
        findings,
        replay.get("source_totals_strategy")
        == "live_methods_with_equivalent_source_moduli",
        "Meihua provider replay source-totals strategy mismatch",
    )
    _finding(
        findings,
        set((replay.get("exact_method_cases") or {}))
        == expected_exact_method_ids,
        "Meihua provider replay exact-method case set mismatch",
    )

    _finding(
        findings,
        fixture.get("schema_version") == "mingli-meihua-fixtures-v51",
        "unexpected fixture schema",
    )
    _finding(
        findings,
        PROVIDER_CAPABILITIES["meihua"].mode == "calculation",
        "Meihua provider capability mode is not calculation",
    )
    _finding(findings, len(catalog) == 64, "provider catalog must contain 64 hexagrams")
    _finding(findings, len(examples) >= 30, "fixture requires at least 30 source examples")
    _finding(
        findings,
        len({str(case.get("id") or "") for case in examples}) == len(examples),
        "source example ids are not unique",
    )
    _finding(findings, categories["classical_case"] >= 10, "fixture requires ten classical cases")
    _finding(findings, categories["trigram_remainder"] == 8, "fixture requires eight trigram remainder cases")
    _finding(findings, categories["moving_remainder"] == 6, "fixture requires six moving remainder cases")
    _finding(findings, categories["method_formula"] >= 6, "fixture requires six method formula cases")

    matrix_payload = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(matrix_payload, ROOT)
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    source_profile = matrix_payload["source_registry"]["meihua_yishu"]
    fixture_source = dict(fixture.get("source_examples_source") or {})
    _finding(
        findings,
        fixture_source
        == {
            "path": source_profile["normalized_path"],
            "sha256": source_profile["sha256"],
        },
        "fixture source identity diverges from the audited Meihua source",
    )
    source_table = yaml.safe_load(
        (ROOT / meihua.TABLE_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    source_text = ""
    if resolved_research_root is not None:
        source_path = resolved_research_root / str(source_profile["normalized_path"])
        source_verification_findings = source_verification.setdefault("findings", [])
        try:
            _finding(
                source_verification_findings,
                source_path.is_file(),
                "Meihua normalized source is missing",
            )
            if source_path.is_file():
                _finding(
                    source_verification_findings,
                    _sha256(source_path) == source_profile["sha256"],
                    "Meihua normalized source hash mismatch",
                )
                source_text = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            source_verification_findings.append(
                f"Meihua normalized source failed: {exc}"
            )

    for case in examples:
        case_findings_start = len(findings)
        try:
            anchored = ""
            if resolved_research_root is not None:
                anchored = _source_slice(source_text, str(case["source_anchor"]))
                source_verification_findings = source_verification.setdefault(
                    "findings", []
                )
                _finding(
                    source_verification_findings,
                    _anchor_supports_case(case, anchored),
                    f"source anchor does not support fixture: {case.get('id')}",
                )
            independent_plate = _reference_plate(dict(case["input"]), source_table)
            expected_plate = dict(case.get("expected") or {})
            formula_projection = {
                key: independent_plate.get(key) for key in expected_plate
            }
            independent_formula_cases += 1
            _finding(
                findings,
                formula_projection == expected_plate,
                f"independent formula mismatch: {case.get('id')}",
            )
            if formula_projection != expected_plate:
                independent_formula_mismatches += 1
            if resolved_research_root is not None and case.get("category") == "classical_case":
                identifier = str(case.get("id") or "")
                source_verification_findings = source_verification.setdefault(
                    "findings", []
                )
                source_input = _source_derived_input(identifier, anchored)
                reference_plate = _reference_plate(source_input, source_table)
                _finding(
                    source_verification_findings,
                    source_input == case.get("input"),
                    f"classical source-derived input mismatch: {identifier}",
                )
                _finding(
                    source_verification_findings,
                    reference_plate == case.get("expected"),
                    f"classical reference plate mismatch: {identifier}",
                )
                contract = case.get("source_contract")
                _finding(
                    source_verification_findings,
                    isinstance(contract, Mapping),
                    f"classical source contract missing: {case.get('id')}",
                )
                if isinstance(contract, Mapping):
                    _finding(
                        source_verification_findings,
                        contract.get("input") == source_input,
                        f"classical source contract input mismatch: {case.get('id')}",
                    )
                    _finding(
                        source_verification_findings,
                        contract.get("expected") == reference_plate,
                        f"classical source contract expected mismatch: {case.get('id')}",
                    )
                    claims = contract.get("exact_claims")
                    _finding(
                        source_verification_findings,
                        isinstance(claims, list) and bool(claims),
                        f"classical source contract claims missing: {case.get('id')}",
                    )
                    if isinstance(claims, list):
                        for claim in claims:
                            _finding(
                                source_verification_findings,
                                isinstance(claim, str) and claim in anchored,
                                f"classical source claim absent: {case.get('id')}: {claim}",
                            )
            request = _provider_request(case, replay, source_table)
            first = MeihuaProvider(ROOT).calculate(request)
            provider_calculations += 1
            second = MeihuaProvider(ROOT).calculate(request)
            provider_calculations += 1
            determinism_checks += 1
            first_facts = first.facts["chart_facts"]
            second_facts = second.facts["chart_facts"]
            validator_checks += 2
            _finding(
                findings,
                first.system == "meihua" and second.system == "meihua",
                f"provider system mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                first.provider_id == MeihuaProvider.provider_id
                and second.provider_id == MeihuaProvider.provider_id
                and first.provider_version == MeihuaProvider.provider_version
                and second.provider_version == MeihuaProvider.provider_version,
                f"provider identity mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                meihua.validate_fact_layer(first_facts)["ok"]
                and meihua.validate_fact_layer(second_facts)["ok"],
                f"provider validation mismatch: {case.get('id')}",
            )
            if first.to_dict() != second.to_dict():
                findings.append(f"provider determinism mismatch: {case.get('id')}")
                determinism_mismatches += 1
            plate = first_facts["output"]
            casting = plate["casting"]
            method = str(request.chart_data["casting_method"])
            category = str(case.get("category") or "")
            _finding(
                findings,
                casting["method"] == method,
                f"provider casting method mismatch: {case.get('id')}",
            )
            if category in LIVE_REMAINDER_METHODS:
                _finding(
                    findings,
                    method == LIVE_REMAINDER_METHODS[category],
                    f"live remainder boundary requires {LIVE_REMAINDER_METHODS[category]}: {case.get('id')}",
                )
            source_totals = dict(case["input"])
            expected_totals = {
                "upper": int(source_totals["upper_total"]),
                "lower": int(source_totals["lower_total"]),
                "moving": int(source_totals["moving_total"]),
            }
            if str(case.get("id") or "") in direct_total_method_ids:
                _finding(
                    findings,
                    plate["totals"] == expected_totals,
                    f"provider exact source totals mismatch: {case.get('id')}",
                )
            elif category in LIVE_REMAINDER_METHODS:
                actual_remainders = {
                    "upper": (int(plate["totals"]["upper"]) - 1) % 8 + 1,
                    "lower": (int(plate["totals"]["lower"]) - 1) % 8 + 1,
                    "moving": (int(plate["totals"]["moving"]) - 1) % 6 + 1,
                }
                expected_remainders = {
                    "upper": (expected_totals["upper"] - 1) % 8 + 1,
                    "lower": (expected_totals["lower"] - 1) % 8 + 1,
                    "moving": (expected_totals["moving"] - 1) % 6 + 1,
                }
                _finding(
                    findings,
                    actual_remainders == expected_remainders,
                    f"live provider remainder mismatch: {case.get('id')}",
                )
            else:
                _finding(
                    findings,
                    casting["provenance"].get("source_input_totals")
                    == source_totals,
                    f"provider source totals provenance mismatch: {case.get('id')}",
                )
            expected = case["expected"]
            _finding(
                findings,
                plate["primary_hexagram"]["name"] == expected["primary"],
                f"primary mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                plate["changed_hexagram"]["name"] == expected["changed"],
                f"changed mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                plate["moving_line"] == expected["moving_line"],
                f"moving-line mismatch: {case.get('id')}",
            )
            if expected.get("mutual"):
                _finding(
                    findings,
                    plate["mutual_hexagram"]["name"] == expected["mutual"],
                    f"mutual mismatch: {case.get('id')}",
                )
            if len(findings) == case_findings_start:
                qualifying_cases += 1
                qualifying_casting_methods[method] += 1
                if category in LIVE_REMAINDER_METHODS:
                    live_remainder_boundary_counts[category] += 1
                    live_remainder_casting_methods[method] += 1
            else:
                provider_mismatches += 1
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"source example failed: {case.get('id')}: {exc}")
            provider_mismatches += 1

    _finding(
        findings,
        len(boundary_cases) >= 6,
        "fixture requires at least six calendar/season boundaries",
    )
    boundary_counts = Counter(
        str(case.get("category") or "") for case in boundary_cases
    )
    for category, minimum in REQUIRED_CALENDAR_COUNTS.items():
        _finding(
            findings,
            boundary_counts[category] >= minimum,
            f"calendar boundary category {category} requires {minimum} cases",
        )
    observed_seasons: set[str] = set()
    for case in boundary_cases:
        case_findings_start = len(findings)
        try:
            calendar = calendar_core.normalize_calendar(
                case["datetime"],
                timezone_name=case["timezone"],
                location=case["location"],
                zi_hour_policy=case["zi_hour_policy"],
            )
            _finding(
                findings,
                [calendar["ganzhi"][key] for key in ("year", "month", "day", "hour")]
                == list(case["expected_pillars"]),
                f"calendar boundary mismatch: {case.get('id')}",
            )
            lunar = calendar["lunar_date"]
            _finding(
                findings,
                [
                    lunar["year"],
                    lunar["month"],
                    lunar["day"],
                    lunar["is_leap_month"],
                ]
                == list(case["expected_lunar"]),
                f"calendar lunar boundary mismatch: {case.get('id')}",
            )
            request = _calendar_boundary_request(case)
            first = MeihuaProvider(ROOT).calculate(request)
            provider_calculations += 1
            second = MeihuaProvider(ROOT).calculate(request)
            provider_calculations += 1
            determinism_checks += 1
            facts = first.facts["chart_facts"]
            validator_checks += 2
            output = facts["output"]
            expected_cast = case["expected_time_cast"]
            casting_inputs = output["casting"]["inputs"]
            _finding(
                findings,
                casting_inputs["lunar_year"] == case["expected_lunar"][0],
                f"calendar time cast lunar year mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                casting_inputs["year_branch_number"]
                == (case["expected_lunar"][0] - 4) % 12 + 1,
                f"calendar time cast year branch mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                casting_inputs["lunar_leap_month"] == case["expected_lunar"][3],
                f"calendar time cast leap-month mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                output["totals"] == expected_cast["totals"]
                and output["primary_hexagram"]["name"] == expected_cast["primary"]
                and output["changed_hexagram"]["name"] == expected_cast["changed"]
                and output["moving_line"] == expected_cast["moving_line"],
                f"calendar time cast plate mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                meihua.validate_fact_layer(facts)["ok"]
                and meihua.validate_fact_layer(second.facts["chart_facts"])["ok"],
                f"calendar boundary fact validation failed: {case.get('id')}",
            )
            _finding(
                findings,
                first.system == "meihua" and second.system == "meihua",
                f"calendar boundary provider system mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                first.provider_id == MeihuaProvider.provider_id
                and first.provider_version == MeihuaProvider.provider_version,
                f"calendar boundary provider identity mismatch: {case.get('id')}",
            )
            if first.to_dict() != second.to_dict():
                findings.append(
                    f"calendar boundary determinism mismatch: {case.get('id')}"
                )
                determinism_mismatches += 1
            observed_seasons.add(
                facts["output"]["seasonal_strength"]["body"]["season"]
            )
            _finding(
                findings,
                len(facts["output"]["body_relation_facts"]) == 5,
                f"calendar boundary body relation facts incomplete: {case.get('id')}",
            )
            if len(findings) == case_findings_start:
                boundary_provider_cases += 1
            else:
                provider_mismatches += 1
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"calendar boundary failed: {case.get('id')}: {exc}")
            provider_mismatches += 1
    _finding(
        findings,
        observed_seasons == {"spring", "summer", "autumn", "winter", "seasonal_earth"},
        "calendar boundaries do not cover all five seasonal profiles",
    )

    source_report = audit_algorithm_sources.audit_matrix(
        matrix_payload,
        root=ROOT,
        systems=("meihua",),
    )
    findings.extend(f"source audit: {item}" for item in source_report["findings"])
    dependency_ids = {
        str(row["id"])
        for row in matrix_payload["providers"]["meihua"]["dependencies"]
    }
    calendar = calendar_core.normalize_calendar(
        "2024-02-10T12:00:00",
        timezone_name="Asia/Shanghai",
        location="上海",
    )
    representative = meihua.build_from_method(
        {"casting_method": "time"}, calendar_facts=calendar
    )["output"]
    observed_dependency_ids = {
        representative["casting"]["source_dependency_id"],
        representative["primary_hexagram"]["source_dependency_id"],
        representative["body_use"]["source_dependency_id"],
    }
    _finding(
        findings,
        observed_dependency_ids == dependency_ids,
        "provider facts do not cover the exact audited Meihua dependency ids",
    )

    _finding(
        findings,
        qualifying_cases >= 30,
        "Meihua provider requires at least 30 qualifying live-provider cases",
    )
    _finding(
        findings,
        live_remainder_boundary_counts
        == Counter({"trigram_remainder": 8, "moving_remainder": 6}),
        "Meihua live provider remainder boundary coverage is incomplete",
    )
    _finding(
        findings,
        live_remainder_casting_methods == Counter({"time": 8, "observation": 6}),
        "Meihua live remainder boundaries must use real casting methods",
    )
    _finding(
        findings,
        provider_calculations
        >= 2 * (qualifying_cases + boundary_provider_cases),
        "Meihua provider replay did not execute every qualifying case twice",
    )
    _finding(
        findings,
        determinism_mismatches == 0,
        "Meihua provider replay contains nondeterministic results",
    )
    boundary_categories = sorted(
        set(categories)
        | set(boundary_counts)
        | {"calendar_witness", "seasonal_profile"}
    )
    if resolved_research_root is not None:
        source_verification["ok"] = not source_verification.get("findings")
        source_verification["status"] = (
            "verified" if source_verification["ok"] else "failed"
        )
    findings = list(dict.fromkeys(findings))
    ready = not findings and qualifying_cases >= 30

    return {
        "schema_version": "mingli-meihua-completeness-audit-v1",
        "system": "meihua",
        "status": "pass" if ready else "fail",
        "provider_ready": ready,
        "source_verification": source_verification,
        "provider": {
            "provider_class": MeihuaProvider.__name__,
            "provider_id": MeihuaProvider.provider_id,
            "provider_version": MeihuaProvider.provider_version,
            "capability_mode": PROVIDER_CAPABILITIES["meihua"].mode,
            "adapter_version": meihua.ADAPTER_VERSION,
            "validator": "reading_engine.meihua.validate_fact_layer",
            "algorithm_dependency_ids": sorted(dependency_ids),
        },
        "route_owned_case_ids": [str(case.get("id") or "") for case in examples],
        "fixture": {
            "path": (
                fixture_path.relative_to(ROOT).as_posix()
                if fixture_path.is_relative_to(ROOT)
                else str(fixture_path)
            ),
            "sha256": fixture_sha256,
            "expected_sha256": FIXTURE_SHA256,
        },
        "boundary_categories": boundary_categories,
        "qualifying_casting_methods": dict(
            sorted(qualifying_casting_methods.items())
        ),
        "live_remainder_boundary_counts": dict(
            sorted(live_remainder_boundary_counts.items())
        ),
        "live_remainder_casting_methods": dict(
            sorted(live_remainder_casting_methods.items())
        ),
        "counts": {
            "hexagrams": len(catalog),
            "source_examples": len(examples),
            "classical_examples": categories["classical_case"],
            "source_rule_boundary_vectors": len(examples)
            - categories["classical_case"],
            "qualifying_cases": qualifying_cases,
            "route_owned_cases": len(examples),
            "provider_calculations": provider_calculations,
            "provider_extensions": 0,
            "boundary_provider_cases": boundary_provider_cases,
            "determinism_checks": determinism_checks,
            "boundary_case_count": len(boundary_cases),
            "independent_formula_cases": independent_formula_cases,
            "independent_formula_mismatches": independent_formula_mismatches,
            "validator_checks": validator_checks,
            "provider_mismatches": provider_mismatches,
            "determinism_mismatches": determinism_mismatches,
            "casting_methods": len(meihua.METHODS),
            "calendar_boundaries": len(boundary_cases),
            "seasonal_profiles": len(observed_seasons),
            "algorithm_dependencies": source_report["dependency_count"],
            "fact_dependency_ids": len(observed_dependency_ids),
        },
        "source_table": {
            "path": meihua.TABLE_RELATIVE_PATH,
            "sha256": meihua.source_table_digest(),
        },
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args()
    report = audit_meihua_provider(fixture_path=args.fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
