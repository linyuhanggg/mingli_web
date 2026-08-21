#!/usr/bin/env python3
"""Build or verify immutable exact-output fixtures for every Selection formula."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping

import yaml

from reading_engine import selection
from reading_engine.contracts import canonical_digest
import selection_formula_reference


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/selection-v51.yaml"
REFERENCE_EVALUATOR_PATH = ROOT / "scripts/selection_formula_reference.py"
REFERENCE_EVALUATOR_SHA256 = (
    "cf3476eaa81be24ec106528b67200b91e52d71ef672b2bfc0fa700359bab9b3e"
)
POLICY_INACTIVE_KINDS = {"official_rejected_rule", "lunar_zhoutang"}
INTRINSICALLY_ACTIVE_KINDS = {
    "record",
    "hour_path",
    "good_gods",
    "bad_gods",
    "renshen_location",
    "medical_policy",
}
SAMPLE_KINDS = ("positive", "negative", "exact_jie_boundary")


def _reference_evaluator_sha256() -> str:
    return hashlib.sha256(REFERENCE_EVALUATOR_PATH.read_bytes()).hexdigest()


def _load_fixture(path: Path = FIXTURE) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Selection fixture must be an object")
    return payload


def _profiles() -> dict[str, dict[str, Any]]:
    return selection.source_table()["event_profiles"]


def _first_profile(field: str) -> str:
    return next(
        profile
        for profile, contract in _profiles().items()
        if field in contract["required_event_fact_fields"]
    )


def _input(civil_date: str, profile: str, **changes: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "date": civil_date,
        "event_profile": profile,
        "requested_actions": list(
            _profiles()[profile].get("official_terms") or []
        )[:1],
    }
    payload.update(changes)
    return payload


_RECORD_CACHE: dict[str, dict[str, Any]] = {}


def _build(raw: Mapping[str, Any]) -> dict[str, Any]:
    key = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if key not in _RECORD_CACHE:
        _RECORD_CACHE[key] = selection.build_day_record(
            str(raw["date"]),
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile=str(raw["event_profile"]),
            requested_actions=list(raw.get("requested_actions") or []),
            requested_scopes=raw.get("requested_scopes"),
            directional_context=raw.get("directional_context"),
            participant_facts=raw.get("participant_facts"),
            include_folk_comparison=bool(
                raw.get("include_folk_comparison", False)
            ),
        )
    return copy.deepcopy(_RECORD_CACHE[key])


def _activation_examples(
    fixture: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    active: dict[str, dict[str, Any]] = {}
    inactive: dict[str, dict[str, Any]] = {}
    profiles = _profiles()

    for case in fixture.get("event_rule_cases") or ():
        raw = dict(case["input"])
        raw.setdefault(
            "requested_actions",
            list(profiles[raw["event_profile"]].get("official_terms") or [])[:1],
        )
        record = _build(raw)
        for field, fact in record["event_specific_facts"].items():
            (active if fact["active"] else inactive).setdefault(field, raw)

    current = date(2024, 1, 1)
    while current <= date(2024, 4, 5):
        for profile in profiles:
            raw = _input(
                current.isoformat(), profile, include_folk_comparison=True
            )
            record = _build(raw)
            for field, fact in record["event_specific_facts"].items():
                (active if fact["active"] else inactive).setdefault(field, raw)
        current += timedelta(days=1)

    definitions = selection.source_table()["event_fact_definitions"]
    for field, definition in definitions.items():
        applicable_actions = list(definition.get("applicable_actions") or ())
        if not applicable_actions:
            continue
        profile = _first_profile(field)
        current = date(2024, 1, 1)
        while current <= date(2024, 12, 31) and field not in active:
            raw = _input(
                current.isoformat(),
                profile,
                requested_actions=[str(applicable_actions[0])],
            )
            if _build(raw)["event_specific_facts"][field]["active"]:
                active[field] = raw
            current += timedelta(days=1)

    for field in ("dajiangjun", "jinshen_qisha", "directional_hits"):
        profile = _first_profile(field)
        directional = _build(_input("2024-01-01", profile))["directional_facts"]
        key = {
            "dajiangjun": "dajiangjun_branch",
            "jinshen_qisha": "jinshen_qisha_branches",
            "directional_hits": "dajiangjun_branch",
        }[field]
        value = directional[key]
        branch = value[0] if isinstance(value, list) else value
        raw = _input(
            "2024-01-01",
            profile,
            requested_scopes=["directional_judgment"],
            directional_context={"site_branch": branch},
        )
        if _build(raw)["event_specific_facts"][field]["active"]:
            active[field] = raw

    profile = _first_profile("luohou")
    mountain = _build(_input("2024-01-01", profile))["directional_facts"][
        "xunshan_luohou_mountain"
    ]
    raw = _input(
        "2024-01-01",
        profile,
        requested_actions=["立向"],
        requested_scopes=["directional_judgment"],
        directional_context={"site_mountain": mountain},
    )
    if _build(raw)["event_specific_facts"]["luohou"]["active"]:
        active["luohou"] = raw

    for field in (
        "mountain_family_clashes",
        "directional_avoidance_when_relevant",
    ):
        profile = _first_profile(field)
        branch = _build(_input("2024-01-01", profile))["directional_facts"][
            "dajiangjun_branch"
        ]
        raw = _input(
            "2024-01-01",
            profile,
            requested_scopes=["directional_judgment"],
            directional_context={"site_branch": branch},
        )
        if _build(raw)["event_specific_facts"][field]["active"]:
            active[field] = raw

    profile = "marriage"
    base = _build(_input("2024-01-01", profile))
    day_branch = base["calendar"]["ganzhi"]["day"][1]
    raw = _input(
        "2024-01-01",
        profile,
        participant_facts=[
            {
                "id": "a",
                "year_branch": selection.OPPOSITE_BRANCHES[day_branch],
                "day_branch": "寅",
            },
            {"id": "b", "year_branch": "丑", "day_branch": "卯"},
        ],
    )
    if _build(raw)["event_specific_facts"]["participant_clashes"]["active"]:
        active["participant_clashes"] = raw
    return active, inactive


def generate_payload(fixture: Mapping[str, Any]) -> dict[str, Any]:
    definitions = selection.source_table()["event_fact_definitions"]
    active, inactive = _activation_examples(fixture)
    source_contracts: dict[str, Any] = {}
    cases: list[dict[str, Any]] = []
    for field, definition in definitions.items():
        kind = str(definition["kind"])
        source_contracts[field] = {
            "kind": kind,
            "source_anchors": list(definition["source_anchors"]),
            "definition_sha256": canonical_digest(definition),
            "reference_evaluator": selection_formula_reference.REFERENCE_EVALUATOR_ID,
            "reference_evaluator_version": (
                selection_formula_reference.REFERENCE_EVALUATOR_VERSION
            ),
            "reference_evaluator_sha256": REFERENCE_EVALUATOR_SHA256,
        }
        boundary = _input("2024-02-04", _first_profile(field))
        positive = active.get(field) or boundary
        negative = inactive.get(field) or boundary
        samples = (
            (
                "positive",
                positive,
                "official_policy_never_active"
                if kind in POLICY_INACTIVE_KINDS
                else "must_be_active",
            ),
            (
                "negative",
                negative,
                "intrinsically_calculated_always_active"
                if kind in INTRINSICALLY_ACTIVE_KINDS
                or (kind == "god_presence" and not definition.get("names"))
                else "must_be_inactive",
            ),
            ("exact_jie_boundary", boundary, "exact_snapshot"),
        )
        for sample_kind, raw, activation_contract in samples:
            record = _build(raw)
            fact = selection_formula_reference.evaluate_event_fact(
                field, raw, record, selection.source_table()
            )
            cases.append(
                {
                    "id": f"{field}--{sample_kind}",
                    "field": field,
                    "sample_kind": sample_kind,
                    "activation_contract": activation_contract,
                    "input": copy.deepcopy(raw),
                    "expected": {
                        "active": bool(fact["active"]),
                        "kind": str(fact["kind"]),
                        "value_sha256": canonical_digest(fact["value"]),
                    },
                }
            )
    return {
        "event_fact_formula_fixture_policy": {
            "oracle_status": selection_formula_reference.REFERENCE_EVALUATOR_ID,
            "reference_evaluator_version": (
                selection_formula_reference.REFERENCE_EVALUATOR_VERSION
            ),
            "reference_evaluator_sha256": REFERENCE_EVALUATOR_SHA256,
            "snapshot_contract": "immutable exact-output source oracles generated by an evaluator that consumes only public day primitives and versioned definitions, never provider event-fact output",
            "sample_kinds": list(SAMPLE_KINDS),
            "value_contract": "canonical SHA-256 of the complete structured value; active and kind are asserted separately",
            "policy_inactive_kinds": sorted(POLICY_INACTIVE_KINDS),
            "intrinsically_active_kinds": sorted(INTRINSICALLY_ACTIVE_KINDS),
        },
        "event_fact_formula_sources": source_contracts,
        "event_fact_formula_cases": cases,
    }


def audit_formula_fixtures(fixture: Mapping[str, Any]) -> dict[str, Any]:
    definitions = selection.source_table()["event_fact_definitions"]
    sources = fixture.get("event_fact_formula_sources") or {}
    cases = fixture.get("event_fact_formula_cases") or []
    mismatches: list[str] = []
    policy = fixture.get("event_fact_formula_fixture_policy") or {}
    if (
        _reference_evaluator_sha256() != REFERENCE_EVALUATOR_SHA256
        or policy.get("oracle_status")
        != selection_formula_reference.REFERENCE_EVALUATOR_ID
        or policy.get("reference_evaluator_version")
        != selection_formula_reference.REFERENCE_EVALUATOR_VERSION
        or policy.get("reference_evaluator_sha256")
        != REFERENCE_EVALUATOR_SHA256
    ):
        mismatches.append("independent reference evaluator hash mismatch")
    if set(sources) != set(definitions):
        mismatches.append("formula source coverage mismatch")
    for field, definition in definitions.items():
        expected_source = {
            "kind": definition["kind"],
            "source_anchors": definition["source_anchors"],
            "definition_sha256": canonical_digest(definition),
            "reference_evaluator": selection_formula_reference.REFERENCE_EVALUATOR_ID,
            "reference_evaluator_version": (
                selection_formula_reference.REFERENCE_EVALUATOR_VERSION
            ),
            "reference_evaluator_sha256": REFERENCE_EVALUATOR_SHA256,
        }
        if sources.get(field) != expected_source:
            mismatches.append(f"formula source mismatch: {field}")
    observed_kinds: dict[str, set[str]] = {field: set() for field in definitions}
    observed_pairs: dict[tuple[str, str], int] = {}
    observed_ids: set[str] = set()
    if len(cases) != len(definitions) * len(SAMPLE_KINDS):
        mismatches.append("formula case count mismatch")
    for case in cases:
        try:
            field = str(case["field"])
            sample_kind = str(case["sample_kind"])
            case_id = str(case["id"])
            if field not in definitions or sample_kind not in SAMPLE_KINDS:
                raise ValueError("unknown formula field or sample kind")
            if case_id != f"{field}--{sample_kind}":
                raise ValueError("formula case identity mismatch")
            if case_id in observed_ids:
                raise ValueError("duplicate formula case identity")
            observed_ids.add(case_id)
            observed_kinds[field].add(sample_kind)
            pair = (field, sample_kind)
            observed_pairs[pair] = observed_pairs.get(pair, 0) + 1
            record = _build(case["input"])
            fact = record["event_specific_facts"][field]
            reference = selection_formula_reference.evaluate_event_fact(
                field, case["input"], record, selection.source_table()
            )
            expected = case["expected"]
            if (
                bool(fact["active"]) is not bool(reference["active"])
                or fact["kind"] != reference["kind"]
                or canonical_digest(fact["value"])
                != canonical_digest(reference["value"])
            ):
                raise ValueError("independent formula reference mismatch")
            if (
                bool(reference["active"]) is not bool(expected["active"])
                or reference["kind"] != expected["kind"]
                or canonical_digest(reference["value"])
                != expected["value_sha256"]
            ):
                raise ValueError("independent formula fixture mismatch")
            contract = str(case["activation_contract"])
            if contract == "must_be_active" and fact["active"] is not True:
                raise ValueError("positive formula case is inactive")
            if contract in {
                "must_be_inactive",
                "official_policy_never_active",
            } and fact["active"] is not False:
                raise ValueError("inactive formula case is active")
            if (
                case["sample_kind"] == "exact_jie_boundary"
                and case["input"]["date"] != "2024-02-04"
            ):
                raise ValueError("boundary case does not use exact Jie date")
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            mismatches.append(f"formula case mismatch: {case.get('id')}:{error}")
    for field, kinds in observed_kinds.items():
        if kinds != set(SAMPLE_KINDS):
            mismatches.append(f"formula sample-kind coverage mismatch: {field}")
        for sample_kind in SAMPLE_KINDS:
            if observed_pairs.get((field, sample_kind)) != 1:
                mismatches.append(
                    f"formula sample multiplicity mismatch: {field}:{sample_kind}"
                )
    return {
        "ok": not mismatches,
        "formula_count": len(definitions),
        "case_count": len(cases),
        "positive_case_count": sum(
            case.get("sample_kind") == "positive" for case in cases
        ),
        "negative_case_count": sum(
            case.get("sample_kind") == "negative" for case in cases
        ),
        "boundary_case_count": sum(
            case.get("sample_kind") == "exact_jie_boundary" for case in cases
        ),
        "mismatches": mismatches,
    }


def _write_payload(path: Path, payload: Mapping[str, Any]) -> None:
    original = path.read_text(encoding="utf-8")
    start_marker = "event_fact_formula_fixture_policy:\n"
    end_marker = "external_reference_cases:\n"
    if end_marker not in original:
        raise RuntimeError("Selection fixture insertion marker missing")
    if start_marker in original:
        prefix, remainder = original.split(start_marker, 1)
        _, suffix = remainder.split(end_marker, 1)
    else:
        prefix, suffix = original.split(end_marker, 1)
    rendered = yaml.safe_dump(
        dict(payload),
        allow_unicode=True,
        sort_keys=False,
        width=1_000_000,
    )
    path.write_text(prefix + rendered + end_marker + suffix, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(FIXTURE))
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = Path(args.fixture)
    fixture = _load_fixture(path)
    if args.write:
        _write_payload(path, generate_payload(fixture))
        fixture = _load_fixture(path)
    report = audit_formula_fixtures(fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
