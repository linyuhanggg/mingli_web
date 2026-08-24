#!/usr/bin/env python3
"""Audit Daliuren transmission hidden stems against an independent Jiazi oracle."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import liuren_calc
import liuren_fact_adapter
from reading_engine.liuren_contract import (
    LiurenRuntimeContractError,
    validate_runtime_core_facts,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/liuren-transmission-hidden-stems-v1.json"
SOURCE_QUOTE_INDEX = ROOT / "references/books/san-shi/liuren-miben/quote-index.md"
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
JIAZI = tuple(STEMS[index % 10] + BRANCHES[index % 12] for index in range(60))


def _oracle(day_ganzhi: str) -> tuple[str, dict[str, str], list[str]]:
    start = (JIAZI.index(day_ganzhi) // 10) * 10
    rows = JIAZI[start : start + 10]
    stem_by_branch = {ganzhi[1]: ganzhi[0] for ganzhi in rows}
    empty = [branch for branch in BRANCHES if branch not in stem_by_branch]
    return rows[0], stem_by_branch, empty


def _contract(case: dict[str, Any]) -> dict[str, Any]:
    chart = liuren_fact_adapter.build_from_chart(
        **case["input"],
        question="脱敏三传遁干审计",
        location="fixture",
    )
    return liuren_calc.extend_liuren_facts(
        chart,
        requested_dimensions=("relationship",),
        horizon={"kind": "instant"},
        target_relative=None,
    )["runtime_core_facts"]


def _mutate(contract: dict[str, Any], mutation: str) -> None:
    rows = contract["three_transmissions"]
    if mutation == "omit_hidden_stem_from_all_three_rows":
        for row in rows:
            del row["hidden_stem"]
    elif mutation == "omit_hidden_stem_from_first_row":
        del rows[0]["hidden_stem"]
    elif mutation == "set_first_hidden_stem_to_甲":
        rows[0]["hidden_stem"] = "甲"
    elif mutation == "set_first_hidden_stem_to_array":
        rows[0]["hidden_stem"] = []
    elif mutation == "set_xun_to_甲子":
        contract["xunkong"]["xun"] = "甲子"
    else:
        raise ValueError(f"unsupported fixture mutation: {mutation}")


def audit_liuren_transmission_hidden_stems() -> dict[str, Any]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    findings: list[str] = []
    quote_index = SOURCE_QUOTE_INDEX.read_text(encoding="utf-8")
    if (
        "### LM-Q008" not in quote_index
        or "甲子旬，子儀神，卯丁神，戌亥天中" not in quote_index
    ):
        findings.append("LM-Q008 source witness is missing or changed")

    mapping_checks = 0
    for day_ganzhi in JIAZI:
        expected_xun, expected_map, expected_empty = _oracle(day_ganzhi)
        actual_xunkong = liuren_fact_adapter._xunkong(day_ganzhi)
        if actual_xunkong != {"xun": expected_xun, "branches": expected_empty}:
            findings.append(f"{day_ganzhi}: xunkong differs from independent oracle")
        if (
            liuren_fact_adapter._xun_hidden_stem(day_ganzhi, day_ganzhi[1])
            != day_ganzhi[0]
        ):
            findings.append(f"{day_ganzhi}: day branch does not map back to day stem")
        for branch in BRANCHES:
            mapping_checks += 1
            actual = liuren_fact_adapter._xun_hidden_stem(day_ganzhi, branch)
            if actual != expected_map.get(branch):
                findings.append(
                    f"{day_ganzhi}/{branch}: expected {expected_map.get(branch)!r}, got {actual!r}"
                )

    cases = fixture["cases"]
    built: dict[str, dict[str, Any]] = {}
    for case_name in ("positive", "partial"):
        case = cases[case_name]
        contract = _contract(case)
        built[case_name] = contract
        expected = case["expected"]
        actual = {
            "xun": contract["xunkong"]["xun"],
            "xunkong": contract["xunkong"]["branches"],
            "branches": [row["branch"] for row in contract["three_transmissions"]],
            "hidden_stems": [
                row["hidden_stem"] for row in contract["three_transmissions"]
            ],
        }
        if actual != expected:
            findings.append(f"{case_name}: fixture mismatch: {actual!r}")

    legacy = copy.deepcopy(built[cases["legacy_absent"]["base_case"]])
    _mutate(legacy, cases["legacy_absent"]["mutation"])
    try:
        validate_runtime_core_facts(legacy)
    except LiurenRuntimeContractError as exc:
        findings.append(f"legacy_absent: old v1 payload was rejected: {exc}")

    invalid_checked = 0
    for case in cases["invalid"]:
        invalid_checked += 1
        mutated = copy.deepcopy(built[case["base_case"]])
        _mutate(mutated, case["mutation"])
        try:
            validate_runtime_core_facts(mutated)
        except LiurenRuntimeContractError as exc:
            if case["error_contains"] not in str(exc):
                findings.append(f"{case['id']}: unexpected error: {exc}")
        else:
            findings.append(f"{case['id']}: invalid payload was accepted")

    return {
        "schema_version": "mingli-liuren-transmission-hidden-stem-audit-v1",
        "calculation_source": fixture["calculation_source"],
        "source_reference": fixture["source_reference"],
        "day_count": len(JIAZI),
        "mapping_checks": mapping_checks,
        "positive_case_count": 1,
        "partial_case_count": 1,
        "legacy_absent_case_count": 1,
        "invalid_case_count": invalid_checked,
        "findings": findings,
        "ready": not findings,
    }


def main() -> int:
    report = audit_liuren_transmission_hidden_stems()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
