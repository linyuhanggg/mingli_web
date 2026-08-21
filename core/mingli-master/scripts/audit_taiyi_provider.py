#!/usr/bin/env python3
"""Machine-readable completeness audit for the deterministic Taiyi provider."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

import audit_algorithm_sources
from audit_provider_preflight import provider_preflight_failure
from reading_engine import calendar_core, evidence_rules, taiyi
from reading_engine.contracts import ReadingRequest, canonical_digest
from reading_engine.providers import PROVIDER_CAPABILITIES, TaiyiProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/taiyi-v51.yaml"
RAW_EXTERNAL_FIXTURE = ROOT / "references/fixtures/kintaiyi-taiyi-v51.yaml"
RAW_EXTERNAL_GENERATOR = (
    ROOT / "scripts/fixtures/kintaiyi_taiyi_fixture_generator.py"
)
MATRIX = ROOT / "references/matrices/algorithm-source-dependencies.yaml"
SOURCE_TABLE = ROOT / "references/matrices/taiyi-source-tables-v1.yaml"
FIXTURE_SHA256 = "fb736b6a4f8908bd0d4602952df347f99248ba1162cd17c93720de5b3aa3c5b7"
EXPECTED_PROVIDER_ID = "mingli-master.taiyi.v1"
EXPECTED_PROVIDER_VERSION = "5.2.0"
RAW_EXTERNAL_FIXTURE_SHA256 = "502a1178442a008bd5d900f9e1461f8fd5f5e23da00e61525ecac25a119b6e0f"
RAW_EXTERNAL_GENERATOR_SHA256 = "067ca9e107116d9e1ef2e2a4999371c5287f1d18a5ef37d7de8fc0c522b32598"
RAW_EXTERNAL_CASES_SHA256 = "a128b4de6ca06d8374d5acfb87a534c9c3ff89d8c4a9237e35946ecb6ccc7b54"

_BRANCH_DOMAIN_ORDER = tuple("戌亥子丑寅卯辰巳午未申酉")
_PALACE_FORWARD_FROM_ONE = (1, 2, 3, 4, 6, 7, 8, 9)
_PALACE_FORWARD_FROM_SEVEN = (7, 8, 9, 1, 2, 3, 4, 6)
_FOUR_PLACE_ORDER = (1, 2, 3, 4, 5, 6, 7, 8, 9, "絳", "明", "玉")
_FOUR_STARTS = {
    "sishen": (1, 9, 5),
    "tianyi": (6, 2, "絳"),
    "diyi": (9, 5, 1),
    "zhifu": (5, 1, 9),
}
_OPPOSITE_POSITION = {
    "乾": "巽",
    "巽": "乾",
    "午": "子",
    "子": "午",
    "艮": "坤",
    "坤": "艮",
    "卯": "酉",
    "酉": "卯",
}
_MAIN_PALACES = {"乾": 1, "午": 2, "艮": 3, "卯": 4, "酉": 6, "坤": 7, "子": 8, "巽": 9}
_PREDICATE_EXPRESSIONS = {
    "TY-P01": "shiji_same_as_taiyi",
    "TY-P02": "tianmu_wenchang_same_as_taiyi",
    "TY-P03": "shiji_opposes_taiyi",
    "TY-P04": "tianmu_wenchang_opposes_taiyi",
    "TY-P05": "host_general_same_as_taiyi",
    "TY-P06": "host_assistant_same_as_taiyi",
    "TY-P07": "guest_general_same_as_taiyi",
    "TY-P08": "guest_assistant_same_as_taiyi",
    "TY-P09": "guest_general_opposes_taiyi",
    "TY-P10": "guest_assistant_opposes_taiyi",
}
_PATTERN_UNRESOLVED_CHECKS = (
    "并见格局、制化与主客关系",
    "宏观事项范围及盘面取用",
    "现实成败、吉凶与应期",
)
_LONG_CYCLE_IDENTITIES = {
    "junji": ("君基", "upper-jiayin-long-cycle-v1", 284287, 360, "fulltext.md L602-L604"),
    "chenji": ("臣基", "upper-jiayin-long-cycle-v1", 284287, 36, "fulltext.md L606-L608"),
    "minji": ("民基", "upper-jiayin-long-cycle-v1", 284287, 12, "fulltext.md L610-L612"),
    "wufu": ("五福", "wufu-dayou-long-cycle-v1", 12607, 225, "fulltext.md L614-L617"),
    "dayou": ("大游", "wufu-dayou-long-cycle-v1", 12607, 288, "fulltext.md L619-L638"),
    "xiaoyou": ("小游", "xiaoyou-four-deity-v1", 2637, 24, "fulltext.md L644-L646"),
    "sishen": ("四神", "xiaoyou-four-deity-v1", 2637, 180, "fulltext.md L648-L651"),
    "tianyi": ("天乙", "xiaoyou-four-deity-v1", 2637, 180, "fulltext.md L653-L655"),
    "diyi": ("地乙", "xiaoyou-four-deity-v1", 2637, 180, "fulltext.md L661-L759"),
    "zhifu": ("直符", "xiaoyou-four-deity-v1", 2637, 180, "fulltext.md L657-L659"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(findings: list[str], condition: bool, message: str) -> None:
    if not condition:
        findings.append(message)


def _one_based_mod(value: int, modulus: int) -> int:
    return (int(value) - 1) % int(modulus) + 1


def _canonical_sha256(value: Any) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _oracle_long_cycle_deities(lunar_year: int) -> dict[str, dict[str, Any]]:
    """Recompute all ten positions without importing provider helpers/tables."""

    upper = int(lunar_year) + 284287
    wufu_year = int(lunar_year) + 12607
    small = int(lunar_year) + 2637
    upper_360 = _one_based_mod(upper, 360)
    upper_36 = _one_based_mod(upper_360, 36)
    upper_12 = _one_based_mod(upper_360, 12)
    wufu_225 = _one_based_mod(wufu_year, 225)
    dayou_288 = _one_based_mod(wufu_year, 288)
    xiaoyou_24 = _one_based_mod(small, 24)
    four_180 = _one_based_mod(small, 180)
    yuan = (four_180 - 1) // 60
    within_yuan = (four_180 - 1) % 60

    positions: dict[str, Any] = {
        "junji": _BRANCH_DOMAIN_ORDER[(upper_360 - 1) // 30],
        "chenji": _BRANCH_DOMAIN_ORDER[(upper_36 - 1) // 3],
        "minji": _BRANCH_DOMAIN_ORDER[upper_12 - 1],
        "wufu": ("乾", "艮", "巽", "坤", "中")[(wufu_225 - 1) // 45],
        "dayou": _PALACE_FORWARD_FROM_SEVEN[(dayou_288 - 1) // 36],
        "xiaoyou": _PALACE_FORWARD_FROM_ONE[(xiaoyou_24 - 1) // 3],
    }
    for name, starts in _FOUR_STARTS.items():
        start = _FOUR_PLACE_ORDER.index(starts[yuan])
        positions[name] = _FOUR_PLACE_ORDER[
            (start + within_yuan // 3) % len(_FOUR_PLACE_ORDER)
        ]

    accumulated = {
        "junji": upper,
        "chenji": upper,
        "minji": upper,
        "wufu": wufu_year,
        "dayou": wufu_year,
        "xiaoyou": small,
        "sishen": small,
        "tianyi": small,
        "diyi": small,
        "zhifu": small,
    }
    cycle_positions = {
        "junji": upper_360,
        "chenji": upper_36,
        "minji": upper_12,
        "wufu": wufu_225,
        "dayou": dayou_288,
        "xiaoyou": xiaoyou_24,
        "sishen": four_180,
        "tianyi": four_180,
        "diyi": four_180,
        "zhifu": four_180,
    }
    return {
        name: {
            "name": identity[0],
            "position": positions[name],
            "epoch_profile": identity[1],
            "accumulated_year": accumulated[name],
            "cycle_position": cycle_positions[name],
            "source_anchor": identity[4],
            "status": "calculated_position_not_verdict",
        }
        for name, identity in _LONG_CYCLE_IDENTITIES.items()
    }


def _pointer(board: Mapping[str, Any], path: str) -> Any:
    value: Any = board
    for component in path.strip("/").split("/"):
        if not isinstance(value, Mapping) or component not in value:
            raise KeyError(path)
        value = value[component]
    return value


def _predicate_matches(
    board: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> bool:
    left = _pointer(board, str(contract["left_fact_path"]))
    right = str(_pointer(board, str(contract["right_fact_path"])))
    relation = str(contract["relation"])
    if relation == "same_position":
        return str(left) == right
    if relation == "opposite_position":
        return str(left) == _OPPOSITE_POSITION[right]
    if relation == "same_palace":
        return int(left) == _MAIN_PALACES[right]
    if relation == "opposite_palace":
        return int(left) == _MAIN_PALACES[_OPPOSITE_POSITION[right]]
    raise ValueError(f"unknown Taiyi predicate relation: {relation}")


def _oracle_board_predicates(
    board: Mapping[str, Any],
    contracts: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    expected = []
    rules = {
        rule.local_rule_id: rule
        for rule in evidence_rules.production_evidence_rules()
        if rule.system == "taiyi"
        and rule.local_rule_id in _PREDICATE_EXPRESSIONS
        and rule.runtime_active
        and rule.classical_binding_status == "verified"
        and rule.classical_binding_digest
    }
    for contract in contracts:
        identifier = str(contract["id"])
        if not _predicate_matches(board, contract):
            continue
        rule = rules.get(identifier)
        if rule is None:
            raise ValueError(f"missing verified Taiyi predicate rule: {identifier}")
        expected.append(
            {
                "id": identifier,
                "name": str(contract["name"]),
                "predicate": _PREDICATE_EXPRESSIONS[identifier],
                "fact_paths": [
                    str(contract["left_fact_path"]),
                    str(contract["right_fact_path"]),
                ],
                "source_anchor": f"fulltext.md {contract['source_anchor']}",
                "source_dependency_id": "taiyi.evidence.board-predicates-and-scope",
                "status": "predicate_matched_not_verdict",
                "identity_adjudication": {
                    "status": "adjudicated_pattern_identity",
                    "decision_scope": "taiyi_board_pattern_identity",
                    "pattern_id": identifier,
                    "pattern_name": str(contract["name"]),
                    "hard_verdict": None,
                    "event_verdict": None,
                    "source_ref": {
                        "pack": rule.source_pack,
                        "rule_id": rule.local_rule_id,
                        "source_anchor": f"{rule.source_path}#{rule.local_rule_id}",
                        "verification_status": rule.classical_binding_status,
                        "binding_digest": rule.classical_binding_digest,
                    },
                    "unresolved_checks": list(_PATTERN_UNRESOLVED_CHECKS),
                },
            }
        )
    return expected


def _raw_to_canonical(raw: Mapping[str, Any]) -> dict[str, Any]:
    host = int(raw["host_count_literal"])
    guest = int(raw["guest_count_literal"])
    host_general = host // 10 if host % 10 == 0 else host % 10
    guest_general = guest // 10 if guest % 10 == 0 else guest % 10
    return {
        "bureau": int(raw["bureau"]),
        "taiyi": str(raw["taiyi_palace_literal"]),
        "tianmu_position": str(raw["wenchang_position_literal"]),
        "shiji": str(raw["shiji_position_literal"]),
        "host_count": host,
        "host_general": host_general,
        "host_assistant": (host_general * 3) % 10 or 5,
        "guest_count": guest,
        "guest_general": guest_general,
        "guest_assistant": (guest_general * 3) % 10 or 5,
        "jishen": str(raw["jishen_mapping"]),
    }


def audit_taiyi_provider(
    *,
    fixture_path: Path = FIXTURE,
    raw_external_fixture_path: Path = RAW_EXTERNAL_FIXTURE,
    raw_external_generator_path: Path = RAW_EXTERNAL_GENERATOR,
    matrix_path: Path = MATRIX,
    source_table_path: Path = SOURCE_TABLE,
    research_root: Path | None = None,
) -> dict[str, Any]:
    """Audit the deterministic Taiyi provider for Task 7N completeness.

    ``research_root`` is the release-time fulltext tree for source
    verification.  It is intentionally independent of ``audit_matrix``'s own
    optional research-root wiring so a portable checkout can prove runtime
    readiness without an external corpus, while a release build passes an
    explicit root to close the source-verification gate.  Runtime readiness
    (``provider_ready``) never depends on the external fulltext tree; the
    ``source_verification`` block is ``skipped`` without a root and verified
    when one is provided.
    """
    preflight = provider_preflight_failure(
        system="taiyi",
        schema_version="mingli-taiyi-provider-audit-v1",
        provider_class=TaiyiProvider,
        expected_mode="calculation",
        expected_provider_id=EXPECTED_PROVIDER_ID,
        expected_provider_version=EXPECTED_PROVIDER_VERSION,
    )
    if preflight is not None:
        return preflight
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    table = yaml.safe_load(source_table_path.read_text(encoding="utf-8"))
    raw_external = yaml.safe_load(
        raw_external_fixture_path.read_text(encoding="utf-8")
    )
    findings: list[str] = []
    _finding(
        findings,
        TaiyiProvider.provider_id == EXPECTED_PROVIDER_ID
        and TaiyiProvider.provider_version == EXPECTED_PROVIDER_VERSION,
        "Taiyi provider identity drift",
    )
    _finding(
        findings,
        PROVIDER_CAPABILITIES["taiyi"].mode == "calculation",
        "Taiyi provider capability mode is not calculation",
    )

    _finding(
        findings,
        _sha256(fixture_path) == FIXTURE_SHA256,
        "Taiyi fixture artifact hash mismatch",
    )
    _finding(
        findings,
        table.get("schema_version") == taiyi.SOURCE_TABLE_SCHEMA,
        "unexpected Taiyi source-table schema",
    )
    _finding(
        findings,
        _sha256(source_table_path) == taiyi.source_table_digest(),
        "Taiyi source-table artifact hash mismatch",
    )
    _finding(
        findings,
        _sha256(raw_external_fixture_path) == RAW_EXTERNAL_FIXTURE_SHA256,
        "Taiyi raw external fixture artifact hash mismatch",
    )
    _finding(
        findings,
        _sha256(raw_external_generator_path) == RAW_EXTERNAL_GENERATOR_SHA256,
        "Taiyi raw external generator artifact hash mismatch",
    )
    raw_source = raw_external.get("source") or {}
    source_reference = table.get("source_profiles", {}).get(
        "kintaiyi_engineering_reference", {}
    )
    fixture_reference = fixture.get("external_reference") or {}
    _finding(
        findings,
        raw_external.get("schema_version") == "kintaiyi-taiyi-raw-v1",
        "unexpected Taiyi raw external fixture schema",
    )
    _finding(
        findings,
        raw_source.get("repository") == source_reference.get("repository")
        == fixture_reference.get("repository")
        and raw_source.get("commit") == source_reference.get("commit")
        == fixture_reference.get("commit")
        and raw_source.get("license") == source_reference.get("license")
        == fixture_reference.get("license"),
        "Taiyi raw external source identity mismatch",
    )
    generator_identity = raw_external.get("generator") or {}
    _finding(
        findings,
        generator_identity.get("path")
        == "scripts/fixtures/kintaiyi_taiyi_fixture_generator.py"
        and generator_identity.get("sha256") == RAW_EXTERNAL_GENERATOR_SHA256,
        "Taiyi raw external generator identity mismatch",
    )
    projection_contract = raw_external.get("projection_contract") or {}
    _finding(
        findings,
        projection_contract.get("projection_kind")
        == "static source projection with literal tables and labelled derivations; not pan() output"
        and projection_contract.get("upstream_origins", {}).get(
            "host_count_literal"
        )
        == "config.find_cal yangcal row 0; annual Yang 立成"
        and projection_contract.get("upstream_origins", {}).get(
            "jishen_mapping"
        )
        == "derived by replaying Taiyi.__init__ jigod_map with the annual branch",
        "Taiyi raw external projection origin contract mismatch",
    )
    raw_cases = list(raw_external.get("raw_cases") or ())
    _finding(
        findings,
        len(raw_cases) == 72
        and [case.get("raw", {}).get("bureau") for case in raw_cases]
        == list(range(1, 73)),
        "Taiyi raw external projection must contain bureaus 1 through 72",
    )
    _finding(
        findings,
        raw_external.get("raw_cases_sha256") == RAW_EXTERNAL_CASES_SHA256
        == _canonical_sha256(raw_cases),
        "Taiyi raw external case digest mismatch",
    )

    source_rows = list(table.get("annual_yang_72_source_rows") or ())
    _finding(
        findings,
        [row.get("bureau") for row in source_rows] == list(range(1, 73)),
        "Taiyi source table must contain bureaus 1 through 72 exactly once",
    )
    source_board_mismatches = 0
    for row in source_rows:
        bureau = int(row.get("bureau") or 0)
        try:
            board = taiyi.build_annual_board_from_accumulated_year(bureau)
            actual = {
                key: board[key]
                for key in row
                if key != "bureau"
            }
            expected = {key: value for key, value in row.items() if key != "bureau"}
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            source_board_mismatches += 1
            findings.append(f"Taiyi source board failed: bureau {bureau}: {exc}")
        else:
            if actual != expected:
                source_board_mismatches += 1
                findings.append(f"Taiyi source board mismatch: bureau {bureau}")

    states = []
    for accumulated_year in range(1, 361):
        try:
            states.append(
                taiyi.build_annual_board_from_accumulated_year(accumulated_year)[
                    "cycle"
                ]
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"Taiyi cycle position failed: {accumulated_year}: {exc}")
    _finding(findings, len(states) == 360, "Taiyi 360-year cycle is incomplete")
    if states:
        _finding(
            findings,
            {row["ji"] for row in states} == set(range(1, 7)),
            "Taiyi cycle does not cover all six Ji",
        )
        _finding(
            findings,
            {row["zi_yuan"] for row in states} == set(range(1, 6)),
            "Taiyi cycle does not cover all five Zi-Yuan",
        )
        _finding(
            findings,
            {row["bureau"] for row in states} == set(range(1, 73)),
            "Taiyi cycle does not cover all 72 bureaus",
        )

    raw_by_year = {
        int(case["input"]["lunar_year"]): _raw_to_canonical(case["raw"])
        for case in raw_cases
        if isinstance(case, Mapping)
        and isinstance(case.get("input"), Mapping)
        and isinstance(case.get("raw"), Mapping)
    }
    declared_raw_differences = {
        30: {"shiji": ("丑", "申")},
        44: {"host_count": (23, 33)},
        66: {"shiji": ("丑", "申")},
    }
    external_raw_mismatches = 0
    for case in raw_cases:
        try:
            lunar_year = int(case["input"]["lunar_year"])
            expected = _raw_to_canonical(case["raw"])
            board = taiyi.build_annual_board(lunar_year)
            actual = {
                key: board["cycle"]["bureau"] if key == "bureau" else board[key]
                for key in expected
            }
            bureau = int(expected["bureau"])
            differences = declared_raw_differences.get(bureau, {})
            for field, (raw_value, primary_value) in differences.items():
                if expected[field] != raw_value or actual[field] != primary_value:
                    raise ValueError(f"declared difference changed: {field}")
            comparable_expected = {
                key: value for key, value in expected.items() if key not in differences
            }
            comparable_actual = {
                key: value for key, value in actual.items() if key not in differences
            }
            if comparable_actual != comparable_expected:
                raise ValueError("undeclared raw comparator mismatch")
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            external_raw_mismatches += 1
            findings.append(
                f"Taiyi raw external replay failed: {case.get('id')}: {exc}"
            )

    external_cases = list(fixture.get("external_reference_cases") or ())
    external_reference_mismatches = 0
    qualifying_cases = 0
    provider_calculations = 0
    provider_extensions = 0
    determinism_checks = 0
    for case in external_cases:
        identifier = str(case.get("id") or "")
        try:
            lunar_year = int(case["lunar_year"])
            # July is unambiguously inside the declared lunar year.  The year
            # comes from the frozen route fixture; this timestamp only bridges
            # that annual oracle into the live Provider request contract.
            request = ReadingRequest(
                query=f"Task 7N Taiyi provider replay {identifier}",
                action="new",
                system="taiyi",
                reference_datetime=f"{lunar_year:04d}-07-01T12:00:00+08:00",
                timezone="Asia/Shanghai",
                location="上海",
            )
            first = TaiyiProvider(ROOT).calculate(request)
            second = TaiyiProvider(ROOT).calculate(request)
            provider_calculations += 2
            for result in (first, second):
                if (
                    result.system != "taiyi"
                    or result.provider_id != TaiyiProvider.provider_id
                    or result.provider_version != TaiyiProvider.provider_version
                ):
                    raise ValueError("live provider identity mismatch")
                if (
                    result.facts["chart_facts"]["output"]["calendar"][
                        "lunar_year"
                    ]
                    != lunar_year
                ):
                    raise ValueError("live provider annual input mismatch")
            if (
                first.result_hash != second.result_hash
                or first.input_hash != second.input_hash
                or canonical_digest(first.facts) != canonical_digest(second.facts)
            ):
                raise ValueError("live provider calculation is nondeterministic")
            determinism_checks += 1

            horizon = {
                "kind": "year",
                "start": str(lunar_year),
                "end": str(lunar_year),
            }
            dimensions = tuple(PROVIDER_CAPABILITIES["taiyi"].dimensions)
            first_extended = TaiyiProvider(ROOT).extend(first, dimensions, horizon)
            second_extended = TaiyiProvider(ROOT).extend(second, dimensions, horizon)
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

            board = first.facts["chart_facts"]["output"]
            actual = {key: board[key] for key in case["expected"]}
            raw_expected = raw_by_year[lunar_year]
            normalized_from_raw = {
                key: raw_expected[key]
                for key in case["expected"]
                if key in raw_expected
            }
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            external_reference_mismatches += 1
            findings.append(f"Taiyi external board failed: {identifier}: {exc}")
        else:
            normalized_common = {
                key: value
                for key, value in case.get("expected", {}).items()
                if key in raw_expected
            }
            if (
                actual != case.get("expected")
                or normalized_from_raw != normalized_common
            ):
                external_reference_mismatches += 1
                findings.append(f"Taiyi external board mismatch: {identifier}")
            else:
                qualifying_cases += 1
    _finding(
        findings,
        len(external_cases) == 30,
        "Taiyi requires exactly 30 frozen external reference boards",
    )
    _finding(
        findings,
        len(external_cases) == len({case.get("id") for case in external_cases}),
        "Taiyi external fixture identifiers are not unique",
    )
    _finding(
        findings,
        qualifying_cases >= 30,
        "Taiyi live provider replay requires at least 30 qualifying cases",
    )
    _finding(
        findings,
        provider_calculations == 2 * len(external_cases)
        and provider_extensions == 2 * len(external_cases)
        and determinism_checks == 2 * len(external_cases),
        "Taiyi live provider replay did not execute every case twice",
    )

    boundaries = list(fixture.get("calendar_boundary_cases") or ())
    boundary_mismatches = 0
    boundary_provider_calculations = 0
    boundary_provider_determinism_checks = 0
    for case in boundaries:
        identifier = str(case.get("id") or "")
        try:
            calendar = calendar_core.normalize_calendar(
                str(case["datetime"]),
                timezone_name=str(case["timezone"]),
                location=str(case["location"]),
            )
            facts = taiyi.build_fact_layer(calendar)
            actual = {
                "lunar_year": facts["output"]["calendar"]["lunar_year"],
                "bureau": facts["output"]["cycle"]["bureau"],
            }
            expected = {
                "lunar_year": case["expected_lunar_year"],
                "bureau": case["expected_bureau"],
            }
            request = ReadingRequest(
                query=f"Task 7N Taiyi boundary replay {identifier}",
                action="new",
                system="taiyi",
                reference_datetime=str(case["datetime"]),
                timezone=str(case["timezone"]),
                location=str(case["location"]),
            )
            first = TaiyiProvider(ROOT).calculate(request)
            second = TaiyiProvider(ROOT).calculate(request)
            boundary_provider_calculations += 2
            if not (
                first.input_hash == second.input_hash
                and first.result_hash == second.result_hash
                and canonical_digest(first.facts) == canonical_digest(second.facts)
            ):
                raise ValueError("live boundary provider replay is nondeterministic")
            boundary_provider_determinism_checks += 1
            live_output = first.facts["chart_facts"]["output"]
            if {
                "lunar_year": live_output["calendar"]["lunar_year"],
                "bureau": live_output["cycle"]["bureau"],
            } != expected:
                raise ValueError("live boundary provider result mismatch")
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            boundary_mismatches += 1
            findings.append(f"Taiyi calendar boundary failed: {identifier}: {exc}")
        else:
            if actual != expected:
                boundary_mismatches += 1
                findings.append(f"Taiyi calendar boundary mismatch: {identifier}")
    _finding(
        findings,
        len(boundaries) >= 10,
        "Taiyi requires at least ten calendar boundary fixtures",
    )

    long_cycle_mismatches = 0
    for lunar_year in range(1, 361):
        actual = taiyi.build_annual_board(lunar_year)["long_cycle_deities"]
        expected = _oracle_long_cycle_deities(lunar_year)
        for name in _LONG_CYCLE_IDENTITIES:
            if actual.get(name) != expected[name]:
                long_cycle_mismatches += 1
                findings.append(
                    f"Taiyi long-cycle deity mismatch: year {lunar_year}: {name}"
                )

    predicate_contracts = list(table.get("board_predicate_contracts") or ())
    predicate_mismatches = 0
    activated_predicates = set()
    for bureau in range(1, 73):
        board = taiyi.build_annual_board_from_accumulated_year(bureau)
        actual = list(board.get("board_predicates") or ())
        expected = _oracle_board_predicates(board, predicate_contracts)
        activated_predicates.update(str(row.get("id") or "") for row in actual)
        if actual != expected:
            predicate_mismatches += 1
            findings.append(f"Taiyi board predicate mismatch: bureau {bureau}")
    _finding(
        findings,
        activated_predicates == set(taiyi.BOARD_PREDICATE_IDS),
        "Taiyi 72-board cycle does not activate every declared predicate",
    )

    dependency_rows = matrix["providers"]["taiyi"]["dependencies"]
    dependency_ids = [str(row.get("id") or "") for row in dependency_rows]
    _finding(
        findings,
        dependency_ids == list(taiyi.SOURCE_DEPENDENCIES),
        "Taiyi dependency IDs do not match the provider contract",
    )
    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(matrix, ROOT)
    )
    # Runtime matrix audit stays research-root-free: its structural findings
    # (schema, dependencies, release-located sources) are runtime readiness
    # properties.  The fulltext-tree checks run only inside the release-time
    # ``source_verification`` gate, so an explicit research root can never
    # flip ``provider_ready``.
    source_audit = audit_algorithm_sources.audit_matrix(
        matrix,
        root=ROOT,
        systems=("taiyi",),
    )
    findings.extend(
        f"algorithm source audit: {item}"
        for item in source_audit["findings"]
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    if resolved_research_root is not None:
        # Release-time source verification.  The ``source_report`` block
        # carries every ``audit_matrix`` finding, including the fulltext-tree
        # checks that only run against an explicit research root.  Runtime
        # readiness (``provider_ready``) stays independent of the external
        # corpus: the provider, digests, and oracle checks above never touch
        # the fulltext tree.
        source_report = audit_algorithm_sources.audit_matrix(
            matrix,
            root=ROOT,
            systems=("taiyi",),
            research_root=resolved_research_root,
        )
        source_verification["source_report"] = {
            "ok": bool(source_report.get("ok")),
            "research_sources_verified": bool(
                source_report.get("research_sources_verified")
            ),
            "dependency_count": int(source_report.get("dependency_count") or 0),
            "findings": list(source_report.get("findings") or ()),
        }
        if source_report.get("ok") and not source_report.get("findings"):
            source_verification["ok"] = True
            source_verification["status"] = "verified"
        else:
            source_verification["ok"] = False
            source_verification["status"] = "failed"
            source_verification["findings"] = list(
                source_report.get("findings") or ()
            )

    return {
        "schema_version": "mingli-taiyi-provider-audit-v1",
        "system": "taiyi",
        "profile_id": taiyi.TABLE_PROFILE,
        "provider_ready": not findings,
        "status": "pass" if not findings else "fail",
        "provider": {
            "provider_id": TaiyiProvider.provider_id,
            "provider_version": TaiyiProvider.provider_version,
            "capability_mode": PROVIDER_CAPABILITIES["taiyi"].mode,
        },
        "route_owned_case_ids": [
            str(case.get("id") or "") for case in external_cases
        ],
        "fixture": {
            "path": str(fixture_path),
            "sha256": _sha256(fixture_path),
            "expected_sha256": FIXTURE_SHA256,
        },
        "fixture_sha256": _sha256(fixture_path),
        "counts": {
            "qualifying_cases": qualifying_cases,
            "route_owned_cases": len(external_cases),
            "provider_calculations": provider_calculations,
            "provider_extensions": provider_extensions,
            "determinism_checks": determinism_checks,
            "boundary_case_count": len(boundaries),
            "boundary_provider_calculations": boundary_provider_calculations,
            "boundary_provider_determinism_checks": (
                boundary_provider_determinism_checks
            ),
            "annual_source_boards": len(source_rows),
            "source_board_mismatches": source_board_mismatches,
            "external_raw_boards": len(raw_cases),
            "external_raw_mismatches": external_raw_mismatches,
            "external_reference_boards": len(external_cases),
            "external_reference_mismatches": external_reference_mismatches,
            "calendar_boundaries": len(boundaries),
            "calendar_boundary_mismatches": boundary_mismatches,
            "cycle_positions": len(states),
            "long_cycle_years": 360,
            "long_cycle_comparisons": 360 * len(_LONG_CYCLE_IDENTITIES),
            "long_cycle_mismatches": long_cycle_mismatches,
            "predicate_boards": 72,
            "predicate_mismatches": predicate_mismatches,
            "board_predicates": len(activated_predicates),
            "algorithm_dependencies": len(dependency_rows),
        },
        "boundary_categories": sorted(
            (
                {str(case.get("category") or "") for case in boundaries}
                | {"annual_external_reference"}
            )
            - {""}
        ),
        "source_verification": source_verification,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_taiyi_provider()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"Taiyi provider ready: {report['provider_ready']} "
            f"({report['counts']['annual_source_boards']} boards, "
            f"{len(report['findings'])} findings)"
        )
        for finding in report["findings"]:
            print(f"- {finding}")
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
