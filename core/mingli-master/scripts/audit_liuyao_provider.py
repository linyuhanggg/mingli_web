#!/usr/bin/env python3
"""Machine-readable Task 7F completeness audit for deterministic Liuyao."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping
from unittest import mock

import yaml

import audit_algorithm_sources
from audit_provider_preflight import provider_preflight_failure
from reading_engine import calendar_core, liuyao, providers as providers_module
from reading_engine.contracts import (
    AcceptedReading,
    PreparedReading,
    ReadingRequest,
    canonical_digest,
)
from reading_engine.factory import build_production_engine
from reading_engine.provider_protocol import ProviderRequest
from reading_engine.providers import PROVIDER_CAPABILITIES, LiuyaoProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "liuyao-v51.yaml"
FIXTURE_SHA256 = "c0e36e39191fab1eff941058e49a4660346e0cc68dd2b7340d712dd11ca2d5d6"
MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
ALGORITHM_SAMPLES = (
    ROOT / "references" / "fixtures" / "algorithm-source-samples-v51.yaml"
)
TRIGRAM_BITS = {
    "乾": "111", "兑": "110", "离": "101", "震": "100",
    "巽": "011", "坎": "010", "艮": "001", "坤": "000",
}
CALENDAR_WITNESS_POLICY = {
    "role": "reproducible_witness_for_source_recorded_month_branch_and_day_ganzhi",
    "historical_divination_date_claimed": False,
    "calendar_engine": "reading_engine.calendar_core.normalize_calendar",
}
ANCHOR_RE = re.compile(r"^L(?P<start>\d+)-L(?P<end>\d+)$")
SOURCE_LINE_VALUES = {"○": 9, "ㄨ": 6, "⚊": 7, "⚋": 8}
SOURCE_RELATIVE_NAMES = {
    "父母": "父母",
    "兄弟": "兄弟",
    "子孫": "子孙",
    "妻財": "妻财",
    "官鬼": "官鬼",
}
SOURCE_PLATE_RE = re.compile(
    r"^(?P<main_relative>父母|兄弟|子孫|妻財|官鬼)"
    r"(?P<main_branch>[子丑寅卯辰巳午未申酉戌亥])"
    r"(?P<main_element>[木火土金水])"
    r"(?P<main_symbol>[○ㄨ⚊⚋])\s*"
    r"(?P<role>[世應])?\s*"
    r"(?:(?P<changed_relative>父母|兄弟|子孫|妻財|官鬼)"
    r"(?P<changed_branch>[子丑寅卯辰巳午未申酉戌亥])"
    r"(?P<changed_element>[木火土金水])"
    r"(?P<changed_symbol>[○ㄨ⚊⚋]))?$"
)


def _finding(findings: list[str], condition: bool, message: str) -> None:
    if not condition:
        findings.append(message)


def _stable_tosses(case: dict[str, Any]) -> list[int]:
    bits = TRIGRAM_BITS[str(case["lower"])] + TRIGRAM_BITS[str(case["upper"])]
    return [7 if bit == "1" else 8 for bit in bits]


def _provider_request(
    case: Mapping[str, Any],
    *,
    tosses: list[int] | None = None,
) -> ReadingRequest:
    witness = case.get("calendar_witness")
    if not isinstance(witness, Mapping):
        raise ValueError("Liuyao calendar witness must be a structured object")
    return ReadingRequest(
        query=f"Task 7N Liuyao replay {case.get('id')}",
        action="new",
        system="liuyao",
        event_datetime=str(witness.get("event_datetime") or ""),
        timezone=str(witness.get("timezone") or ""),
        location=str(witness.get("location") or ""),
        chart_data={
            "casting_method": "supplied_complete_cast",
            "tosses": list(tosses if tosses is not None else case["tosses"]),
            "provenance": {
                "kind": "source_anchored_complete_cast",
                "fixture_id": str(case.get("id") or ""),
                "source_anchor": str(case.get("source_anchor") or ""),
            },
        },
        metadata={
            "zi_hour_policy": str(witness.get("zi_hour_policy") or "")
        },
    )


def _boundary_request(case: Mapping[str, Any], tosses: list[int]) -> ReadingRequest:
    witness_case = {
        "id": case.get("id"),
        "source_anchor": "fixture:calendar-boundary",
        "calendar_witness": {
            "event_datetime": case.get("datetime"),
            "timezone": case.get("timezone"),
            "location": case.get("location"),
            "zi_hour_policy": case.get("zi_hour_policy"),
        },
        "tosses": tosses,
    }
    return _provider_request(witness_case)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _anchored_lines(text: str, anchor: str) -> str:
    match = ANCHOR_RE.fullmatch(anchor)
    if match is None:
        raise ValueError(f"invalid classical source anchor: {anchor}")
    start = int(match.group("start"))
    end = int(match.group("end"))
    lines = text.splitlines()
    if start < 1 or end < start or end > len(lines):
        raise ValueError(f"classical source anchor out of range: {anchor}")
    return "\n".join(lines[start - 1 : end])


def _source_tosses(anchored_text: str) -> list[int]:
    top_down: list[int] = []
    for line in anchored_text.splitlines():
        positions = [
            (line.find(symbol), value)
            for symbol, value in SOURCE_LINE_VALUES.items()
            if symbol in line
        ]
        if positions:
            top_down.append(min(positions)[1])
    if len(top_down) != 6:
        raise ValueError(
            f"anchored classical diagram must contain six primary lines, got {len(top_down)}"
        )
    return list(reversed(top_down))


def _source_plate_lines(anchored_text: str) -> list[list[Any]]:
    top_down: list[list[Any]] = []
    for source_line in anchored_text.splitlines():
        match = SOURCE_PLATE_RE.fullmatch(source_line.strip())
        if match is None:
            continue
        main_relative = SOURCE_RELATIVE_NAMES[match.group("main_relative")]
        changed_relative = match.group("changed_relative")
        top_down.append(
            [
                main_relative,
                match.group("main_branch"),
                match.group("main_element"),
                match.group("main_symbol"),
                {"世": "世", "應": "应"}.get(match.group("role")),
                SOURCE_RELATIVE_NAMES[changed_relative]
                if changed_relative
                else main_relative,
                match.group("changed_branch") or match.group("main_branch"),
                match.group("changed_element") or match.group("main_element"),
                match.group("changed_symbol") or match.group("main_symbol"),
            ]
        )
    if len(top_down) != 6:
        raise ValueError(
            f"anchored classical diagram must contain six complete lines, got {len(top_down)}"
        )
    return list(reversed(top_down))


def _random_cast_turn_request(*, action: str) -> ProviderRequest:
    return ProviderRequest(
        query={
            "new": "建立数字起卦审计样本",
            "continue": "继续核验同一卦",
            "correct": "更正用神关系后核验同一卦",
            "recast": "换一件事重新数字起卦",
        }[action],
        subject_refs=("subject:task-7n-random-cast-audit",),
        object_id="concrete_event",
        dimension_ids=("outcome",),
        horizon={"kind": "instant", "start": None, "end": None},
        facts={
            "subject:task-7n-random-cast-audit": {
                "cast": "digital_coin",
                "event_datetime": "2024-02-10T12:00:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
            }
        },
    )


def _accept_random_cast_turn(engine: Any, state_token: str) -> AcceptedReading:
    accepted = engine.complete_turn(
        state_token,
        "六爻卦象事实已列明。\n本次只核验数字起卦事务的连续性。",
    )
    if not isinstance(accepted, AcceptedReading):
        raise RuntimeError("random cast audit could not accept prepared reading")
    return accepted


def _private_cast(prepared_record: Any) -> dict[str, Any]:
    casting = prepared_record.calculation.facts["chart_facts"]["output"]["casting"]
    if not isinstance(casting, Mapping):
        raise ValueError("random cast audit calculation has no casting object")
    return copy.deepcopy(dict(casting))


def _contains_private_seed_key(payload: Any) -> bool:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key) in {"seed", liuyao.TRANSACTION_CAST_SEED_KEY}:
                return True
            if _contains_private_seed_key(value):
                return True
    elif isinstance(payload, (list, tuple)):
        return any(_contains_private_seed_key(item) for item in payload)
    return False


def _seed_commitments(prepared: PreparedReading) -> list[str]:
    return [
        str(fact.value)
        for fact in prepared.fact_index
        if fact.path.endswith("/casting/seed_commitment")
    ]


def _reading_id_seed_candidates(reading_id: str) -> set[str]:
    return {
        canonical_digest(
            {
                "profile": "liuyao-digital-coin-v1",
                "reading_id": reading_id,
            }
        ),
        hashlib.sha256(reading_id.encode("utf-8")).hexdigest(),
        hashlib.sha256(
            f"liuyao-digital-coin-v1:{reading_id}".encode("utf-8")
        ).hexdigest(),
    }


def _audit_random_cast_contract() -> tuple[dict[str, Any], list[str]]:
    """Exercise the real transaction lifecycle without returning replayable seeds."""

    proof_names = (
        "new_seed_format_valid",
        "new_seed_not_reading_id_derived",
        "public_contract_seed_redacted",
        "stored_request_seed_redacted",
        "private_calculation_seed_persisted",
        "restart_replay_exact",
        "continuation_seed_reused",
        "correction_seed_reused",
        "recast_created_new_reading",
        "recast_seed_distinct",
        "seed_commitment_verified",
        "public_report_seed_redacted",
    )
    proofs = {name: False for name in proof_names}
    token_hex_call_sizes: list[int | None] = []
    token_hex_outputs: list[str] = []
    private_seeds: list[str] = []
    new_cast_count = 0
    lifecycle_findings: list[str] = []
    original_token_hex = providers_module.secrets.token_hex

    def observed_token_hex(nbytes: int | None = None) -> str:
        token_hex_call_sizes.append(nbytes)
        value = str(original_token_hex(nbytes))
        token_hex_outputs.append(value)
        return value

    try:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            providers_module.secrets,
            "token_hex",
            side_effect=observed_token_hex,
        ):
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            first_turn = engine.prepare_turn(
                engine.providers["liuyao"].descriptor,
                _random_cast_turn_request(action="new"),
            )
            first_public = first_turn.result
            if not isinstance(first_public, PreparedReading):
                raise RuntimeError("random cast audit new action was not prepared")
            new_cast_count += 1
            first_record = engine.store.load_prepared(first_public.reading_id)
            first_cast = _private_cast(first_record)
            first_seed = str(first_cast.get("seed") or "")
            private_seeds.append(first_seed)

            restarted_engine = build_production_engine(
                skill_dir=ROOT,
                store_root=temporary,
            )
            restarted_record = restarted_engine.store.load_prepared(
                first_public.reading_id
            )
            restarted_cast = _private_cast(restarted_record)
            replay = liuyao.cast_from_seed(first_seed)
            proofs["restart_replay_exact"] = (
                restarted_cast == first_cast
                and all(
                    replay[field] == restarted_cast[field]
                    for field in (
                        "seed",
                        "algorithm",
                        "coin_values",
                        "coin_faces",
                        "tosses",
                    )
                )
            )
            engine = restarted_engine
            first_accepted = _accept_random_cast_turn(
                engine, first_turn.state_token
            )

            continued_turn = engine.prepare_turn(
                engine.providers["liuyao"].descriptor,
                _random_cast_turn_request(action="continue"),
                state_token=first_turn.state_token,
            )
            continued_public = continued_turn.result
            if not isinstance(continued_public, PreparedReading):
                raise RuntimeError("random cast audit continue action was not prepared")
            continued_record = engine.store.load_prepared(continued_public.reading_id)
            continued_cast = _private_cast(continued_record)
            proofs["continuation_seed_reused"] = continued_cast == first_cast
            continued_accepted = _accept_random_cast_turn(
                engine,
                continued_turn.state_token,
            )

            corrected_turn = engine.prepare_turn(
                engine.providers["liuyao"].descriptor,
                _random_cast_turn_request(action="correct"),
                state_token=continued_turn.state_token,
                transition="correct",
            )
            corrected_public = corrected_turn.result
            if not isinstance(corrected_public, PreparedReading):
                raise RuntimeError("random cast audit correct action was not prepared")
            corrected_record = engine.store.load_prepared(corrected_public.reading_id)
            corrected_cast = _private_cast(corrected_record)
            proofs["correction_seed_reused"] = corrected_cast == first_cast
            corrected_accepted = _accept_random_cast_turn(
                engine,
                corrected_turn.state_token,
            )

            recast_turn = engine.prepare_turn(
                engine.providers["liuyao"].descriptor,
                _random_cast_turn_request(action="recast"),
                state_token=corrected_turn.state_token,
                transition="restart",
            )
            recast_public = recast_turn.result
            if not isinstance(recast_public, PreparedReading):
                raise RuntimeError("random cast audit recast action was not prepared")
            new_cast_count += 1
            recast_record = engine.store.load_prepared(recast_public.reading_id)
            recast_cast = _private_cast(recast_record)
            recast_seed = str(recast_cast.get("seed") or "")
            private_seeds.append(recast_seed)

            proofs["new_seed_format_valid"] = all(
                re.fullmatch(r"[0-9a-f]{64}", seed) is not None
                for seed in private_seeds
            )
            proofs["new_seed_not_reading_id_derived"] = (
                private_seeds == token_hex_outputs
                and all(
                    seed not in _reading_id_seed_candidates(reading_id)
                    for seed, reading_id in (
                        (first_seed, first_public.reading_id),
                        (recast_seed, recast_public.reading_id),
                    )
                )
            )
            public_payloads = [
                prepared.to_dict()
                for prepared in (
                    first_public,
                    continued_public,
                    corrected_public,
                    recast_public,
                )
            ]
            request_payloads = [
                record.request.to_dict()
                for record in (
                    first_record,
                    continued_record,
                    corrected_record,
                    recast_record,
                )
            ]
            proofs["public_contract_seed_redacted"] = all(
                not _contains_private_seed_key(payload)
                and all(seed not in json.dumps(payload, ensure_ascii=False) for seed in private_seeds)
                for payload in public_payloads
            )
            proofs["stored_request_seed_redacted"] = all(
                not _contains_private_seed_key(payload)
                and all(seed not in json.dumps(payload, ensure_ascii=False) for seed in private_seeds)
                for payload in request_payloads
            )
            proofs["private_calculation_seed_persisted"] = (
                first_cast.get("seed") == first_seed
                and first_cast.get("seed_source") == liuyao.TRANSACTION_CAST_SEED_SOURCE
                and recast_cast.get("seed") == recast_seed
                and recast_cast.get("seed_source") == liuyao.TRANSACTION_CAST_SEED_SOURCE
            )
            proofs["recast_created_new_reading"] = (
                recast_public.reading_id != corrected_accepted.reading_id
                and recast_public.parent_reading_id == corrected_accepted.reading_id
                and recast_public.root_reading_id == corrected_accepted.root_reading_id
            )
            proofs["recast_seed_distinct"] = first_seed != recast_seed
            proofs["seed_commitment_verified"] = all(
                _seed_commitments(prepared)
                == [liuyao.transaction_cast_seed_commitment(seed)]
                for prepared, seed in (
                    (first_public, first_seed),
                    (continued_public, first_seed),
                    (corrected_public, first_seed),
                    (recast_public, recast_seed),
                )
            )
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        lifecycle_findings.append(
            f"random cast lifecycle execution failed ({type(exc).__name__})"
        )

    contract: dict[str, Any] = {
        "schema_version": "mingli-liuyao-random-cast-contract-v1",
        **proofs,
        "new_cast_count": new_cast_count,
        "token_hex_call_count": len(token_hex_call_sizes),
        "token_hex_32_byte_requests": sum(
            size == 32 for size in token_hex_call_sizes
        ),
    }
    contract["public_report_seed_redacted"] = all(
        seed not in json.dumps(contract, ensure_ascii=False, sort_keys=True)
        for seed in private_seeds
    )
    required = {
        name: bool(contract[name])
        for name in proof_names
    }
    required["two_new_casts"] = new_cast_count == 2
    required["two_token_hex_calls"] = len(token_hex_call_sizes) == 2
    required["token_hex_uses_32_bytes"] = token_hex_call_sizes == [32, 32]
    messages = {
        "new_seed_format_valid": "new digital cast seed is not 64-character lowercase hex",
        "new_seed_not_reading_id_derived": "new digital cast seed is not bound to the observed CSPRNG output",
        "public_contract_seed_redacted": "public prepared contract discloses a private digital cast seed",
        "stored_request_seed_redacted": "stored request discloses a private digital cast seed",
        "private_calculation_seed_persisted": "private calculation did not persist the transaction seed",
        "restart_replay_exact": "restart did not reproduce the exact private digital cast",
        "continuation_seed_reused": "continue did not reuse the preserved digital cast",
        "correction_seed_reused": "correct did not reuse the preserved digital cast",
        "recast_created_new_reading": "recast did not create the required child reading",
        "recast_seed_distinct": "recast CSPRNG seed is not distinct from the original seed",
        "seed_commitment_verified": "public seed commitment does not match the private seed",
        "public_report_seed_redacted": "random cast audit report discloses a private seed",
        "two_new_casts": "random cast lifecycle did not create exactly two new casts",
        "two_token_hex_calls": "random cast lifecycle did not invoke token_hex exactly twice",
        "token_hex_uses_32_bytes": "random cast lifecycle did not request 32 CSPRNG bytes per cast",
    }
    lifecycle_findings.extend(
        messages[name] for name, passed in required.items() if not passed
    )
    lifecycle_findings = list(dict.fromkeys(lifecycle_findings))
    contract["ready"] = not lifecycle_findings
    return contract, lifecycle_findings


def audit_liuyao_provider(
    *, fixture_path: Path = FIXTURE, research_root: Path | None = None
) -> dict[str, Any]:
    preflight = provider_preflight_failure(
        system="liuyao",
        schema_version="mingli-liuyao-completeness-audit-v1",
        provider_class=LiuyaoProvider,
        expected_mode="calculation",
    )
    if preflight is not None:
        return preflight
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    fixture_sha256 = _sha256(fixture_path)
    cases = list(fixture.get("hexagram_reference_cases") or ())
    classical_cases = list(fixture.get("classical_examples") or ())
    classical_expectations = dict(fixture.get("classical_fact_expectations") or {})
    boundary_cases = list(fixture.get("calendar_boundary_cases") or ())
    calendar_cases = dict(fixture.get("calendar_boundaries") or {})
    moving_cases = list(fixture.get("moving_boundaries") or ())
    findings: list[str] = []
    qualifying_cases = 0
    provider_calculations = 0
    boundary_provider_cases = 0
    determinism_checks = 0
    provider_mismatches = 0
    determinism_mismatches = 0
    validator_checks = 0
    qualifying_casting_methods: dict[str, int] = {}
    _finding(
        findings,
        fixture_sha256 == FIXTURE_SHA256,
        "Liuyao fixture artifact hash mismatch",
    )
    _finding(
        findings,
        fixture.get("calendar_witness_policy") == CALENDAR_WITNESS_POLICY,
        "Liuyao calendar witness policy mismatch",
    )
    catalog = liuyao.build_hexagram_catalog()
    calendar = calendar_core.normalize_calendar(
        "2024-02-10T12:00:00",
        timezone_name="Asia/Shanghai",
        location="上海",
    )

    _finding(
        findings,
        fixture.get("schema_version") == "mingli-liuyao-fixtures-v51",
        "unexpected fixture schema",
    )
    _finding(
        findings,
        fixture.get("provider_contract")
        == {
            "system": "liuyao",
            "provider_class": "reading_engine.providers.LiuyaoProvider",
            "provider_id": LiuyaoProvider.provider_id,
            "provider_version": LiuyaoProvider.provider_version,
            "adapter_version": liuyao.ADAPTER_VERSION,
            "capability_mode": PROVIDER_CAPABILITIES["liuyao"].mode,
        },
        "Liuyao frozen provider contract mismatch",
    )
    _finding(
        findings,
        PROVIDER_CAPABILITIES["liuyao"].mode == "calculation",
        "Liuyao provider capability mode is not calculation",
    )
    _finding(findings, len(catalog) == 64, "provider catalog does not contain 64 hexagrams")
    _finding(findings, len(cases) == 64, "fixture does not contain 64 source-table plate cases")
    _finding(
        findings,
        len({str(case.get("name") or "") for case in cases}) == len(cases),
        "reference hexagram names are not unique",
    )
    _finding(
        findings,
        len({(case.get("upper"), case.get("lower")) for case in cases}) == len(cases),
        "reference trigram pairs are not unique",
    )
    for case in cases:
        try:
            facts = liuyao.build_fact_layer(
                _stable_tosses(case),
                calendar_facts=calendar,
                casting={"method": "supplied_complete_cast"},
            )
            output = facts["output"]
            primary = output["primary_hexagram"]
            _finding(findings, primary["name"] == case["name"], f"hexagram mismatch: {case.get('name')}")
            _finding(findings, primary["palace"] == case["palace"], f"palace mismatch: {case.get('name')}")
            _finding(findings, primary["stage"] == case["stage"], f"stage mismatch: {case.get('name')}")
            _finding(findings, output["shi_ying"] == {"shi": case["shi"], "ying": case["ying"]}, f"Shi/Ying mismatch: {case.get('name')}")
            _finding(findings, liuyao.validate_fact_layer(facts)["ok"], f"fact validation failed: {case.get('name')}")
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"reference case failed: {case.get('name')}: {exc}")

    source_payload = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(source_payload, ROOT)
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    classical_source = dict(fixture.get("classical_examples_source") or {})
    classical_text = ""
    if resolved_research_root is not None:
        classical_path = resolved_research_root / str(
            classical_source.get("path") or ""
        )
        source_verification_findings = source_verification.setdefault(
            "findings", []
        )
        try:
            _finding(
                source_verification_findings,
                classical_path.is_file(),
                "classical example source is missing",
            )
            if classical_path.is_file():
                _finding(
                    source_verification_findings,
                    _sha256(classical_path) == classical_source.get("sha256"),
                    "classical example source hash mismatch",
                )
                classical_text = classical_path.read_text(encoding="utf-8")
        except OSError as exc:
            source_verification_findings.append(
                f"classical example source failed: {exc}"
            )
    _finding(
        findings,
        len(classical_cases) >= 30,
        "fixture must contain at least 30 source-anchored classical examples",
    )
    _finding(
        findings,
        len({str(case.get("id") or "") for case in classical_cases})
        == len(classical_cases),
        "classical example ids are not unique",
    )
    _finding(
        findings,
        set(classical_expectations)
        == {str(case.get("id") or "") for case in classical_cases},
        "classical fact expectations do not cover the exact example set",
    )
    for case in classical_cases:
        case_findings_start = len(findings)
        try:
            expectation = dict(classical_expectations[str(case["id"])])
            anchored = ""
            if resolved_research_root is not None:
                # Classical fulltext verification is a release-time gate: it
                # runs only when an explicit research root supplies the
                # external corpus, and its findings never block runtime
                # readiness.
                source_verification_findings = source_verification.setdefault(
                    "findings", []
                )
                try:
                    anchored = _anchored_lines(
                        classical_text, str(case["source_anchor"])
                    )
                    _finding(
                        source_verification_findings,
                        str(case["source_heading"]) in anchored,
                        f"classical heading is not present at source anchor: {case.get('id')}",
                    )
                    _finding(
                        source_verification_findings,
                        _source_tosses(anchored) == case["tosses"],
                        f"classical source cast mismatch: {case.get('id')}",
                    )
                    _finding(
                        source_verification_findings,
                        _source_plate_lines(anchored)
                        == list(expectation["source_lines_bottom_up"]),
                        f"classical source plate mismatch: {case.get('id')}",
                    )
                except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                    source_verification_findings.append(
                        f"classical source verification failed: {case.get('id')}: {exc}"
                    )
            witness = case.get("calendar_witness")
            if not isinstance(witness, Mapping):
                raise ValueError("calendar witness must be a structured object")
            source_calendar = calendar_core.normalize_calendar(
                witness.get("event_datetime"),
                timezone_name=witness.get("timezone"),
                location=witness.get("location"),
                zi_hour_policy=witness.get("zi_hour_policy"),
            )
            _finding(
                findings,
                source_calendar["ganzhi"]["month"][1] == case["month_branch"]
                and source_calendar["ganzhi"]["day"] == case["day_ganzhi"],
                f"classical calendar witness mismatch: {case.get('id')}",
            )
            request = _provider_request(case)
            first = LiuyaoProvider(ROOT).calculate(request)
            provider_calculations += 1
            second = LiuyaoProvider(ROOT).calculate(request)
            provider_calculations += 1
            determinism_checks += 1
            first_facts = first.facts["chart_facts"]
            second_facts = second.facts["chart_facts"]
            validator_checks += 2
            _finding(
                findings,
                first.system == "liuyao" and second.system == "liuyao",
                f"classical provider system mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                first.provider_id == LiuyaoProvider.provider_id
                and second.provider_id == LiuyaoProvider.provider_id
                and first.provider_version == LiuyaoProvider.provider_version
                and second.provider_version == LiuyaoProvider.provider_version,
                f"classical provider identity mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                liuyao.validate_fact_layer(first_facts)["ok"]
                and liuyao.validate_fact_layer(second_facts)["ok"],
                f"classical provider validation mismatch: {case.get('id')}",
            )
            if first.to_dict() != second.to_dict():
                findings.append(
                    f"classical provider determinism mismatch: {case.get('id')}"
                )
                determinism_mismatches += 1
            output = first_facts["output"]
            _finding(
                findings,
                output["primary_hexagram"]["name"] == case["primary"],
                f"classical primary mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                output["changed_hexagram"]["name"] == case["changed"],
                f"classical changed mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                output["moving_lines"] == case["moving_lines"],
                f"classical moving-line mismatch: {case.get('id')}",
            )
            day = str(case["day_ganzhi"])
            month = str(case["month_branch"])
            _finding(findings, day in liuyao.JIAZI, f"invalid classical day: {case.get('id')}")
            _finding(findings, month in liuyao.BRANCHES, f"invalid classical month: {case.get('id')}")
            for line in output["lines"]:
                liuyao.calculate_line_relations(
                    line_branch=line["najia"]["branch"],
                    line_element=line["najia"]["element"],
                    month_branch=month,
                    day_branch=day[1],
                )
            liuyao.xunkong_for(day)
            source_lines = list(expectation["source_lines_bottom_up"])
            _finding(
                findings,
                [line["six_relative"] for line in output["lines"]]
                == [line[0] for line in source_lines],
                f"classical main-relative mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["najia"]["branch"] for line in output["lines"]]
                == [line[1] for line in source_lines],
                f"classical main-Najia mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["najia"]["element"] for line in output["lines"]]
                == [line[2] for line in source_lines],
                f"classical main-element mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["roles"] for line in output["lines"]]
                == [
                    [] if line[4] is None else [line[4]]
                    for line in source_lines
                ],
                f"classical Shi/Ying mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["six_relative"] for line in output["changed_plate_lines"]]
                == [line[5] for line in source_lines],
                f"classical changed-relative mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["najia"]["branch"] for line in output["changed_plate_lines"]]
                == [line[6] for line in source_lines],
                f"classical changed-Najia mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["najia"]["element"] for line in output["changed_plate_lines"]]
                == [line[7] for line in source_lines],
                f"classical changed-element mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["yin_yang"] for line in output["changed_plate_lines"]]
                == [
                    "阳" if line[8] in {"○", "⚊"} else "阴"
                    for line in source_lines
                ],
                f"classical changed yin-yang mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["xunkong"] for line in output["changed_plate_lines"]]
                == list(expectation["changed_xunkong_bottom_up"]),
                f"classical changed Xunkong mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [
                    line["month_day_strength"]["seasonal_state"]
                    for line in output["changed_plate_lines"]
                ]
                == list(expectation["changed_seasonal_states_bottom_up"]),
                f"classical changed seasonal states mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [
                    line["month_day_strength"]["month"]["branch_relation"]
                    for line in output["changed_plate_lines"]
                ]
                == list(expectation["changed_month_relations_bottom_up"]),
                f"classical changed month relations mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [
                    line["month_day_strength"]["day"]["branch_relation"]
                    for line in output["changed_plate_lines"]
                ]
                == list(expectation["changed_day_relations_bottom_up"]),
                f"classical changed day relations mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                output["xunkong"]["void_branches"] == list(expectation["xunkong"]),
                f"classical Xunkong mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["month_day_strength"]["seasonal_state"] for line in output["lines"]]
                == list(expectation["seasonal_states_bottom_up"]),
                f"classical seasonal-state mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["month_day_strength"]["month"]["branch_relation"] for line in output["lines"]]
                == list(expectation["month_relations_bottom_up"]),
                f"classical month-relation mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                [line["month_day_strength"]["day"]["branch_relation"] for line in output["lines"]]
                == list(expectation["day_relations_bottom_up"]),
                f"classical day-relation mismatch: {case.get('id')}",
            )
            if len(findings) == case_findings_start:
                qualifying_cases += 1
                casting_method = str(output["casting"]["method"])
                qualifying_casting_methods[casting_method] = (
                    qualifying_casting_methods.get(casting_method, 0) + 1
                )
            else:
                provider_mismatches += 1
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"classical example failed: {case.get('id')}: {exc}")
            provider_mismatches += 1

    try:
        samples = yaml.safe_load(ALGORITHM_SAMPLES.read_text(encoding="utf-8"))
        sample = samples["cases"]["liuyao-changed-line-suppresses-hidden"]
        sample_input = sample["input"]
        sample_expected = sample["expected"]
        sample_output = liuyao.build_fact_layer(
            sample_input["tosses_bottom_up"],
            calendar_facts=calendar,
            casting={"method": "supplied_complete_cast"},
        )["output"]
        _finding(
            findings,
            sample_output["primary_hexagram"]["name"] == sample_input["main"]
            and sample_output["changed_hexagram"]["name"]
            == sample_input["changed"]
            and sample_output["moving_lines"] == sample_expected["moving_lines"],
            "changed-line hidden-suppression sample plate mismatch",
        )
        changed_line = sample_output["changed_plate_lines"][3]
        _finding(
            findings,
            changed_line["najia"]["ganzhi"]
            == sample_expected["line_4_changed"]["stem_branch"]
            and changed_line["six_relative"]
            == sample_expected["line_4_changed"]["six_relative"],
            "changed-line hidden-suppression sample line-four mismatch",
        )
        _finding(
            findings,
            set(sample_output["six_relatives"])
            == set(sample_expected["visible_main_relatives"]),
            "changed-line hidden-suppression sample visible relatives mismatch",
        )
        _finding(
            findings,
            sample_expected["hidden_relative_excluded"]
            not in {
                line["six_relative"] for line in sample_output["hidden_lines"]
            },
            "changed-line hidden-suppression sample emitted forbidden hidden line",
        )
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        findings.append(f"changed-line hidden-suppression sample failed: {exc}")

    required_boundary_counts = {
        "solar_term_boundary": 2,
        "day_rollover": 2,
        "leap_month": 1,
        "timezone_boundary": 2,
    }
    for category, minimum in required_boundary_counts.items():
        _finding(
            findings,
            sum(case.get("category") == category for case in boundary_cases) >= minimum,
            f"calendar boundary category {category} requires {minimum} cases",
        )
    for case in boundary_cases:
        case_findings_start = len(findings)
        try:
            normalized = calendar_core.normalize_calendar(
                case["datetime"],
                timezone_name=case["timezone"],
                location=case["location"],
                zi_hour_policy=case["zi_hour_policy"],
            )
            pillars = [
                normalized["ganzhi"][key]
                for key in ("year", "month", "day", "hour")
            ]
            _finding(
                findings,
                pillars == case["expected_pillars"],
                f"calendar boundary mismatch: {case.get('id')}",
            )
            lunar = normalized["lunar_date"]
            _finding(
                findings,
                [
                    lunar["year"],
                    lunar["month"],
                    lunar["day"],
                    lunar["is_leap_month"],
                ]
                == case["expected_lunar"],
                f"calendar lunar boundary mismatch: {case.get('id')}",
            )
            request = _boundary_request(case, [7, 7, 7, 7, 7, 7])
            first = LiuyaoProvider(ROOT).calculate(request)
            provider_calculations += 1
            second = LiuyaoProvider(ROOT).calculate(request)
            provider_calculations += 1
            determinism_checks += 1
            boundary_facts = first.facts["chart_facts"]
            validator_checks += 2
            _finding(
                findings,
                liuyao.validate_fact_layer(boundary_facts)["ok"]
                and liuyao.validate_fact_layer(second.facts["chart_facts"])["ok"],
                f"calendar boundary fact validation failed: {case.get('id')}",
            )
            _finding(
                findings,
                first.system == "liuyao" and second.system == "liuyao",
                f"calendar boundary provider system mismatch: {case.get('id')}",
            )
            _finding(
                findings,
                first.provider_id == LiuyaoProvider.provider_id
                and first.provider_version == LiuyaoProvider.provider_version,
                f"calendar boundary provider identity mismatch: {case.get('id')}",
            )
            if first.to_dict() != second.to_dict():
                findings.append(
                    f"calendar boundary determinism mismatch: {case.get('id')}"
                )
                determinism_mismatches += 1
            if len(findings) == case_findings_start:
                boundary_provider_cases += 1
            else:
                provider_mismatches += 1
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"calendar boundary failed: {case.get('id')}: {exc}")
            provider_mismatches += 1

    for case in moving_cases:
        case_findings_start = len(findings)
        try:
            request = _boundary_request(
                {
                    "id": case.get("id"),
                    "datetime": "2024-02-10T12:00:00",
                    "timezone": "Asia/Shanghai",
                    "location": "上海",
                    "zi_hour_policy": "midnight",
                },
                list(case["tosses"]),
            )
            first = LiuyaoProvider(ROOT).calculate(request)
            provider_calculations += 1
            second = LiuyaoProvider(ROOT).calculate(request)
            provider_calculations += 1
            determinism_checks += 1
            validator_checks += 2
            output = first.facts["chart_facts"]["output"]
            _finding(
                findings,
                liuyao.validate_fact_layer(first.facts["chart_facts"])["ok"]
                and liuyao.validate_fact_layer(second.facts["chart_facts"])["ok"],
                f"moving boundary fact validation failed: {case.get('id')}",
            )
            _finding(
                findings,
                first.system == "liuyao" and second.system == "liuyao",
                f"moving boundary provider system mismatch: {case.get('id')}",
            )
            _finding(findings, output["moving_lines"] == case["moving_lines"], f"moving lines mismatch: {case.get('id')}")
            _finding(findings, output["primary_hexagram"]["name"] == case["primary"], f"primary mismatch: {case.get('id')}")
            _finding(findings, output["changed_hexagram"]["name"] == case["changed"], f"changed mismatch: {case.get('id')}")
            if first.to_dict() != second.to_dict():
                findings.append(f"moving boundary determinism mismatch: {case.get('id')}")
                determinism_mismatches += 1
            if len(findings) == case_findings_start:
                boundary_provider_cases += 1
            else:
                provider_mismatches += 1
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            findings.append(f"moving boundary failed: {case.get('id')}: {exc}")
            provider_mismatches += 1

    xunkong_days = list(calendar_cases.get("xunkong_days") or ())
    day_stems = list(calendar_cases.get("six_spirit_day_stems") or ())
    _finding(findings, len(xunkong_days) == 6, "fixture must cover six Xunkong cycles")
    _finding(findings, len(day_stems) == 10, "fixture must cover ten six-spirit day stems")
    for day in xunkong_days:
        try:
            _finding(findings, len(liuyao.xunkong_for(day)) == 2, f"invalid Xunkong row: {day}")
        except ValueError as exc:
            findings.append(f"Xunkong boundary failed: {day}: {exc}")
    for stem in day_stems:
        try:
            spirits = liuyao.six_spirits_for(stem)
            _finding(findings, len(spirits) == len(set(spirits)) == 6, f"invalid six-spirit row: {stem}")
        except ValueError as exc:
            findings.append(f"six-spirit boundary failed: {stem}: {exc}")

    source_report = audit_algorithm_sources.audit_matrix(
        source_payload,
        root=ROOT,
        systems=("liuyao",),
    )
    findings.extend(f"source audit: {item}" for item in source_report["findings"])
    dependency_rows = source_payload["providers"]["liuyao"]["dependencies"]
    dependency_ids = {str(row["id"]) for row in dependency_rows}
    representative = liuyao.build_fact_layer(
        [9, 7, 7, 7, 7, 6],
        calendar_facts=calendar,
        casting={"method": "supplied_complete_cast"},
    )["output"]
    observed_dependency_ids = {
        representative["casting"]["source_dependency_id"],
        representative["primary_hexagram"]["source_dependency_id"],
        representative["najia"][0]["source_dependency_id"],
        representative["six_spirit_profile"]["source_dependency_id"],
        representative["xunkong"]["source_dependency_id"],
        representative["hidden_lines"][0]["source_dependency_id"],
        representative["relation_facts"][0]["source_dependency_id"],
    }
    _finding(
        findings,
        observed_dependency_ids == dependency_ids,
        "provider facts do not cover the exact audited Liuyao dependency ids",
    )

    random_cast_contract, random_cast_findings = _audit_random_cast_contract()
    findings.extend(
        f"random cast contract: {item}" for item in random_cast_findings
    )

    _finding(
        findings,
        qualifying_cases >= 30,
        "Liuyao provider requires at least 30 qualifying live-provider cases",
    )
    _finding(
        findings,
        provider_calculations
        >= 2 * (qualifying_cases + boundary_provider_cases),
        "Liuyao provider replay did not execute every qualifying case twice",
    )
    _finding(
        findings,
        determinism_mismatches == 0,
        "Liuyao provider replay contains nondeterministic results",
    )
    boundary_categories = sorted(
        {
            *(str(case.get("category") or "") for case in boundary_cases),
            "calendar_witness",
            "hexagram_catalog",
            "moving_lines",
            "six_spirit_day_stem",
            "xunkong_cycle",
            "random_cast_lifecycle",
        }
        - {""}
    )
    if resolved_research_root is not None:
        source_verification["ok"] = not source_verification.get("findings")
        source_verification["status"] = (
            "verified" if source_verification["ok"] else "failed"
        )
    findings = list(dict.fromkeys(findings))
    ready = not findings and qualifying_cases >= 30

    return {
        "schema_version": "mingli-liuyao-completeness-audit-v1",
        "system": "liuyao",
        "status": "pass" if ready else "fail",
        "provider_ready": ready,
        "source_verification": source_verification,
        "provider": {
            "provider_class": LiuyaoProvider.__name__,
            "provider_id": LiuyaoProvider.provider_id,
            "provider_version": LiuyaoProvider.provider_version,
            "capability_mode": PROVIDER_CAPABILITIES["liuyao"].mode,
            "adapter_version": liuyao.ADAPTER_VERSION,
            "validator": "reading_engine.liuyao.validate_fact_layer",
            "algorithm_dependency_ids": sorted(dependency_ids),
        },
        "route_owned_case_ids": [
            str(case.get("id") or "")
            for case in (*classical_cases, *boundary_cases, *moving_cases)
        ],
        "fixture": {
            "path": (
                fixture_path.relative_to(ROOT).as_posix()
                if fixture_path.is_relative_to(ROOT)
                else str(fixture_path)
            ),
            "sha256": fixture_sha256,
            "expected_sha256": FIXTURE_SHA256,
        },
        "boundary_categories": boundary_categories,
        "qualifying_casting_methods": dict(
            sorted(qualifying_casting_methods.items())
        ),
        "random_cast_contract": random_cast_contract,
        "counts": {
            "hexagrams": len(catalog),
            "source_table_cases": len(cases),
            "complete_reference_cases": len(classical_cases),
            "fixture_oracle_cases": qualifying_cases,
            "qualifying_cases": (
                qualifying_cases + boundary_provider_cases
            ),
            "route_owned_cases": (
                len(classical_cases) + len(boundary_cases) + len(moving_cases)
            ),
            "provider_calculations": provider_calculations,
            "provider_extensions": 0,
            "boundary_provider_cases": boundary_provider_cases,
            "determinism_checks": determinism_checks,
            "boundary_case_count": len(boundary_cases) + len(moving_cases),
            "validator_checks": validator_checks,
            "provider_mismatches": provider_mismatches,
            "determinism_mismatches": determinism_mismatches,
            "calendar_boundary_cases": len(boundary_cases),
            "moving_boundaries": len(moving_cases),
            "day_stem_boundaries": len(day_stems),
            "xunkong_boundaries": len(xunkong_days),
            "algorithm_dependencies": source_report["dependency_count"],
            "fact_dependency_ids": len(observed_dependency_ids),
            "random_cast_new_casts": random_cast_contract["new_cast_count"],
            "random_cast_token_hex_calls": random_cast_contract[
                "token_hex_call_count"
            ],
        },
        "source_table": {
            "path": liuyao.TABLE_RELATIVE_PATH,
            "sha256": liuyao.source_table_digest(),
        },
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args()
    report = audit_liuyao_provider(fixture_path=args.fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
