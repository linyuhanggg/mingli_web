#!/usr/bin/env python3
"""Machine-readable Task 7N completeness audit for the live Ziwei provider."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

import audit_algorithm_sources
from reading_engine.contracts import CalculationResult, ReadingRequest
from reading_engine.providers import ZiweiProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "ziwei-v51.yaml"
SOURCE_MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
MINIMUM_FIXTURE_CASES = 30
EXPECTED_FIXTURE_SHA256 = (
    "a96fc9f3d3d29f67f58409ace766d6430020c2d0f5f72efdf09e2f6438ead9f5"
)
REQUIRED_CATEGORIES = (
    "known_chart",
    "leap_month",
    "zi_hour",
    "direction",
    "limit_boundary",
    "temporal_transformations",
)
EXPECTED_PROVIDER_CLASS = "reading_engine.providers.ZiweiProvider"
EXPECTED_PROVIDER_ID = "mingli-master.ziwei.iztro"
EXPECTED_PROVIDER_VERSION = "1.2.0+iztro-2.5.8"
EXPECTED_DEPENDENCY_IDS = (
    "ziwei.iztro.natal-palaces-stars-transformations",
    "ziwei.iztro.decadal-year-month-horoscope",
    "ziwei.iztro.leap-hour-major-limit-conventions",
    "ziwei.source-conditioned-patterns",
)
EXPECTED_ENGINE_DEPENDENCY_IDS = frozenset(EXPECTED_DEPENDENCY_IDS[:3])
INDEPENDENT_ORACLE_CASE_ID = "known-public-1970"
INDEPENDENT_ORACLE_SHA256 = (
    "84c3db3b9ed415883341f2af74d74384b3fa22b0a2dc432c04e6c549e2ecb826"
)
TRANSFORMATION_ORDER = ("禄", "权", "科", "忌")


def _emit_audit_progress(
    progress: Callable[..., None] | None,
    stage: str,
    **fields: object,
) -> None:
    if progress is not None:
        progress(stage, **fields)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_digest(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _finding(findings: list[str], condition: bool, message: str) -> None:
    if not condition and message not in findings:
        findings.append(message)


def _mismatch(
    findings: list[str],
    case_id: str,
    field: str,
    actual: Any,
    expected: Any,
) -> bool:
    matches = actual == expected
    _finding(findings, matches, f"fixture mismatch: {case_id}:{field}")
    return matches


def _provider_class_name() -> str:
    return f"{ZiweiProvider.__module__}.{ZiweiProvider.__qualname__}"


def _request(case: Mapping[str, Any], contract: Mapping[str, Any]) -> ReadingRequest:
    supplied = dict(case.get("input") or {})
    timezone = str(supplied.get("timezone") or contract.get("timezone") or "")
    location = str(supplied.get("location") or contract.get("location") or "")
    birth_data = {
        "datetime": str(supplied.get("datetime") or ""),
        "timezone": timezone,
        "location": location,
        "gender": str(supplied.get("gender") or ""),
        "zi_hour_policy": str(supplied.get("zi_hour_policy") or "midnight"),
    }
    return ReadingRequest(
        query=f"Task 7N Ziwei fixture {case.get('id')}",
        action="new",
        system="ziwei",
        timezone=timezone,
        location=location,
        birth_data=birth_data,
    )


def _render_transformations(rows: list[dict[str, Any]]) -> list[str]:
    ordered = sorted(
        rows,
        key=lambda item: TRANSFORMATION_ORDER.index(str(item["transformation"])),
    )
    return [
        f"{item['star']}{item['transformation']}@{item['palace']}"
        for item in ordered
    ]


def _first_palace_projection(output: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(output.get("palaces") or ())
    if not rows:
        return {}
    first = dict(rows[0])
    return {
        "name": first.get("name"),
        "earthly_branch": first.get("earthlyBranch"),
        "major_stars": [
            {
                "name": star.get("name"),
                "brightness": star.get("brightness"),
                "mutagen": star.get("mutagen"),
            }
            for star in first.get("majorStars") or ()
        ],
    }


def _segment_at(
    rows: list[dict[str, Any]],
    target_date: str,
    layer_key: str,
) -> dict[str, Any]:
    for row in rows:
        if str(row.get("start_inclusive") or "") <= target_date < str(
            row.get("end_exclusive") or ""
        ):
            layer = row.get(layer_key)
            return dict(layer) if isinstance(layer, dict) else {}
    return {}


def _extension_layers(
    base: CalculationResult,
    extended: CalculationResult,
    target_date: str,
) -> dict[str, dict[str, Any]]:
    extension = extended.fact_extension
    if extension is None:
        return {"major": {}, "annual": {}, "monthly": {}}
    facts = extension.facts
    year = target_date[:4]
    month = target_date[:7]
    annual = dict((facts.get("annual_layers") or {}).get(year) or {})
    monthly = dict((facts.get("monthly_layers") or {}).get(month) or {})
    major_layer = _segment_at(
        list(facts.get("active_major_limit_segments") or ()),
        target_date,
        "major_limit",
    )
    annual_layer = _segment_at(
        list(annual.get("segments") or ()),
        target_date,
        "liu_nian",
    )
    monthly_layer = _segment_at(
        list(monthly.get("segments") or ()),
        target_date,
        "liu_yue",
    )
    palaces = list(
        ((base.facts.get("chart_facts") or {}).get("output") or {}).get("palaces")
        or ()
    )
    by_index = {
        int(item["index"]): item
        for item in palaces
        if isinstance(item, dict) and isinstance(item.get("index"), int)
    }
    active_palace = by_index.get(major_layer.get("index"), {})
    if major_layer:
        major_layer["active_natal_palace"] = {
            "name": active_palace.get("name"),
            "branch": active_palace.get("earthlyBranch"),
        }
    return {
        "major": major_layer,
        "annual": annual_layer,
        "monthly": monthly_layer,
    }


def _check_base_case(
    findings: list[str],
    case: Mapping[str, Any],
    result: CalculationResult,
) -> dict[str, Any] | None:
    case_id = str(case.get("id") or "")
    expected = dict(case.get("expected") or {})
    chart_facts = dict(result.facts.get("chart_facts") or {})
    output = dict(chart_facts.get("output") or {})
    calendar = dict(chart_facts.get("calendar_normalization") or {})
    lunar = dict(calendar.get("lunar_date") or {})

    _finding(findings, result.system == "ziwei", f"provider system mismatch: {case_id}")
    _finding(
        findings,
        result.provider_id == EXPECTED_PROVIDER_ID,
        f"provider id mismatch: {case_id}",
    )
    _finding(
        findings,
        result.provider_version == EXPECTED_PROVIDER_VERSION,
        f"provider version mismatch: {case_id}",
    )
    _finding(
        findings,
        chart_facts.get("fact_layer_status")
        == "calculated_ziwei_chart_from_birth_datetime",
        f"placeholder or incomplete fact layer: {case_id}",
    )
    _finding(
        findings,
        output.get("interpretation_status") == "facts_only",
        f"interpretation leaked into fact layer: {case_id}",
    )
    _finding(
        findings,
        len(output.get("palaces") or ()) == 12,
        f"incomplete twelve-palace layer: {case_id}",
    )
    _finding(
        findings,
        bool(output.get("stars")) and len(output.get("sihua") or ()) == 4,
        f"incomplete star or Sihua layer: {case_id}",
    )
    _finding(
        findings,
        len(output.get("major_limits") or ()) == 12,
        f"incomplete major-limit layer: {case_id}",
    )
    _finding(
        findings,
        bool(result.facts.get("natal_fact_digest")),
        f"missing natal fact digest: {case_id}",
    )

    if "lunar" in expected:
        _mismatch(
            findings,
            case_id,
            "lunar",
            [lunar.get("month"), lunar.get("day"), lunar.get("is_leap_month")],
            list(expected["lunar"]),
        )
    if "ganzhi" in expected:
        ganzhi = dict(calendar.get("ganzhi") or {})
        _mismatch(
            findings,
            case_id,
            "ganzhi",
            [ganzhi.get(key) for key in ("year", "month", "day", "hour")],
            list(expected["ganzhi"]),
        )
    if "ming_shen" in expected:
        ming_shen = dict(output.get("ming_shen") or {})
        _mismatch(
            findings,
            case_id,
            "ming_shen",
            [ming_shen.get("ming_branch"), ming_shen.get("shen_branch")],
            list(expected["ming_shen"]),
        )
    if "five_elements_class" in expected:
        _mismatch(
            findings,
            case_id,
            "five_elements_class",
            output.get("five_elements_class"),
            expected["five_elements_class"],
        )
    if "transformations" in expected:
        layer = list(
            ((output.get("transformation_layers") or {}).get("natal") or ())
        )
        _mismatch(
            findings,
            case_id,
            "transformations",
            _render_transformations(layer),
            list(expected["transformations"]),
        )
    if "first_palace" in expected:
        _mismatch(
            findings,
            case_id,
            "first_palace",
            _first_palace_projection(output),
            dict(expected["first_palace"]),
        )

    category = str(case.get("category") or "")
    if category == "leap_month":
        _finding(
            findings,
            ((chart_facts.get("adapter") or {}).get("engine_contract") or {}).get(
                "fix_leap"
            )
            is True,
            f"leap-month profile is not fixed: {case_id}",
        )
    elif category == "zi_hour":
        normalized = dict((chart_facts.get("input") or {}).get("normalized_input") or {})
        engine_input = dict(normalized.get("ziwei_engine_input") or {})
        _mismatch(
            findings,
            case_id,
            "time_index",
            engine_input.get("time_index"),
            expected.get("time_index"),
        )
        _mismatch(
            findings,
            case_id,
            "engine_solar_date",
            output.get("solar_date"),
            expected.get("engine_solar_date"),
        )
        chinese_parts = str(output.get("chinese_date") or "").split()
        _mismatch(
            findings,
            case_id,
            "day_pillar",
            chinese_parts[2] if len(chinese_parts) > 2 else None,
            expected.get("day_pillar"),
        )
        _mismatch(findings, case_id, "time", output.get("time"), expected.get("time"))
    elif category == "direction":
        direction = dict(output.get("major_limit_direction") or {})
        for field in ("year_stem", "year_polarity", "direction"):
            _mismatch(
                findings,
                case_id,
                field,
                direction.get(field),
                expected.get(field),
            )
        ordered = sorted(
            output.get("major_limits") or (),
            key=lambda row: int(row.get("sequence") or 0),
        )
        _mismatch(
            findings,
            case_id,
            "first_palaces",
            [row.get("palace") for row in ordered[:3]],
            list(expected.get("first_palaces") or ()),
        )

    if case_id == INDEPENDENT_ORACLE_CASE_ID:
        first_palace = _first_palace_projection(output)
        ganzhi = dict(calendar.get("ganzhi") or {})
        projection = {
            "ganzhi": [ganzhi.get(key) for key in ("year", "month", "day", "hour")],
            "first_palace": first_palace,
        }
        oracle = dict(case.get("oracle") or {})
        expected_projection = {
            "ganzhi": list(expected.get("ganzhi") or ()),
            "first_palace": dict(expected.get("first_palace") or {}),
        }
        oracle_metadata_ok = oracle == {
            "kind": "fixed_independent_public_benchmark",
            "source_dependency_id": EXPECTED_DEPENDENCY_IDS[0],
            "source_path": "references/matrices/algorithm-source-dependencies.yaml",
            "source_anchor": "ziwei-public-benchmark-1970-07-22",
            "independence": (
                "expected chart facts are stored outside ZiweiProvider and are never "
                "generated during audit"
            ),
        }
        oracle_digest_ok = (
            _canonical_digest(expected_projection) == INDEPENDENT_ORACLE_SHA256
        )
        _finding(findings, oracle_metadata_ok, "independent oracle metadata mismatch")
        _finding(findings, oracle_digest_ok, "independent oracle contract digest mismatch")
        return {
            "passed": projection == expected_projection
            and oracle_metadata_ok
            and oracle_digest_ok,
            "ganzhi": projection["ganzhi"],
            "palace": [first_palace.get("name"), first_palace.get("earthly_branch")],
            "major_stars": [
                [row.get("name"), row.get("brightness"), row.get("mutagen")]
                for row in first_palace.get("major_stars") or ()
            ],
            "source_dependency_id": oracle.get("source_dependency_id"),
        }
    return None


def _check_temporal_case(
    findings: list[str],
    case: Mapping[str, Any],
    base: CalculationResult,
    extended: CalculationResult,
) -> None:
    case_id = str(case.get("id") or "")
    source = dict(case.get("input") or {})
    expected = dict(case.get("expected") or {})
    target_date = str(source.get("target_date") or "")
    extension = extended.fact_extension
    _finding(
        findings,
        extension is not None and extension.status == "complete",
        f"provider extension incomplete: {case_id}",
    )
    if extension is None or extension.status != "complete":
        return
    calendar_coverage = (
        extension.facts.get("calendar_coverage")
        if isinstance(extension.facts.get("calendar_coverage"), dict)
        else {}
    )
    _finding(
        findings,
        calendar_coverage.get("requested_target_date") == target_date,
        f"provider extension target_date binding mismatch: {case_id}",
    )
    layers = _extension_layers(base, extended, target_date)
    if str(case.get("category") or "") == "limit_boundary":
        major = layers["major"]
        _mismatch(findings, case_id, "limit_index", major.get("index"), expected.get("index"))
        _mismatch(
            findings,
            case_id,
            "limit_stem_branch",
            str(major.get("heavenlyStem") or "") + str(major.get("earthlyBranch") or ""),
            expected.get("stem_branch"),
        )
        _mismatch(
            findings,
            case_id,
            "limit_natal_palace",
            (major.get("active_natal_palace") or {}).get("name"),
            expected.get("natal_palace"),
        )
    else:
        for fixture_scope, layer_name in (
            ("major", "major"),
            ("annual", "annual"),
            ("monthly", "monthly"),
        ):
            layer = layers[layer_name]
            _mismatch(
                findings,
                case_id,
                f"{fixture_scope}_transformations",
                _render_transformations(list(layer.get("transformation_facts") or ())),
                list(expected.get(fixture_scope) or ()),
            )


def _run_extension_pair(
    provider: ZiweiProvider,
    bases: tuple[CalculationResult, CalculationResult],
    requested_dimensions: tuple[str, ...],
    horizon: dict[str, Any],
    findings: list[str],
    label: str,
) -> tuple[list[CalculationResult], int]:
    results: list[CalculationResult] = []
    runs = 0
    for base in bases:
        runs += 1
        try:
            results.append(provider.extend(base, requested_dimensions, dict(horizon)))
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"provider extension failed: {label}: {exc}")
    if len(results) == 2:
        _finding(
            findings,
            results[0].fact_extension is not None
            and results[1].fact_extension is not None
            and results[0].fact_extension.to_dict() == results[1].fact_extension.to_dict(),
            f"provider extension is not deterministic: {label}",
        )
    return results, runs


def audit_ziwei_provider(
    *,
    fixture_path: Path = FIXTURE,
    source_matrix_path: Path = SOURCE_MATRIX,
    research_root: Path | None = None,
    progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    """Audit the live Ziwei provider against frozen V5.1 fixtures.

    ``research_root`` is the release-time fulltext tree for source
    verification.  It is intentionally independent of ``audit_matrix``'s own
    optional research-root wiring so a portable checkout can prove runtime
    readiness without an external corpus, while a release build passes an
    explicit root to close the source-verification gate.  Runtime readiness
    (``provider_ready``) never depends on the external fulltext tree; the
    ``source_verification`` block is ``skipped`` without a root and verified
    when one is provided.
    """
    payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8")) or {}
    contract = dict(payload.get("provider_contract") or {})
    cases = list(payload.get("cases") or ())
    findings: list[str] = []
    provider = ZiweiProvider(ROOT)
    _emit_audit_progress(
        progress,
        "ziwei_fixture_replay",
        completed=0,
        total=len(cases),
    )
    category_counts = Counter(str(case.get("category") or "") for case in cases)
    fixture_sha256 = _sha256(fixture_path)
    _finding(
        findings,
        fixture_sha256 == EXPECTED_FIXTURE_SHA256,
        "Ziwei fixture artifact hash mismatch",
    )

    _finding(
        findings,
        payload.get("schema_version") == "mingli-ziwei-fixtures-v51",
        "unexpected fixture schema",
    )
    _finding(
        findings,
        len(cases) >= MINIMUM_FIXTURE_CASES,
        "fewer than 30 route-owned fixtures",
    )
    _finding(
        findings,
        len({str(case.get("id") or "") for case in cases}) == len(cases),
        "route-owned fixture ids are not unique",
    )
    _finding(
        findings,
        all(str(case.get("id") or "") for case in cases),
        "route-owned fixture has an empty id",
    )
    for category in REQUIRED_CATEGORIES:
        _finding(
            findings,
            category_counts[category] > 0,
            f"missing Ziwei boundary category: {category}",
        )

    _finding(
        findings,
        contract.get("system") == "ziwei",
        "provider contract system mismatch",
    )
    _finding(
        findings,
        contract.get("provider_class") == EXPECTED_PROVIDER_CLASS,
        "provider contract class mismatch",
    )
    _finding(
        findings,
        contract.get("provider_id") == provider.provider_id == EXPECTED_PROVIDER_ID,
        "provider contract id mismatch",
    )
    _finding(
        findings,
        contract.get("provider_version")
        == provider.provider_version
        == EXPECTED_PROVIDER_VERSION,
        "provider contract version mismatch",
    )
    _finding(
        findings,
        _provider_class_name() == EXPECTED_PROVIDER_CLASS,
        "runtime provider class is not ZiweiProvider",
    )
    _finding(
        findings,
        provider.capability.mode == "calculation",
        "Ziwei provider is not in calculation mode",
    )
    _finding(
        findings,
        tuple(provider.capability.horizons) == ("month", "year", "life"),
        "Ziwei provider horizons are incomplete or undeclared",
    )
    _finding(
        findings,
        set(provider.capability.outputs)
        == {
            "ming_shen",
            "palaces",
            "stars",
            "sihua",
            "interpretive_candidates",
            "source_conditioned_patterns",
        },
        "Ziwei provider declared outputs are incomplete",
    )
    _finding(
        findings,
        int(contract.get("minimum_fixture_cases") or 0) == MINIMUM_FIXTURE_CASES,
        "provider contract fixture threshold mismatch",
    )
    _finding(
        findings,
        tuple(contract.get("required_boundary_categories") or ()) == REQUIRED_CATEGORIES,
        "provider contract boundary categories mismatch",
    )
    _finding(
        findings,
        tuple(contract.get("algorithm_dependency_ids") or ())
        == EXPECTED_DEPENDENCY_IDS,
        "provider contract algorithm dependencies mismatch",
    )

    calculation_runs = 0
    calculation_pairs = 0
    extension_runs = 0
    extension_pairs = 0
    temporal_extension_cases = sum(
        1 for case in cases if (case.get("input") or {}).get("target_date")
    )
    independent_oracle_checks: dict[str, Any] = {}
    bases_by_case: dict[str, tuple[CalculationResult, CalculationResult]] = {}
    source_dependency_bindings_complete = True
    qualifying_cases = 0

    for index, case in enumerate(cases):
        _emit_audit_progress(
            progress,
            "ziwei_fixture_replay",
            completed=index,
            total=len(cases),
            case_id=str(case.get("id") or ""),
        )
        case_findings_start = len(findings)
        case_id = str(case.get("id") or "")
        request = _request(case, contract)
        results: list[CalculationResult] = []
        for _ in range(2):
            calculation_runs += 1
            try:
                results.append(provider.calculate(request))
            except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                findings.append(f"provider calculation failed: {case_id}: {exc}")
        if len(results) != 2:
            continue
        calculation_pairs += 1
        first, second = results
        _finding(
            findings,
            first.result_hash == second.result_hash
            and first.input_hash == second.input_hash
            and first.to_dict() == second.to_dict(),
            f"provider calculation is not deterministic: {case_id}",
        )
        bases_by_case[case_id] = (first, second)
        oracle_check = _check_base_case(findings, case, first)
        if oracle_check is not None:
            independent_oracle_checks[case_id] = oracle_check

        chart_facts = dict(first.facts.get("chart_facts") or {})
        engine_contract = dict(
            ((chart_facts.get("adapter") or {}).get("engine_contract") or {})
        )
        dependency_ids = set(engine_contract.get("source_dependency_ids") or ())
        binding_ok = dependency_ids == EXPECTED_ENGINE_DEPENDENCY_IDS
        source_dependency_bindings_complete = (
            source_dependency_bindings_complete and binding_ok
        )
        _finding(
            findings,
            binding_ok,
            f"source dependency binding mismatch: {case_id}",
        )

        target_date = str((case.get("input") or {}).get("target_date") or "")
        if target_date:
            month = target_date[:7]
            requested_dimensions = (
                ("state",)
                if str(case.get("category") or "")
                == "temporal_transformations"
                else ("timing",)
            )
            extended, runs = _run_extension_pair(
                provider,
                (first, second),
                requested_dimensions,
                {
                    "kind": "month",
                    "start": month,
                    "end": month,
                    "target_date": target_date,
                },
                findings,
                case_id,
            )
            extension_runs += runs
            if len(extended) == 2:
                extension_pairs += 1
                _check_temporal_case(findings, case, first, extended[0])
        if len(findings) == case_findings_start:
            qualifying_cases += 1
        _emit_audit_progress(
            progress,
            "ziwei_fixture_replay",
            completed=index + 1,
            total=len(cases),
            case_id=case_id,
        )

    declared_horizon_coverage = {"life": False, "month": temporal_extension_cases > 0, "year": False}
    horizon_probes = (
        (
            "life",
            INDEPENDENT_ORACLE_CASE_ID,
            ("career",),
            {"kind": "life"},
        ),
        (
            "year",
            "direction-yang-male",
            ("timing",),
            {"kind": "year", "start": "2026", "end": "2026"},
        ),
    )
    for kind, case_id, dimensions, horizon in horizon_probes:
        _emit_audit_progress(
            progress,
            "ziwei_horizon_probe",
            kind=kind,
            case_id=case_id,
        )
        bases = bases_by_case.get(case_id)
        if bases is None:
            findings.append(f"declared horizon probe lacks base calculation: {kind}")
            continue
        extended, runs = _run_extension_pair(
            provider,
            bases,
            dimensions,
            horizon,
            findings,
            f"declared-{kind}-horizon",
        )
        extension_runs += runs
        if len(extended) != 2:
            continue
        extension_pairs += 1
        extension = extended[0].fact_extension
        complete = extension is not None and extension.status == "complete"
        if kind == "life" and complete:
            complete = (
                (extension.facts.get("dimension_fact_scope") or {})
                .get("career", {})
                .get("scope")
                == "calculated_natal_ziwei_chart"
            )
        elif kind == "year" and complete:
            complete = "2026" in (extension.facts.get("annual_layers") or {})
        declared_horizon_coverage[kind] = complete
        _finding(findings, complete, f"declared horizon probe incomplete: {kind}")

    _finding(
        findings,
        set(independent_oracle_checks) == {INDEPENDENT_ORACLE_CASE_ID}
        and independent_oracle_checks[INDEPENDENT_ORACLE_CASE_ID].get("passed") is True,
        "independent 1970 benchmark did not pass",
    )

    _emit_audit_progress(progress, "ziwei_source_contract_checks")
    source_payload = yaml.safe_load(source_matrix_path.read_text(encoding="utf-8"))
    provider_sources = dict((source_payload.get("providers") or {}).get("ziwei") or {})
    source_dependency_ids = [
        str(item.get("id") or "")
        for item in provider_sources.get("dependencies") or ()
    ]
    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(source_payload, ROOT)
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    # The runtime matrix audit stays research-root-free: its structural
    # findings (schema, dependencies, release-located sources) are runtime
    # readiness properties.  The fulltext-tree checks run only inside the
    # release-time ``source_verification`` gate, so an explicit research root
    # can never flip ``provider_ready``.
    source_report = audit_algorithm_sources.audit_matrix(
        source_payload,
        root=ROOT,
        systems=("ziwei",),
    )
    if resolved_research_root is not None:
        source_report = audit_algorithm_sources.audit_matrix(
            source_payload,
            root=ROOT,
            systems=("ziwei",),
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
            f"algorithm source audit: {item}"
            for item in source_report.get("findings") or ()
        )
    _finding(
        findings,
        tuple(source_dependency_ids) == EXPECTED_DEPENDENCY_IDS,
        "source matrix dependency ids mismatch",
    )
    source_matrix_text = source_matrix_path.read_text(encoding="utf-8")
    _finding(
        findings,
        "ziwei-public-benchmark-1970-07-22" in source_matrix_text,
        "independent oracle source anchor is missing",
    )

    boundary_coverage = {
        category: category_counts[category] > 0 for category in REQUIRED_CATEGORIES
    }
    provider_ready = not findings
    _emit_audit_progress(
        progress,
        "ziwei_report",
        provider_ready=provider_ready,
        qualifying_cases=qualifying_cases,
    )
    return {
        "schema_version": "mingli-ziwei-provider-audit-v1",
        "system": "ziwei",
        "status": "pass" if provider_ready else "fail",
        "provider_ready": provider_ready,
        "provider": {
            "class": _provider_class_name(),
            "provider_id": provider.provider_id,
            "provider_version": provider.provider_version,
            "capability_mode": provider.capability.mode,
        },
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
                "ziwei_route_fixture": fixture_sha256,
            },
        },
        "counts": {
            "fixture_cases": len(cases),
            "provider_regression_cases": len(cases),
            "qualifying_cases": qualifying_cases,
            "route_owned_cases": len(cases),
            "fixtures_by_category": dict(category_counts),
            "provider_calculation_runs": calculation_runs,
            "provider_calculations": calculation_runs,
            "calculation_determinism_pairs": calculation_pairs,
            "temporal_fixture_extension_cases": temporal_extension_cases,
            "declared_horizon_probe_cases": len(horizon_probes),
            "extension_cases": temporal_extension_cases + len(horizon_probes),
            "provider_extension_runs": extension_runs,
            "provider_extensions": extension_runs,
            "extension_determinism_pairs": extension_pairs,
            "determinism_checks": calculation_pairs + extension_pairs,
            "boundary_case_count": len(cases),
            "algorithm_dependencies": int(source_report.get("dependency_count") or 0),
            "independent_oracles": len(independent_oracle_checks),
        },
        "boundary_coverage": boundary_coverage,
        "boundary_categories": sorted(
            category for category, covered in boundary_coverage.items() if covered
        ),
        "declared_horizon_coverage": declared_horizon_coverage,
        "source_dependency_bindings_complete": source_dependency_bindings_complete,
        "independent_oracle_checks": independent_oracle_checks,
        "algorithm_sources": {
            "ok": bool(source_report.get("ok")),
            "research_sources_verified": bool(
                source_report.get("research_sources_verified")
            ),
            "dependency_ids": source_dependency_ids,
            "findings": list(source_report.get("findings") or ()),
        },
        "source_verification": source_verification,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--source-matrix", type=Path, default=SOURCE_MATRIX)
    parser.add_argument(
        "--research-root",
        type=Path,
        default=None,
        help="explicit research source root for release-time source verification",
    )
    args = parser.parse_args()
    report = audit_ziwei_provider(
        fixture_path=args.fixture,
        source_matrix_path=args.source_matrix,
        research_root=args.research_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
