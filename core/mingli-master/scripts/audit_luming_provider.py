#!/usr/bin/env python3
"""Fail-closed Task 7N live-provider audit for early Luming/Nayin."""

from __future__ import annotations

import argparse
import hashlib
import re
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Callable

import yaml

import audit_algorithm_sources
from reading_engine import luming
from reading_engine.contracts import CalculationResult, ReadingRequest
from reading_engine.providers import PROVIDER_CAPABILITIES, LumingProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "luming-v51.yaml"
SOURCE_MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
EXPECTED_FIXTURE_SHA256 = "cd263b740cbbcb99e7268d1ae07342d5126b0dc3dd4aa29b193d204b70c6549a"
LINE_ANCHOR_RE = re.compile(r"^L(?P<start>\d+)(?:-L(?P<end>\d+))?$")
SOURCE_BOOKS = {
    "李虚中命书": (
        "references/fulltext/luming-nayin/li-xuzhong-mingshu/fulltext.md",
        "0e44902096544b62d55f1bf67b1e9059f9e0c39f3b614dde4fac332154bc3789",
    ),
    "五行精纪": (
        "references/fulltext/luming-nayin/wuxing-jingji/fulltext.md",
        "32e0581bcba3b1b6df2b8e0c48db135a4a6f27e7dca2f010e0a818ab6ba9e08b",
    ),
    "兰台妙选": (
        "references/fulltext/luming-nayin/lantai-miaoxuan/fulltext.md",
        "ae30d81ed02dc99dd227f2ca7b0e6daf34bea9776c8a531f042b8e59bd80346e",
    ),
}
SOURCE_NAYIN_NAMES = tuple(
    value
    for value in (
        "海中金 炉中火 大林木 路旁土 剑锋金 山头火 涧下水 城头土 "
        "白蜡金 杨柳木 泉中水 屋上土 霹雳火 松柏木 长流水 沙中金 "
        "山下火 平地木 壁上土 金箔金 覆灯火 天河水 大驿土 钗钏金 "
        "桑柘木 大溪水 沙中土 天上火 石榴木 大海水"
    ).split()
    for value in (value, value)
)
SOURCE_JIAZI = tuple(
    "甲乙丙丁戊己庚辛壬癸"[index % 10]
    + "子丑寅卯辰巳午未申酉戌亥"[index % 12]
    for index in range(60)
)
SOURCE_NAYIN_BY_JIAZI = dict(zip(SOURCE_JIAZI, SOURCE_NAYIN_NAMES, strict=True))
EXPECTED_PROVIDER_ID = "mingli-master.luming-nayin.v1"
EXPECTED_PROVIDER_VERSION = "1.2.0"
EXPECTED_DEPENDENCY_IDS = (
    "luming.nayin.sixty-jiazi-table",
    "luming.three-yuan-and-taiyuan",
    "luming.relations.lu-ma-gui",
    "luming.source-conditioned-patterns",
)
REQUIRED_SOURCES = ("李虚中命书", "五行精纪", "兰台妙选")
REQUIRED_CALENDAR_CATEGORIES = (
    "solar_term_boundary",
    "day_rollover",
    "leap_month",
    "timezone_boundary",
)
POSITIONS = ("year", "month", "day", "hour")
REQUIRED_OUTPUTS = {
    "four_pillars",
    "nayin",
    "three_yuan_profiles",
    "taiyuan",
    "relations",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(findings: list[str], condition: bool, message: str) -> bool:
    if not condition:
        findings.append(message)
    return condition


def _source_slice(text: str, anchor: str) -> str:
    match = LINE_ANCHOR_RE.fullmatch(anchor)
    if match is None:
        raise ValueError(f"invalid source anchor: {anchor}")
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    lines = text.splitlines()
    if start < 1 or end < start or end > len(lines):
        raise ValueError(f"source anchor out of range: {anchor}")
    return "\n".join(lines[start - 1 : end])


def _canonical_source_text(text: str) -> str:
    """Normalize attested traditional/OCR glyph variants without dropping text."""

    return text.replace("醜", "丑").replace("已亥", "己亥")


def _walk_dependency_ids(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "source_dependency_id" and isinstance(item, str):
                yield item
            yield from _walk_dependency_ids(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_dependency_ids(item)


def _chart_request(
    label: str,
    pillars: list[str],
    *,
    taiyuan_profile: str | None = None,
) -> ReadingRequest:
    metadata = (
        {"luming_taiyuan_profile": taiyuan_profile}
        if taiyuan_profile is not None
        else {}
    )
    return ReadingRequest(
        query=f"Task 7N early-Luming provider replay {label}",
        action="new",
        system="luming-nayin",
        chart_data={"pillars": pillars},
        metadata=metadata,
    )


def _birth_request(case: Mapping[str, Any]) -> ReadingRequest:
    return ReadingRequest(
        query=f"Task 7N early-Luming calendar replay calendar-{case.get('id')}",
        action="new",
        system="luming-nayin",
        timezone=str(case.get("timezone") or ""),
        location=str(case.get("location") or ""),
        birth_data={
            "datetime": str(case.get("datetime") or ""),
            "timezone": str(case.get("timezone") or ""),
            "location": str(case.get("location") or ""),
            "zi_hour_policy": str(case.get("zi_hour_policy") or "midnight"),
        },
    )


def _complete_source_example(
    case: Mapping[str, Any],
    cycle: list[tuple[str, str]],
    index: int,
) -> list[str]:
    pillars = [str(item) for item in case.get("pillars") or ()]
    for offset in range(4 - len(pillars)):
        pillars.append(cycle[(index * 7 + offset + 17) % len(cycle)][0])
    return pillars


def _audit_result(
    result: CalculationResult,
    *,
    label: str,
    run: int,
    findings: list[str],
    counts: Counter[str],
) -> None:
    prefix = f"{label} run {run}"
    _finding(findings, result.system == "luming-nayin", f"wrong system: {prefix}")
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
        chart_facts.get("fact_layer_status")
        == "calculated_early_luming_facts",
        f"incomplete early-Luming fact layer: {prefix}",
    )
    _finding(
        findings,
        REQUIRED_OUTPUTS <= set(output),
        f"required early-Luming output missing: {prefix}",
    )
    _finding(
        findings,
        bool(result.facts.get("chart_digest"))
        and bool(result.facts.get("natal_fact_digest")),
        f"provider digest envelope incomplete: {prefix}",
    )

    validation = luming.validate_facts(chart_facts)
    counts["adapter_validation_checks"] += 1
    _finding(
        findings,
        validation.get("ok") is True,
        f"adapter validation failed: {prefix}: {validation.get('codes')}",
    )

    dependency_ids = set(_walk_dependency_ids(chart_facts))
    counts["source_binding_checks"] += 1
    _finding(
        findings,
        set(EXPECTED_DEPENDENCY_IDS) <= dependency_ids,
        f"algorithm source dependency binding incomplete: {prefix}",
    )


def _audit_pair(
    *,
    label: str,
    request: ReadingRequest,
    oracle: Callable[[CalculationResult, list[str]], int],
    findings: list[str],
    counts: Counter[str],
) -> bool:
    case_findings: list[str] = []
    results: list[CalculationResult] = []
    for run in (1, 2):
        try:
            provider = LumingProvider(ROOT)
            result = provider.calculate(request)
            counts["provider_calculations"] += 1
            results.append(result)
            _audit_result(
                result,
                label=label,
                run=run,
                findings=case_findings,
                counts=counts,
            )
        except (IndexError, KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            case_findings.append(
                f"provider calculation failed: {label} run {run}: {exc}"
            )

    deterministic = False
    if len(results) == 2:
        counts["determinism_checks"] += 1
        deterministic = (
            results[0].result_hash == results[1].result_hash
            and results[0].input_hash == results[1].input_hash
            and results[0].facts == results[1].facts
            and results[0].to_dict() == results[1].to_dict()
        )
        _finding(
            case_findings,
            deterministic,
            f"provider replay is non-deterministic: {label}",
        )
        try:
            counts["oracle_checks"] += oracle(results[0], case_findings)
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            case_findings.append(f"independent oracle failed: {label}: {exc}")
    findings.extend(case_findings)
    return not case_findings and deterministic


def _algorithm_source_report(findings: list[str]) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(SOURCE_MATRIX.read_text(encoding="utf-8"))
        provider = dict((payload.get("providers") or {}).get("luming-nayin") or {})
        dependencies = list(provider.get("dependencies") or ())
        dependency_ids = [str(item.get("id") or "") for item in dependencies]
        report = audit_algorithm_sources.audit_matrix(
            payload,
            root=ROOT,
            systems=("luming-nayin",),
        )
        _finding(
            findings,
            provider.get("source_audit_status") == "source_verified",
            "Luming source audit status is not verified",
        )
        _finding(
            findings,
            tuple(dependency_ids) == EXPECTED_DEPENDENCY_IDS,
            "Luming algorithm dependency ids mismatch",
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
            "Luming algorithm dependency provenance is incomplete",
        )
        findings.extend(
            f"algorithm source audit: {item}"
            for item in report.get("findings") or ()
        )
        return {
            "ok": bool(report.get("ok")) and not report.get("findings"),
            "research_sources_verified": bool(
                report.get("research_sources_verified")
            ),
            "dependency_ids": dependency_ids,
            "dependency_versions": {
                str(item.get("id") or ""): str(item.get("version") or "")
                for item in dependencies
            },
            "findings": list(report.get("findings") or ()),
        }
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        findings.append(f"Luming algorithm source audit failed: {exc}")
        return {
            "ok": False,
            "research_sources_verified": False,
            "dependency_ids": [],
            "dependency_versions": {},
            "findings": [str(exc)],
        }


def audit_luming_provider(
    *, fixture_path: Path = FIXTURE, research_root: Path | None = None
) -> dict[str, Any]:
    """Execute every frozen Luming fixture family through the live provider twice.

    ``research_root`` is the release-time fulltext tree for source
    verification.  It is intentionally independent of ``audit_matrix``'s own
    optional research-root wiring so a portable checkout can prove runtime
    readiness without an external corpus, while a release build passes an
    explicit root to close the source-verification gate.
    """

    findings: list[str] = []
    counts: Counter[str] = Counter()
    payload: dict[str, Any] = {}
    fixture_digest = ""
    try:
        fixture_digest = _sha256(fixture_path)
        loaded = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            payload = loaded
        else:
            findings.append("Luming fixture root must be a mapping")
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        findings.append(f"Luming fixture could not be loaded: {exc}")

    _finding(
        findings,
        not fixture_path.is_symlink(),
        "Luming fixture must not be a symlink",
    )
    _finding(
        findings,
        fixture_digest == EXPECTED_FIXTURE_SHA256,
        "Luming fixture sha256 mismatch",
    )
    _finding(
        findings,
        payload.get("schema_version") == "mingli-luming-fixtures-v51",
        "unexpected fixture schema",
    )
    _finding(
        findings,
        PROVIDER_CAPABILITIES["luming-nayin"].mode == "calculation",
        "Luming provider capability mode is not calculation",
    )

    raw_cycle = list(payload.get("nayin_cycle") or ())
    cycle: list[tuple[str, str]] = []
    for row in raw_cycle:
        if isinstance(row, (list, tuple)) and len(row) == 2:
            cycle.append((str(row[0]), str(row[1])))
    examples = [
        case
        for case in payload.get("source_examples") or ()
        if isinstance(case, Mapping)
    ]
    taiyuan_cases = [
        case
        for case in payload.get("taiyuan_cases") or ()
        if isinstance(case, Mapping)
    ]
    calendar_cases = [
        case
        for case in payload.get("calendar_cases") or ()
        if isinstance(case, Mapping)
    ]
    _finding(findings, len(cycle) == 60, "Nayin cycle must contain 60 rows")
    _finding(
        findings,
        len({row[0] for row in cycle}) == 60,
        "Nayin cycle Jiazi values must be unique",
    )
    _finding(
        findings,
        len(cycle) == 60 and dict(cycle) == luming.NAYIN_BY_JIAZI,
        "provider Nayin table diverges from the frozen 60-row fixture",
    )

    source_counts = Counter(str(case.get("source") or "") for case in examples)
    _finding(findings, len(examples) >= 30, "fewer than 30 source examples")
    _finding(
        findings,
        len({str(case.get("id") or "") for case in examples}) == len(examples)
        and all(case.get("id") for case in examples),
        "source example ids are not unique",
    )
    for source in REQUIRED_SOURCES:
        _finding(
            findings,
            source_counts[source] >= 10,
            f"source example coverage below 10: {source}",
        )

    source_payload = yaml.safe_load(SOURCE_MATRIX.read_text(encoding="utf-8"))
    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(source_payload, ROOT)
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    source_texts: dict[str, str] = {}
    if resolved_research_root is not None:
        for title, (relative, expected_sha256) in SOURCE_BOOKS.items():
            path = resolved_research_root / relative
            try:
                _finding(
                    source_verification.setdefault("findings", []),
                    path.is_file() and _sha256(path) == expected_sha256,
                    f"hash-bound source artifact mismatch: {title}",
                )
                source_texts[title] = path.read_text(encoding="utf-8")
            except OSError as exc:
                source_verification.setdefault("findings", []).append(
                    f"hash-bound source artifact failed: {title}: {exc}"
                )
    for case in examples:
        label = str(case.get("id") or "<missing>")
        title = str(case.get("source") or "")
        counts["source_expectation_checks"] += 1
        pillars = [str(item) for item in case.get("pillars") or ()]
        expected = [str(item) for item in case.get("expected_nayin") or ()]
        expectation_ok = expected == [
            SOURCE_NAYIN_BY_JIAZI[pillar] for pillar in pillars
        ]
        # Nayin table correctness is a runtime property; it never depends on
        # the external fulltext tree.
        _finding(
            findings,
            expectation_ok,
            f"source expectation does not match the independent Nayin table: {label}",
        )
        if resolved_research_root is not None and title in source_texts:
            counts["source_excerpt_checks"] += 1
            try:
                excerpt = _source_slice(
                    source_texts[title],
                    str(case.get("anchor") or ""),
                )
                canonical_excerpt = _canonical_source_text(excerpt)
                anchor_ok = bool(excerpt.strip()) and all(
                    pillar in canonical_excerpt for pillar in pillars
                )
                _finding(
                    source_verification.setdefault("findings", []),
                    anchor_ok,
                    f"source anchor does not contain the declared pillars: {label}",
                )
                if not (anchor_ok and expectation_ok):
                    counts["source_example_mismatches"] += 1
            except (KeyError, TypeError, ValueError) as exc:
                source_verification.setdefault("findings", []).append(
                    f"source anchor verification failed: {label}: {exc}"
                )
                counts["source_example_mismatches"] += 1
        if resolved_research_root is not None:
            counts["source_anchor_checks"] += 1
        if not expectation_ok:
            counts["source_example_mismatches"] += 1
    if resolved_research_root is not None:
        source_verification["ok"] = not source_verification.get("findings")
        source_verification["status"] = (
            "verified" if source_verification["ok"] else "failed"
        )

    calendar_counts = Counter(
        str(case.get("category") or "") for case in calendar_cases
    )
    for category in REQUIRED_CALENDAR_CATEGORIES:
        _finding(
            findings,
            calendar_counts[category] > 0,
            f"missing calendar boundary category: {category}",
        )

    qualifying_cases = 0
    route_owned_cases = 0
    if len(cycle) == 60:
        cycle_oracle = dict(cycle)
        for index, (ganzhi, _expected) in enumerate(cycle):
            pillars = [cycle[(index + offset) % 60][0] for offset in range(4)]
            expected = [cycle_oracle[pillar] for pillar in pillars]

            def cycle_check(
                result: CalculationResult,
                case_findings: list[str],
                *,
                expected_values: list[str] = expected,
                label: str = f"cycle-{ganzhi}",
            ) -> int:
                actual = [
                    result.facts["chart_facts"]["output"]["nayin"][position]
                    for position in POSITIONS
                ]
                _finding(
                    case_findings,
                    actual == expected_values,
                    f"Nayin cycle oracle mismatch: {label}",
                )
                return len(expected_values)

            route_owned_cases += 1
            qualifying_cases += int(
                _audit_pair(
                    label=f"nayin-cycle-{ganzhi}",
                    request=_chart_request(f"nayin-cycle-{ganzhi}", pillars),
                    oracle=cycle_check,
                    findings=findings,
                    counts=counts,
                )
            )

        for index, case in enumerate(examples):
            case_id = str(case.get("id") or f"source-{index}")
            pillars = _complete_source_example(case, cycle, index)
            original_count = len(case.get("pillars") or ())
            expected = [str(item) for item in case.get("expected_nayin") or ()]

            def source_check(
                result: CalculationResult,
                case_findings: list[str],
                *,
                expected_values: list[str] = expected,
                count: int = original_count,
                label: str = case_id,
            ) -> int:
                actual = [
                    result.facts["chart_facts"]["output"]["nayin"][position]
                    for position in POSITIONS[:count]
                ]
                _finding(
                    case_findings,
                    count == len(expected_values) and actual == expected_values,
                    f"source example oracle mismatch: {label}",
                )
                return len(expected_values)

            route_owned_cases += 1
            qualifying_cases += int(
                _audit_pair(
                    label=f"source-example-{case_id}",
                    request=_chart_request(f"source-example-{case_id}", pillars),
                    oracle=source_check,
                    findings=findings,
                    counts=counts,
                )
            )

        for index, case in enumerate(taiyuan_cases):
            case_id = str(case.get("id") or f"taiyuan-{index}")
            pillars = [
                cycle[(index * 11 + 3) % 60][0],
                str(case.get("month_pillar") or ""),
                cycle[(index * 11 + 19) % 60][0],
                cycle[(index * 11 + 37) % 60][0],
            ]

            def taiyuan_check(
                result: CalculationResult,
                case_findings: list[str],
                *,
                expected_value: str = str(case.get("expected") or ""),
                label: str = case_id,
            ) -> int:
                actual = result.facts["chart_facts"]["output"]["taiyuan"]
                _finding(
                    case_findings,
                    actual.get("status") == "calculated"
                    and actual.get("ganzhi") == expected_value,
                    f"Taiyuan oracle mismatch: {label}",
                )
                return 1

            route_owned_cases += 1
            qualifying_cases += int(
                _audit_pair(
                    label=f"taiyuan-{case_id}",
                    request=_chart_request(
                        f"taiyuan-{case_id}",
                        pillars,
                        taiyuan_profile="wuxing-jingji-use-taiyuan-v1",
                    ),
                    oracle=taiyuan_check,
                    findings=findings,
                    counts=counts,
                )
            )

        for index, case in enumerate(calendar_cases):
            case_id = str(case.get("id") or f"calendar-{index}")

            def calendar_check(
                result: CalculationResult,
                case_findings: list[str],
                *,
                expected_pillars: list[str] = [
                    str(item) for item in case.get("expected_pillars") or ()
                ],
                expected_lunar: list[Any] = list(case.get("expected_lunar") or ()),
                expected_offset: int = int(case.get("expected_offset_seconds") or 0),
                label: str = case_id,
            ) -> int:
                calendar = result.facts["chart_facts"]["calendar_normalization"]
                lunar = calendar["lunar_date"]
                actual_pillars = [calendar["ganzhi"][position] for position in POSITIONS]
                actual_lunar = [
                    lunar["year"],
                    lunar["month"],
                    lunar["day"],
                    lunar["is_leap_month"],
                ]
                _finding(
                    case_findings,
                    actual_pillars == expected_pillars,
                    f"calendar pillar oracle mismatch: {label}",
                )
                _finding(
                    case_findings,
                    actual_lunar == expected_lunar,
                    f"lunar boundary oracle mismatch: {label}",
                )
                _finding(
                    case_findings,
                    calendar["timezone_offset_seconds"] == expected_offset,
                    f"timezone offset oracle mismatch: {label}",
                )
                return 9

            route_owned_cases += 1
            qualifying_cases += int(
                _audit_pair(
                    label=f"calendar-{case_id}",
                    request=_birth_request(case),
                    oracle=calendar_check,
                    findings=findings,
                    counts=counts,
                )
            )

    algorithm_sources = _algorithm_source_report(findings)
    expected_runs = 2 * route_owned_cases
    _finding(
        findings,
        route_owned_cases >= 30,
        "fewer than 30 route-owned Luming provider cases",
    )
    _finding(
        findings,
        qualifying_cases == route_owned_cases,
        "one or more route-owned Luming cases did not qualify",
    )
    _finding(
        findings,
        counts["provider_calculations"] == expected_runs,
        "not every Luming route-owned case ran through the provider twice",
    )
    _finding(
        findings,
        counts["determinism_checks"] == route_owned_cases,
        "not every Luming route-owned case received a determinism check",
    )
    _finding(
        findings,
        counts["adapter_validation_checks"] == expected_runs,
        "not every Luming provider result passed through the adapter validator",
    )
    _finding(
        findings,
        counts["source_binding_checks"] == expected_runs,
        "not every Luming provider result received a source-binding check",
    )
    findings = list(dict.fromkeys(findings))
    boundary_categories = sorted(
        set(REQUIRED_CALENDAR_CATEGORIES) & set(calendar_counts)
    )
    route_owned_case_ids = [
        *(f"nayin-cycle-{ganzhi}" for ganzhi, _ in cycle),
        *(f"source-example-{case.get('id')}" for case in examples),
        *(f"taiyuan-{case.get('id')}" for case in taiyuan_cases),
        *(f"calendar-{case.get('id')}" for case in calendar_cases),
    ]
    ready = (
        not findings
        and fixture_digest == EXPECTED_FIXTURE_SHA256
        and qualifying_cases == route_owned_cases
        and route_owned_cases >= 30
        and algorithm_sources["ok"]
        and set(REQUIRED_CALENDAR_CATEGORIES) <= set(boundary_categories)
    )
    return {
        "schema_version": "mingli-luming-completeness-audit-v1",
        "system": "luming-nayin",
        "status": "pass" if ready else "fail",
        "provider_ready": ready,
        "provider": {
            "class": "reading_engine.providers.LumingProvider",
            "provider_id": EXPECTED_PROVIDER_ID,
            "provider_version": EXPECTED_PROVIDER_VERSION,
            "capability_mode": PROVIDER_CAPABILITIES["luming-nayin"].mode,
        },
        "route_owned_case_ids": route_owned_case_ids,
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
        "algorithm_sources": algorithm_sources,
        "source_verification": source_verification,
        "counts": {
            "nayin_rows": len(cycle),
            "source_examples": len(examples),
            "taiyuan_examples": len(taiyuan_cases),
            "calendar_boundaries": len(calendar_cases),
            "source_examples_by_book": dict(source_counts),
            "route_owned_cases": route_owned_cases,
            "qualifying_cases": qualifying_cases,
            "provider_calculations": counts["provider_calculations"],
            "provider_extensions": 0,
            "determinism_checks": counts["determinism_checks"],
            "boundary_case_count": len(calendar_cases),
            "source_anchor_checks": counts["source_anchor_checks"],
            "source_excerpt_checks": counts["source_excerpt_checks"],
            "source_expectation_checks": counts["source_expectation_checks"],
            "source_example_mismatches": counts["source_example_mismatches"],
            "adapter_validation_checks": counts["adapter_validation_checks"],
            "source_binding_checks": counts["source_binding_checks"],
            "oracle_checks": counts["oracle_checks"],
            "algorithm_dependencies": len(
                algorithm_sources["dependency_ids"]
            ),
            "boundary_categories": len(boundary_categories),
        },
        "lookup_coverage": {
            "lu_stems": len(luming.LU_BY_STEM),
            "tianyi_stems": len(luming.TIANYI_BY_STEM),
            "yima_branches": len(luming.YIMA_BY_BRANCH),
        },
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args()
    report = audit_luming_provider(fixture_path=args.fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
