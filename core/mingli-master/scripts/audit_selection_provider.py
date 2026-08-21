#!/usr/bin/env python3
"""Machine-readable completeness audit for the V5.1 Selection provider."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import re
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import yaml

import audit_algorithm_sources
from audit_provider_preflight import provider_preflight_failure
import build_selection_formula_fixtures
from reading_engine import selection
from reading_engine.contracts import ReadingRequest, canonical_digest
from reading_engine.providers import PROVIDER_CAPABILITIES, SelectionProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/selection-v51.yaml"
MATRIX = ROOT / "references/matrices/algorithm-source-dependencies.yaml"
SOURCE_TABLE = ROOT / "references/matrices/selection-source-tables-v1.yaml"
XIEJI_RULES = ROOT / "references/books/selection/xieji-bianfang-shu/rules.md"
EXPECTED_FIXTURE_SHA256 = "ec2ac7599b18b9ea8ad8762e8b7214aad0e7a402a3f9eaac1bf4f3a09bb18686"
EXPECTED_PROVIDER_ID = "mingli-master.selection.v1"
EXPECTED_PROVIDER_VERSION = "1.3.0"
EXPECTED_SOURCE_TABLE_SHA256 = "3a32f9fe65b0ecb8b1285ef4578e5492cff9be622d44424c89bddd2346a93ec6"
EXPECTED_CLASSICAL_BINDINGS_SHA256 = "73c5a8a5d2041e7d49f838c70d0ca184fee060fd355a8f29b0fd6f9a0a7abc8d"
EXPECTED_PRIMARY_CLASSICAL_RULE_WITNESSES = {"xieji-xunshan-luohou-v1"}
EXPECTED_LUOHOU_MITIGATION_WITNESSES = (
    (
        "L10778",
        "one_white_mitigation",
        "36b1757d2592669dc5d848f1eb6700d359f413788e0042ef8ca2c779d2ea8af4",
    ),
    (
        "L10969",
        "explicit_action_scope",
        "e56cda9e42fa2a319adf8d3af98d19d75a9972756e13284efe67d39917982883",
    ),
    (
        "L10970",
        "non_same_palace_mitigation",
        "88baa779a2edc6794de9589cae68757c07824796a8567978a34b43178dd56d6f",
    ),
    (
        "L10970",
        "same_palace_prohibition",
        "654ed24a53e62eea113e90e3be211d5f747f4616bb2b804fae9e50a186a5c7e5",
    ),
    (
        "L11305",
        "explicit_action_scope_restatement",
        "81a7c422b8f641aab4549e95ce9f374fbc9375b110042d3684ac21198fdbf7e0",
    ),
)


def _extension_covers_declared_range(
    facts: Mapping[str, Any], horizon: Mapping[str, Any]
) -> bool:
    try:
        kind = str(horizon["kind"])
        start_value = str(horizon["start"])
        end_value = str(horizon["end"])
        if kind == "day":
            start_date = date.fromisoformat(start_value)
            end_date = date.fromisoformat(end_value)
        elif kind == "month":
            start_year, start_month = (int(item) for item in start_value.split("-"))
            end_year, end_month = (int(item) for item in end_value.split("-"))
            start_date = date(start_year, start_month, 1)
            next_year = end_year + (1 if end_month == 12 else 0)
            next_month = 1 if end_month == 12 else end_month + 1
            end_date = date.fromordinal(date(next_year, next_month, 1).toordinal() - 1)
        elif kind == "year":
            start_date = date(int(start_value), 1, 1)
            end_date = date(int(end_value), 12, 31)
        else:
            return False
        expected_dates = [
            date.fromordinal(ordinal).isoformat()
            for ordinal in range(start_date.toordinal(), end_date.toordinal() + 1)
        ]
        candidates = facts.get("calendar_candidates")
        if not isinstance(candidates, list):
            return False
        actual_dates = [
            str(candidate.get("civil_date") or "")
            for candidate in candidates
            if isinstance(candidate, Mapping)
        ]
        return actual_dates == expected_dates
    except (KeyError, TypeError, ValueError):
        return False


def _extension_samples_match_independent_build(
    facts: Mapping[str, Any],
    horizon: Mapping[str, Any],
    *,
    spec: Mapping[str, Any],
    timezone_name: str,
    location: str,
) -> bool:
    if not _extension_covers_declared_range(facts, horizon):
        return False
    candidates = facts.get("calendar_candidates")
    if not isinstance(candidates, list) or not candidates:
        return False
    indexes = sorted({0, len(candidates) // 2, len(candidates) - 1})
    comparable_keys = (
        "candidate_id",
        "civil_date",
        "best_date_time_basis",
        "eligibility",
        "rejection_reasons",
        "ranking_components",
        "active_source_rule_ids",
    )
    try:
        for index in indexes:
            actual = candidates[index]
            if not isinstance(actual, Mapping):
                return False
            civil_date = str(actual["civil_date"])
            single_spec = copy.deepcopy(dict(spec))
            single_spec["date_range"] = {
                "start": civil_date,
                "end": civil_date,
            }
            rebuilt = selection.build_fact_layer(
                single_spec,
                timezone_name=timezone_name,
                location=location,
            )
            expected = rebuilt["output"]["calendar_candidates"][0]
            if any(actual.get(key) != expected.get(key) for key in comparable_keys):
                return False
    except (KeyError, TypeError, ValueError):
        return False
    return True
EXPECTED_SELECTION_RULE_IDS = {
    *(f"DR-{index:02d}" for index in range(1, 11)),
    *(f"XR-{index:02d}" for index in range(1, 19)),
    *(f"KR-{index:02d}" for index in range(1, 21)),
    *(f"JR-{index:02d}" for index in range(1, 21)),
}
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object in {path}")
    return payload


def published_case_matches_artifact(
    case: dict[str, Any], comparator: dict[str, Any], artifact: bytes
) -> bool:
    """Verify a fixture against the exact cited row of an HKO CSV artifact."""

    try:
        anchor = re.fullmatch(r"CSV row (\d+)", str(case["source_anchor"]))
        if not anchor:
            return False
        rows = list(csv.reader(io.StringIO(artifact.decode("utf-8-sig"))))
        row_number = int(anchor.group(1))
        if row_number < 2 or row_number > len(rows):
            return False
        if rows[0][:5] != [
            "Gregorian Date",
            "Chinese year (Gan-Zhi)",
            "Chinese year (Zodiac)",
            "Lunar month",
            "Lunar Date",
        ]:
            return False
        row = rows[row_number - 1]
        if len(row) < 5:
            return False
        day_text, month_text, year_text = row[0].split("-")
        year_value = 2000 + int(year_text)
        civil_date = date(
            year_value, HKO_MONTHS[month_text], int(day_text)
        ).isoformat()
        if civil_date != str(comparator["input"]["date"]):
            return False

        expected = case["expected"]
        lunar_year = int(expected["lunar_year"])
        expected_ganzhi = STEMS[(lunar_year - 4) % 10] + BRANCHES[
            (lunar_year - 4) % 12
        ]
        if (
            str(expected["chinese_year_ganzhi"]) != expected_ganzhi
            or row[1].strip() != f"{expected_ganzhi}年"
        ):
            return False

        lunar_month_text = row[3].strip().removesuffix("月")
        is_leap = lunar_month_text.startswith(("閏", "闰"))
        if is_leap:
            lunar_month_text = lunar_month_text[1:]
        lunar_day_text = row[4].strip()
        return (
            CHINESE_LUNAR_MONTHS[lunar_month_text]
            == int(expected["lunar_month"])
            and CHINESE_LUNAR_DAYS[lunar_day_text]
            == int(expected["lunar_day"])
            and is_leap is bool(expected["is_leap_month"])
        )
    except (KeyError, TypeError, ValueError, UnicodeError):
        return False


def audit_selection_provider(
    *,
    fixture_path: str | Path = FIXTURE,
    source_table_path: str | Path = SOURCE_TABLE,
    verify_published_sources: bool = False,
    research_root: Path | None = None,
) -> dict[str, Any]:
    """Audit the live Selection provider against frozen V5.1 fixtures.

    ``research_root`` is the release-time fulltext tree for source
    verification.  Without an explicit root, ``provider_ready`` reflects only
    runtime capability (fixtures, provider calculation, digest, oracle) and
    never fails because the external fulltext corpus is absent; hash-bound
    fulltext checks then report into the ``source_verification`` block as
    ``skipped``.  A release build passes an explicit root to close that gate.
    """
    preflight = provider_preflight_failure(
        system="selection",
        schema_version="mingli-selection-provider-audit-v1",
        provider_class=SelectionProvider,
        expected_mode="calculation",
        expected_provider_id=EXPECTED_PROVIDER_ID,
        expected_provider_version=EXPECTED_PROVIDER_VERSION,
    )
    if preflight is not None:
        return preflight

    fixture_path = Path(fixture_path)
    source_table_path = Path(source_table_path)
    fixture = _load(fixture_path)
    source = _load(source_table_path)
    matrix = _load(MATRIX)
    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(matrix, ROOT)
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    findings: list[str] = []
    if (
        SelectionProvider.provider_id != EXPECTED_PROVIDER_ID
        or SelectionProvider.provider_version != EXPECTED_PROVIDER_VERSION
    ):
        findings.append("Selection provider identity drift")
    if PROVIDER_CAPABILITIES["selection"].mode != "calculation":
        findings.append("Selection provider capability mode is not calculation")

    source_table_hash_matches = (
        _sha256(source_table_path) == EXPECTED_SOURCE_TABLE_SHA256
    )
    fixture_hash_matches = _sha256(fixture_path) == EXPECTED_FIXTURE_SHA256
    if not source_table_hash_matches:
        findings.append("Selection source-table artifact hash mismatch")
    if not fixture_hash_matches:
        findings.append("Selection fixture artifact hash mismatch")
    if source.get("schema_version") != "mingli-selection-source-tables-v1":
        findings.append("Selection source-table schema mismatch")
    if source.get("version") != "1.2.1":
        findings.append("Selection source-table version mismatch")
    if fixture.get("schema_version") != "mingli-selection-fixtures-v51":
        findings.append("Selection fixture schema mismatch")

    event_profiles = source.get("event_profiles") or {}
    event_definitions = source.get("event_fact_definitions") or {}
    allowed_rank_effects = {
        "hard_elimination",
        "favorable_preference",
        "informational",
        "comparison_only",
    }
    required_event_fields = {
        str(field)
        for profile in event_profiles.values()
        if isinstance(profile, dict)
        for field in profile.get("required_event_fact_fields") or ()
    }
    if set(event_definitions) != required_event_fields:
        findings.append("Selection event fact definition coverage mismatch")
    for field, definition in event_definitions.items():
        if not isinstance(definition, dict) or not definition.get("kind"):
            findings.append(f"Selection event fact definition invalid: {field}")
            continue
        anchors = definition.get("source_anchors") or ()
        if not isinstance(anchors, list) or not all(
            isinstance(anchor, str) and anchor.strip() for anchor in anchors
        ):
            findings.append(f"Selection event fact source anchors missing: {field}")
        if (
            definition.get("rank_effect") is not None
            and definition.get("rank_effect") not in allowed_rank_effects
        ):
            findings.append(f"Selection event fact rank effect invalid: {field}")
    for profile, contract in event_profiles.items():
        if not isinstance(contract, dict):
            findings.append(f"Selection event profile contract invalid: {profile}")
            continue
        fields = contract.get("required_event_fact_fields") or ()
        if len(fields) != len(set(fields)):
            findings.append(f"Selection event profile repeats a fact: {profile}")
        if not contract.get("source_rules"):
            findings.append(f"Selection event profile source rules missing: {profile}")

    for profile, source_profile in (source.get("source_profiles") or {}).items():
        if not isinstance(source_profile, dict):
            findings.append(f"Selection source profile invalid: {profile}")
            continue
        # The classical fulltext hash is a release-time gate: it is only
        # checkable against an explicit research source root and must not
        # block runtime readiness in a portable checkout.
        if resolved_research_root is not None:
            relative_source = Path(str(source_profile.get("normalized_path") or ""))
            normalized_path = resolved_research_root / relative_source
            if (
                not normalized_path.is_file()
                or _sha256(normalized_path) != source_profile.get("sha256")
            ):
                source_verification.setdefault("findings", []).append(
                    f"Selection classical source hash mismatch: {profile}"
                )
        release_path = source_profile.get("release_table_path")
        if release_path and (
            not (ROOT / str(release_path)).is_file()
            or _sha256(ROOT / str(release_path))
            != source_profile.get("release_table_sha256")
        ):
            findings.append(f"Selection release table hash mismatch: {profile}")

    primary_classical_rule_witness_checks = 0
    primary_witnesses = source.get("primary_classical_rule_witnesses") or {}
    if not isinstance(primary_witnesses, dict):
        primary_witnesses = {}
    if set(primary_witnesses) != EXPECTED_PRIMARY_CLASSICAL_RULE_WITNESSES:
        findings.append("Selection primary classical rule witness coverage mismatch")
    for identifier, witness in primary_witnesses.items():
        valid = isinstance(witness, dict)
        if not valid:
            findings.append(
                f"Selection primary classical rule witness invalid: {identifier}"
            )
            continue
        valid = False
        source_valid = resolved_research_root is None
        try:
            source_profile_id = str(witness["source_profile"])
            source_profile = source["source_profiles"][source_profile_id]
            exact_quote = str(witness["exact_quote"])
            normalized_formula = str(witness["normalized_formula"])
            runtime_evidence_statement = str(witness["runtime_evidence_statement"])
            event_profile_id = str(witness["event_profile"])
            event_fact_field = str(witness["event_fact_field"])
            definition = event_definitions[event_fact_field]
            event_profile = event_profiles[event_profile_id]
            formula_key = str(witness["directional_formula_key"])
            formula = source["directional_formulas"][formula_key]
            taboo_actions = witness["explicitly_taboo_actions"]
            exempt_actions = witness["explicitly_exempt_actions"]
            glyph_normalization = witness["source_action_glyph_normalization"]
            source_actions = [
                "".join(glyph_normalization.get(glyph, glyph) for glyph in action)
                for action in taboo_actions + exempt_actions
            ]
            expected_exact_quote = (
                "起例巡山羅㬋為太嵗前一位"
                + "".join(f"{branch}年在{formula[branch]}" for branch in BRANCHES)
                + "○選擇宗鏡曰巡山羅㬋止忌"
                + "".join(source_actions)
                + "不忌"
            )
            expected_normalized_formula = (
                "；".join(f"{branch}{formula[branch]}" for branch in BRANCHES)
                + f"；止忌{'、'.join(taboo_actions)}"
                + f"；{'、'.join(exempt_actions)}不忌"
            )
            mitigation_witnesses = witness["mitigation_witnesses"]
            observed_mitigation_witnesses = tuple(
                (
                    str(row["source_anchor"]),
                    str(row["role"]),
                    str(row["exact_excerpt_sha256"]),
                )
                for row in mitigation_witnesses
            )
            mitigation_hashes_valid = all(
                hashlib.sha256(
                    str(row["exact_excerpt"]).encode("utf-8")
                ).hexdigest()
                == row.get("exact_excerpt_sha256")
                for row in mitigation_witnesses
            )
            # Structural witness integrity is a pure source-table contract and
            # never depends on the external fulltext tree.
            valid = all(
                (
                    witness.get("source_anchor")
                    == (source_profile.get("anchors") or {}).get("xunshan_luohou"),
                    exact_quote == expected_exact_quote,
                    hashlib.sha256(exact_quote.encode("utf-8")).hexdigest()
                    == witness.get("exact_quote_sha256"),
                    normalized_formula == expected_normalized_formula,
                    hashlib.sha256(normalized_formula.encode("utf-8")).hexdigest()
                    == witness.get("normalized_formula_sha256"),
                    witness.get("evidence_rule_id") == "XR-18",
                    runtime_evidence_statement in XIEJI_RULES.read_text(encoding="utf-8"),
                    hashlib.sha256(
                        runtime_evidence_statement.encode("utf-8")
                    ).hexdigest()
                    == witness.get("runtime_evidence_statement_sha256"),
                    definition.get("kind") == "direction_formula",
                    formula_key == f"{definition.get('formula')}_by_year_branch",
                    set(formula) == set(BRANCHES),
                    definition.get("applicable_actions") == taboo_actions,
                    definition.get("explicitly_exempt_actions")
                    == exempt_actions,
                    definition.get("rank_effect") == "informational",
                    "rank_effect" not in witness,
                    isinstance(taboo_actions, list),
                    isinstance(exempt_actions, list),
                    taboo_actions == ["立向"],
                    exempt_actions == ["开山", "修方"],
                    glyph_normalization == {"开": "開"},
                    bool(taboo_actions),
                    bool(exempt_actions),
                    not set(taboo_actions) & set(exempt_actions),
                    set(taboo_actions + exempt_actions)
                    <= set(event_profile.get("official_terms") or ()),
                    witness.get("runtime_rank_policy")
                    == "informational_until_same_palace_and_mitigation_facts_are_calculated",
                    observed_mitigation_witnesses
                    == EXPECTED_LUOHOU_MITIGATION_WITNESSES,
                    mitigation_hashes_valid,
                    (source_profile.get("anchors") or {}).get(
                        "xunshan_luohou_mitigation"
                    )
                    == ["L10778", "L10969-L10970", "L11305"],
                    definition.get("source_anchors")
                    == [
                        "XR-18",
                        "xieji-fulltext-L1699-L1700",
                        "xieji-fulltext-L10778",
                        "xieji-fulltext-L10969-L10970",
                        "xieji-fulltext-L11305",
                        "xieji-xunshan-luohou-v1",
                    ],
                    "exact primary classical witness"
                    in str(witness.get("role") or ""),
                )
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            valid = False
        # Binding the exact quotes to the hash-bound fulltext is the
        # release-time gate; it runs only with an explicit research root and
        # any failure there must not block runtime readiness.
        if resolved_research_root is not None:
            try:
                normalized_path = resolved_research_root / Path(
                    str(source["source_profiles"][str(witness["source_profile"])][
                        "normalized_path"
                    ])
                )
                source_text = normalized_path.read_text(encoding="utf-8")
                source_valid = all(
                    (
                        normalized_path.is_file(),
                        _sha256(normalized_path)
                        == source["source_profiles"][str(witness["source_profile"])][
                            "sha256"
                        ],
                        str(witness["exact_quote"]) in source_text,
                        all(
                            str(row["exact_excerpt"]) in source_text
                            for row in witness["mitigation_witnesses"]
                        ),
                    )
                )
            except (AttributeError, KeyError, OSError, TypeError, ValueError):
                source_valid = False
        if valid and source_valid:
            primary_classical_rule_witness_checks += 1
        elif resolved_research_root is not None:
            source_verification.setdefault("findings", []).append(
                f"Selection primary classical rule witness invalid: {identifier}"
            )
        else:
            findings.append(
                f"Selection primary classical rule witness invalid: {identifier}"
            )

    for identifier, contract in (
        source.get("engineering_verification_sources") or {}
    ).items():
        normalized_rule = str(contract.get("normalized_rule") or "")
        normalized_hash = hashlib.sha256(
            normalized_rule.encode("utf-8")
        ).hexdigest()
        exact_excerpt = str(contract.get("exact_excerpt") or "")
        exact_excerpt_hash = hashlib.sha256(
            exact_excerpt.encode("utf-8")
        ).hexdigest()
        if (
            not str(contract.get("url") or "").startswith("https://")
            or not contract.get("publisher")
            or not contract.get("issued_year")
            or not contract.get("source_anchor")
            or exact_excerpt_hash != contract.get("exact_excerpt_sha256")
            or normalized_hash != contract.get("normalized_rule_sha256")
            or "never a classical or official-primary evidence source"
            not in str(contract.get("role") or "")
        ):
            findings.append(
                f"Selection engineering verification source invalid: {identifier}"
            )

    supplemental_local_artifact_checks = 0
    supplemental_source_verification_failures = 0
    for identifier, contract in (
        source.get("supplemental_classical_sources") or {}
    ).items():
        exact_quote = str(contract.get("exact_quote") or "")
        exact_hash = hashlib.sha256(exact_quote.encode("utf-8")).hexdigest()
        normalized_formula = str(contract.get("normalized_formula") or "")
        normalized_formula_hash = hashlib.sha256(
            normalized_formula.encode("utf-8")
        ).hexdigest()
        if (
            not str(contract.get("url") or "").startswith("https://")
            or not contract.get("witness")
            or not contract.get("source_anchor")
            or exact_hash != contract.get("exact_quote_sha256")
            or (
                normalized_formula
                and normalized_formula_hash
                != contract.get("normalized_formula_sha256")
            )
            or "classical" not in str(contract.get("role") or "")
        ):
            findings.append(
                f"Selection supplemental classical source invalid: {identifier}"
            )
        local_path = ROOT / str(contract.get("local_artifact_path") or "")
        try:
            local_text = local_path.read_text(encoding="utf-8")
            if (
                not local_path.is_file()
                or _sha256(local_path)
                != str(contract.get("local_artifact_sha256") or "")
                or exact_quote not in local_text
            ):
                raise ValueError("supplemental local artifact mismatch")
            supplemental_local_artifact_checks += 1
        except (OSError, ValueError):
            findings.append(
                f"Selection supplemental local artifact invalid: {identifier}"
            )
        if verify_published_sources:
            try:
                request = Request(
                    str(contract["url"]),
                    headers={"User-Agent": "mingli-master-source-audit/4.1"},
                )
                with urlopen(request, timeout=30) as response:
                    artifact_text = response.read().decode("utf-8", "ignore")
                if exact_quote not in artifact_text:
                    raise ValueError("supplemental exact quote not found")
            except (KeyError, OSError, ValueError):
                supplemental_source_verification_failures += 1
    if supplemental_source_verification_failures:
        findings.append(
            "Selection supplemental source verification failures: "
            f"{supplemental_source_verification_failures}"
        )

    evidence_bindings = source.get("evidence_fact_bindings") or {}
    evidence_contracts = evidence_bindings.get("contracts") or {}
    evidence_rules = evidence_bindings.get("rules") or {}
    if (
        evidence_bindings.get("version") != "1.1.0"
        or set(evidence_rules) != EXPECTED_SELECTION_RULE_IDS
    ):
        findings.append("Selection evidence fact binding coverage mismatch")
    for rule_id, contract_id in evidence_rules.items():
        predicates = evidence_contracts.get(contract_id)
        if not isinstance(predicates, list) or not predicates:
            findings.append(f"Selection evidence fact contract missing: {rule_id}")
            continue
        for predicate in predicates:
            if (
                not isinstance(predicate, dict)
                or not str(predicate.get("path_suffix") or "").startswith("/")
                or predicate.get("operator")
                not in {
                    "present",
                    "nonempty",
                    "eq",
                    "in",
                    "contains",
                    "descendant_eq",
                }
            ):
                findings.append(f"Selection evidence fact predicate invalid: {rule_id}")
                break

    dependencies = matrix.get("providers", {}).get("selection", {}).get("dependencies", [])
    dependency_ids = tuple(row.get("id") for row in dependencies if isinstance(row, dict))
    if dependency_ids != selection.SOURCE_DEPENDENCIES:
        findings.append("Selection dependency order or identity mismatch")
    for row in dependencies:
        artifact = row.get("source_artifact") if isinstance(row, dict) else {}
        expected_artifact_hash = (
            EXPECTED_CLASSICAL_BINDINGS_SHA256
            if row.get("id") == "selection.source-conditioned-patterns"
            else EXPECTED_SOURCE_TABLE_SHA256
        )
        if artifact.get("sha256") != expected_artifact_hash:
            findings.append(f"Selection dependency source hash mismatch: {row.get('id')}")
    event_dependency = next(
        (
            row
            for row in dependencies
            if isinstance(row, dict)
            and row.get("id") == "selection.event-rules-and-lineage-conflicts"
        ),
        {},
    )
    expected_primary_rule_witnesses = [
        {
            "id": identifier,
            "source_profile": witness.get("source_profile"),
            "source_anchor": witness.get("source_anchor"),
            "event_profile": witness.get("event_profile"),
            "event_fact_field": witness.get("event_fact_field"),
            "directional_formula_key": witness.get("directional_formula_key"),
            "evidence_rule_id": witness.get("evidence_rule_id"),
            "exact_quote_sha256": witness.get("exact_quote_sha256"),
            "normalized_formula_sha256": witness.get("normalized_formula_sha256"),
            "explicitly_taboo_actions": witness.get("explicitly_taboo_actions"),
            "explicitly_exempt_actions": witness.get(
                "explicitly_exempt_actions"
            ),
            "source_action_glyph_normalization": witness.get(
                "source_action_glyph_normalization"
            ),
            "runtime_rank_policy": witness.get("runtime_rank_policy"),
            "runtime_evidence_statement_sha256": witness.get(
                "runtime_evidence_statement_sha256"
            ),
            "mitigation_witnesses": [
                {
                    "source_anchor": row.get("source_anchor"),
                    "exact_excerpt_sha256": row.get("exact_excerpt_sha256"),
                    "role": row.get("role"),
                }
                for row in witness.get("mitigation_witnesses") or ()
                if isinstance(row, dict)
            ],
        }
        for identifier, witness in primary_witnesses.items()
        if isinstance(witness, dict)
    ]
    if event_dependency.get("primary_rule_witnesses") != expected_primary_rule_witnesses:
        findings.append("Selection primary rule witness dependency mismatch")
    oracle = event_dependency.get("reference_oracle_artifact") or {}
    oracle_path = ROOT / str(oracle.get("path") or "")
    if (
        oracle.get("id")
        != build_selection_formula_fixtures.selection_formula_reference.REFERENCE_EVALUATOR_ID
        or oracle.get("version")
        != build_selection_formula_fixtures.selection_formula_reference.REFERENCE_EVALUATOR_VERSION
        or not oracle_path.is_file()
        or _sha256(oracle_path)
        != build_selection_formula_fixtures.REFERENCE_EVALUATOR_SHA256
        or oracle.get("sha256")
        != build_selection_formula_fixtures.REFERENCE_EVALUATOR_SHA256
    ):
        findings.append("Selection independent reference evaluator hash mismatch")

    external_cases = fixture.get("external_reference_cases") or []
    if not source_table_hash_matches or not fixture_hash_matches:
        donggong_ids = {
            line.split("|", 2)[1].strip()
            for line in selection.DONGGONG_TABLE_PATH.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.startswith("| DG-D")
        }
        verdict_profiles = (
            (source.get("donggong_event_verdicts") or {}).get("profiles") or {}
        )
        for profile, verdicts in verdict_profiles.items():
            if not isinstance(verdicts, dict):
                continue
            groups = {
                verdict: list(verdicts.get(verdict) or ())
                for verdict in ("recommend", "avoid", "mixed_conditional")
            }
            complete = {
                identifier: next(
                    (
                        verdict
                        for verdict, identifiers in groups.items()
                        if identifier in identifiers
                    ),
                    "not_stated",
                )
                for identifier in sorted(donggong_ids)
            }
            digest = hashlib.sha256(
                json.dumps(
                    complete,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            if digest != verdicts.get("classification_sha256"):
                findings.append(
                    f"Selection Donggong classification hash mismatch: {profile}"
                )
        return {
            "schema_version": "mingli-selection-provider-audit-v1",
            "system": "selection",
            "provider_ready": False,
            "status": "fail",
            "provider": {
                "provider_id": SelectionProvider.provider_id,
                "provider_version": SelectionProvider.provider_version,
                "capability_mode": PROVIDER_CAPABILITIES["selection"].mode,
            },
            "route_owned_case_ids": [
                str(case.get("id") or "")
                for case in external_cases
                if isinstance(case, dict)
            ],
            "fixture": {
                "path": str(fixture_path),
                "sha256": _sha256(fixture_path),
                "expected_sha256": EXPECTED_FIXTURE_SHA256,
            },
            "fixture_sha256": _sha256(fixture_path),
            "counts": {
                "qualifying_cases": 0,
                "route_owned_cases": len(external_cases),
            },
            "boundary_categories": [],
            "source_verification": source_verification,
            "findings": list(dict.fromkeys(findings)),
        }
    unexplained = 0
    declared = 0
    qualifying_cases = 0
    provider_calculations = 0
    provider_extensions = 0
    determinism_checks = 0
    declared_horizons: set[str] = set()
    replay_cases = (
        external_cases
        if source_table_hash_matches and fixture_hash_matches
        else ()
    )
    for index, case in enumerate(replay_cases):
        try:
            supplied = case["input"]
            civil_date = str(supplied["date"])
            timezone_name = str(supplied["timezone"])
            location = str(supplied["location"])
            spec = {
                "event_profile": str(
                    supplied.get("event_profile") or "generic_selection"
                ),
                "requested_actions": list(supplied.get("requested_actions") or []),
                "date_range": {"start": civil_date, "end": civil_date},
                # The frozen comparator cases explicitly declare 12:00.  A
                # one-minute hard window makes the live candidate use that
                # same civil instant, including exact-Jie transition days.
                "hard_constraints": {
                    "time_windows": [{"start": "12:00", "end": "12:01"}]
                },
                "participant_facts": [],
                "include_folk_comparison": False,
            }
            if supplied.get("requested_scopes"):
                spec["requested_scopes"] = list(supplied["requested_scopes"])
            if supplied.get("directional_context"):
                spec["directional_context"] = dict(supplied["directional_context"])
            request = ReadingRequest(
                query=f"Task 7N Selection provider replay {case.get('id')}",
                action="new",
                system="selection",
                timezone=timezone_name,
                location=location,
                chart_data={"selection_spec": spec},
            )
            first = SelectionProvider(ROOT).calculate(request)
            second = SelectionProvider(ROOT).calculate(request)
            provider_calculations += 2
            for result in (first, second):
                if (
                    result.system != "selection"
                    or result.provider_id != SelectionProvider.provider_id
                    or result.provider_version != SelectionProvider.provider_version
                ):
                    raise ValueError("live provider identity mismatch")
                candidates = result.facts["chart_facts"]["output"][
                    "calendar_candidates"
                ]
                if len(candidates) != 1 or candidates[0]["civil_date"] != civil_date:
                    raise ValueError("live provider did not preserve the bounded day")
            if (
                first.result_hash != second.result_hash
                or first.input_hash != second.input_hash
                or canonical_digest(first.facts) != canonical_digest(second.facts)
            ):
                raise ValueError("live provider calculation is nondeterministic")
            determinism_checks += 1

            horizon_kind = PROVIDER_CAPABILITIES["selection"].horizons[
                index % len(PROVIDER_CAPABILITIES["selection"].horizons)
            ]
            declared_horizons.add(horizon_kind)
            horizon = {
                "kind": horizon_kind,
                "start": {
                    "day": civil_date,
                    "month": civil_date[:7],
                    "year": civil_date[:4],
                }[horizon_kind],
                "end": {
                    "day": civil_date,
                    "month": civil_date[:7],
                    "year": civil_date[:4],
                }[horizon_kind],
            }
            dimensions = tuple(PROVIDER_CAPABILITIES["selection"].dimensions)
            first_extended = SelectionProvider(ROOT).extend(
                first, dimensions, horizon
            )
            second_extended = SelectionProvider(ROOT).extend(
                second, dimensions, horizon
            )
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
            if not _extension_covers_declared_range(
                first_extension.facts, horizon
            ) or not _extension_covers_declared_range(
                second_extension.facts, horizon
            ):
                raise ValueError(
                    "live provider extension does not cover the declared range"
                )
            if not _extension_samples_match_independent_build(
                first_extension.facts,
                horizon,
                spec=spec,
                timezone_name=timezone_name,
                location=location,
            ) or not _extension_samples_match_independent_build(
                second_extension.facts,
                horizon,
                spec=spec,
                timezone_name=timezone_name,
                location=location,
            ):
                raise ValueError(
                    "live provider extension contains cloned or stale candidates"
                )
            determinism_checks += 1

            record = first.facts["chart_facts"]["output"][
                "calendar_candidates"
            ][0]
            expected = case["expected"]
            common_ok = (
                record["calendar"]["lunar_date"] == expected["lunar_date"]
                and record["calendar"]["ganzhi"]["year"] == expected["ganzhi"]["year"]
                and record["calendar"]["ganzhi"]["month"] == expected["ganzhi"]["month"]
                and record["calendar"]["ganzhi"]["day"] == expected["ganzhi"]["day"]
                and record["mansion"]["short_name"] == expected["mansion"]
                and record["day_path"]["class"] == expected["huanghei"]
                and record["clash"]["zodiac"] == expected["clash"][-1]
            )
            source_specific_ok = (
                record["jianchu"]["value"] == expected["jianchu"]
                and record["day_path"]["runtime_name"] == expected["day_twelve_god"]
            )
            if case["id"] == "lunar-python-03":
                declared += 1
                qualifies = (
                    common_ok
                    and not source_specific_ok
                    and record["calendar"]["boundary_status"] == "intra_day_jie_boundary"
                    and record["jianchu"]["value"] == "收"
                    and record["day_path"]["runtime_name"] == "青龙"
                )
            else:
                qualifies = common_ok and source_specific_ok
            if qualifies:
                qualifying_cases += 1
            else:
                unexplained += 1
        except (KeyError, TypeError, ValueError, RuntimeError):
            unexplained += 1
    if unexplained:
        findings.append(f"Selection external unexplained mismatches: {unexplained}")
    if declared != 1:
        findings.append("Selection exact-Jie comparator difference was not uniquely declared")
    if qualifying_cases < 30:
        findings.append(
            "Selection live provider replay requires at least 30 qualifying cases"
        )
    if (
        provider_calculations != 2 * len(external_cases)
        or provider_extensions != 2 * len(external_cases)
        or determinism_checks != 2 * len(external_cases)
    ):
        findings.append(
            "Selection live provider replay did not execute every case twice"
        )
    if declared_horizons != set(PROVIDER_CAPABILITIES["selection"].horizons):
        findings.append(
            "Selection live provider replay does not cover every declared horizon"
        )

    published_sources = fixture.get("published_calendar_sources") or {}
    published_cases = fixture.get("published_calendar_cases") or []
    published_mismatches = 0
    external_by_id = {
        str(case.get("id")): case
        for case in external_cases
        if isinstance(case, dict)
    }
    published_local_artifact_checks = 0
    published_local_artifact_failures = 0
    published_source_verification_failures = 0
    published_artifacts: dict[str, bytes] = {}
    for source_id, source_contract in published_sources.items():
        if not isinstance(source_contract, dict):
            published_mismatches += 1
            continue
        match = re.fullmatch(r"hko-(\d{4})", str(source_id))
        artifact_hash = str(source_contract.get("artifact_sha256") or "")
        if (
            not match
            or source_contract.get("publisher") != "Hong Kong Observatory"
            or source_contract.get("format") != "CSV"
            or len(artifact_hash) != 64
            or not all(character in "0123456789abcdef" for character in artifact_hash)
            or not str(source_contract.get("artifact_url") or "").endswith(
                f"nongli_calendar_{match.group(1) if match else ''}.csv"
            )
            or "government-published independent calendar example"
            not in str(source_contract.get("role") or "")
        ):
            published_mismatches += 1
        try:
            local_path = ROOT / str(source_contract["local_artifact_path"])
            artifact = local_path.read_bytes()
            if (
                not local_path.is_file()
                or hashlib.sha256(artifact).hexdigest() != artifact_hash
            ):
                raise ValueError("published local artifact hash mismatch")
            published_artifacts[str(source_id)] = artifact
            published_local_artifact_checks += 1
        except (KeyError, OSError, ValueError):
            published_local_artifact_failures += 1
        if verify_published_sources:
            try:
                with urlopen(str(source_contract["artifact_url"]), timeout=30) as response:
                    remote_artifact = response.read()
                if (
                    hashlib.sha256(remote_artifact).hexdigest() != artifact_hash
                    or remote_artifact != published_artifacts[str(source_id)]
                ):
                    raise ValueError("published source artifact hash mismatch")
            except (KeyError, OSError, ValueError):
                published_source_verification_failures += 1
    published_ids: set[str] = set()
    for case in published_cases:
        try:
            identifier = str(case["id"])
            if identifier in published_ids:
                raise ValueError("duplicate published calendar case")
            published_ids.add(identifier)
            source_id = str(case["source_id"])
            if source_id not in published_sources:
                raise ValueError("unknown published source")
            comparator = external_by_id[str(case["comparator_case_id"])]
            civil_date = date.fromisoformat(str(comparator["input"]["date"]))
            expected_anchor = f"CSV row {civil_date.timetuple().tm_yday + 1}"
            if (
                source_id != f"hko-{civil_date.year}"
                or case.get("source_anchor") != expected_anchor
            ):
                raise ValueError("published source row identity mismatch")
            expected = case["expected"]
            lunar_year = int(expected["lunar_year"])
            lunar_date = {
                "year": lunar_year,
                "month": int(expected["lunar_month"]),
                "day": int(expected["lunar_day"]),
                "is_leap_month": bool(expected["is_leap_month"]),
            }
            published_year_ganzhi = (
                STEMS[(lunar_year - 4) % 10]
                + BRANCHES[(lunar_year - 4) % 12]
            )
            if expected["chinese_year_ganzhi"] != published_year_ganzhi:
                raise ValueError("published Chinese-year identity mismatch")
            record = selection.build_day_record(
                civil_date.isoformat(),
                timezone_name=str(comparator["input"]["timezone"]),
                location=str(comparator["input"]["location"]),
                event_profile="generic_selection",
            )
            if record["calendar"]["lunar_date"] != lunar_date:
                raise ValueError("published lunar date mismatch")
            if not published_case_matches_artifact(
                case, comparator, published_artifacts[source_id]
            ):
                raise ValueError("published cited CSV row mismatch")
        except (KeyError, TypeError, ValueError, RuntimeError):
            published_mismatches += 1
    if len(published_cases) < 30:
        findings.append("Selection published calendar fixture count below 30")
    if published_mismatches:
        findings.append(
            f"Selection published calendar fixture mismatches: {published_mismatches}"
        )
    if published_local_artifact_failures:
        findings.append(
            "Selection published local artifact failures: "
            f"{published_local_artifact_failures}"
        )
    if published_source_verification_failures:
        findings.append(
            "Selection published source verification failures: "
            f"{published_source_verification_failures}"
        )

    boundary_cases = fixture.get("boundary_cases") or []
    boundary_provider_calculations = 0
    boundary_provider_determinism_checks = 0
    for case in boundary_cases:
        try:
            record = selection.build_day_record(
                case["date"],
                timezone_name="Asia/Shanghai",
                location="上海",
                event_profile="generic_selection",
            )
            expected_status = case.get("expected_boundary_status")
            if expected_status and record["calendar"]["boundary_status"] != expected_status:
                findings.append(f"Selection boundary status mismatch: {case['id']}")
            variants = case.get("expected_month_ganzhi_variants")
            if variants and record["calendar"]["month_ganzhi_variants"] != variants:
                findings.append(f"Selection boundary variants mismatch: {case['id']}")
            lunar = case.get("expected_lunar_date")
            if lunar and record["calendar"]["lunar_date"] != lunar:
                findings.append(f"Selection lunar boundary mismatch: {case['id']}")
            boundary_name = case.get("expected_month_boundary_jie")
            if boundary_name and (
                not isinstance(record["calendar"].get("month_boundary_jie"), dict)
                or record["calendar"]["month_boundary_jie"].get("name") != boundary_name
            ):
                findings.append(f"Selection boundary Jie identity mismatch: {case['id']}")
            if not (source_table_hash_matches and fixture_hash_matches):
                continue
            spec = {
                "event_profile": "generic_selection",
                "requested_actions": [],
                "date_range": {"start": case["date"], "end": case["date"]},
                "hard_constraints": {
                    "time_windows": [{"start": "12:00", "end": "12:01"}]
                },
                "participant_facts": [],
                "include_folk_comparison": False,
            }
            request = ReadingRequest(
                query=f"Task 7N Selection boundary replay {case.get('id')}",
                action="new",
                system="selection",
                timezone="Asia/Shanghai",
                location="上海",
                chart_data={"selection_spec": spec},
            )
            first = SelectionProvider(ROOT).calculate(request)
            second = SelectionProvider(ROOT).calculate(request)
            boundary_provider_calculations += 2
            if not (
                first.input_hash == second.input_hash
                and first.result_hash == second.result_hash
                and canonical_digest(first.facts) == canonical_digest(second.facts)
            ):
                raise ValueError("live boundary provider replay is nondeterministic")
            boundary_provider_determinism_checks += 1
            live_record = first.facts["chart_facts"]["output"][
                "calendar_candidates"
            ][0]
            if (
                expected_status
                and live_record["calendar"]["boundary_status"] != expected_status
            ):
                raise ValueError("live boundary provider status mismatch")
            if (
                variants
                and live_record["calendar"]["month_ganzhi_variants"] != variants
            ):
                raise ValueError("live boundary provider variants mismatch")
        except (KeyError, TypeError, ValueError, RuntimeError):
            findings.append(f"Selection boundary case failed: {case.get('id')}")

    event_cases = fixture.get("event_profile_cases") or []
    observed_profiles: set[str] = set()
    for case in event_cases:
        try:
            record = selection.build_day_record(
                case["date"],
                timezone_name="Asia/Shanghai",
                location="上海",
                event_profile=case["event_profile"],
            )
            observed_profiles.add(record["official_event_rules"]["profile"])
            declared_fields = set(
                (event_profiles.get(case["event_profile"]) or {}).get(
                    "required_event_fact_fields", ()
                )
            )
            actual_facts = record.get("event_specific_facts") or {}
            if set(actual_facts) != declared_fields:
                findings.append(
                    f"Selection event fact output coverage mismatch: {case['id']}"
                )
            for field, value in actual_facts.items():
                if (
                    not isinstance(value, dict)
                    or value.get("status") != "calculated"
                    or not isinstance(value.get("active"), bool)
                    or value.get("rank_effect") not in allowed_rank_effects
                    or not value.get("source_anchors")
                ):
                    findings.append(
                        f"Selection event fact output invalid: {case['id']}:{field}"
                    )
        except (KeyError, TypeError, ValueError, RuntimeError):
            findings.append(f"Selection event profile case failed: {case.get('id')}")
    if observed_profiles != set(source.get("event_profiles") or {}):
        findings.append("Selection event profile fixture coverage mismatch")

    event_rule_cases = fixture.get("event_rule_cases") or []
    event_rule_mismatches = 0
    for case in event_rule_cases:
        try:
            raw = case["input"]
            source_rule_ids = case.get("source_rule_ids") or ()
            if (
                not source_rule_ids
                or not set(source_rule_ids) <= EXPECTED_SELECTION_RULE_IDS
            ):
                raise ValueError("invalid source rule identities")
            record = selection.build_day_record(
                raw["date"],
                timezone_name="Asia/Shanghai",
                location="上海",
                event_profile=raw["event_profile"],
                requested_actions=raw.get("requested_actions"),
                requested_scopes=raw.get("requested_scopes"),
                directional_context=raw.get("directional_context"),
                include_folk_comparison=bool(
                    raw.get("include_folk_comparison", False)
                ),
            )
            lunar = record["calendar"]["lunar_date"]
            observed = {
                "year_ganzhi": record["calendar"]["ganzhi"]["year"],
                "month_ganzhi": record["calendar"]["ganzhi"]["month"],
                "day_ganzhi": record["calendar"]["ganzhi"]["day"],
                "lunar_month_day": f"{lunar['month']}-{lunar['day']}",
                "jianchu": record["jianchu"]["value"],
                "day_path": record["day_path"]["runtime_name"],
                "mansion": record["mansion"]["short_name"],
                "yi_matches": record["official_event_rules"]["yi_matches"],
                "ji_matches": record["official_event_rules"]["ji_matches"],
                "universal_avoidance": record["official_event_rules"][
                    "universal_avoidance"
                ],
                "eligible": record["eligibility"]["eligible"],
                "active_event_facts": sorted(
                    field
                    for field, value in record["event_specific_facts"].items()
                    if value["active"]
                ),
            }
            if "directional_hits" in case["expected"]:
                observed["directional_hits"] = record["directional_facts"][
                    "evaluated_hits"
                ]
            if "donggong_verdict" in case["expected"]:
                observed["donggong_verdict"] = record["folk_comparison"][
                    "donggong_verdict"
                ]
                observed["folk_disagreement"] = record["folk_comparison"][
                    "disagreement"
                ]
            if observed != case["expected"]:
                event_rule_mismatches += 1
        except (KeyError, TypeError, ValueError, RuntimeError):
            event_rule_mismatches += 1
    if len(event_rule_cases) < 30:
        findings.append("Selection event-rule fixture count below 30")
    if event_rule_mismatches:
        findings.append(
            f"Selection event-rule fixture mismatches: {event_rule_mismatches}"
        )

    formula_report = build_selection_formula_fixtures.audit_formula_fixtures(
        fixture
    )
    if not formula_report["ok"]:
        findings.extend(formula_report["mismatches"])

    completion_cases = fixture.get("completion_cases") or []
    for case in completion_cases:
        try:
            raw = dict(case["input"])
            timezone_name = str(raw.pop("timezone"))
            location = str(raw.pop("location"))
            facts = selection.build_fact_layer(
                raw,
                timezone_name=timezone_name,
                location=location,
            )
            expected = case["expected"]
            if len(facts["output"]["calendar_candidates"]) != expected["candidate_count"]:
                findings.append(f"Selection completion count mismatch: {case['id']}")
            if "hour_fact_count" in expected and any(
                len(row["hour_facts"]) != expected["hour_fact_count"]
                for row in facts["output"]["calendar_candidates"]
            ):
                findings.append(f"Selection completion hours mismatch: {case['id']}")
            if "ranking_method" in expected and facts["output"]["ranking"]["method"] != expected["ranking_method"]:
                findings.append(f"Selection ranking method mismatch: {case['id']}")
            if "date_time_candidate_min_count" in expected and len(facts["output"]["date_time_candidates"]) < expected["date_time_candidate_min_count"]:
                findings.append(f"Selection date-time candidate count mismatch: {case['id']}")
            if "eligible_hour_branches" in expected:
                observed = [
                    row["branch"]
                    for row in facts["output"]["calendar_candidates"][0]["hour_facts"]
                    if row["hard_constraint_eligible"]
                ]
                if observed != expected["eligible_hour_branches"]:
                    findings.append(f"Selection eligible-hour mismatch: {case['id']}")
            if "no_valid_candidate" in expected and facts["output"]["no_valid_candidate"] is not expected["no_valid_candidate"]:
                findings.append(f"Selection completion no-candidate mismatch: {case['id']}")
            if "timezone_resolution" in expected:
                timezone_expected = expected["timezone_resolution"]
                hour = next(
                    row
                    for row in facts["output"]["calendar_candidates"][0]["hour_facts"]
                    if row["branch"] == timezone_expected["branch"]
                )
                for field in ("nonexistent_minute_count", "ambiguous_minute_count"):
                    if hour["timezone_resolution"][field] != timezone_expected[field]:
                        findings.append(f"Selection timezone resolution mismatch: {case['id']}:{field}")
        except (KeyError, TypeError, ValueError, RuntimeError):
            findings.append(f"Selection completion case failed: {case.get('id')}")

    no_candidate_cases = fixture.get("no_candidate_cases") or []
    for case in no_candidate_cases:
        try:
            raw = dict(case["input"])
            timezone_name = str(raw.pop("timezone"))
            location = str(raw.pop("location"))
            facts = selection.build_fact_layer(raw, timezone_name=timezone_name, location=location)
            expected = case["expected"]
            if facts["output"]["no_valid_candidate"] is not expected["no_valid_candidate"]:
                findings.append(f"Selection no-candidate status mismatch: {case['id']}")
            if len(facts["output"]["eliminations"]) != expected["elimination_count"]:
                findings.append(f"Selection no-candidate elimination mismatch: {case['id']}")
        except (KeyError, TypeError, ValueError, RuntimeError):
            findings.append(f"Selection no-candidate case failed: {case.get('id')}")

    donggong_lines = [
        line
        for line in selection.DONGGONG_TABLE_PATH.read_text(encoding="utf-8").splitlines()
        if line.startswith("| DG-D")
    ]
    donggong_ids = [line.split("|", 2)[1].strip() for line in donggong_lines]
    if len(donggong_lines) != 144:
        findings.append("Selection Donggong table raw row count mismatch")
    if len(set(donggong_ids)) != 144:
        findings.append("Selection Donggong table identifier uniqueness mismatch")
    donggong_id_set = set(donggong_ids)
    verdict_contract = source.get("donggong_event_verdicts") or {}
    verdict_profiles = verdict_contract.get("profiles") or {}
    if (
        verdict_contract.get("version") != "1.0.0"
        or verdict_contract.get("default") != "not_stated"
        or set(verdict_profiles) != set(event_profiles)
    ):
        findings.append("Selection Donggong profile coverage mismatch")
    donggong_classified_pairs = 0
    for profile, verdicts in verdict_profiles.items():
        if not isinstance(verdicts, dict):
            findings.append(f"Selection Donggong verdict contract invalid: {profile}")
            continue
        groups = {
            verdict: list(verdicts.get(verdict) or ())
            for verdict in ("recommend", "avoid", "mixed_conditional")
        }
        explicit = [identifier for values in groups.values() for identifier in values]
        if len(explicit) != len(set(explicit)):
            findings.append(f"Selection Donggong verdict overlap: {profile}")
        if not set(explicit) <= donggong_id_set:
            findings.append(f"Selection Donggong verdict has unknown row: {profile}")
        complete = {
            identifier: next(
                (
                    verdict
                    for verdict, identifiers in groups.items()
                    if identifier in identifiers
                ),
                "not_stated",
            )
            for identifier in sorted(donggong_id_set)
        }
        digest = hashlib.sha256(
            json.dumps(
                complete,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if digest != verdicts.get("classification_sha256"):
            findings.append(
                f"Selection Donggong classification hash mismatch: {profile}"
            )
        if set(complete) != donggong_id_set or any(
            verdict
            not in {"recommend", "avoid", "mixed_conditional", "not_stated"}
            for verdict in complete.values()
        ):
            findings.append(f"Selection Donggong classification incomplete: {profile}")
        donggong_classified_pairs += len(complete)

    counts = {
        "qualifying_cases": qualifying_cases,
        "route_owned_cases": len(external_cases),
        "provider_calculations": provider_calculations,
        "provider_extensions": provider_extensions,
        "determinism_checks": determinism_checks,
        "external_reference_cases": len(external_cases),
        "external_declared_boundary_differences": declared,
        "external_unexplained_mismatches": unexplained,
        "published_calendar_cases": len(published_cases),
        "published_calendar_mismatches": published_mismatches,
        "published_local_artifact_checks": published_local_artifact_checks,
        "published_source_verification_failures": published_source_verification_failures,
        "supplemental_local_artifact_checks": supplemental_local_artifact_checks,
        "supplemental_source_verification_failures": supplemental_source_verification_failures,
        "primary_classical_rule_witness_checks": primary_classical_rule_witness_checks,
        "boundary_cases": len(boundary_cases),
        "boundary_case_count": len(boundary_cases),
        "boundary_provider_calculations": boundary_provider_calculations,
        "boundary_provider_determinism_checks": (
            boundary_provider_determinism_checks
        ),
        "event_profiles": len(observed_profiles),
        "event_rule_cases": len(event_rule_cases),
        "event_rule_mismatches": event_rule_mismatches,
        "completion_cases": len(completion_cases),
        "no_candidate_cases": len(no_candidate_cases),
        "algorithm_dependencies": len(dependencies),
        "donggong_raw_rows": len(donggong_lines),
        "donggong_unique_ids": len(set(donggong_ids)),
        "donggong_rows": len(selection._donggong_rows()),
        "event_fact_definitions": len(event_definitions),
        "event_fact_formula_cases": formula_report["case_count"],
        "event_fact_positive_cases": formula_report["positive_case_count"],
        "event_fact_negative_cases": formula_report["negative_case_count"],
        "event_fact_boundary_cases": formula_report["boundary_case_count"],
        "event_fact_formula_mismatches": len(formula_report["mismatches"]),
        "evidence_fact_bindings": len(evidence_rules),
        "donggong_classified_profile_rows": donggong_classified_pairs,
    }
    if resolved_research_root is not None:
        source_verification["ok"] = not source_verification.get("findings")
        source_verification["status"] = (
            "verified" if source_verification["ok"] else "failed"
        )
    return {
        "schema_version": "mingli-selection-provider-audit-v1",
        "system": "selection",
        "provider_ready": not findings,
        "status": "pass" if not findings else "fail",
        "provider": {
            "provider_id": SelectionProvider.provider_id,
            "provider_version": SelectionProvider.provider_version,
            "capability_mode": PROVIDER_CAPABILITIES["selection"].mode,
        },
        "route_owned_case_ids": [
            str(case.get("id") or "") for case in external_cases
        ],
        "fixture": {
            "path": str(fixture_path),
            "sha256": _sha256(fixture_path),
            "expected_sha256": EXPECTED_FIXTURE_SHA256,
        },
        "fixture_sha256": _sha256(fixture_path),
        "counts": counts,
        "boundary_categories": sorted(
            {"calendar_boundary", "external_reference", *declared_horizons}
        ),
        "source_verification": source_verification,
        "findings": list(dict.fromkeys(findings)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(FIXTURE))
    parser.add_argument("--source-table", default=str(SOURCE_TABLE))
    parser.add_argument("--verify-published-sources", action="store_true")
    args = parser.parse_args()
    report = audit_selection_provider(
        fixture_path=args.fixture,
        source_table_path=args.source_table,
        verify_published_sources=args.verify_published_sources,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
