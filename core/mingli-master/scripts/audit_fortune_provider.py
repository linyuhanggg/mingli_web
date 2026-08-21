#!/usr/bin/env python3
"""Machine-readable Task 7N completeness audit for the Fortune provider."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

import audit_algorithm_sources
import near_time_fortune_adapter
from reading_engine.contracts import ReadingRequest
from reading_engine.providers import FortuneProvider
from reading_engine.providers import PROVIDER_CAPABILITIES


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "fortune-v51.yaml"
MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
EXPECTED_FIXTURE_SHA256 = "b84f4bf9c5aa3c3ea04825e6271485cc31a8e0187f0d0b66314dd9df7d71275d"
EXPECTED_DEPENDENCY_ID = "fortune.bounded-target-period-over-bazi"
EXPECTED_DEPENDENCY_VERSION = "fortune-v6-one-explicit-period"
REQUIRED_BOUNDARY_CATEGORIES = {
    "solar_term_boundary",
    "day_rollover",
    "lunar_new_year_boundary",
    "leap_day",
    "leap_month_boundary",
}
HKO_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
CHINESE_LUNAR_MONTHS = {
    "正": 1,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
}
CHINESE_LUNAR_DAYS = {
    **{f"初{glyph}": value for value, glyph in enumerate("一二三四五六七八九", 1)},
    "初十": 10,
    **{f"十{glyph}": value for value, glyph in enumerate("一二三四五六七八九", 11)},
    "二十": 20,
    "廿": 20,
    **{f"廿{glyph}": value for value, glyph in enumerate("一二三四五六七八九", 21)},
    "三十": 30,
}
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object in {path}")
    return payload


def _finding(findings: list[str], condition: bool, message: str) -> None:
    if not condition:
        findings.append(message)


def _expected_lunar_year(civil: date, lunar_month: int) -> int:
    if civil.month <= 2 and lunar_month >= 11:
        return civil.year - 1
    return civil.year


def _hko_projection(
    case: Mapping[str, Any],
    rows: list[list[str]],
) -> dict[str, Any] | None:
    try:
        anchor = re.fullmatch(r"CSV row (\d+)", str(case["source_anchor"]))
        if anchor is None:
            return None
        row_number = int(anchor.group(1))
        if row_number < 2 or row_number > len(rows):
            return None
        if rows[0][:5] != [
            "Gregorian Date",
            "Chinese year (Gan-Zhi)",
            "Chinese year (Zodiac)",
            "Lunar month",
            "Lunar Date",
        ]:
            return None
        row = rows[row_number - 1]
        day_text, month_text, year_text = row[0].split("-")
        civil = date(2000 + int(year_text), HKO_MONTHS[month_text], int(day_text))
        lunar_month_text = row[3].strip().removesuffix("月")
        is_leap = lunar_month_text.startswith(("閏", "闰"))
        if is_leap:
            lunar_month_text = lunar_month_text[1:]
        lunar_month = CHINESE_LUNAR_MONTHS[lunar_month_text]
        lunar_year = _expected_lunar_year(civil, lunar_month)
        return {
            "civil_date": civil.isoformat(),
            "chinese_year_ganzhi": row[1].strip().removesuffix("年"),
            "lunar": {
                "year": lunar_year,
                "month": lunar_month,
                "day": CHINESE_LUNAR_DAYS[row[4].strip()],
                "is_leap_month": is_leap,
            },
        }
    except (IndexError, KeyError, TypeError, UnicodeError, ValueError):
        return None


def _audit_source_artifacts(
    fixture: Mapping[str, Any],
    findings: list[str],
) -> tuple[dict[str, list[list[str]]], int]:
    rows_by_source: dict[str, list[list[str]]] = {}
    mismatches = 0
    sources = fixture.get("oracle_sources") or {}
    if not isinstance(sources, Mapping) or set(sources) != {
        "hko-2024",
        "hko-2025",
        "hko-2026",
    }:
        findings.append("Fortune oracle source coverage mismatch")
        return rows_by_source, 1
    for source_id, source in sources.items():
        label = f"Fortune oracle source {source_id}"
        if not isinstance(source, Mapping):
            findings.append(f"{label} is invalid")
            mismatches += 1
            continue
        path = (ROOT / str(source.get("artifact_path") or "")).resolve()
        if ROOT not in path.parents or not path.is_file() or path.is_symlink():
            findings.append(f"{label} artifact is missing, escaped, or symlinked")
            mismatches += 1
            continue
        if _sha256(path) != source.get("artifact_sha256"):
            findings.append(f"{label} artifact hash mismatch")
            mismatches += 1
            continue
        if source.get("role") != (
            "government-published independent calendar oracle; "
            "not a Fortune interpretation oracle"
        ):
            findings.append(f"{label} role is not scope-limited")
            mismatches += 1
        try:
            rows_by_source[str(source_id)] = list(
                csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig")))
            )
        except (OSError, UnicodeError):
            findings.append(f"{label} artifact cannot be decoded")
            mismatches += 1

    boundary_sources = fixture.get("boundary_oracles") or {}
    if not isinstance(boundary_sources, Mapping) or set(boundary_sources) != {
        "exact_li_chun",
        "civil_midnight",
    }:
        findings.append("Fortune boundary oracle coverage mismatch")
        return rows_by_source, mismatches + 1
    for source_id, source in boundary_sources.items():
        label = f"Fortune boundary oracle {source_id}"
        if not isinstance(source, Mapping):
            findings.append(f"{label} is invalid")
            mismatches += 1
            continue
        path = (ROOT / str(source.get("source_path") or "")).resolve()
        if ROOT not in path.parents or not path.is_file() or path.is_symlink():
            findings.append(f"{label} source is missing, escaped, or symlinked")
            mismatches += 1
            continue
        if _sha256(path) != source.get("source_sha256"):
            findings.append(f"{label} source hash mismatch")
            mismatches += 1
        text = path.read_text(encoding="utf-8")
        anchors = str(source.get("source_anchor") or "").split(" and ")
        if not anchors or any(anchor not in text for anchor in anchors):
            findings.append(f"{label} source anchor mismatch")
            mismatches += 1
    return rows_by_source, mismatches


def _audit_algorithm_source(
    findings: list[str],
    *,
    research_root: Path | None = None,
) -> tuple[int, int, dict[str, Any]]:
    matrix = _load(MATRIX)
    provider = (matrix.get("providers") or {}).get("fortune") or {}
    dependencies = list(provider.get("dependencies") or ())
    report = audit_algorithm_sources.audit_matrix(
        matrix,
        root=ROOT,
        systems=("fortune",),
        research_root=research_root,
    )
    if research_root is not None:
        source_verification = {
            "ok": bool(report.get("ok")) and not (report.get("findings") or ()),
            "status": (
                "verified"
                if bool(report.get("ok")) and not (report.get("findings") or ())
                else "failed"
            ),
            "findings": list(report.get("findings") or ()),
        }
    else:
        source_verification = {
            "status": "skipped",
            "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
        }
    for finding in report["findings"]:
        if research_root is None:
            findings.append(f"Fortune algorithm source: {finding}")
    _finding(
        findings,
        provider.get("source_audit_status") == "source_verified",
        "Fortune algorithm source status is not verified",
    )
    _finding(
        findings,
        len(dependencies) == 1,
        "Fortune algorithm dependency count mismatch",
    )
    if len(dependencies) == 1:
        dependency = dependencies[0]
        _finding(
            findings,
            dependency.get("id") == EXPECTED_DEPENDENCY_ID,
            "Fortune algorithm dependency id mismatch",
        )
        _finding(
            findings,
            dependency.get("version") == EXPECTED_DEPENDENCY_VERSION,
            "Fortune algorithm dependency version mismatch",
        )
        _finding(
            findings,
            dependency.get("status") == "verified",
            "Fortune algorithm dependency is not verified",
        )
        _finding(
            findings,
            bool(dependency.get("primary_sources")),
            "Fortune algorithm dependency has no primary source",
        )
        _finding(
            findings,
            bool(dependency.get("independent_test_sample")),
            "Fortune algorithm dependency has no independent sample",
        )
    return len(dependencies), len(report["findings"]), source_verification


def _request(profile: Mapping[str, Any], case: Mapping[str, Any]) -> ReadingRequest:
    return ReadingRequest(
        query=f"核验这一天的确定性 Fortune 事实 {case.get('id')}",
        action="new",
        system="fortune",
        birth_data=dict(profile),
        reference_datetime=str(case["reference_datetime"]),
    )


def _audit_one_result(
    case: Mapping[str, Any],
    calculation: Any,
    extension: Any,
) -> list[str]:
    case_id = str(case.get("id") or "<missing>")
    failures: list[str] = []
    chart = calculation.facts.get("chart_facts") or {}
    reference = datetime.fromisoformat(str(case["reference_datetime"]))
    target = reference.date().isoformat()
    if calculation.system != "fortune":
        failures.append(f"Fortune case system mismatch: {case_id}")
    if calculation.provider_id != FortuneProvider.provider_id:
        failures.append(f"Fortune case provider id mismatch: {case_id}")
    if calculation.provider_version != FortuneProvider.provider_version:
        failures.append(f"Fortune case provider version mismatch: {case_id}")
    if chart.get("target_date") != target:
        failures.append(f"Fortune target date mismatch: {case_id}")
    if chart.get("calendar_normalization", {}).get("lunar_date") != case.get(
        "expected_lunar"
    ):
        failures.append(f"Fortune lunar oracle mismatch: {case_id}")
    selection = chart.get("reference_selection") or {}
    if selection.get("basis") != "reference_datetime":
        failures.append(f"Fortune reference selection basis mismatch: {case_id}")
    if selection.get("selected_at") != reference.isoformat():
        failures.append(f"Fortune reference instant precision mismatch: {case_id}")
    segment = chart.get("selected_bazi_day_segment") or {}
    try:
        if not (
            datetime.fromisoformat(str(segment["start_inclusive"]))
            <= reference
            < datetime.fromisoformat(str(segment["end_exclusive"]))
        ):
            failures.append(f"Fortune selected segment misses reference: {case_id}")
    except (KeyError, TypeError, ValueError):
        failures.append(f"Fortune selected segment is invalid: {case_id}")
    segment_transits = segment.get("active_transits") or {}
    transit_layers = chart.get("transit_layers") or {}
    for layer in ("year", "month", "day"):
        if (transit_layers.get(layer) or {}).get("pillar") != segment_transits.get(
            layer
        ):
            failures.append(f"Fortune {layer} layer diverges from segment: {case_id}")
    for layer, expected in (case.get("expected_active_transits") or {}).items():
        if segment_transits.get(layer) != expected:
            failures.append(f"Fortune {layer} boundary mismatch: {case_id}")
    bounded = chart.get("bounded_view") or {}
    if (
        bounded.get("base_system") != "bazi"
        or bounded.get("period_kind") != "civil_day"
        or bounded.get("periods") != [target]
        or bounded.get("period_count") != 1
        or bounded.get("base_fact_layer") != "bazi_day_fact_extension"
    ):
        failures.append(f"Fortune bounded-view contract mismatch: {case_id}")
    natal_digest = calculation.facts.get("natal_fact_digest")
    if not isinstance(natal_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", natal_digest):
        failures.append(f"Fortune natal digest is invalid: {case_id}")
    fact_extension = extension.fact_extension
    if fact_extension is None or fact_extension.status != "complete":
        failures.append(f"Fortune day extension is incomplete: {case_id}")
        return failures
    extension_facts = fact_extension.facts
    if extension_facts.get("target_period") != {
        "kind": "day",
        "start": target,
        "end": target,
    }:
        failures.append(f"Fortune target period mismatch: {case_id}")
    target_facts = extension_facts.get("target_period_facts") or {}
    required = {
        "calendar_normalization",
        "active_luck_cycle",
        "active_luck_cycle_detail",
        "transit_layers",
        "bazi_day_fact_layer",
        "selected_bazi_day_segment",
        "mechanism_stack",
        "hour_profiles",
    }
    if not required <= set(target_facts):
        failures.append(f"Fortune target-period fact layer is incomplete: {case_id}")
    if not any(
        trace.get("source_dependency_id") == EXPECTED_DEPENDENCY_ID
        and trace.get("rule_id") == "fortune.single-target-day-v1"
        for trace in fact_extension.rule_traces
    ):
        failures.append(f"Fortune source applicability trace is missing: {case_id}")
    return failures


def audit_fortune_provider(
    *,
    fixture_path: str | Path = FIXTURE,
    research_root: Path | None = None,
) -> dict[str, Any]:
    """Execute every Fortune fixture through the live provider and fail closed.

    ``research_root`` is the release-time fulltext tree for source
    verification.  It is intentionally independent of ``audit_matrix``'s own
    optional research-root wiring so a portable checkout can prove runtime
    readiness without an external corpus, while a release build passes an
    explicit root to close the source-verification gate.  Runtime readiness
    (``provider_ready``) never depends on the external fulltext tree.
    """
    fixture_path = Path(fixture_path)
    fixture = _load(fixture_path)
    findings: list[str] = []
    fixture_is_symlink = fixture_path.is_symlink()
    _finding(
        findings,
        not fixture_is_symlink,
        "Fortune fixture must not be a symlink",
    )
    _finding(
        findings,
        _sha256(fixture_path) == EXPECTED_FIXTURE_SHA256,
        "Fortune fixture artifact hash mismatch",
    )
    _finding(
        findings,
        fixture.get("schema_version") == "mingli-fortune-provider-fixtures-v1",
        "Fortune fixture schema mismatch",
    )
    _finding(findings, fixture.get("system") == "fortune", "Fortune fixture system mismatch")

    capability = PROVIDER_CAPABILITIES["fortune"]
    provider_contract = fixture.get("provider_contract") or {}
    _finding(findings, capability.mode == "calculation", "Fortune mode is not calculation")
    _finding(
        findings,
        capability.horizons == ("day", "week"),
        "Fortune horizons must cover exact day and week periods",
    )
    _finding(
        findings,
        "reference_datetime" in capability.required_inputs,
        "Fortune reference_datetime is not declared required",
    )
    _finding(
        findings,
        set(capability.extension_outputs)
        == {"target_period", "available_periods", "period_markers"},
        "Fortune extension output declaration mismatch",
    )
    _finding(
        findings,
        provider_contract.get("provider_id") == FortuneProvider.provider_id,
        "Fortune fixture provider id mismatch",
    )
    _finding(
        findings,
        provider_contract.get("provider_version") == FortuneProvider.provider_version,
        "Fortune fixture provider version mismatch",
    )
    _finding(
        findings,
        provider_contract.get("adapter_name") == near_time_fortune_adapter.ADAPTER_NAME,
        "Fortune adapter name mismatch",
    )
    _finding(
        findings,
        provider_contract.get("adapter_version") == near_time_fortune_adapter.ADAPTER_VERSION,
        "Fortune adapter version mismatch",
    )
    _finding(
        findings,
        provider_contract.get("algorithm_dependency_id") == EXPECTED_DEPENDENCY_ID,
        "Fortune fixture dependency id mismatch",
    )
    _finding(
        findings,
        provider_contract.get("algorithm_dependency_version") == EXPECTED_DEPENDENCY_VERSION,
        "Fortune fixture dependency version mismatch",
    )
    placeholder_text = json.dumps(
        {
            "provider_id": FortuneProvider.provider_id,
            "provider_version": FortuneProvider.provider_version,
            "mode": capability.mode,
        },
        ensure_ascii=False,
    )
    _finding(
        findings,
        re.search(r"unavailable|placeholder|validated-user-chart", placeholder_text, re.I)
        is None,
        "Fortune provider is placeholder-backed",
    )

    cases = list(fixture.get("cases") or ())
    profiles = fixture.get("natal_profiles") or {}
    case_ids = [str(case.get("id") or "") for case in cases if isinstance(case, Mapping)]
    _finding(findings, len(cases) >= 30, "Fortune has fewer than 30 route-owned fixtures")
    ids_unique = len(case_ids) == len(cases) == len(set(case_ids)) and all(case_ids)
    _finding(findings, ids_unique, "Fortune fixture case ids are not unique")
    categories = {
        str(case.get("category") or "")
        for case in cases
        if isinstance(case, Mapping)
    }
    for category in sorted(REQUIRED_BOUNDARY_CATEGORIES - categories):
        findings.append(f"Fortune missing boundary category: {category}")
    for case in cases:
        if not isinstance(case, Mapping):
            findings.append("Fortune fixture case is not an object")
            continue
        label = str(case.get("id") or "<missing>")
        if case.get("horizon") != {"kind": "day"}:
            findings.append(f"Fortune fixture horizon is not day-only: {label}")
        profile = profiles.get(str(case.get("profile_id") or "")) if isinstance(profiles, Mapping) else None
        if not isinstance(profile, Mapping) or not all(
            profile.get(field)
            for field in ("birth_datetime", "timezone", "location", "gender")
        ):
            findings.append(f"Fortune fixture profile is incomplete: {label}")
        try:
            datetime.fromisoformat(str(case["reference_datetime"]))
        except (KeyError, TypeError, ValueError):
            findings.append(f"Fortune fixture reference datetime is invalid: {label}")

    rows_by_source, source_artifact_mismatches = _audit_source_artifacts(
        fixture, findings
    )
    oracle_mismatches = 0
    for case in cases:
        if not isinstance(case, Mapping):
            oracle_mismatches += 1
            continue
        rows = rows_by_source.get(str(case.get("source_id") or ""))
        projection = _hko_projection(case, rows or [])
        try:
            reference_date = datetime.fromisoformat(
                str(case["reference_datetime"])
            ).date().isoformat()
        except (KeyError, TypeError, ValueError):
            reference_date = ""
        if (
            projection is None
            or projection["civil_date"] != reference_date
            or projection["chinese_year_ganzhi"]
            != case.get("expected_chinese_year_ganzhi")
            or projection["lunar"] != case.get("expected_lunar")
        ):
            findings.append(f"Fortune independent oracle mismatch: {case.get('id')}")
            oracle_mismatches += 1
        elif (
            STEMS[(int(projection["lunar"]["year"]) - 4) % 10]
            + BRANCHES[(int(projection["lunar"]["year"]) - 4) % 12]
            != projection["chinese_year_ganzhi"]
        ):
            findings.append(f"Fortune lunar-year Ganzhi mismatch: {case.get('id')}")
            oracle_mismatches += 1

    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(_load(MATRIX), ROOT)
    )
    algorithm_dependencies, algorithm_source_findings, source_verification = (
        _audit_algorithm_source(
            findings,
            research_root=resolved_research_root,
        )
    )

    qualifying_cases = 0
    provider_calculations = 0
    provider_extensions = 0
    deterministic_mismatches = 0
    extension_mismatches = 0
    execution_failures = 0
    structurally_executable = (
        not fixture_is_symlink
        and ids_unique
        and len(cases) >= 30
        and not any(
            finding.startswith("Fortune fixture case")
            or finding.startswith("Fortune fixture profile")
            or finding.startswith("Fortune fixture reference")
            for finding in findings
        )
    )
    if structurally_executable:
        for case in cases:
            case_id = str(case.get("id") or "<missing>")
            profile = profiles[str(case["profile_id"])]
            try:
                provider = FortuneProvider(ROOT)
                first = provider.calculate(_request(profile, case))
                provider_calculations += 1
                target = datetime.fromisoformat(
                    str(case["reference_datetime"])
                ).date().isoformat()
                first_extended = provider.extend(
                    first,
                    ("timing",),
                    {"kind": "day", "start": target, "end": target},
                )
                provider_extensions += 1
                second_provider = FortuneProvider(ROOT)
                second = second_provider.calculate(_request(profile, case))
                provider_calculations += 1
                second_extended = second_provider.extend(
                    second,
                    ("timing",),
                    {"kind": "day", "start": target, "end": target},
                )
                provider_extensions += 1
                case_failures = _audit_one_result(
                    case, first, first_extended
                ) + _audit_one_result(case, second, second_extended)
                findings.extend(case_failures)
                if first.result_hash != second.result_hash or first.facts != second.facts:
                    findings.append(f"Fortune calculation is nondeterministic: {case_id}")
                    deterministic_mismatches += 1
                first_extension = first_extended.fact_extension
                second_extension = second_extended.fact_extension
                if (
                    first_extension is None
                    or second_extension is None
                    or first_extension.extension_digest
                    != second_extension.extension_digest
                    or first_extension.facts != second_extension.facts
                ):
                    findings.append(f"Fortune extension is nondeterministic: {case_id}")
                    extension_mismatches += 1
                if (
                    not case_failures
                    and first.result_hash == second.result_hash
                    and first_extension is not None
                    and second_extension is not None
                    and first_extension.extension_digest
                    == second_extension.extension_digest
                    and first_extension.facts == second_extension.facts
                ):
                    qualifying_cases += 1
            except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
                findings.append(f"Fortune provider execution failed: {case_id}: {exc}")
                execution_failures += 1

    boundary_cases = sum(
        1
        for case in cases
        if isinstance(case, Mapping)
        and str(case.get("category") or "") in REQUIRED_BOUNDARY_CATEGORIES
    )
    findings = list(dict.fromkeys(findings))
    ready = not findings and qualifying_cases >= 30
    return {
        "schema_version": "mingli-fortune-completeness-audit-v1",
        "system": "fortune",
        "status": "pass" if ready else "fail",
        "provider_ready": ready,
        "provider": {
            "provider_id": FortuneProvider.provider_id,
            "provider_version": FortuneProvider.provider_version,
            "mode": capability.mode,
            "capability_mode": capability.mode,
            "horizons": list(capability.horizons),
            "algorithm_dependency_id": EXPECTED_DEPENDENCY_ID,
        },
        "route_owned_case_ids": case_ids,
        "fixture": {
            "path": str(fixture_path),
            "sha256": _sha256(fixture_path),
            "expected_sha256": EXPECTED_FIXTURE_SHA256,
        },
        "source_applicability": {
            "dependency_ids": [EXPECTED_DEPENDENCY_ID],
            "rule_trace_ids": ["fortune.single-target-day-v1"],
            "status": "verified" if ready else "blocked",
        },
        "source_verification": source_verification,
        "counts": {
            "fixture_cases": len(cases),
            "qualifying_cases": qualifying_cases,
            "route_owned_cases": len(cases),
            "boundary_cases": boundary_cases,
            "provider_calculations": provider_calculations,
            "provider_extensions": provider_extensions,
            "determinism_checks": qualifying_cases * 2,
            "boundary_case_count": boundary_cases,
            "oracle_mismatches": oracle_mismatches,
            "deterministic_mismatches": deterministic_mismatches,
            "extension_mismatches": extension_mismatches,
            "source_artifact_mismatches": source_artifact_mismatches,
            "algorithm_dependencies": algorithm_dependencies,
            "algorithm_source_findings": algorithm_source_findings,
            "execution_failures": execution_failures,
        },
        "boundary_categories": sorted(categories),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args()
    report = audit_fortune_provider(fixture_path=args.fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
