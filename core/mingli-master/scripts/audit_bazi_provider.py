#!/usr/bin/env python3
"""Machine-readable Task 7N completeness audit for the Bazi provider."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

import audit_algorithm_sources
import bazi_calc
import bazi_fact_adapter as bazi
import reading_evidence_bundle
from reading_engine import calendar_core
from reading_engine.contracts import CalculationResult, ReadingRequest, canonical_digest
from reading_engine.evidence_rules import production_evidence_rules
from reading_engine.fact_index import build_fact_index
from reading_engine.providers import PROVIDER_CAPABILITIES, BaziProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "bazi-fortune-v51.yaml"
SOURCE_MATRIX = (
    ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
)
FIXTURE_SHA256 = "f5e7e1f5460ef1faf1b2d64dcc5b97cbfca8adeca03945aa9c59f2fb25bf13a4"
REQUIRED_CATEGORY_COUNTS = {
    "strong_weak_dispute": 6,
    "following_dispute": 3,
    "transformation_dispute": 3,
    "seasonal_extreme": 8,
    "luck_cycle_boundary": 8,
    "long_horizon": 6,
}
EXPECTED_DEPENDENCY_IDS = {
    "bazi.calendar.sxtwl-jieqi-four-pillars",
    "bazi.luck.major-cycle-three-days-per-year",
    "bazi.relations.ten-gods-hidden-stems-branch-relations",
    "bazi.seasonal-tiaohou.day-master-month",
    "bazi.shensha.yima-taohua-auxiliary",
}
PLACEHOLDER_RE = re.compile(
    r"(?:placeholder|generic|unavailable|not[-_ ]implemented|\bTODO\b|\bTBD\b)",
    re.IGNORECASE,
)
QIONGTONG_FIXTURE_REQUIRED_LOCAL_IDS = {
    "QR-01-01",
    "QR-01-02",
    "QR-01-03",
    "QR-01-05",
    "QR-02-01",
    "QR-02-02",
    "QR-02-04",
    "QR-03-01",
    "QR-03-04",
    "QR-03-06",
    "QR-03-07",
    "QR-04-01",
    "QR-04-02",
    "QR-04-07",
    "QR-05-02",
    "QR-05-04",
    "QR-05-08",
}
QIONGTONG_FIXTURE_REQUIRED_RULE_IDS = {
    f"bazi/qiongtong-baojian#{local_id}"
    for local_id in QIONGTONG_FIXTURE_REQUIRED_LOCAL_IDS
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_pointer_exists(payload: Any, pointer: str) -> bool:
    """Resolve one manifest pointer independently of provider projection code."""

    if not pointer.startswith("/"):
        return False
    current = payload
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping) and token in current:
            current = current[token]
            continue
        if isinstance(current, (list, tuple)) and token.isdigit():
            index = int(token)
            if index < len(current):
                current = current[index]
                continue
        return False
    return True


def _finding(findings: list[str], condition: bool, message: str) -> bool:
    if not condition:
        findings.append(message)
    return condition


def _birth_request(
    identifier: str,
    civil_datetime: str,
    *,
    gender: str = "male",
    reference_datetime: str | None = None,
) -> ReadingRequest:
    return ReadingRequest(
        query=f"Bazi provider audit fixture {identifier}",
        action="new",
        system="bazi",
        reference_datetime=reference_datetime,
        birth_data={
            "datetime": civil_datetime,
            "timezone": "Asia/Shanghai",
            "location": "上海",
            "gender": gender,
        },
    )


def _pillar_request(identifier: str, pillars: Iterable[str]) -> ReadingRequest:
    return ReadingRequest(
        query=f"Bazi provider audit fixture {identifier}",
        action="new",
        system="bazi",
        chart_data={"pillars": list(pillars)},
    )


def _calculation_pair(
    provider: BaziProvider,
    request: ReadingRequest,
    findings: list[str],
    *,
    label: str,
) -> tuple[CalculationResult, CalculationResult]:
    first = provider.calculate(request)
    second = provider.calculate(request)
    _finding(
        findings,
        first.result_hash == second.result_hash,
        f"provider calculation digest is non-deterministic: {label}",
    )
    _finding(
        findings,
        canonical_digest(first.facts) == canonical_digest(second.facts),
        f"provider calculation facts are non-deterministic: {label}",
    )
    _finding(
        findings,
        first.input_hash == second.input_hash,
        f"provider calculation input identity is non-deterministic: {label}",
    )
    for result in (first, second):
        _finding(findings, result.system == "bazi", f"wrong provider system: {label}")
        _finding(
            findings,
            result.provider_id == BaziProvider.provider_id,
            f"wrong provider id: {label}",
        )
        _finding(
            findings,
            result.provider_version == BaziProvider.provider_version,
            f"wrong provider version: {label}",
        )
        _finding(
            findings,
            {
                "chart_digest",
                "natal_fact_digest",
                "chart_facts",
            }
            <= set(result.facts),
            f"provider required fact envelope is incomplete: {label}",
        )
        payload = result.to_dict()
        bound_outputs = {
            binding.name
            for binding in PROVIDER_CAPABILITIES["bazi"].output_bindings
            if any(
                _json_pointer_exists(payload, pointer)
                for pointer in binding.json_pointers
            )
        }
        _finding(
            findings,
            set(PROVIDER_CAPABILITIES["bazi"].outputs) == bound_outputs,
            f"provider declared output is absent: {label}",
        )
    return first, second


def _extension_pair(
    provider: BaziProvider,
    calculations: tuple[CalculationResult, CalculationResult],
    dimensions: tuple[str, ...],
    horizon: dict[str, Any],
    findings: list[str],
    *,
    label: str,
) -> tuple[CalculationResult, CalculationResult]:
    first = provider.extend(calculations[0], dimensions, horizon)
    second = provider.extend(calculations[1], dimensions, horizon)
    first_extension = first.fact_extension
    second_extension = second.fact_extension
    _finding(
        findings,
        first_extension is not None and second_extension is not None,
        f"provider extension is absent: {label}",
    )
    if first_extension is None or second_extension is None:
        return first, second
    _finding(
        findings,
        first_extension.status == second_extension.status == "complete",
        f"provider extension is incomplete: {label}",
    )
    _finding(
        findings,
        first_extension.extension_digest == second_extension.extension_digest,
        f"provider extension digest is non-deterministic: {label}",
    )
    _finding(
        findings,
        canonical_digest(first_extension.facts)
        == canonical_digest(second_extension.facts),
        f"provider extension facts are non-deterministic: {label}",
    )
    return first, second


def _walk_dependency_ids(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "source_dependency_id" and isinstance(item, str):
                yield item
            yield from _walk_dependency_ids(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_dependency_ids(item)


def _source_applicability(
    representative: CalculationResult | None,
    findings: list[str],
) -> tuple[dict[str, Any], bool]:
    rules = [rule for rule in production_evidence_rules() if rule.system == "bazi"]
    bound = [rule for rule in rules if rule.required_fact_predicates]
    unbound = [rule for rule in rules if not rule.required_fact_predicates]
    structural_tiaohou_rules = [
        rule
        for rule in bound
        if rule.source_pack == "bazi/qiongtong-baojian"
        and rule.evidence_role == "issue_specific_judgment_rule"
        and re.fullmatch(r"bazi/qiongtong-baojian#QR-0[1-5]-0[1-8]", rule.rule_id)
    ]
    verified_tiaohou_rules = [
        rule
        for rule in structural_tiaohou_rules
        if rule.runtime_active and rule.classical_binding_status == "verified"
    ]
    day_stems: set[str] = set()
    month_branches: set[str] = set()
    exact_shape = True
    for rule in structural_tiaohou_rules:
        predicates = {
            item.path_suffix: item for item in rule.required_fact_predicates
        }
        stem = predicates.get("/day_master/stem")
        month = predicates.get("/month_command/branch")
        if stem is None or stem.operator != "eq" or not isinstance(stem.value, str):
            exact_shape = False
        else:
            day_stems.add(stem.value)
        if month is None or month.operator != "in" or not month.values:
            exact_shape = False
        else:
            month_branches.update(str(value) for value in month.values)

    runtime_ids: set[str] = set()
    if representative is not None:
        fact_index = build_fact_index(
            representative,
            reading_id="bazi-provider-audit",
            version=1,
        )
        source_packs = sorted({rule.source_pack for rule in rules})
        eligible = reading_evidence_bundle._eligible_rules(
            {
                "system": "bazi",
                "sources": [{"pack": pack} for pack in source_packs],
            },
            fact_index,
            rules=tuple(rules),
        )
        runtime_ids = {
            candidate[0].rule_id
            for candidates in eligible.values()
            for candidate in candidates
        }
    bound_ids = {rule.rule_id for rule in bound}
    unbound_ids = {rule.rule_id for rule in unbound}
    unbound_fail_closed = (
        representative is not None
        and bool(runtime_ids)
        and runtime_ids <= bound_ids
        and runtime_ids.isdisjoint(unbound_ids)
    )
    verified_tiaohou_ids = {rule.rule_id for rule in verified_tiaohou_rules}
    fixture_covered_ids = (
        QIONGTONG_FIXTURE_REQUIRED_RULE_IDS & verified_tiaohou_ids
    )
    complete = (
        len(structural_tiaohou_rules) == 40
        and exact_shape
        and day_stems == set(bazi.STEMS)
        and month_branches == set(bazi.BRANCHES)
        and fixture_covered_ids == QIONGTONG_FIXTURE_REQUIRED_RULE_IDS
        and unbound_fail_closed
    )
    _finding(
        findings,
        len(structural_tiaohou_rules) == 40,
        "Bazi source applicability does not contain 40 structural day-master/season chapters",
    )
    _finding(
        findings,
        exact_shape,
        "Bazi source applicability contains a non-exact predicate shape",
    )
    _finding(
        findings,
        day_stems == set(bazi.STEMS),
        "Bazi source applicability does not cover all ten day stems",
    )
    _finding(
        findings,
        month_branches == set(bazi.BRANCHES),
        "Bazi source applicability does not cover all twelve month branches",
    )
    _finding(
        findings,
        fixture_covered_ids == QIONGTONG_FIXTURE_REQUIRED_RULE_IDS,
        "Bazi verified Qiongtong chapters do not cover every route fixture context",
    )
    _finding(
        findings,
        unbound_fail_closed,
        "Bazi predicate-free source rules are not demonstrably fail-closed",
    )
    return (
        {
            "total_rules": len(rules),
            "applicable_rules": len(bound),
            "tiaohou_applicability_rules": len(structural_tiaohou_rules),
            "structural_tiaohou_chapters": len(structural_tiaohou_rules),
            "runtime_verified_tiaohou_chapters": len(verified_tiaohou_rules),
            "runtime_verified_tiaohou_rule_ids": sorted(verified_tiaohou_ids),
            "fixture_required_tiaohou_chapters": len(
                QIONGTONG_FIXTURE_REQUIRED_RULE_IDS
            ),
            "fixture_covered_tiaohou_chapters": len(fixture_covered_ids),
            "fixture_covered_tiaohou_rule_ids": sorted(fixture_covered_ids),
            "unbound_rules": len(unbound),
            "runtime_eligible_rules": len(runtime_ids),
            "day_stems": sorted(day_stems),
            "month_branches": sorted(month_branches),
            "unbound_fail_closed": unbound_fail_closed,
        },
        complete,
    )


def audit_bazi_provider(
    *, fixture_path: Path = FIXTURE, research_root: Path | None = None
) -> dict[str, Any]:
    """Execute every Bazi fixture through the live provider and fail closed.

    ``research_root`` is the release-time fulltext tree for source
    verification.  It is intentionally independent of ``audit_matrix``'s own
    optional research-root wiring so a portable checkout can prove runtime
    readiness without an external corpus, while a release build passes an
    explicit root to close the source-verification gate.  Runtime readiness
    (``provider_ready``) never depends on the external fulltext tree.
    """

    findings: list[str] = []
    fixture: dict[str, Any] = {}
    fixture_digest = ""
    try:
        fixture_digest = _sha256(fixture_path)
        loaded = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            fixture = loaded
        else:
            findings.append("Bazi fixture root must be a mapping")
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        findings.append(f"Bazi fixture could not be loaded: {exc}")

    fixture_integrity = _finding(
        findings,
        fixture_digest == FIXTURE_SHA256,
        "Bazi fixture sha256 mismatch",
    )
    _finding(
        findings,
        fixture.get("schema_version") == "mingli-bazi-fortune-fixtures-v1",
        "unexpected Bazi fixture schema",
    )
    source_scope = str(fixture.get("source_scope") or "")
    _finding(
        findings,
        "Fixed regression cases" in source_scope
        and "never verdicts" in source_scope,
        "Bazi fixture lacks an independent fixed-oracle scope",
    )
    cases = list(fixture.get("cases") or ())
    categories = Counter(
        str(case.get("category") or "")
        for case in cases
        if isinstance(case, Mapping)
    )
    fixture_threshold = _finding(
        findings,
        len(cases) >= 30,
        "Bazi provider requires at least 30 route-owned fixtures",
    )
    unique_ids = _finding(
        findings,
        len(cases)
        == len(
            {
                str(case.get("id") or "")
                for case in cases
                if isinstance(case, Mapping)
            }
        )
        and all(
            isinstance(case, Mapping) and bool(case.get("id"))
            for case in cases
        ),
        "Bazi fixture ids must be non-empty and unique",
    )
    boundary_coverage = True
    for category, minimum in REQUIRED_CATEGORY_COUNTS.items():
        boundary_coverage &= _finding(
            findings,
            categories[category] >= minimum,
            f"Bazi boundary category {category} requires {minimum} fixtures",
        )

    capability = PROVIDER_CAPABILITIES["bazi"]
    provider_identity = (
        capability.system == "bazi"
        and capability.mode == "calculation"
        and capability.independent_lineage == "bazi"
        and BaziProvider.__name__ == "BaziProvider"
        and BaziProvider.provider_id == "mingli-master.bazi.v7"
        and BaziProvider.provider_version == bazi_calc.CALCULATION_CONTRACT
    )
    _finding(findings, provider_identity, "Bazi provider identity is generic or drifted")
    required_fields = (
        bool(capability.required_inputs)
        and "birth_datetime_or_four_pillars" in capability.required_inputs
        and set(capability.horizons) == {"day", "month", "year", "life"}
        # The manifest is the sole output vocabulary authority.  The audit
        # verifies a closed declaration instead of duplicating those names in
        # Python; _calculation_pair above proves every declared output exists.
        and bool(capability.outputs)
        and set(capability.outputs)
        == {binding.name for binding in capability.output_bindings}
        and set(capability.extension_outputs)
        == {
            "year_layers",
            "month_layers",
            "day_layers",
            "dimension_fact_scope",
        }
    )
    _finding(findings, required_fields, "Bazi provider declaration is incomplete")
    no_placeholder = not any(
        PLACEHOLDER_RE.search(value)
        for value in (
            BaziProvider.__name__,
            BaziProvider.provider_id,
            BaziProvider.provider_version,
            capability.mode,
        )
    )
    _finding(findings, no_placeholder, "Bazi runtime contains placeholder identity")

    provider = BaziProvider(ROOT)
    qualifying = 0
    calculation_pairs = 0
    extension_pairs = 0
    deterministic_pairs = 0
    microsecond_boundaries = 0
    microsecond_serializations = 0
    microsecond_serialization_ok = True
    executed_horizons: set[str] = set()
    observed_dependency_ids: set[str] = set()
    representative: CalculationResult | None = None
    temporal_representative: CalculationResult | None = None
    for raw_case in cases:
        if not isinstance(raw_case, Mapping):
            findings.append("Bazi fixture case must be a mapping")
            continue
        case = dict(raw_case)
        identifier = str(case.get("id") or "")
        category = str(case.get("category") or "")
        case_input = case.get("input") or {}
        expected = case.get("expected") or {}
        before = len(findings)
        try:
            if category.endswith("dispute"):
                request = _pillar_request(identifier, case_input["pillars"])
            elif category == "seasonal_extreme":
                request = _birth_request(identifier, str(case_input["datetime"]))
            elif category == "luck_cycle_boundary":
                request = _birth_request(
                    identifier,
                    "2000-10-18T06:45:00",
                    gender=str(case_input["gender"]),
                    reference_datetime=str(case_input["instant"]),
                )
            elif category == "long_horizon":
                request = _birth_request(
                    identifier,
                    "2000-10-18T06:45:00",
                )
            else:
                findings.append(f"unknown Bazi fixture category: {identifier}")
                continue

            calculations = _calculation_pair(
                provider,
                request,
                findings,
                label=identifier,
            )
            calculation_pairs += 1
            deterministic_pairs += 1
            representative = representative or calculations[0]
            chart = calculations[0].facts["chart_facts"]
            observed_dependency_ids.update(_walk_dependency_ids(chart))

            if category.endswith("dispute"):
                output = chart["output"]
                analysis = output["interpretive_candidates"]
                _finding(
                    findings,
                    output["day_master"]["element"] == expected["day_element"],
                    f"independent day-element oracle mismatch: {identifier}",
                )
                _finding(
                    findings,
                    output["month_command"]["branch"] == expected["month_branch"],
                    f"independent month-command oracle mismatch: {identifier}",
                )
                _finding(
                    findings,
                    analysis["strength"]["status"] == "evidence_only"
                    and analysis["strength"]["hard_verdict"] is None
                    and analysis["structure"]["status"] == "candidate_only"
                    and analysis["structure"]["hard_verdict"] is None
                    and analysis["following_and_transformation"]["status"]
                    == "requires_classical_adjudication",
                    f"disputed chart was promoted to a verdict: {identifier}",
                )
                if "life" not in executed_horizons:
                    extensions = _extension_pair(
                        provider,
                        calculations,
                        tuple(capability.dimensions),
                        {"kind": "life"},
                        findings,
                        label=f"{identifier}:life",
                    )
                    extension_pairs += 1
                    deterministic_pairs += 1
                    executed_horizons.add("life")
                    extension = extensions[0].fact_extension
                    scope = (
                        (extension.facts if extension is not None else {}).get(
                            "dimension_fact_scope"
                        )
                        or {}
                    )
                    _finding(
                        findings,
                        set(scope) == set(capability.dimensions),
                        "Bazi life horizon omits a declared dimension",
                    )
            elif category == "seasonal_extreme":
                temporal_representative = temporal_representative or calculations[0]
                _finding(
                    findings,
                    chart["calendar_normalization"]["ganzhi"]["month"]
                    == expected["month_ganzhi"],
                    f"independent seasonal month oracle mismatch: {identifier}",
                )
                _finding(
                    findings,
                    chart["output"]["seasonal_profile"]["temperature"]
                    == expected["temperature"]
                    and chart["output"]["seasonal_profile"]["moisture"]
                    == expected["moisture"],
                    f"independent seasonal climate oracle mismatch: {identifier}",
                )
            elif category == "luck_cycle_boundary":
                temporal_representative = temporal_representative or calculations[0]
                point = datetime.fromisoformat(str(case_input["instant"]))
                horizon = {
                    "kind": "day",
                    "start": point.date().isoformat(),
                    "end": point.date().isoformat(),
                }
                extensions = _extension_pair(
                    provider,
                    calculations,
                    ("timing",),
                    horizon,
                    findings,
                    label=identifier,
                )
                extension_pairs += 1
                deterministic_pairs += 1
                executed_horizons.add("day")
                observed_dependency_ids.update(
                    _walk_dependency_ids(extensions[0].fact_extension.facts)
                    if extensions[0].fact_extension is not None
                    else ()
                )
                exact_first = bazi._extension_active_luck_cycle_interval(
                    point,
                    point + timedelta(microseconds=1),
                    calculations[0].facts["chart_facts"],
                    transition_status="transition_period",
                )
                exact_second = bazi._extension_active_luck_cycle_interval(
                    point,
                    point + timedelta(microseconds=1),
                    calculations[1].facts["chart_facts"],
                    transition_status="transition_period",
                )
                _finding(
                    findings,
                    canonical_digest(exact_first) == canonical_digest(exact_second),
                    f"microsecond luck boundary is non-deterministic: {identifier}",
                )
                _finding(
                    findings,
                    exact_first["status"] == expected["status"]
                    and [row["sequence"] for row in exact_first["cycles"]]
                    == expected["sequences"],
                    f"independent luck-boundary oracle mismatch: {identifier}",
                )
                serialized = json.dumps(exact_first, ensure_ascii=False)
                if point.microsecond:
                    microsecond_boundaries += 1
                    if exact_first["cycles"]:
                        microsecond_serializations += 1
                        preserved = f".{point.microsecond:06d}" in serialized
                        microsecond_serialization_ok &= _finding(
                            findings,
                            preserved,
                            f"luck boundary lost microsecond precision: {identifier}",
                        )
            elif category == "long_horizon":
                temporal_representative = temporal_representative or calculations[0]
                kind = str(case_input["kind"])
                horizon = {
                    "kind": kind,
                    "start": str(case_input["start"]),
                    "end": str(case_input["end"]),
                }
                extensions = _extension_pair(
                    provider,
                    calculations,
                    ("timing",),
                    horizon,
                    findings,
                    label=identifier,
                )
                extension_pairs += 1
                deterministic_pairs += 1
                executed_horizons.add(kind)
                extension = extensions[0].fact_extension
                extension_facts = extension.facts if extension is not None else {}
                observed_dependency_ids.update(_walk_dependency_ids(extension_facts))
                collection_name = {
                    "year": "year_layers",
                    "month": "month_layers",
                    "day": "day_layers",
                }[kind]
                layers = extension_facts.get(collection_name) or {}
                keys = list(layers)
                _finding(
                    findings,
                    len(keys) == int(expected["count"])
                    and bool(keys)
                    and keys[0] == str(expected["first"])
                    and keys[-1] == str(expected["last"]),
                    f"independent long-horizon oracle mismatch: {identifier}",
                )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"Bazi provider fixture failed: {identifier}: {exc}")
        if len(findings) == before:
            qualifying += 1

    source_payload: dict[str, Any] = {}
    source_report = {
        "ok": False,
        "dependency_count": 0,
        "findings": ["source matrix unavailable"],
    }
    try:
        loaded_source = yaml.safe_load(SOURCE_MATRIX.read_text(encoding="utf-8"))
        if isinstance(loaded_source, dict):
            source_payload = loaded_source
            source_report = audit_algorithm_sources.audit_matrix(
                source_payload,
                root=ROOT,
                systems=("bazi",),
            )
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
        findings.append(f"Bazi algorithm source audit failed to load: {exc}")
    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(source_payload, ROOT)
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    if resolved_research_root is not None:
        # Fulltext verification is a release-time gate: its findings belong in
        # the source_verification block, never in runtime provider_ready.
        source_report = audit_algorithm_sources.audit_matrix(
            source_payload,
            root=ROOT,
            systems=("bazi",),
            research_root=resolved_research_root,
        )
        source_verification["ok"] = bool(source_report.get("ok")) and not (
            source_report.get("findings") or ()
        )
        source_verification["status"] = (
            "verified" if source_verification["ok"] else "failed"
        )
        if not source_verification["ok"]:
            source_verification["findings"] = list(
                source_report.get("findings") or ()
            )
    else:
        # A portable checkout with no research corpus cannot verify fulltext;
        # keep the matrix provenance audit as a runtime gate exactly as before.
        findings.extend(
            f"Bazi algorithm source audit: {item}"
            for item in source_report.get("findings") or ()
        )
    dependency_rows = (
        ((source_payload.get("providers") or {}).get("bazi") or {}).get(
            "dependencies"
        )
        or ()
    )
    declared_dependency_ids = {
        str(row.get("id") or "")
        for row in dependency_rows
        if isinstance(row, Mapping)
    }
    dependency_provenance = (
        declared_dependency_ids == EXPECTED_DEPENDENCY_IDS
        and EXPECTED_DEPENDENCY_IDS <= observed_dependency_ids
    )
    # The matrix provenance gate (release artifacts, samples, dependency
    # declarations) is a runtime condition only when no explicit research
    # root is driving fulltext verification; with an explicit root those
    # checks are reported by ``source_verification`` and ``provider_ready``
    # stays a runtime-only property.
    source_provenance = dependency_provenance and (
        resolved_research_root is not None or bool(source_report.get("ok"))
    )
    _finding(
        findings,
        declared_dependency_ids == EXPECTED_DEPENDENCY_IDS,
        "Bazi algorithm dependency declaration set drifted",
    )
    _finding(
        findings,
        EXPECTED_DEPENDENCY_IDS <= observed_dependency_ids,
        "Bazi live facts do not expose every audited dependency identity",
    )

    algorithm_versions = (
        bool(BaziProvider.provider_version)
        and bool(bazi.VERSION)
        and bool(calendar_core.ALGORITHM_VERSION)
        and temporal_representative is not None
        and temporal_representative.facts["chart_facts"]["adapter"]["version"]
        == bazi.VERSION
        and temporal_representative.facts["chart_facts"][
            "calendar_normalization"
        ]["algorithm_version"]
        == calendar_core.ALGORITHM_VERSION
    )
    _finding(
        findings,
        algorithm_versions,
        "Bazi live algorithm versions are absent or drifted",
    )

    source_applicability, applicability_complete = _source_applicability(
        representative,
        findings,
    )
    determinism = deterministic_pairs == calculation_pairs + extension_pairs
    provider_execution = (
        calculation_pairs == len(cases)
        and qualifying == len(cases)
        and len(cases) >= 30
        and executed_horizons == set(capability.horizons)
    )
    microsecond_precision = (
        microsecond_boundaries == categories["luck_cycle_boundary"]
        and microsecond_boundaries >= 8
        and microsecond_serializations >= 6
        and microsecond_serialization_ok
    )
    _finding(
        findings,
        microsecond_precision,
        "Bazi microsecond luck boundaries are incomplete",
    )
    checks = {
        "fixture_integrity": fixture_integrity,
        "fixture_threshold": fixture_threshold and unique_ids,
        "boundary_coverage": boundary_coverage,
        "provider_identity": provider_identity,
        "required_fields": required_fields,
        "no_placeholder": no_placeholder,
        "provider_execution": provider_execution,
        "determinism": determinism,
        "microsecond_precision": microsecond_precision,
        "algorithm_versions": algorithm_versions,
        "source_provenance": source_provenance,
        "source_applicability": applicability_complete,
    }
    # Each before/at pair below shares one public provider request; the
    # microsecond distinction is verified by the dedicated exact-boundary
    # oracle.  Count that pair once in route replay coverage rather than
    # claiming query labels as distinct provider inputs.
    microsecond_oracle_only_case_ids = {
        "luck-male-cycle-1-before",
        "luck-male-cycle-2-before",
        "luck-female-cycle-1-before",
        "luck-female-cycle-3-before",
    }
    route_owned_cases = [
        case
        for case in cases
        if str(case.get("id") or "") not in microsecond_oracle_only_case_ids
    ]
    ready = not findings and all(checks.values())
    return {
        "schema_version": "mingli-bazi-provider-audit-v1",
        "system": "bazi",
        "status": "pass" if ready else "fail",
        "provider_ready": ready,
        "provider": {
            "provider_class": BaziProvider.__name__,
            "provider_id": BaziProvider.provider_id,
            "provider_version": BaziProvider.provider_version,
            "capability_mode": capability.mode,
        },
        "route_owned_case_ids": [
            str(case.get("id") or "") for case in route_owned_cases
        ],
        "runtime": {
            "provider_class": BaziProvider.__name__,
            "provider_id": BaziProvider.provider_id,
            "provider_version": BaziProvider.provider_version,
            "adapter_version": bazi.VERSION,
            "calendar_algorithm_version": calendar_core.ALGORITHM_VERSION,
        },
        "fixture": {
            "path": (
                fixture_path.relative_to(ROOT).as_posix()
                if fixture_path.is_relative_to(ROOT)
                else str(fixture_path)
            ),
            "sha256": fixture_digest,
            "expected_sha256": FIXTURE_SHA256,
        },
        "counts": {
            "fixture_cases": len(cases),
            "fixture_oracle_cases": qualifying,
            "qualifying_provider_cases": len(route_owned_cases),
            "qualifying_cases": len(route_owned_cases),
            "route_owned_cases": len(route_owned_cases),
            "provider_calculations": calculation_pairs * 2,
            "provider_extensions": extension_pairs * 2,
            "determinism_checks": deterministic_pairs,
            "boundary_case_count": len(cases),
            "supplied_static_cases": sum(
                categories[name]
                for name in (
                    "strong_weak_dispute",
                    "following_dispute",
                    "transformation_dispute",
                )
            ),
            "birth_timing_cases": len(cases)
            - sum(
                categories[name]
                for name in (
                    "strong_weak_dispute",
                    "following_dispute",
                    "transformation_dispute",
                )
            ),
            "provider_calculation_pairs": calculation_pairs,
            "provider_extension_pairs": extension_pairs,
            "determinism_pairs": deterministic_pairs,
            "declared_horizons_executed": len(executed_horizons),
            "boundary_categories": len(
                set(REQUIRED_CATEGORY_COUNTS) & set(categories)
            ),
            "microsecond_boundaries": microsecond_boundaries,
            "microsecond_serializations": microsecond_serializations,
            "algorithm_dependencies": int(
                source_report.get("dependency_count") or 0
            ),
            "fact_dependency_ids": len(observed_dependency_ids),
            "source_applicable_rules": source_applicability[
                "applicable_rules"
            ],
            "source_unbound_rules": source_applicability["unbound_rules"],
        },
        "category_counts": dict(sorted(categories.items())),
        "boundary_categories": sorted(
            set(REQUIRED_CATEGORY_COUNTS) & set(categories)
        ),
        "source_applicability": source_applicability,
        "source_verification": source_verification,
        "checks": checks,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args()
    report = audit_bazi_provider(fixture_path=args.fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
