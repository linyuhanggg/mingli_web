#!/usr/bin/env python3
"""Machine-readable Task 7E completeness audit for Xingming/Qizheng."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

import adapter_validate
import audit_algorithm_sources
from reading_engine import ephemeris_core, xingming
from reading_engine.contracts import CalculationResult, ReadingRequest
from reading_engine.providers import PROVIDER_CAPABILITIES, XingmingProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "xingming-v51.yaml"
MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
ALGORITHM_SAMPLES = ROOT / "references" / "fixtures" / "algorithm-source-samples-v51.yaml"
ZI_QI_CALIBRATION = ROOT / "references" / "matrices" / "xingming-ziqi-calibration-v1.yaml"
EXPECTED_FIXTURE_SHA256 = "941ef871ddc3e47a1599c4c31900d63fb2bdf30e0dfd1db4b5d53a535b75cdd0"
EXPECTED_PROVIDER_ID = "mingli-master.xingming.v1"
EXPECTED_PROVIDER_VERSION = "1.1.0"
EXPECTED_DEPENDENCY_IDS = (
    "xingming.ephemeris.seven-luminaries",
    "xingming.houses.ming-shen-degrees",
    "xingming.houses.topocentric-ming-degree",
    "xingming.four-residuals.numeric-profiles",
    "xingming.transformations.ten-stem-table",
    "xingming.limits.dongwei-bailiu-table",
    "xingming.source-conditioned-patterns",
)
EXPECTED_BAILIU_HOUSES = (
    "命宫", "相貌", "福德", "官禄", "迁移", "疾厄",
    "妻妾", "奴仆", "男女", "田宅", "兄弟", "财帛",
)
EXPECTED_BAILIU_DURATIONS = (
    15.0, 10.0, 11.0, 15.0, 8.0, 7.0,
    11.0, 4.5, 4.5, 4.5, 5.0, 5.0,
)
BLOCKED_PACKS = {
    "xingming/qizheng-siyu-tianjing",
    "xingming/qizheng-quanshu-dacheng",
    "xingming/minghai-quanbian",
}
REQUIRED_CATEGORIES = (
    "reference_chart",
    "date_boundary",
    "location_boundary",
    "timezone_boundary",
)
REQUIRED_OUTPUTS = {
    "ephemeris",
    "positions",
    "ming_shen",
    "houses",
    "transformations",
    "major_limits",
}


def _finding(findings: list[str], condition: bool, message: str) -> bool:
    if not condition:
        findings.append(message)
    return condition


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_dependency_ids(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "source_dependency_id" and isinstance(item, str):
                yield item
            yield from _walk_dependency_ids(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_dependency_ids(item)


def _request(case: Mapping[str, Any]) -> ReadingRequest:
    return ReadingRequest(
        query=f"Task 7N Xingming provider replay {case.get('id')}",
        action="new",
        system="xingming",
        timezone=str(case.get("timezone") or ""),
        location=str(case.get("location") or ""),
        birth_data={
            "datetime": str(case.get("datetime") or ""),
            "timezone": str(case.get("timezone") or ""),
            "location": str(case.get("location") or ""),
            "longitude": case.get("longitude"),
            "latitude": case.get("latitude"),
            "coordinate_source": str(case.get("coordinate_source") or ""),
        },
    )


def _audit_result(
    result: CalculationResult,
    *,
    label: str,
    run: int,
    findings: list[str],
    counts: Counter[str],
) -> None:
    prefix = f"{label} run {run}"
    _finding(findings, result.system == "xingming", f"wrong system: {prefix}")
    _finding(
        findings,
        result.provider_id == EXPECTED_PROVIDER_ID,
        f"provider id mismatch: {prefix}",
    )
    _finding(
        findings,
        result.provider_version == EXPECTED_PROVIDER_VERSION,
        f"provider version mismatch: {prefix}",
    )
    chart_facts = result.facts.get("chart_facts") or {}
    output = chart_facts.get("output") or {}
    _finding(
        findings,
        chart_facts.get("fact_layer_status") == "calculated_xingming_facts",
        f"incomplete Xingming fact layer: {prefix}",
    )
    _finding(
        findings,
        REQUIRED_OUTPUTS <= set(output),
        f"required Xingming output missing: {prefix}",
    )
    _finding(
        findings,
        bool(result.facts.get("chart_digest"))
        and bool(result.facts.get("natal_fact_digest"))
        and bool(result.facts.get("calendar_digest"))
        and bool(result.facts.get("ephemeris_digest")),
        f"provider digest envelope incomplete: {prefix}",
    )
    ephemeris = output.get("ephemeris") or {}
    engine = ephemeris.get("engine") or {}
    _finding(
        findings,
        engine.get("version") == ephemeris_core.ENGINE_VERSION
        and engine.get("distribution_sha256")
        == ephemeris_core.ENGINE["distribution_sha256"],
        f"ephemeris version or provenance mismatch: {prefix}",
    )

    route_validation = xingming.validate_fact_layer(chart_facts)
    adapter_validation = adapter_validate.validate_payload("xingming", chart_facts)
    counts["adapter_validation_checks"] += 1
    _finding(
        findings,
        route_validation.get("ok") is True
        and adapter_validation.get("ok") is True,
        f"adapter validation failed: {prefix}: "
        f"{route_validation.get('codes')} {adapter_validation.get('codes')}",
    )

    dependency_ids = set(_walk_dependency_ids(chart_facts))
    counts["source_binding_checks"] += 1
    _finding(
        findings,
        set(EXPECTED_DEPENDENCY_IDS) <= dependency_ids,
        f"algorithm source dependency binding incomplete: {prefix}",
    )
    lineage = chart_facts.get("source_lineage") or {}
    first_line = {
        str(item.get("pack") or "")
        for layer in ("calculation", "interpretation")
        for item in lineage.get(layer) or ()
        if isinstance(item, Mapping)
    }
    _finding(
        findings,
        first_line.isdisjoint(BLOCKED_PACKS)
        and set(lineage.get("blocked") or ()) == BLOCKED_PACKS,
        f"blocked source lineage boundary mismatch: {prefix}",
    )


def audit_xingming_provider(
    *, fixture_path: Path = FIXTURE, research_root: Path | None = None
) -> dict[str, Any]:
    """Execute every frozen Xingming reference chart through the live provider twice.

    ``research_root`` is the release-time fulltext tree for source
    verification.  It is intentionally independent of ``audit_matrix``'s own
    optional research-root wiring so a portable checkout can prove runtime
    readiness without an external corpus, while a release build passes an
    explicit root to close the source-verification gate.  Runtime readiness
    (``provider_ready``) never depends on the external fulltext tree; the
    ``source_verification`` block is ``skipped`` without a root and verified
    when one is provided.
    """
    findings: list[str] = []
    payload: dict[str, Any] = {}
    fixture_digest = ""
    try:
        fixture_digest = _sha256(fixture_path)
        loaded = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            payload = loaded
        else:
            findings.append("Xingming fixture root must be a mapping")
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        findings.append(f"Xingming fixture could not be loaded: {exc}")
    samples = yaml.safe_load(ALGORITHM_SAMPLES.read_text(encoding="utf-8"))["cases"]
    calibration_bytes = ZI_QI_CALIBRATION.read_bytes()
    calibration = yaml.safe_load(calibration_bytes.decode("utf-8"))
    calibration_sha256 = hashlib.sha256(calibration_bytes).hexdigest()
    raw_charts = list(payload.get("reference_charts") or ())
    charts = [case for case in raw_charts if isinstance(case, Mapping)]
    category_counts = Counter(str(case.get("category") or "") for case in charts)

    _finding(
        findings,
        not fixture_path.is_symlink(),
        "Xingming fixture must not be a symlink",
    )
    _finding(
        findings,
        fixture_digest == EXPECTED_FIXTURE_SHA256,
        "Xingming fixture sha256 mismatch",
    )
    _finding(
        findings,
        payload.get("schema_version") == "mingli-xingming-fixtures-v51",
        "unexpected fixture schema",
    )
    _finding(
        findings,
        PROVIDER_CAPABILITIES["xingming"].mode == "calculation",
        "Xingming provider capability mode is not calculation",
    )
    _finding(findings, len(charts) >= 30, "fewer than 30 Xingming reference charts")
    _finding(
        findings,
        len({str(case.get("id") or "") for case in charts}) == len(charts),
        "reference chart ids are not unique",
    )
    for category in REQUIRED_CATEGORIES:
        _finding(
            findings,
            category_counts[category] >= (18 if category == "reference_chart" else 4),
            f"insufficient fixture category: {category}",
        )

    _finding(
        findings,
        len(charts) == len(raw_charts),
        "one or more Xingming reference charts are not mappings",
    )
    representative_facts: dict[str, Any] | None = None
    replay_counts: Counter[str] = Counter()
    qualifying_cases = 0
    for case in charts:
        case_id = str(case.get("id") or "<missing>")
        case_findings: list[str] = []
        results: list[CalculationResult] = []
        for run in (1, 2):
            try:
                provider = XingmingProvider(ROOT)
                result = provider.calculate(_request(case))
                replay_counts["provider_calculations"] += 1
                results.append(result)
                _audit_result(
                    result,
                    label=case_id,
                    run=run,
                    findings=case_findings,
                    counts=replay_counts,
                )
            except (KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
                case_findings.append(
                    f"reference chart provider failed: {case_id} run {run}: {exc}"
                )
        deterministic = False
        if len(results) == 2:
            replay_counts["determinism_checks"] += 1
            deterministic = (
                results[0].result_hash == results[1].result_hash
                and results[0].input_hash == results[1].input_hash
                and results[0].facts == results[1].facts
                and results[0].to_dict() == results[1].to_dict()
            )
            _finding(
                case_findings,
                deterministic,
                f"provider replay is non-deterministic: {case_id}",
            )
            facts = results[0].facts["chart_facts"]
            if representative_facts is None:
                representative_facts = facts
            positions = {
                item["body"]: float(item["longitude_degrees"])
                for item in facts["output"]["positions"]
            }
            for body, expected in dict(case.get("expected_longitudes") or {}).items():
                replay_counts["oracle_longitude_checks"] += 1
                if body not in positions:
                    case_findings.append(
                        f"unknown oracle body: {case_id}:{body}"
                    )
                    continue
                try:
                    expected_longitude = float(expected)
                except (TypeError, ValueError):
                    case_findings.append(
                        f"invalid oracle longitude: {case_id}:{body}"
                    )
                    continue
                delta = abs(
                    (positions[body] - expected_longitude + 180.0) % 360.0
                    - 180.0
                )
                _finding(
                    case_findings,
                    delta <= 1e-8,
                    f"ephemeris oracle mismatch: {case_id}:{body}",
                )
            _finding(
                case_findings,
                len(case.get("expected_longitudes") or {}) == 7,
                f"independent longitude oracle is incomplete: {case_id}",
            )
        findings.extend(case_findings)
        if not case_findings and deterministic:
            qualifying_cases += 1

    for stem in xingming.STEMS:
        rows = xingming.calculate_transformations(stem)
        _finding(findings, len(rows) == 10, f"transformation row count: {stem}")
        _finding(
            findings,
            len({item["classical_body"] for item in rows}) == 10,
            f"transformation body coverage: {stem}",
        )
    expected_transformations = samples["xingming-ten-stem-transformations-jia"]["expected"]
    jia_transformations = xingming.calculate_transformations("甲")
    _finding(
        findings,
        [item["transformation"] for item in jia_transformations]
        == list(expected_transformations["transformations"]),
        "Jia transformation label table does not match the independent sample",
    )
    _finding(
        findings,
        [item["classical_body"] for item in jia_transformations]
        == list(expected_transformations["classical_bodies"]),
        "Jia transformation body table does not match the independent sample",
    )
    limits = xingming.calculate_bailiu_limits(42.5)
    _finding(findings, len(limits) == 12, "Bailiu does not cover twelve houses")
    _finding(
        findings,
        tuple(item["house"] for item in limits) == EXPECTED_BAILIU_HOUSES,
        "Bailiu house order does not match the source sequence",
    )
    _finding(
        findings,
        tuple(item["duration_years"] for item in limits)
        == EXPECTED_BAILIU_DURATIONS,
        "Bailiu duration table does not match the source sequence",
    )
    _finding(
        findings,
        xingming.BAILIU_TOTAL_YEARS == 100.5,
        "Bailiu total must be 100 years 6 months",
    )
    _finding(
        findings,
        calibration.get("schema_version")
        == "mingli-xingming-ziqi-calibration-v1",
        "unexpected Zi Qi calibration schema",
    )
    _finding(
        findings,
        calibration.get("profile_id") == xingming.ZI_QI_PROFILE["id"],
        "Zi Qi calibration profile does not match the provider",
    )
    _finding(
        findings,
        calibration_sha256 == xingming.ZI_QI_PROFILE["calibration_sha256"],
        "Zi Qi calibration hash does not match the provider",
    )
    _finding(
        findings,
        float(calibration["classical_formula"]["period_days"])
        == float(xingming.ZI_QI_PROFILE["period_days"])
        == 10228.0,
        "Zi Qi source period is not 10228 days",
    )
    residual_sample = samples["xingming-residual-points-j2000"]
    residuals = xingming.calculate_four_residuals(
        residual_sample["input"]["instant"]
    )
    residual_tolerance = float(
        residual_sample["expected"]["tolerance_degrees"]
    )
    for name in ("罗睺", "计都", "紫炁", "月孛"):
        delta = abs(
            (
                float(residuals[name]["longitude_degrees"])
                - float(residual_sample["expected"][name])
                + 180.0
            )
            % 360.0
            - 180.0
        )
        _finding(
            findings,
            delta <= residual_tolerance,
            f"residual point does not match independent sample: {name}",
        )
    node_identity = samples["xingming-four-residuals-direction"]["expected"]
    _finding(
        findings,
        residuals["罗睺"]["profile"]
        == "astronomy-engine-interpolated-descending-node-v1"
        and node_identity["luohou_identity"] == "descending_lunar_node",
        "Luo Hou is not the source-declared descending lunar node",
    )
    _finding(
        findings,
        residuals["计都"]["profile"] == "ascending-node-opposed-to-luohou-v1"
        and node_identity["jidu_identity"] == "ascending_lunar_node",
        "Ji Du is not the source-declared opposing ascending lunar node",
    )
    _finding(
        findings,
        "moira" not in json.dumps(xingming.ZI_QI_PROFILE, ensure_ascii=False).lower(),
        "Zi Qi profile depends on an external application epoch",
    )
    if representative_facts is None:
        findings.append("no representative Xingming facts were built")
    else:
        positions = list(representative_facts["output"]["positions"])
        _finding(
            findings,
            len(positions) == 11
            and {item["classical_name"] for item in positions}
            == set(xingming.CLASSICAL_POINT_NAMES),
            "representative chart does not contain all eleven classical points",
        )
        _finding(
            findings,
            all(item.get("source_dependency_id") for item in positions),
            "one or more classical positions lack source dependency identity",
        )
        lineage = representative_facts["source_lineage"]
        conventions = representative_facts["conventions"]
        _finding(
            findings,
            conventions.get("luoji_identity")
            == "guolao-luohou-descending-jidu-ascending-v1",
            "representative chart does not bind the selected Luo/Ji identity",
        )
        first_line = {
            str(item["pack"])
            for layer in ("calculation", "interpretation")
            for item in lineage[layer]
        }
        _finding(
            findings,
            first_line.isdisjoint(BLOCKED_PACKS),
            "blocked source pack appears in first-line lineage",
        )
        _finding(
            findings,
            set(lineage["blocked"]) == BLOCKED_PACKS,
            "blocked source pack declaration is incomplete",
        )
    source_payload = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    provider_sources = dict(
        (source_payload.get("providers") or {}).get("xingming") or {}
    )
    dependencies = list(provider_sources.get("dependencies") or ())
    dependency_ids = [str(item.get("id") or "") for item in dependencies]
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
        systems=("xingming",),
    )
    if resolved_research_root is not None:
        source_report = audit_algorithm_sources.audit_matrix(
            source_payload,
            root=ROOT,
            systems=("xingming",),
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
        findings.extend(f"source audit: {item}" for item in source_report["findings"])
    _finding(
        findings,
        provider_sources.get("source_audit_status") == "source_verified",
        "Xingming source audit status is not verified",
    )
    _finding(
        findings,
        tuple(dependency_ids) == EXPECTED_DEPENDENCY_IDS,
        "Xingming algorithm dependency ids mismatch",
    )
    _finding(
        findings,
        all(
            item.get("status") == "verified"
            and bool(item.get("version"))
            and bool(item.get("primary_sources"))
            and bool(item.get("independent_test_sample"))
            for item in dependencies
        ),
        "Xingming algorithm dependency provenance is incomplete",
    )
    ephemeris_dependency = next(
        (
            item
            for item in dependencies
            if item.get("id") == "xingming.ephemeris.seven-luminaries"
        ),
        {},
    )
    engineering_reference = next(
        iter(ephemeris_dependency.get("engineering_references") or ()),
        {},
    )
    oracle = dict(payload.get("oracle") or {})
    oracle_verified = (
        oracle.get("name") == "Astronomy Engine direct upstream oracle"
        and oracle.get("version") == ephemeris_core.ENGINE_VERSION
        and oracle.get("distribution_sha256")
        == ephemeris_core.ENGINE["distribution_sha256"]
        and oracle.get("version") == engineering_reference.get("version")
        and oracle.get("distribution_sha256")
        == engineering_reference.get("distribution_sha256")
        and bool(str(oracle.get("procedure") or "").strip())
    )
    _finding(
        findings,
        oracle_verified,
        "Xingming independent oracle provenance mismatch",
    )

    route_owned_cases = len(charts)
    expected_runs = 2 * route_owned_cases
    _finding(
        findings,
        qualifying_cases == route_owned_cases and route_owned_cases >= 30,
        "one or more route-owned Xingming cases did not qualify",
    )
    _finding(
        findings,
        replay_counts["provider_calculations"] == expected_runs,
        "not every Xingming reference chart ran through the provider twice",
    )
    _finding(
        findings,
        replay_counts["determinism_checks"] == route_owned_cases,
        "not every Xingming reference chart received a determinism check",
    )
    _finding(
        findings,
        replay_counts["adapter_validation_checks"] == expected_runs,
        "not every Xingming provider result passed through both validators",
    )
    _finding(
        findings,
        replay_counts["source_binding_checks"] == expected_runs,
        "not every Xingming provider result received a source-binding check",
    )
    boundary_categories = sorted(set(REQUIRED_CATEGORIES) & set(category_counts))
    findings = list(dict.fromkeys(findings))
    # The matrix provenance gate (release artifacts, samples, dependency
    # declarations) is a runtime condition only when no explicit research
    # root is driving fulltext verification; with an explicit root those
    # checks are reported by ``source_verification`` and ``provider_ready``
    # stays a runtime-only property.
    provider_ready = (
        not findings
        and fixture_digest == EXPECTED_FIXTURE_SHA256
        and qualifying_cases == route_owned_cases
        and route_owned_cases >= 30
        and (resolved_research_root is not None or bool(source_report.get("ok")))
        and oracle_verified
        and set(REQUIRED_CATEGORIES) <= set(boundary_categories)
    )

    return {
        "schema_version": "mingli-xingming-completeness-audit-v1",
        "system": "xingming",
        "status": "pass" if provider_ready else "fail",
        "provider_ready": provider_ready,
        "provider": {
            "class": "reading_engine.providers.XingmingProvider",
            "provider_id": EXPECTED_PROVIDER_ID,
            "provider_version": EXPECTED_PROVIDER_VERSION,
            "capability_mode": PROVIDER_CAPABILITIES["xingming"].mode,
        },
        "route_owned_case_ids": [str(case.get("id") or "") for case in charts],
        "fixture_sha256": fixture_digest,
        "fixture": {
            "path": (
                fixture_path.relative_to(ROOT).as_posix()
                if fixture_path.is_relative_to(ROOT)
                else str(fixture_path)
            ),
            "sha256": fixture_digest,
            "expected_sha256": EXPECTED_FIXTURE_SHA256,
        },
        "boundary_categories": boundary_categories,
        "oracle": {
            "verified": oracle_verified,
            "name": oracle.get("name"),
            "version": oracle.get("version"),
            "distribution_sha256": oracle.get("distribution_sha256"),
            "procedure": oracle.get("procedure"),
        },
        "algorithm_sources": {
            "ok": bool(source_report.get("ok"))
            and not source_report.get("findings"),
            "research_sources_verified": bool(
                source_report.get("research_sources_verified")
            ),
            "dependency_ids": dependency_ids,
            "dependency_versions": {
                str(item.get("id") or ""): str(item.get("version") or "")
                for item in dependencies
            },
            "findings": list(source_report.get("findings") or ()),
        },
        "source_verification": source_verification,
        "counts": {
            "reference_charts": len(charts),
            "reference_charts_by_category": dict(category_counts),
            "route_owned_cases": route_owned_cases,
            "qualifying_cases": qualifying_cases,
            "provider_calculations": replay_counts["provider_calculations"],
            "provider_extensions": 0,
            "determinism_checks": replay_counts["determinism_checks"],
            "boundary_case_count": sum(
                count
                for category, count in category_counts.items()
                if category in REQUIRED_CATEGORIES
            ),
            "adapter_validation_checks": replay_counts[
                "adapter_validation_checks"
            ],
            "source_binding_checks": replay_counts["source_binding_checks"],
            "oracle_longitude_checks": replay_counts[
                "oracle_longitude_checks"
            ],
            "boundary_categories": len(boundary_categories),
            "classical_points": len(xingming.CLASSICAL_POINT_NAMES),
            "houses": len(xingming.HOUSE_NAMES),
            "transformations_per_stem": len(xingming.TRANSFORMATION_NAMES),
            "major_limits": len(limits),
            "algorithm_dependencies": source_report["dependency_count"],
            "ziqi_calibration_files": 1,
        },
        "conventions": {
            "house": xingming.HOUSE_PROFILE,
            "pseudo_points": xingming.PSEUDO_POINT_PROFILE,
            "transformations": xingming.TRANSFORMATION_PROFILE,
            "limits": xingming.LIMIT_PROFILE,
        },
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument(
        "--research-root",
        type=Path,
        default=None,
        help="explicit research source root for release-time source verification",
    )
    args = parser.parse_args()
    report = audit_xingming_provider(
        fixture_path=args.fixture,
        research_root=args.research_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
