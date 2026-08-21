#!/usr/bin/env python3
"""Machine-readable Task 7I completeness audit for deterministic Qimen."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

import audit_algorithm_sources
from audit_provider_preflight import provider_preflight_failure
from reading_engine import calendar_core, qimen
from reading_engine.contracts import ReadingRequest, canonical_digest
from reading_engine.providers import PROVIDER_CAPABILITIES, QimenProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "qimen-v51.yaml"
MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
SOURCE_TABLE = ROOT / "references" / "matrices" / "qimen-source-tables-v1.yaml"
EXTERNAL_FIXTURE = ROOT / "references" / "fixtures" / "qimen-go-v51.yaml"
EXTERNAL_FIXTURE_SHA256 = "bf4a1e70c07575b66695c0e5d897b516c27b5bcd92e6a0525b2e7b584927f14d"
EXPECTED_FIXTURE_SHA256 = (
    "14c3f8a5dba09454acafdf332bf5eb9fc72359aa82ab5eeeb11d4a49c59f07ce"
)
EXPECTED_PROVIDER_ID = "mingli-master.qimen.v1"
EXPECTED_PROVIDER_VERSION = "5.2.0"
PATTERN_CONTRACT = ROOT / "references" / "fixtures" / "qimen-pattern-contract-v51.yaml"
EVIDENCE_INDEX = ROOT / "references" / "index" / "evidence-rules.jsonl"
PATTERN_CONTRACT_SHA256 = "2c463a5fddb75c0d81c2bb93ee31076fa6898abd2dc9d336ca036e38d0dec392"
PATTERN_CONTRACT_FIELDS = (
    "name", "predicate", "upper", "lower", "door", "doors", "deity",
    "palace", "cases", "pillar", "lower_stems", "low_palaces",
    "high_palaces",
)
PATTERN_SOURCE_FIELDS = (
    "source_profile", "definition_version", "source_anchor", "source_phrase",
    "incompatible_definition", "evidence_quote", "evidence_anchor",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(findings: list[str], condition: bool, message: str) -> None:
    if not condition:
        findings.append(message)


def _board_signature(board: dict[str, Any]) -> str:
    rows = sorted(board.get("palaces") or (), key=lambda row: int(row["palace"]))
    if len(rows) != 9:
        raise ValueError("independent Qimen signature requires nine palaces")
    return "|".join(
        f"{row['palace']}:{row['earth_stem']}/"
        f"{'+'.join(str(value) for value in row.get('heaven_stems') or ()) or '-'}/"
        f"{'+'.join(str(value) for value in row.get('stars') or ()) or '-'}/"
        f"{row.get('door') or '-'}/{row.get('deity') or '-'}"
        for row in rows
    )


def _expected_board(board: dict[str, Any]) -> dict[str, Any]:
    return {
        "dun": board["dun"],
        "yuan": board["yuan"],
        "symbol_head": board["symbol_head"],
        "ju": board["ju"]["number"],
        "xun": board["xunkong"]["xun"],
        "hidden_instrument": board["chief"]["hidden_instrument"],
        "chief": board["chief"]["star"],
        "chief_palace": board["chief"]["destination_palace"],
        "director": board["director"]["door"],
        "director_palace": board["director"]["destination_palace"],
        "void_branches": board["xunkong"]["branches"],
        "void_palaces": board["xunkong"]["palaces"],
        "horse_branch": board["horse"]["branch"],
        "horse_palace": board["horse"]["palace"],
        "signature": _board_signature(board),
    }


def _qimen_go_raw_projection(board: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the selected board to the pinned qimen-go raw projection."""

    rows: list[dict[str, Any]] = []
    for row in sorted(board.get("palaces") or (), key=lambda item: int(item["palace"])):
        palace = int(row["palace"])
        heaven_stems = list(row.get("heaven_stems") or ())
        stars = list(row.get("stars") or ())
        rows.append(
            {
                "palace": palace,
                "earth": str(row["earth_stem"]),
                "heaven": "" if palace == 5 else str(heaven_stems[0]),
                "star": "" if palace == 5 else str(stars[0]).removeprefix("天"),
                "door": "" if palace == 5 else str(row.get("door") or "").removesuffix("门"),
                "deity": "" if palace == 5 else str(row.get("deity") or ""),
            }
        )
    return rows


def _compatible_qimen_go_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [dict(row) for row in rows]
    for row in normalized:
        if int(row.get("palace") or 0) == 5:
            row.update({"heaven": "", "star": "", "door": "", "deity": ""})
    return normalized


def _qimen_go_signature(rows: list[dict[str, Any]]) -> str:
    serialized = "|".join(
        f"{row['palace']}:{row['earth']}/"
        f"{row['heaven'] or '-'}/{row['star'] or '-'}/"
        f"{row['door'] or '-'}/{row['deity'] or '-'}"
        for row in _compatible_qimen_go_rows(rows)
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _qimen_go_scalar_projection(board: dict[str, Any]) -> dict[str, Any]:
    return {
        "term": board["active_solar_term"],
        "day": board["day_hour"]["day_ganzhi"],
        "hour": board["day_hour"]["hour_ganzhi"],
        "yuan": {"upper": 1, "middle": 2, "lower": 3}[board["yuan"]],
        "ju": board["ju"]["number"] if board["dun"] == "yang" else -board["ju"]["number"],
        "xun": board["xunkong"]["xun"],
        "void": "".join(board["xunkong"]["branches"]),
        "horse": board["horse"]["branch"],
        "chief": board["chief"]["star"].removeprefix("天"),
        "chief_palace": board["chief"]["destination_palace"],
        "director": board["director"]["door"].removesuffix("门"),
        "director_palace": board["director"]["destination_palace"],
    }


def _reference_expected(
    table: dict[str, Any], supplied: dict[str, str]
) -> dict[str, Any]:
    """Provider-independent transcription of the source board procedure."""

    stems = "甲乙丙丁戊己庚辛壬癸"
    branches = "子丑寅卯辰巳午未申酉戌亥"
    cycle = [stems[index % 10] + branches[index % 12] for index in range(60)]
    day_index = cycle.index(supplied["day_ganzhi"])
    hour_index = cycle.index(supplied["hour_ganzhi"])
    symbol_head = cycle[day_index - day_index % 5]
    symbol_branch = symbol_head[1]
    yuan = (
        "upper"
        if symbol_branch in "子午卯酉"
        else "middle"
        if symbol_branch in "寅申巳亥"
        else "lower"
    )
    term = table["term_yuan_ju"][supplied["active_term"]]
    dun = str(term["dun"])
    ju = int(term[yuan])
    earth: dict[int, str] = {}
    palace = ju
    for token in table["orders"]["earth_plate_tokens"]:
        earth[palace] = str(token)
        palace = palace % 9 + 1 if dun == "yang" else (palace - 2) % 9 + 1
    by_stem = {stem: palace for palace, stem in earth.items()}
    xun = cycle[hour_index - hour_index % 10]
    xun_profile = table["xun_profiles"][xun]
    hidden = str(xun_profile["hidden_instrument"])
    origin = by_stem[hidden]
    hosted_origin = 2 if origin == 5 else origin
    profiles = {int(key): value for key, value in table["palaces"].items()}
    chief = str(profiles[origin]["star"])
    director = str(profiles[hosted_origin]["door"])
    target_stem = hidden if supplied["hour_ganzhi"][0] == "甲" else supplied["hour_ganzhi"][0]
    chief_destination_raw = by_stem[target_stem]
    chief_destination = 2 if chief_destination_raw == 5 else chief_destination_raw
    director_raw = (
        origin - 1
        + ((hour_index % 10) if dun == "yang" else -(hour_index % 10))
    ) % 9 + 1
    director_destination = 2 if director_raw == 5 else director_raw
    star_outer = [
        int(value) for value in table["orders"]["star_rotation_outer_palaces"]
    ]
    door_outer = [
        int(value) for value in table["orders"]["door_rotation_outer_palaces"]
    ]
    deity_outer = [
        int(value) for value in table["orders"]["deity_rotation_outer_palaces"]
    ]

    def rotate(order: list[int], start: int) -> list[int]:
        index = order.index(start)
        return order[index:] + order[:index]

    rotation_origin = 2 if origin == 5 else origin
    stars: dict[int, list[str]] = {palace: [] for palace in range(1, 10)}
    heaven: dict[int, list[str]] = {palace: [] for palace in range(1, 10)}
    for home, landing in zip(
        rotate(star_outer, rotation_origin),
        rotate(star_outer, chief_destination),
    ):
        stars[landing].append(str(profiles[home]["star"]))
        heaven[landing].append(earth[home])
    tianrui_destination = next(
        palace
        for palace, placed_stars in stars.items()
        if str(profiles[2]["star"]) in placed_stars
    )
    stars[tianrui_destination].append(str(profiles[5]["star"]))
    heaven[tianrui_destination].append(earth[5])
    doors = {
        landing: str(profiles[home]["door"])
        for home, landing in zip(
            rotate(door_outer, rotation_origin),
            rotate(door_outer, director_destination),
        )
    }
    deities = [str(value) for value in table["orders"]["deities"]["baihu_xuanwu_variant"]]
    chief_outer_index = deity_outer.index(chief_destination)
    deity_palaces = [
        deity_outer[(chief_outer_index + (offset if dun == "yang" else -offset)) % 8]
        for offset in range(8)
    ]
    deity_by_palace = dict(zip(deity_palaces, deities))
    signature = "|".join(
        f"{palace}:{earth[palace]}/"
        f"{'+'.join(heaven[palace]) or '-'}/"
        f"{'+'.join(stars[palace]) or '-'}/"
        f"{doors.get(palace) or '-'}/{deity_by_palace.get(palace) or '-'}"
        for palace in range(1, 10)
    )

    def branch_palace(branch: str) -> int:
        return next(
            palace
            for palace, profile in profiles.items()
            if branch in (profile.get("branches") or ())
        )

    void_branches = [str(value) for value in xun_profile["void_branches"]]
    horse = table["horse_by_hour_branch"][supplied["hour_ganzhi"][1]]
    return {
        "dun": dun,
        "yuan": yuan,
        "symbol_head": symbol_head,
        "ju": ju,
        "xun": xun,
        "hidden_instrument": hidden,
        "chief": chief,
        "chief_palace": chief_destination,
        "director": director,
        "director_palace": director_destination,
        "void_branches": void_branches,
        "void_palaces": sorted({branch_palace(branch) for branch in void_branches}),
        "horse_branch": str(horse["horse_branch"]),
        "horse_palace": int(horse["palace"]),
        "signature": signature,
    }


def _source_checks(
    source_text: str,
    source_sha256: str,
    table: dict[str, Any],
    *,
    xieji_text: str,
    faqiao_text: str,
    wuxing_text: str,
) -> dict[str, Any]:
    compact = "".join(source_text.split())
    chinese_digits = "零一二三四五六七八九"
    compact_lines = ["".join(line.split()) for line in source_text.splitlines()]
    term_aliases = {"惊蛰": "惊蜇"}
    term_ju_table_parsed = all(
        any(
            term_aliases.get(str(term), str(term)) in line
            and "".join(
                chinese_digits[int(profile[key])]
                for key in ("upper", "middle", "lower")
            ) in line
            for line in compact_lines
        )
        for term, profile in table["term_yuan_ju"].items()
    )
    plate_phrases_present = all(
        phrase in compact
        for phrase in (
            "坎一天蓬",
            "坤二天芮",
            "震三天冲",
            "巽四天辅",
            "中五天禽",
            "乾六天心",
            "兑七天柱",
            "艮八天任",
            "离九天英",
            "坎休、艮生、震伤、巽杜、离景、坤死、兑惊、乾开",
            "戊己庚辛壬癸为六仪",
            "乙为日奇，丙为月奇，丁为星奇",
            "甲子遁于六戊",
            "甲寅遁于六癸",
        )
    )
    chief_director_rules_present = all(
        phrase in compact
        for phrase in (
            "地盘旬首所临之宫，其星即为值符，其门即为值使",
            "看用时之干临于地盘何宫，即以天盘值符加于此宫",
            "阴遁须用逆布",
            "五日为一元",
            "以甲己二干为一元之首",
        )
    )
    center_hosting_rule_present = (
        "天禽阳遁阴遁俱寄坤宫" in compact
    )
    expected_palaces = {
        1: ("天蓬", "休门"), 2: ("天芮", "死门"),
        3: ("天冲", "伤门"), 4: ("天辅", "杜门"),
        5: ("天禽", None), 6: ("天心", "开门"),
        7: ("天柱", "惊门"), 8: ("天任", "生门"),
        9: ("天英", "景门"),
    }
    observed_palaces = {
        int(palace): (profile.get("star"), profile.get("door"))
        for palace, profile in table.get("palaces", {}).items()
    }
    expected_outer = [1, 8, 3, 4, 9, 2, 7, 6]
    expected_orders = {
        "earth_plate_tokens": list("戊己庚辛壬癸丁丙乙"),
        "six_instruments": list("戊己庚辛壬癸"),
        "three_wonders": list("乙丙丁"),
        "star_rotation_outer_palaces": expected_outer,
        "door_rotation_outer_palaces": expected_outer,
        "deity_rotation_outer_palaces": expected_outer,
        "tongzong_numeric_door_outer_palaces": [1, 2, 3, 4, 6, 7, 8, 9],
        "stars_rotating": ["天蓬", "天任", "天冲", "天辅", "天英", "天芮", "天柱", "天心"],
        "doors_rotating": ["休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"],
        "doors_numeric_outer": ["休门", "死门", "伤门", "杜门", "开门", "惊门", "生门", "景门"],
    }
    observed_orders = table.get("orders") or {}
    plate_orders_parsed = (
        plate_phrases_present
        and observed_palaces == expected_palaces
        and all(observed_orders.get(key) == value for key, value in expected_orders.items())
        and (observed_orders.get("deities") or {}).get("baihu_xuanwu_variant")
        == ["值符", "腾蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"]
    )
    expected_xun = {
        "甲子": {"hidden_instrument": "戊", "void_branches": ["戌", "亥"]},
        "甲戌": {"hidden_instrument": "己", "void_branches": ["申", "酉"]},
        "甲申": {"hidden_instrument": "庚", "void_branches": ["午", "未"]},
        "甲午": {"hidden_instrument": "辛", "void_branches": ["辰", "巳"]},
        "甲辰": {"hidden_instrument": "壬", "void_branches": ["寅", "卯"]},
        "甲寅": {"hidden_instrument": "癸", "void_branches": ["子", "丑"]},
    }
    expected_horse_branch = {
        "申": "寅", "子": "寅", "辰": "寅",
        "寅": "申", "午": "申", "戌": "申",
        "巳": "亥", "酉": "亥", "丑": "亥",
        "亥": "巳", "卯": "巳", "未": "巳",
    }
    observed_horse_branch = {
        branch: profile.get("horse_branch")
        for branch, profile in (table.get("horse_by_hour_branch") or {}).items()
    }
    xun_horse_tables_verified = (
        table.get("xun_profiles") == expected_xun
        and observed_horse_branch == expected_horse_branch
        and all(
            phrase in wuxing_text
            for phrase in (
                "寅午戌生人，驛馬從來會在申",
                "申子辰年，馬在寅",
                "巳酉醜年馬在亥",
                "亥卯未人馬在巳",
                "旬後兩位",
            )
        )
    )
    selected_spatial_plate_rules_verified = (
        "直使加時宫不論隂陽八門順轉八卦" in xieji_text
        and "九星亦是順行八卦" in xieji_text
        and observed_orders.get("star_rotation_outer_palaces") == expected_outer
        and observed_orders.get("door_rotation_outer_palaces") == expected_outer
    )
    selected_chaibu_rule_verified = all(
        phrase in faqiao_text
        for phrase in (
            "专以交节之日视何甲己起元，再以交节之日分元定局",
            "则丁未交节之日，即用冬至下元甲辰符首之局",
            "此拆局补局之法",
        )
    )
    source_lines = source_text.splitlines()
    named_pattern_anchors_verified = True
    for profile in table["named_pattern_predicates"]:
        anchor = str(profile["source_anchor"])
        if anchor.startswith("qimen-faqiao "):
            marker = anchor.removeprefix("qimen-faqiao ")
            try:
                start = next(
                    index
                    for index, line in enumerate(faqiao_text.splitlines())
                    if line.startswith(f"## {marker}")
                )
            except StopIteration:
                named_pattern_anchors_verified = False
                continue
            excerpt = " ".join(faqiao_text.splitlines()[start : start + 4])
        else:
            location = anchor.removeprefix("qimen-tongzong ")
            start_text, _, end_text = location.removeprefix("L").partition("-L")
            try:
                start = int(start_text)
                end = int(end_text or start_text)
                excerpt = " ".join(source_lines[start - 1 : end])
            except (TypeError, ValueError):
                named_pattern_anchors_verified = False
                continue
        source_phrase = str(profile.get("source_phrase") or "")
        normalized_excerpt = "".join(excerpt.split())
        normalized_phrase = "".join(source_phrase.split())
        definition_version = str(
            profile.get("definition_version")
            or table.get("named_pattern_definition_default")
            or ""
        )
        if (
            not normalized_phrase
            or normalized_phrase not in normalized_excerpt
            or not definition_version
        ):
            named_pattern_anchors_verified = False
    return {
        "source_sha256": source_sha256,
        "term_ju_table_parsed": term_ju_table_parsed,
        "plate_orders_parsed": plate_orders_parsed,
        "chief_director_rules_present": chief_director_rules_present,
        "center_hosting_rule_present": center_hosting_rule_present,
        "selected_spatial_plate_rules_verified": selected_spatial_plate_rules_verified,
        "selected_chaibu_rule_verified": selected_chaibu_rule_verified,
        "xun_horse_tables_verified": xun_horse_tables_verified,
        "named_pattern_anchors_verified": named_pattern_anchors_verified,
    }


def audit_qimen_provider(
    *,
    fixture_path: Path = FIXTURE,
    matrix_path: Path = MATRIX,
    source_table_path: Path = SOURCE_TABLE,
    external_fixture_path: Path = EXTERNAL_FIXTURE,
    pattern_contract_path: Path = PATTERN_CONTRACT,
    evidence_index_path: Path = EVIDENCE_INDEX,
    research_root: Path | None = None,
) -> dict[str, Any]:
    """Audit the deterministic Qimen provider for Task 7I completeness.

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
        system="qimen",
        schema_version="mingli-qimen-provider-audit-v1",
        provider_class=QimenProvider,
        expected_mode="calculation",
        expected_provider_id=EXPECTED_PROVIDER_ID,
        expected_provider_version=EXPECTED_PROVIDER_VERSION,
    )
    if preflight is not None:
        return preflight
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    table = yaml.safe_load(source_table_path.read_text(encoding="utf-8"))
    external_fixture = yaml.safe_load(
        external_fixture_path.read_text(encoding="utf-8")
    )
    pattern_contract = yaml.safe_load(
        pattern_contract_path.read_text(encoding="utf-8")
    )
    qimen_evidence_rules = [
        record
        for line in evidence_index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for record in (json.loads(line),)
        if record.get("system") == "qimen"
    ]
    cases = list(fixture.get("source_rule_boards") or ())
    pattern_cases = list(fixture.get("named_pattern_cases") or ())
    classical_cases = list(fixture.get("classical_cases") or ())
    classical_door_map_cases = list(fixture.get("classical_door_map_cases") or ())
    boundaries = list(fixture.get("calendar_boundaries") or ())
    pattern_coverage_cases = list(fixture.get("pattern_coverage_cases") or ())
    pattern_activation_cases = list(fixture.get("named_pattern_cases") or ())
    external_reference_cases = list(external_fixture.get("cases") or ())
    calendar_pattern_witnesses = list(
        fixture.get("calendar_pattern_witnesses") or ()
    )
    findings: list[str] = []
    fixture_sha256 = _sha256(fixture_path)
    _finding(
        findings,
        QimenProvider.provider_id == EXPECTED_PROVIDER_ID
        and QimenProvider.provider_version == EXPECTED_PROVIDER_VERSION,
        "Qimen provider identity drift",
    )
    _finding(
        findings,
        fixture_sha256 == EXPECTED_FIXTURE_SHA256,
        "Qimen fixture artifact hash mismatch",
    )
    _finding(
        findings,
        PROVIDER_CAPABILITIES["qimen"].mode == "calculation",
        "Qimen provider capability mode is not calculation",
    )

    _finding(findings, fixture.get("schema_version") == "mingli-qimen-fixtures-v51", "unexpected Qimen fixture schema")
    _finding(findings, fixture.get("profile_id") == qimen.TABLE_PROFILE, "Qimen fixture profile mismatch")
    _finding(findings, len(cases) >= 30, "Qimen fixture requires at least 30 source-rule boards")
    _finding(findings, len(cases) == len({case.get("id") for case in cases}), "Qimen fixture ids are not unique")
    _finding(findings, len(boundaries) >= 8, "Qimen fixture requires at least eight calendar boundaries")
    categories = Counter(str(case.get("category") or "") for case in boundaries)
    _finding(findings, categories["solar_term_boundary"] >= 6, "Qimen fixture requires six exact solar-term boundary cases")
    _finding(findings, categories["day_rollover"] >= 2, "Qimen fixture requires two day-rollover cases")
    _finding(findings, categories["lunar_leap_month"] >= 1, "Qimen fixture requires a lunar leap-month case")
    boundary_provider_calculations = 0
    boundary_provider_determinism_checks = 0
    for case in boundaries:
        identifier = str(case.get("id") or "")
        try:
            request = ReadingRequest(
                query=f"Task 7N Qimen boundary replay {identifier}",
                action="new",
                system="qimen",
                event_datetime=str(case["datetime"]),
                timezone=str(case["timezone"]),
                location=str(case["location"]),
            )
            first = QimenProvider(ROOT).calculate(request)
            second = QimenProvider(ROOT).calculate(request)
            boundary_provider_calculations += 2
            _finding(
                findings,
                first.input_hash == second.input_hash
                and first.result_hash == second.result_hash
                and canonical_digest(first.facts) == canonical_digest(second.facts),
                f"Qimen boundary provider replay is nondeterministic: {identifier}",
            )
            boundary_provider_determinism_checks += 1
            _finding(
                findings,
                first.facts["chart_facts"]["output"]["active_solar_term"]
                == case["expected_active_term"],
                f"Qimen boundary provider term mismatch: {identifier}",
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(
                f"Qimen boundary provider replay failed: {identifier}: {exc}"
            )
    _finding(findings, _sha256(source_table_path) == qimen.source_table_digest(), "Qimen source table hash mismatch")

    external_identity = dict(external_fixture.get("source") or {})
    expected_external_identity = {
        "repository": "https://github.com/deminzhang/qimen-go",
        "commit": "4d3f58fa0f401b5b3a337f119138e99e90685dda",
        "license": "MIT",
        "license_sha256": "cfdb13c1a086ecc3f498b6a75a65d1dab3d93072c58efd26d383db776749b996",
        "go_mod_sha256": "38764017b89640a525a101b76a957710a17eefc42fcc2432e46f82ad44f10ada",
        "go_sum_sha256": "8e09608fe80d2037657618da67977e3b83ddc39ccb71ad6227f802ca7931d3bb",
        "implementation_path": "xuan/qimen.go",
        "implementation_sha256": "93ba61a632af3d402bfd65754d1adeb74b937f87b40e62fc50adc15a1d4bd350",
        "definitions_path": "xuan/qimen_defs.go",
        "definitions_sha256": "bacb7684160cb0d4297e1a13fb3674c7eebf56183fea2e7a5c12bb18a7dd47ac",
        "generator_path": "scripts/fixtures/qimen_go_fixture_generator.go",
        "generator_sha256": "6f089a57a608dff7c2b47f4f2058b00831172af69019f76f75a6140bc618b398",
        "canonical_cases_sha256": "1cf3b5a6fd3757d03471f65ff67e9fe62af37d225daf40fb8e512f87e6bca8f5",
    }
    _finding(
        findings,
        _sha256(external_fixture_path) == EXTERNAL_FIXTURE_SHA256,
        "Qimen external fixture artifact hash mismatch",
    )
    for key, expected_value in expected_external_identity.items():
        _finding(
            findings,
            external_identity.get(key) == expected_value,
            f"Qimen external reference identity mismatch: {key}",
        )
    external_canonical = json.dumps(
        external_reference_cases,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    _finding(
        findings,
        hashlib.sha256(external_canonical).hexdigest()
        == external_identity.get("canonical_cases_sha256"),
        "Qimen external reference cases hash mismatch",
    )
    generator_path = ROOT / str(external_identity.get("generator_path") or "")
    _finding(
        findings,
        generator_path.is_file()
        and _sha256(generator_path) == external_identity.get("generator_sha256"),
        "Qimen external fixture generator hash mismatch",
    )
    _finding(
        findings,
        len(external_reference_cases) == 30,
        "Qimen fixture requires exactly 30 frozen external reference boards",
    )
    _finding(
        findings,
        len(external_reference_cases)
        == len({case.get("id") for case in external_reference_cases}),
        "Qimen external reference fixture ids are not unique",
    )
    external_reference_mismatches = 0
    qualifying_cases = 0
    provider_calculations = 0
    provider_extensions = 0
    determinism_checks = 0
    for case in external_reference_cases:
        identifier = str(case.get("id") or "")
        try:
            calendar = calendar_core.normalize_calendar(
                str(case["datetime"]),
                timezone_name="Asia/Shanghai",
                location="上海",
            )
            previous_term = (calendar.get("solar_terms") or {}).get("previous") or {}
            pillars = calendar.get("ganzhi") or {}
            calendar_input = {
                "term": previous_term.get("name"),
                "day": pillars.get("day"),
                "hour": pillars.get("hour"),
            }
            if calendar_input != {
                "term": case.get("term"),
                "day": case.get("day"),
                "hour": case.get("hour"),
            }:
                external_reference_mismatches += 1
                findings.append(
                    f"external reference calendar input mismatch: {identifier}"
                )
                continue
            board = qimen.build_board(
                str(case["term"]), str(case["day"]), str(case["hour"])
            )
            expected_rows = list(case.get("raw_projection") or ())
            supplied_signature = str(
                case.get("compatible_signature_sha256") or ""
            )
            raw_signature = _qimen_go_signature(expected_rows)
            if raw_signature != supplied_signature:
                external_reference_mismatches += 1
                findings.append(
                    f"external reference raw signature mismatch: {identifier}"
                )
                continue
            actual_rows = _qimen_go_raw_projection(board)
            if actual_rows != _compatible_qimen_go_rows(expected_rows):
                external_reference_mismatches += 1
                findings.append(
                    f"external reference raw board mismatch: {identifier}"
                )
                continue
            actual_scalar = _qimen_go_scalar_projection(board)
            expected_scalar = {
                key: case.get(key)
                for key in (
                    "term", "day", "hour", "yuan", "ju", "xun", "void",
                    "horse", "chief", "chief_palace", "director",
                    "director_palace",
                )
            }
            if actual_scalar != expected_scalar:
                external_reference_mismatches += 1
                findings.append(
                    f"external reference scalar mismatch: {identifier}"
                )
                continue

            request = ReadingRequest(
                query=f"Task 7N Qimen provider replay {identifier}",
                action="new",
                system="qimen",
                event_datetime=str(case["datetime"]),
                timezone="Asia/Shanghai",
                location="上海",
            )
            first = QimenProvider(ROOT).calculate(request)
            second = QimenProvider(ROOT).calculate(request)
            provider_calculations += 2
            for result in (first, second):
                if (
                    result.system != "qimen"
                    or result.provider_id != QimenProvider.provider_id
                    or result.provider_version != QimenProvider.provider_version
                ):
                    raise ValueError("live provider identity mismatch")
                provider_board = result.facts["chart_facts"]["output"]
                if (
                    _qimen_go_raw_projection(provider_board)
                    != _compatible_qimen_go_rows(expected_rows)
                    or _qimen_go_scalar_projection(provider_board)
                    != expected_scalar
                ):
                    raise ValueError("live provider result differs from frozen oracle")
            if (
                first.result_hash != second.result_hash
                or first.input_hash != second.input_hash
                or canonical_digest(first.facts) != canonical_digest(second.facts)
            ):
                raise ValueError("live provider calculation is nondeterministic")
            determinism_checks += 1

            dimensions = tuple(PROVIDER_CAPABILITIES["qimen"].dimensions)
            horizon = {"kind": "instant"}
            first_extended = QimenProvider(ROOT).extend(first, dimensions, horizon)
            second_extended = QimenProvider(ROOT).extend(second, dimensions, horizon)
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
            qualifying_cases += 1
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            external_reference_mismatches += 1
            findings.append(f"external reference board failed: {identifier}: {exc}")
    _finding(
        findings,
        qualifying_cases >= 30,
        "Qimen live provider replay requires at least 30 qualifying cases",
    )
    _finding(
        findings,
        provider_calculations == 2 * len(external_reference_cases)
        and provider_extensions == 2 * len(external_reference_cases)
        and determinism_checks == 2 * len(external_reference_cases),
        "Qimen live provider replay did not execute every case twice",
    )

    pattern_contract_rows = list(pattern_contract.get("predicates") or ())
    _finding(
        findings,
        _sha256(pattern_contract_path) == PATTERN_CONTRACT_SHA256,
        "Qimen independent pattern contract artifact hash mismatch",
    )
    expected_functional_contract = {
        str(row.get("id") or ""): dict(row.get("contract") or {})
        for row in pattern_contract_rows
    }
    observed_functional_contract = {
        str(row.get("id") or ""): {
            key: row[key]
            for key in PATTERN_CONTRACT_FIELDS
            if key in row
        }
        for row in table.get("named_pattern_predicates") or ()
    }
    structured_pattern_contract_verified = (
        pattern_contract.get("schema_version")
        == "mingli-qimen-pattern-contract-v1"
        and len(pattern_contract_rows) == 40
        and observed_functional_contract == expected_functional_contract
    )
    _finding(
        findings,
        structured_pattern_contract_verified,
        "Qimen structured pattern contract mismatch",
    )
    expected_source_contract = {
        str(row.get("id") or ""): {
            key: row[key]
            for key in PATTERN_SOURCE_FIELDS
            if key in row
        }
        for row in pattern_contract.get("source_contracts") or ()
    }
    default_definition = str(table.get("named_pattern_definition_default") or "")
    observed_source_contract = {
        str(row.get("id") or ""): {
            **{
                "source_profile": str(row.get("source_profile") or "qimen_tongzong"),
                "definition_version": str(row.get("definition_version") or default_definition),
                "source_anchor": str(row.get("source_anchor") or ""),
                "source_phrase": str(row.get("source_phrase") or ""),
                "evidence_quote": str(row.get("evidence_quote") or ""),
                "evidence_anchor": str(row.get("evidence_anchor") or ""),
            },
            **(
                {"incompatible_definition": str(row["incompatible_definition"])}
                if row.get("incompatible_definition")
                else {}
            ),
        }
        for row in table.get("named_pattern_predicates") or ()
    }
    source_identity_contract_verified = (
        len(expected_source_contract) == 40
        and observed_source_contract == expected_source_contract
    )
    _finding(
        findings,
        source_identity_contract_verified,
        "Qimen pattern source identity contract mismatch",
    )
    evidence_by_id = {
        str(row.get("local_rule_id") or ""): row
        for row in qimen_evidence_rules
    }
    evidence_source_bridge_verified = (
        len(qimen_evidence_rules) == 40
        and len(evidence_by_id) == 40
    )
    for identifier, profile in {
        str(row.get("id") or ""): row
        for row in table.get("named_pattern_predicates") or ()
    }.items():
        evidence = evidence_by_id.get(identifier) or {}
        source_profile = str(profile.get("source_profile") or "qimen_tongzong")
        expected_pack = (
            "san-shi/qimen-faqiao"
            if source_profile == "qimen_faqiao"
            else "san-shi/qimen-dunjia-tongzhi"
        )
        source_path = ROOT / str(evidence.get("source_path") or "")
        valid = (
            evidence.get("source_pack") == expected_pack
            and evidence.get("quote") == profile.get("evidence_quote")
            and evidence.get("source_anchor") == profile.get("evidence_anchor")
            and source_path.is_file()
            and _sha256(source_path) == evidence.get("source_sha256")
        )
        evidence_source_bridge_verified = evidence_source_bridge_verified and valid
    _finding(
        findings,
        evidence_source_bridge_verified,
        "Qimen evidence/source identity bridge mismatch",
    )
    positive_contract_fixtures = {
        str(row.get("id") or ""): str(row.get("positive_fixture_id") or "")
        for row in pattern_contract_rows
    }
    observed_positive_fixtures = {
        str(case.get("expected_rule_id") or ""): str(case.get("id") or "")
        for case in pattern_coverage_cases
    }
    _finding(
        findings,
        positive_contract_fixtures == observed_positive_fixtures,
        "Qimen pattern contract positive fixtures mismatch",
    )

    expected_pattern_ids = {
        str(row.get("id") or "")
        for row in table.get("named_pattern_predicates") or ()
    }
    covered_pattern_ids: set[str] = set()
    for case in pattern_coverage_cases:
        identifier = str(case.get("id") or "")
        expected_rule_id = str(case.get("expected_rule_id") or "")
        try:
            board = qimen.build_board(**case["input"])
            observed_ids = {
                str(row.get("id") or "")
                for row in board.get("named_patterns") or ()
            }
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"pattern coverage board failed: {identifier}: {exc}")
            continue
        _finding(
            findings,
            expected_rule_id in observed_ids,
            f"pattern coverage board mismatch: {identifier}",
        )
        if expected_rule_id in observed_ids:
            covered_pattern_ids.add(expected_rule_id)
    _finding(
        findings,
        covered_pattern_ids == expected_pattern_ids,
        "Qimen fixtures do not activate every named-pattern predicate",
    )
    coverage_by_rule = {
        str(case.get("expected_rule_id") or ""): case
        for case in pattern_coverage_cases
    }
    verified_calendar_pattern_witnesses = 0
    for witness in calendar_pattern_witnesses:
        identifier = str(witness.get("id") or "")
        expected_rule_id = str(witness.get("expected_rule_id") or "")
        try:
            calendar = calendar_core.normalize_calendar(
                str(witness["datetime"]),
                timezone_name=str(witness["timezone"]),
                location=str(witness["location"]),
            )
            pillars = dict(calendar.get("ganzhi") or {})
            previous_term = (calendar.get("solar_terms") or {}).get("previous") or {}
            board = qimen.build_fact_layer(calendar)["output"]
            coverage_input = dict(coverage_by_rule[expected_rule_id]["input"])
            derived_input = {
                "active_term": str(previous_term.get("name") or ""),
                "day_ganzhi": str(pillars.get("day") or ""),
                "hour_ganzhi": str(pillars.get("hour") or ""),
                "year_ganzhi": str(pillars.get("year") or ""),
                "month_ganzhi": str(pillars.get("month") or ""),
            }
            observed_ids = {
                str(row.get("id") or "")
                for row in board.get("named_patterns") or ()
            }
            valid = (
                expected_rule_id in {"QM-P27", "QM-P28"}
                and pillars == dict(witness.get("expected_pillars") or {})
                and previous_term.get("name") == witness.get("expected_active_term")
                and expected_rule_id in observed_ids
                and coverage_input == derived_input
            )
            _finding(
                findings,
                valid,
                f"calendar pattern witness mismatch: {identifier}",
            )
            if valid:
                verified_calendar_pattern_witnesses += 1
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"calendar pattern witness failed: {identifier}: {exc}")
    _finding(
        findings,
        verified_calendar_pattern_witnesses == 2,
        "Qimen requires real-calendar witnesses for year and month grid patterns",
    )

    for case in pattern_activation_cases:
        identifier = str(case.get("id") or "")
        try:
            board = qimen.build_board(**case["input"])
            observed_ids = {
                str(row.get("id") or "")
                for row in board.get("named_patterns") or ()
            }
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"pattern activation board failed: {identifier}: {exc}")
            continue
        _finding(
            findings,
            observed_ids == set(case.get("expected_pattern_ids") or ()),
            f"pattern activation board mismatch: {identifier}",
        )

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
    source_path = ROOT / str(source_identity.get("path") or "")
    source_text = ""
    source_hash = ""
    if resolved_research_root is not None:
        # Release-time source verification: the fulltext tree is only
        # consulted when an explicit research root supplies it.  Runtime
        # readiness is unaffected by a missing external corpus.
        source_path = resolved_research_root / str(source_identity.get("path") or "")
        try:
            _finding(
                source_verification.setdefault("findings", []),
                source_path.is_file(),
                "Qimen normalized source is missing",
            )
            if source_path.is_file():
                source_hash = _sha256(source_path)
                _finding(
                    source_verification.setdefault("findings", []),
                    source_hash == source_identity.get("sha256"),
                    "Qimen normalized source hash mismatch",
                )
                source_text = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            source_verification.setdefault("findings", []).append(
                f"Qimen normalized source failed: {exc}"
            )

    def read_declared_source(profile_name: str) -> str:
        profile = (table.get("source_profiles") or {}).get(profile_name) or {}
        path = Path(str(profile.get("normalized_path") or ""))
        if profile_name == "qimen_faqiao":
            # The faqiao excerpt is part of the portable checkout, so its
            # identity is a runtime property and its failures are readiness
            # findings.
            full_path = ROOT / path
            target_findings = findings
        elif resolved_research_root is not None:
            full_path = resolved_research_root / path
            target_findings = source_verification.setdefault("findings", [])
        else:
            # No external fulltext tree: release-time source verification is
            # skipped, so do not fail on a missing external corpus.
            return ""
        try:
            raw = full_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != str(profile.get("sha256") or ""):
                target_findings.append(
                    f"Qimen declared source hash mismatch: {profile_name}"
                )
            return raw.decode("utf-8")
        except OSError as exc:
            target_findings.append(
                f"Qimen declared source failed: {profile_name}: {exc}"
            )
            return ""

    tongzong_text = read_declared_source("qimen_tongzong")
    xieji_text = read_declared_source("xieji_bianfang")
    faqiao_text = read_declared_source("qimen_faqiao")
    wuxing_text = read_declared_source("wuxing_jingji")

    def evidence_anchor_excerpt(text: str, anchor: str) -> str:
        lines = text.splitlines()
        if anchor.startswith("fulltext.md L"):
            span = anchor.removeprefix("fulltext.md L").replace("L", "")
            bounds = [int(value) for value in span.split("-")]
            start = bounds[0]
            end = bounds[-1]
            return "\n".join(lines[start - 1:end])
        marker = anchor.rsplit(" ", 1)[-1]
        start = next(index for index, line in enumerate(lines) if marker in line)
        return "\n".join(lines[start:start + 6])

    def evidence_quote_occurs_at_anchor(quote: str, excerpt: str) -> bool:
        def normalized(value: str) -> str:
            return "".join(value.split())

        expected = normalized(quote)
        return bool(expected) and expected in normalized(excerpt)

    if resolved_research_root is not None:
        evidence_quote_source_text_verified = True
        profile_by_id = {
            str(row.get("id") or ""): row
            for row in table.get("named_pattern_predicates") or ()
        }
        for evidence in qimen_evidence_rules:
            try:
                profile = profile_by_id[str(evidence["local_rule_id"])]
                source_profile = str(profile.get("source_profile") or "qimen_tongzong")
                declared_text = (
                    faqiao_text if source_profile == "qimen_faqiao" else tongzong_text
                )
                excerpt = evidence_anchor_excerpt(
                    declared_text,
                    str(profile["evidence_anchor"]),
                )
                evidence_quote_source_text_verified = (
                    evidence_quote_source_text_verified
                    and evidence_quote_occurs_at_anchor(
                        str(profile["evidence_quote"]), excerpt
                    )
                )
            except (KeyError, StopIteration, TypeError, ValueError):
                evidence_quote_source_text_verified = False
    else:
        evidence_quote_source_text_verified = True

    source_checks = _source_checks(
        source_text,
        source_hash,
        table,
        xieji_text=xieji_text,
        faqiao_text=faqiao_text,
        wuxing_text=wuxing_text,
    )
    source_checks["declared_tongzong_identity_verified"] = (
        bool(source_text)
        and bool(tongzong_text)
        and tongzong_text == source_text
    )
    source_checks["structured_pattern_contract_verified"] = (
        structured_pattern_contract_verified
    )
    source_checks["pattern_source_identity_contract_verified"] = (
        source_identity_contract_verified
    )
    source_checks["evidence_source_identity_bridge_verified"] = (
        evidence_source_bridge_verified
    )
    source_checks["evidence_quote_source_text_verified"] = (
        evidence_quote_source_text_verified
    )
    incompatible_definitions = table.get("named_pattern_incompatible_definitions") or {}
    source_checks["pattern_conflicts_versioned"] = all(
        str(row.get("incompatible_definition") or "") in incompatible_definitions
        for row in table.get("named_pattern_predicates") or ()
        if row.get("incompatible_definition")
    ) and {
        "QM-P10", "QM-P23", "QM-P26", "QM-P34", "QM-P35", "QM-P36",
        "QM-P39",
    } == {
        str(row.get("id") or "")
        for row in table.get("named_pattern_predicates") or ()
        if row.get("incompatible_definition")
    }
    tongzong_numeric_door_conflict_verified = False
    if resolved_research_root is not None and source_text:
        for case in classical_door_map_cases:
            try:
                source_line = source_text.splitlines()[
                    int(str(case["source_anchor"]).removeprefix("L")) - 1
                ]
                board = qimen.build_board(**case["input"])
                director_home = int(board["director"]["xun_palace"])
                if director_home == 5:
                    director_home = 2
                destination = int(board["director"]["destination_palace"])
                order = [
                    int(value)
                    for value in table["orders"]["tongzong_numeric_door_outer_palaces"]
                ]
                profiles = {int(key): value for key, value in table["palaces"].items()}
                shift = order.index(destination) - order.index(director_home)
                alternate = {
                    str(profiles[home]["door"]): order[(order.index(home) + shift) % 8]
                    for home in order
                }
                expected = {str(key): int(value) for key, value in case["expected"].items()}
                chinese_digits = "零一二三四五六七八九"
                source_contract = all(
                    door in source_line
                    and (
                        chinese_digits[palace] in source_line
                        or str(profiles[palace]["trigram"]) in source_line
                    )
                    for door, palace in expected.items()
                )
                selected = {
                    str(row["door"]): int(row["palace"])
                    for row in board["palaces"]
                    if row.get("door")
                }
                tongzong_numeric_door_conflict_verified = (
                    alternate == expected and selected != expected and source_contract
                )
            except (IndexError, KeyError, TypeError, ValueError) as exc:
                source_verification.setdefault("findings", []).append(
                    f"Tongzong door conflict fixture failed: {exc}"
                )
    source_checks["tongzong_numeric_door_conflict_verified"] = (
        tongzong_numeric_door_conflict_verified
    )
    for key in (
        "term_ju_table_parsed",
        "plate_orders_parsed",
        "chief_director_rules_present",
        "center_hosting_rule_present",
        "selected_spatial_plate_rules_verified",
        "selected_chaibu_rule_verified",
        "xun_horse_tables_verified",
        "tongzong_numeric_door_conflict_verified",
        "named_pattern_anchors_verified",
        "declared_tongzong_identity_verified",
        "structured_pattern_contract_verified",
        "pattern_source_identity_contract_verified",
        "evidence_source_identity_bridge_verified",
        "evidence_quote_source_text_verified",
        "pattern_conflicts_versioned",
    ):
        if resolved_research_root is not None:
            _finding(
                source_verification.setdefault("findings", []),
                source_checks[key] is True,
                f"Qimen normalized-source check failed: {key}",
            )

    independent_oracle_mismatches = 0
    activated_pattern_ids: set[str] = set(covered_pattern_ids)
    for case in cases:
        identifier = str(case.get("id") or "")
        try:
            board = qimen.build_board(**case["input"])
            actual = _expected_board(board)
            activated_pattern_ids.update(
                str(item["id"]) for item in board["named_patterns"]
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"fixture board failed: {identifier}: {exc}")
            continue
        _finding(
            findings,
            actual == case.get("expected"),
            f"fixture board mismatch: {identifier}",
        )
        try:
            reference = _reference_expected(table, case["input"])
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            independent_oracle_mismatches += 1
            findings.append(f"independent fixture oracle failed: {identifier}: {exc}")
        else:
            if reference != case.get("expected"):
                independent_oracle_mismatches += 1
            _finding(
                findings,
                reference == case.get("expected"),
                f"independent fixture oracle mismatch: {identifier}",
            )

    _finding(
        findings,
        len(pattern_cases) >= 3,
        "Qimen fixture requires explicit activation boards for uncovered patterns",
    )
    _finding(
        findings,
        len(pattern_cases) == len({case.get("id") for case in pattern_cases}),
        "Qimen named-pattern fixture ids are not unique",
    )
    for case in pattern_cases:
        identifier = str(case.get("id") or "")
        try:
            board = qimen.build_board(**case["input"])
            actual_ids = {
                str(item["id"]) for item in board["named_patterns"]
            }
            expected_ids = {
                str(value) for value in case.get("expected_pattern_ids") or ()
            }
            activated_pattern_ids.update(actual_ids)
            _finding(
                findings,
                actual_ids == expected_ids,
                f"named-pattern activation mismatch: {identifier}",
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"named-pattern activation failed: {identifier}: {exc}")
    source_pattern_ids = {
        str(profile["id"])
        for profile in table.get("named_pattern_predicates") or ()
    }
    _finding(
        findings,
        activated_pattern_ids == source_pattern_ids,
        "Qimen frozen boards do not activate every source-bound pattern",
    )

    _finding(findings, len(classical_cases) >= 1, "Qimen fixture requires a complete classical worked board")
    for case in classical_cases:
        identifier = str(case.get("id") or "")
        anchor = str(case.get("source_anchor") or "")
        try:
            board = qimen.build_board(**case["input"])
            director_palace = int(board["director"]["destination_palace"])
            director_row = next(
                row for row in board["palaces"] if row["palace"] == director_palace
            )
            observed = {
                "dun": board["dun"],
                "yuan": board["yuan"],
                "ju": board["ju"]["number"],
                "xun": board["xunkong"]["xun"],
                "chief": board["chief"]["star"],
                "chief_palace": board["chief"]["destination_palace"],
                "director": board["director"]["door"],
                "director_palace": director_palace,
                "director_deity": director_row["deity"],
                "signature": _board_signature(board),
            }
            _finding(
                findings,
                observed == case.get("expected"),
                f"classical worked board mismatch: {identifier}",
            )
            if resolved_research_root is not None and source_text:
                line_number = int(anchor.removeprefix("L"))
                source_line = source_text.splitlines()[line_number - 1]
                contract = case["source_text_contract"]
                chinese_digits = "零一二三四五六七八九"
                required_phrases = (
                    str(contract["dun_ju"]),
                    str(contract["day_stem_group"]),
                    str(contract["hour_ganzhi"]),
                    str(contract["xun"]),
                    f"加{chinese_digits[int(contract['chief_destination_palace'])]}宫",
                    f"{contract['director']}值使加{chinese_digits[int(contract['director_destination_palace'])]}宫",
                    f"上临{contract['director_deity']}",
                )
                _finding(
                    source_verification.setdefault("findings", []),
                    all(phrase in source_line for phrase in required_phrases),
                    f"classical source contract mismatch: {identifier}",
                )
        except (IndexError, KeyError, TypeError, ValueError, StopIteration) as exc:
            findings.append(f"classical worked board failed: {identifier}: {exc}")

    term_count = len({case.get("input", {}).get("active_term") for case in cases})
    yuan = {case.get("expected", {}).get("yuan") for case in cases}
    dun = {case.get("expected", {}).get("dun") for case in cases}
    xun = {case.get("expected", {}).get("xun") for case in cases}
    _finding(findings, term_count == 24, "Qimen fixtures do not cover all 24 solar terms")
    _finding(findings, yuan == {"upper", "middle", "lower"}, "Qimen fixtures do not cover all three Yuan")
    _finding(findings, dun == {"yang", "yin"}, "Qimen fixtures do not cover both Dun directions")
    _finding(findings, xun == set(qimen.XUN_HEADS), "Qimen fixtures do not cover all six Xunshou")

    dependency_rows = matrix["providers"]["qimen"]["dependencies"]
    dependency_ids = [str(row.get("id") or "") for row in dependency_rows]
    _finding(
        findings,
        dependency_ids == list(qimen.SOURCE_DEPENDENCIES),
        "Qimen dependency IDs do not match the provider contract",
    )
    source_audit = audit_algorithm_sources.audit_matrix(
        matrix,
        root=ROOT,
        systems=("qimen",),
    )
    findings.extend(
        f"algorithm source audit: {item}"
        for item in source_audit["findings"]
    )
    if resolved_research_root is not None:
        source_verification["ok"] = not source_verification.get("findings")
        source_verification["status"] = (
            "verified" if source_verification["ok"] else "failed"
        )
    palace_profiles = table["palaces"]
    report = {
        "schema_version": "mingli-qimen-provider-audit-v1",
        "system": "qimen",
        "provider_ready": not findings,
        "status": "pass" if not findings else "fail",
        "provider": {
            "provider_id": QimenProvider.provider_id,
            "provider_version": QimenProvider.provider_version,
            "capability_mode": PROVIDER_CAPABILITIES["qimen"].mode,
        },
        "route_owned_case_ids": [
            str(case.get("id") or "") for case in external_reference_cases
        ],
        "fixture": {
            "path": str(fixture_path),
            "sha256": fixture_sha256,
            "expected_sha256": EXPECTED_FIXTURE_SHA256,
        },
        "fixture_sha256": fixture_sha256,
        "fixture_artifacts": {
            "route_fixture_sha256": fixture_sha256,
            "expected_route_fixture_sha256": EXPECTED_FIXTURE_SHA256,
            "qualifying_external_fixture_sha256": _sha256(
                external_fixture_path
            ),
            "qualifying_artifact_hashes": {
                "qimen_route_fixture": fixture_sha256,
                "qimen_go_external_fixture": _sha256(external_fixture_path),
            },
        },
        "profile_id": qimen.TABLE_PROFILE,
        "counts": {
            "qualifying_cases": qualifying_cases,
            "route_owned_cases": len(external_reference_cases),
            "provider_calculations": provider_calculations,
            "provider_extensions": provider_extensions,
            "determinism_checks": determinism_checks,
            "boundary_case_count": len(boundaries),
            "boundary_provider_calculations": boundary_provider_calculations,
            "boundary_provider_determinism_checks": (
                boundary_provider_determinism_checks
            ),
            "source_rule_boards": len(cases),
            "classical_worked_boards": len(classical_cases),
            "classical_conflict_boards": len(classical_door_map_cases),
            "solar_terms": term_count,
            "yuan_profiles": len(yuan),
            "dun_profiles": len(dun),
            "xun_profiles": len(xun),
            "calendar_boundaries": len(boundaries),
            "lunar_leap_months": categories["lunar_leap_month"],
            "palaces": len(palace_profiles),
            "stars": len({row["star"] for row in palace_profiles.values()}),
            "doors": len({row["door"] for row in palace_profiles.values() if row["door"]}),
            "deities": len(table["orders"]["deities"]["baihu_xuanwu_variant"]),
            "algorithm_dependencies": len(dependency_rows),
            "named_pattern_predicates": len(table["named_pattern_predicates"]),
            "independent_pattern_contracts": len(pattern_contract_rows),
            "source_bound_evidence_rules": len(qimen_evidence_rules),
            "named_pattern_coverage": len(covered_pattern_ids),
            "pattern_activation_boards": len(pattern_activation_cases),
            "calendar_pattern_witnesses": verified_calendar_pattern_witnesses,
            "independent_reference_boards": len(cases),
            "independent_oracle_mismatches": independent_oracle_mismatches,
            "external_reference_boards": len(external_reference_cases),
            "external_reference_mismatches": external_reference_mismatches,
        },
        "boundary_categories": sorted(
            (
                {str(case.get("category") or "") for case in boundaries}
                | {"external_reference"}
            )
            - {""}
        ),
        "source_checks": source_checks,
        "source_verification": source_verification,
        "findings": findings,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_qimen_provider()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"Qimen provider ready: {report['provider_ready']} "
            f"({report['counts']['source_rule_boards']} boards, "
            f"{len(report['findings'])} findings)"
        )
        for finding in report["findings"]:
            print(f"- {finding}")
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
