#!/usr/bin/env python3
"""Machine-readable completeness audit for the Task 7L Fengshui provider."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

import audit_algorithm_sources
from audit_provider_preflight import provider_preflight_failure
from reading_engine import fengshui
from reading_engine.contracts import ReadingRequest, canonical_digest
from reading_engine.evidence_rules import production_evidence_rules
from reading_engine.providers import PROVIDER_CAPABILITIES, FengshuiProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/fengshui-v51.yaml"
SOURCE_TABLE = ROOT / "references/matrices/fengshui-source-tables-v1.yaml"
MATRIX = ROOT / "references/matrices/algorithm-source-dependencies.yaml"
FIXTURE_SHA256 = "e94670e3f82f03f1ef69a68fd2cb55adebced53fa0c46e55cee86da068be1935"
EXPECTED_PROVIDER_ID = "mingli-master.fengshui.v1"
EXPECTED_PROVIDER_VERSION = "1.0.0"
SOURCE_TABLE_SHA256 = "7d3f56abeb302736daf1f2822d45fd2ea9dccad69dc386f6175ffac060b42e9e"
MOUNTAINS = tuple("子癸丑艮寅甲卯乙辰巽巳丙午丁未坤申庚酉辛戌乾亥壬")
SOURCE_PROFILE_PACKS = {
    "yangzhai_shishu": "fengshui/yangzhai-shishu",
    "huangdi_zhaijing": "fengshui/huangdi-zhaijing",
    "yangzhai_sanyao": "fengshui/yangzhai-sanyao",
    "zangshu": "fengshui/zangshu",
    "hanlong_jing": "fengshui/hanlong-jing",
    "yilong_jing": "fengshui/yilong-jing",
    "xuexin_fu": "fengshui/xuexin-fu",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _finding(findings: list[str], condition: bool, message: str) -> None:
    if not condition:
        findings.append(message)


def _measurement(degrees: float, *, identifier: str = "compass-1") -> dict[str, Any]:
    return {
        "measurement_id": identifier,
        "facing_degrees": degrees,
        "method": "handheld_compass",
        "north_reference": "true",
        "correction_degrees": 0.0,
        "uncertainty_degrees": 0.5,
        "quality": "good",
        "source_type": "user_measurement",
        "source_ref": f"fixture-{identifier}",
    }


def _has_exact_fengshui_predicates(rule: Any) -> bool:
    predicates = [item.to_dict() for item in rule.required_fact_predicates]
    return (
        {
            "path_suffix": "/fact_layer_status",
            "operator": "eq",
            "value": "observation_driven_fengshui_facts",
        }
        in predicates
        and {
            "path_suffix": "/active_source_rule_ids",
            "operator": "descendant_eq",
            "value": rule.rule_id,
        }
        in predicates
    )


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)


def _runtime_source_packs(table: Mapping[str, Any]) -> set[str]:
    candidates = list(
        _walk_strings(
            {
                "observation": table.get("observation_contract", {}).get(
                    "rule_activation", {}
                ),
                "calculated": table.get("calculated_rule_activation", {}),
            }
        )
    )
    return {
        item.split("#", 1)[0]
        for item in candidates
        if item.startswith("fengshui/") and "#" in item
    }


def _load_reference_evaluator(
    fixture: Mapping[str, Any],
    findings: list[str],
) -> Any | None:
    contract = fixture.get("oracle_policy") or {}
    relative = str(contract.get("evaluator_path") or "")
    evaluator_path = (ROOT / relative).resolve()
    if not evaluator_path.is_file():
        findings.append("Fengshui fixture oracle evaluator is missing")
        return None
    expected = str(contract.get("evaluator_sha256") or "")
    if _sha256(evaluator_path) != expected:
        findings.append("Fengshui fixture oracle evaluator hash mismatch")
        return None
    source = evaluator_path.read_text(encoding="utf-8")
    for forbidden in contract.get("forbidden_imports") or ():
        if str(forbidden) in source:
            findings.append(
                f"Fengshui fixture oracle imports forbidden production module {forbidden}"
            )
            return None
    spec = importlib.util.spec_from_file_location(
        "mingli_fengshui_fixture_reference",
        evaluator_path,
    )
    if spec is None or spec.loader is None:
        findings.append("Fengshui fixture oracle cannot be imported")
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evaluator = getattr(module, "evaluate_complete_spec", None)
    if not callable(evaluator):
        findings.append("Fengshui fixture oracle lacks evaluate_complete_spec")
        return None
    return evaluator


def _audit_source_profiles(
    table: Mapping[str, Any],
    matrix: Mapping[str, Any],
    findings: list[str],
    research_root: Path | None,
) -> tuple[int, int]:
    profiles = table.get("source_profiles") or {}
    source_mismatches = 0
    excerpt_mismatches = 0
    for profile_id, pack in SOURCE_PROFILE_PACKS.items():
        profile = profiles.get(profile_id)
        label = f"Fengshui source profile {profile_id}"
        if not isinstance(profile, Mapping):
            findings.append(f"{label} is missing")
            source_mismatches += 1
            continue
        if research_root is None:
            continue
        path = research_root / str(profile.get("normalized_path") or "")
        if not path.is_file() or path.is_symlink():
            findings.append(f"{label} normalized source is missing")
            source_mismatches += 1
            continue
        if _sha256(path) != profile.get("sha256"):
            findings.append(f"{label} normalized source hash mismatch")
            source_mismatches += 1
        text = path.read_text(encoding="utf-8")
        excerpts = profile.get("exact_excerpts")
        if not isinstance(excerpts, Mapping) or not excerpts:
            findings.append(f"{label} has no exact excerpt")
            excerpt_mismatches += 1
        else:
            for excerpt_id, excerpt in excerpts.items():
                if str(excerpt) not in text:
                    findings.append(
                        f"{label} exact excerpt {excerpt_id} is not in normalized source"
                    )
                    excerpt_mismatches += 1

    runtime_packs = _runtime_source_packs(table)
    declared_packs = set(SOURCE_PROFILE_PACKS.values())
    for pack in sorted(runtime_packs - declared_packs):
        findings.append(f"Fengshui runtime source pack lacks source profile: {pack}")

    matrix_paths: set[str] = set()
    provider = (matrix.get("providers") or {}).get("fengshui") or {}
    for dependency in provider.get("dependencies") or ():
        for source in dependency.get("primary_sources") or ():
            if isinstance(source, Mapping):
                matrix_paths.add(str(source.get("normalized_path") or ""))
    for profile_id, pack in SOURCE_PROFILE_PACKS.items():
        if pack not in runtime_packs:
            continue
        profile = profiles.get(profile_id) or {}
        path = str(profile.get("normalized_path") or "")
        if path not in matrix_paths:
            findings.append(
                f"Fengshui runtime source pack is outside algorithm-source closure: {pack}"
            )
            source_mismatches += 1
    return source_mismatches, excerpt_mismatches


def _scrub_scenario(value: Any) -> Any:
    ignored = {
        "measurement_id",
        "observation_id",
        "asset_id",
        "source_ref",
        "confirmed_measurement_id",
    }
    if isinstance(value, Mapping):
        return {
            key: _scrub_scenario(item)
            for key, item in value.items()
            if key not in ignored
            and key not in {"compass_measurements", "declared_orientation"}
        }
    if isinstance(value, list):
        return [_scrub_scenario(item) for item in value]
    return value


def _provider_projection(output: Mapping[str, Any]) -> dict[str, Any]:
    facing = output["compass"]["facing"]
    sitting = output["compass"]["sitting"]
    bazhai = output["liqi"].get("bazhai") or {}
    return {
        "facing_mountain": facing.get("mountain") if facing else None,
        "sitting_mountain": sitting.get("mountain") if sitting else None,
        "form_status": output["form"]["status"],
        "origin_gua": bazhai.get("origin_gua"),
        "origin_group": bazhai.get("origin_group"),
        "active_source_rule_ids": output["active_source_rule_ids"],
    }


def _audit_assets(
    fixture: Mapping[str, Any],
    findings: list[str],
) -> tuple[dict[str, Mapping[str, Any]], int, int]:
    by_hash: dict[str, Mapping[str, Any]] = {}
    asset_mismatches = 0
    annotation_mismatches = 0
    root = ROOT.resolve()
    for row in fixture.get("asset_manifest") or ():
        label = f"Fengshui asset {row.get('manifest_id')}"
        path = (ROOT / str(row.get("path") or "")).resolve()
        inside_root = path == root or root in path.parents
        if not inside_root or not path.is_file() or path.is_symlink():
            findings.append(f"{label} path is missing, escaped, or symlinked")
            asset_mismatches += 1
            continue
        if path.stat().st_size != row.get("byte_length"):
            findings.append(f"{label} byte length mismatch")
            asset_mismatches += 1
        actual = _sha256(path)
        if actual != row.get("sha256"):
            findings.append(f"{label} sha256 mismatch")
            asset_mismatches += 1
        if row.get("license") != "project_authored_test_fixture":
            findings.append(f"{label} license is not project-authored")
            asset_mismatches += 1
        annotations = row.get("annotations") or []
        if _canonical_sha256(annotations) != row.get("annotations_sha256"):
            findings.append(f"{label} annotation digest mismatch")
            annotation_mismatches += 1
        by_hash[str(row.get("sha256") or "")] = row
    if len(by_hash) < 4:
        findings.append("Fengshui requires at least four distinct fixture assets")
        asset_mismatches += 1
    return by_hash, asset_mismatches, annotation_mismatches


def _annotation_identity(observation: Mapping[str, Any]) -> str:
    return _canonical_sha256(
        {
            "kind": observation.get("kind"),
            "region_anchor": observation.get("region_anchor"),
            "value": observation.get("value"),
        }
    )


def _manifest_annotation_identities(row: Mapping[str, Any]) -> set[str]:
    return {
        _canonical_sha256(
            {
                "kind": annotation.get("kind"),
                "region_anchor": annotation.get("region_anchor"),
                "value": annotation.get("value"),
            }
        )
        for annotation in row.get("annotations") or ()
    }


def audit_fengshui_provider(
    *,
    fixture_path: Path = FIXTURE,
    source_table_path: Path = SOURCE_TABLE,
    matrix_path: Path = MATRIX,
    research_root: Path | None = None,
) -> dict[str, Any]:
    """Audit the Fengshui provider's runtime readiness and, when an explicit
    release-time fulltext root is supplied, verify source provenance.

    ``research_root`` is the release-time fulltext tree for source
    verification.  It is intentionally independent of ``audit_matrix``'s own
    optional research-root wiring so a portable checkout can prove runtime
    readiness without an external corpus, while a release build passes an
    explicit root to close the source-verification gate.
    """
    preflight = provider_preflight_failure(
        system="fengshui",
        schema_version="mingli-fengshui-provider-audit-v1",
        provider_class=FengshuiProvider,
        expected_mode="observation_driven_ready",
        expected_provider_id=EXPECTED_PROVIDER_ID,
        expected_provider_version=EXPECTED_PROVIDER_VERSION,
    )
    if preflight is not None:
        return preflight

    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    table = yaml.safe_load(source_table_path.read_text(encoding="utf-8"))
    matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    findings: list[str] = []

    _finding(
        findings,
        FengshuiProvider.provider_id == EXPECTED_PROVIDER_ID
        and FengshuiProvider.provider_version == EXPECTED_PROVIDER_VERSION,
        "Fengshui provider identity drift",
    )
    _finding(
        findings,
        PROVIDER_CAPABILITIES["fengshui"].mode == "observation_driven_ready",
        "Fengshui provider capability mode is not observation_driven_ready",
    )

    _finding(
        findings,
        _sha256(source_table_path) == SOURCE_TABLE_SHA256,
        "Fengshui source-table artifact hash mismatch",
    )
    _finding(
        findings,
        _sha256(fixture_path) == FIXTURE_SHA256,
        "Fengshui fixture artifact hash mismatch",
    )
    _finding(
        findings,
        table.get("schema_version") == "mingli-fengshui-source-tables-v1",
        "unexpected Fengshui source-table schema",
    )
    _finding(
        findings,
        fixture.get("schema_version") == "mingli-fengshui-fixtures-v51",
        "unexpected Fengshui fixture schema",
    )
    _finding(
        findings,
        (table.get("selected_convention") or {}).get("classification")
        == "engineering_measurement_convention",
        "Fengshui degree sectors must be labelled as an engineering convention",
    )
    _finding(
        findings,
        tuple(row.get("mountain") for row in table.get("mountain_order_clockwise") or ())
        == MOUNTAINS,
        "Fengshui 24-mountain source table is incomplete or reordered",
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
    if resolved_research_root is not None:
        source_mismatches, excerpt_mismatches = _audit_source_profiles(
            table,
            matrix,
            source_verification.setdefault("findings", []),
            resolved_research_root,
        )
        source_verification["source_profile_mismatches"] = source_mismatches
        source_verification["source_excerpt_mismatches"] = excerpt_mismatches
        source_verification["ok"] = not source_verification.get("findings")
        source_verification["status"] = (
            "verified" if source_verification["ok"] else "failed"
        )
    else:
        source_mismatches, excerpt_mismatches = _audit_source_profiles(
            table,
            matrix,
            findings,
            None,
        )

    boundary_mismatches = 0
    for index, mountain in enumerate(MOUNTAINS):
        boundary = (7.5 + 15.0 * index) % 360.0
        before = (boundary - 0.0001) % 360.0
        if fengshui.mountain_for_degrees(before) != mountain:
            boundary_mismatches += 1
        exact = _measurement(boundary, identifier=f"boundary-{index}")
        exact["uncertainty_degrees"] = 0.0
        normalized = fengshui.normalize_compass_measurements([exact])
        if (
            normalized.get("status") != "resolved"
            or (normalized.get("facing") or {}).get("mountain")
            != MOUNTAINS[(index + 1) % 24]
        ):
            boundary_mismatches += 1
    _finding(
        findings,
        boundary_mismatches == 0,
        "Fengshui compass boundary oracle mismatch",
    )

    compass_reference_mismatches = 0
    compass_rows = fixture.get("compass_reference_fixtures") or ()
    for row in compass_rows:
        normalized = fengshui.normalize_compass_measurements(
            [_measurement(float(row["facing_degrees"]), identifier=str(row["id"]))]
        )
        if (
            (normalized.get("facing") or {}).get("mountain")
            != row.get("facing_mountain")
            or (normalized.get("sitting") or {}).get("mountain")
            != row.get("sitting_mountain")
        ):
            compass_reference_mismatches += 1
            findings.append(f"Fengshui compass reference mismatch: {row.get('id')}")
    if len(compass_rows) != 24:
        findings.append("Fengshui compass reference must contain 24 centers")

    evaluator = _load_reference_evaluator(fixture, findings)
    manifest_by_hash, asset_mismatches, annotation_mismatches = _audit_assets(
        fixture,
        findings,
    )

    complete_cases = list(fixture.get("complete_observation_fixtures") or ())
    fixture_mismatches = 0
    oracle_mismatches = 0
    deterministic_mismatches = 0
    scenario_digests: set[str] = set()
    observed_kinds: set[str] = set()
    observed_scopes: set[str] = set()
    observed_source_types: set[str] = set()
    used_asset_hashes: set[str] = set()
    confirmed_correction_cases = 0
    qualifying_cases = 0
    provider_calculations = 0
    provider_extensions = 0
    determinism_checks = 0
    invented_observations = 0
    observation_fact_key_mismatches = 0

    def live_provider_pair(
        spec: Mapping[str, Any],
        *,
        label: str,
    ) -> dict[str, Any]:
        nonlocal provider_calculations
        nonlocal provider_extensions
        nonlocal determinism_checks
        nonlocal invented_observations
        nonlocal observation_fact_key_mismatches
        request = ReadingRequest(
            query=f"Task 7N Fengshui provider replay {label}",
            action="new",
            system="fengshui",
            chart_data={"fengshui_spec": copy.deepcopy(dict(spec))},
        )
        results = []
        errors: list[Exception] = []
        for _ in range(2):
            provider_calculations += 1
            try:
                results.append(FengshuiProvider(ROOT).calculate(request))
            except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                errors.append(exc)
        if errors or len(results) != 2:
            raise ValueError(
                "live provider calculation failed twice consistently: "
                + " | ".join(str(item) for item in errors)
            )
        first, second = results
        for result in results:
            if (
                result.system != "fengshui"
                or result.provider_id != FengshuiProvider.provider_id
                or result.provider_version != FengshuiProvider.provider_version
            ):
                raise ValueError("live provider identity mismatch")
            output = result.facts["chart_facts"]["output"]
            supplied_ids = {
                str(item.get("observation_id") or "")
                for item in spec.get("observations") or ()
                if isinstance(item, Mapping)
            }
            emitted_ids = {
                str(item)
                for item in output["observation_provenance"]["observation_ids"]
            }
            invented_observations += len(emitted_ids - supplied_ids)
            accepted_rows = [
                row
                for row in output["form"]["observations"]
                if row["status"] == "accepted_observation_not_verdict"
            ]
            expected_fact_keys = sorted(
                {
                    f"{row['kind']}|{row['value']['relation']}"
                    for row in accepted_rows
                }
            )
            if output["form"].get("accepted_observation_fact_keys") != expected_fact_keys:
                observation_fact_key_mismatches += 1
        if (
            first.result_hash != second.result_hash
            or first.input_hash != second.input_hash
            or canonical_digest(first.facts) != canonical_digest(second.facts)
        ):
            raise ValueError("live provider calculation is nondeterministic")
        determinism_checks += 1

        dimensions = tuple(PROVIDER_CAPABILITIES["fengshui"].dimensions)
        horizon = {"kind": "instant"}
        extended = []
        for result in results:
            provider_extensions += 1
            extended.append(
                FengshuiProvider(ROOT).extend(result, dimensions, horizon)
            )
        first_extension = extended[0].fact_extension
        second_extension = extended[1].fact_extension
        expected_status = (
            "partial"
            if first.facts["chart_facts"]["output"]["critical_missing"]
            else "complete"
        )
        if (
            first_extension is None
            or second_extension is None
            or first_extension.status != expected_status
            or second_extension.status != expected_status
            or first_extension.extension_digest
            != second_extension.extension_digest
            or canonical_digest(first_extension.facts)
            != canonical_digest(second_extension.facts)
        ):
            raise ValueError("live provider extension is incomplete or nondeterministic")
        determinism_checks += 1
        return first.facts["chart_facts"]

    for case in complete_cases:
        case_id = str(case.get("id") or "<missing-id>")
        case_finding_start = len(findings)
        spec = copy.deepcopy((case.get("input") or {}).get("fengshui_spec"))
        expected = case.get("expected")
        if not isinstance(spec, Mapping) or not isinstance(expected, Mapping):
            findings.append(f"Fengshui complete fixture is malformed: {case_id}")
            fixture_mismatches += 1
            continue
        try:
            first = live_provider_pair(spec, label=case_id)
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            findings.append(f"Fengshui complete fixture failed: {case_id}: {exc}")
            fixture_mismatches += 1
            continue
        output = first["output"]
        projection = _provider_projection(output)
        if projection != dict(expected):
            findings.append(f"Fengshui provider fixture mismatch: {case_id}")
            fixture_mismatches += 1
        if (
            output["form"]["status"] != "complete"
            or output["critical_missing"]
            or output["conflicts"]
            or "xuankong" in output["liqi"]
            or "sanhe" in output["liqi"]
        ):
            findings.append(f"Fengshui complete fixture is not complete: {case_id}")
            fixture_mismatches += 1
        if evaluator is not None:
            try:
                oracle = evaluator(spec)
            except (KeyError, TypeError, ValueError) as exc:
                findings.append(f"Fengshui fixture oracle failed: {case_id}: {exc}")
                oracle_mismatches += 1
            else:
                if oracle != dict(expected):
                    findings.append(f"Fengshui fixture oracle mismatch: {case_id}")
                    oracle_mismatches += 1

        scenario_digests.add(_canonical_sha256(_scrub_scenario(spec)))
        observed_scopes.add(str(spec["property_scope"]))
        asset_hash_by_id = {
            str(asset["asset_id"]): str(asset["sha256"])
            for asset in spec["assets"]
        }
        used_asset_hashes.update(asset_hash_by_id.values())
        for observation in spec["observations"]:
            observed_kinds.add(str(observation["kind"]))
            observed_source_types.add(str(observation["source_type"]))
            if observation["source_type"] != "image_transcription":
                continue
            asset_hash = asset_hash_by_id.get(str(observation.get("asset_id") or ""))
            manifest = manifest_by_hash.get(str(asset_hash or ""))
            if (
                manifest is None
                or _annotation_identity(observation)
                not in _manifest_annotation_identities(manifest)
            ):
                findings.append(
                    f"Fengshui image observation lacks manifest annotation: {case_id}"
                )
                annotation_mismatches += 1
        if len(spec.get("compass_measurements") or ()) > 1 and spec.get(
            "confirmed_measurement_id"
        ):
            confirmed_correction_cases += 1
        if len(findings) == case_finding_start:
            qualifying_cases += 1

    allowed_kinds = set(
        (table.get("observation_contract") or {}).get("allowed_kinds") or ()
    )
    _finding(
        findings,
        len(complete_cases) >= 20,
        "Fengshui requires at least twenty complete observation fixtures",
    )
    _finding(
        findings,
        len(scenario_digests) >= 20,
        "Fengshui complete fixtures are observation-scenario clones",
    )
    _finding(
        findings,
        observed_kinds == allowed_kinds,
        "Fengshui complete fixtures do not cover every observation kind",
    )
    _finding(
        findings,
        observed_scopes
        == {"residential", "site_general", "burial_cultural_study"},
        "Fengshui complete fixtures do not cover every property scope",
    )
    _finding(
        findings,
        {"image_transcription", "user_text", "user_file"}
        <= observed_source_types,
        "Fengshui complete fixtures lack required source types",
    )
    _finding(
        findings,
        len(used_asset_hashes) >= 4,
        "Fengshui complete fixtures do not use all four pinned assets",
    )
    _finding(
        findings,
        confirmed_correction_cases >= 1,
        "Fengshui complete fixtures lack a user-confirmed correction case",
    )
    _finding(
        findings,
        qualifying_cases >= 20,
        "Fengshui live provider replay requires at least 20 qualifying cases",
    )
    _finding(
        findings,
        invented_observations == 0,
        "Fengshui live provider invented observations absent from supplied input",
    )
    _finding(
        findings,
        observation_fact_key_mismatches == 0,
        "Fengshui accepted observation fact keys are not row-scoped",
    )

    complete_by_id = {str(case["id"]): case for case in complete_cases}
    special_cases = list(fixture.get("special_observation_fixtures") or ())
    categories = Counter(str(case.get("category") or "") for case in special_cases)
    special_mismatches = 0
    for case in special_cases:
        case_id = str(case.get("id") or "")
        category = str(case.get("category") or "")
        expected = case.get("expected") or {}
        try:
            if category in {"partial", "conflict"}:
                spec = copy.deepcopy(case["input"]["fengshui_spec"])
                output = live_provider_pair(spec, label=case_id)["output"]
                if category == "partial":
                    observed = {
                        "form_status": output["form"]["status"],
                        "critical_missing": output["critical_missing"],
                    }
                else:
                    observed = {
                        "compass_status": output["compass"]["status"],
                        "liqi_status": output["liqi"]["status"],
                        "critical_missing": output["critical_missing"],
                    }
                if observed != expected:
                    raise ValueError("expected projection differs")
            elif category == "low_quality":
                base = copy.deepcopy(
                    complete_by_id["FS-O01"]["input"]["fengshui_spec"]
                )
                mutation = case["mutation"]
                base["observations"][0]["quality"][mutation["quality_field"]] = mutation[
                    "value"
                ]
                output = live_provider_pair(base, label=case_id)["output"]
                observed = {
                    "observation_status": output["form"]["observations"][0][
                        "status"
                    ],
                    "critical_missing": output["critical_missing"],
                }
                if observed != expected:
                    raise ValueError("expected projection differs")
            elif category == "school_isolation":
                base = copy.deepcopy(
                    complete_by_id[str(case["input_case"])]["input"][
                        "fengshui_spec"
                    ]
                )
                liqi = live_provider_pair(base, label=case_id)["output"]["liqi"]
                if (
                    liqi["selected_school"] != expected["selected_school"]
                    or "xuankong" in liqi
                    or "flying_stars" in liqi
                ):
                    raise ValueError("school isolation differs")
            elif category == "invalid_scope_school":
                mutation = case["mutation"]
                base = copy.deepcopy(
                    complete_by_id[str(mutation["base_case"])]["input"][
                        "fengshui_spec"
                    ]
                )
                base["property_scope"] = mutation["property_scope"]
                error_messages: list[str] = []
                for _ in range(2):
                    provider_calculations += 1
                    try:
                        FengshuiProvider(ROOT).calculate(
                            ReadingRequest(
                                query=f"Task 7N Fengshui rejection replay {case_id}",
                                action="new",
                                system="fengshui",
                                chart_data={"fengshui_spec": copy.deepcopy(base)},
                            )
                        )
                    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                        error_messages.append(str(exc))
                if (
                    len(error_messages) != 2
                    or error_messages[0] != error_messages[1]
                    or str(case["expected_error"]) not in error_messages[0]
                ):
                    raise ValueError("invalid scope school rejection is nondeterministic")
                determinism_checks += 1
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            findings.append(f"Fengshui special fixture mismatch: {case_id}: {exc}")
            special_mismatches += 1

    _finding(findings, categories["partial"] >= 1, "Fengshui partial fixture missing")
    _finding(findings, categories["conflict"] >= 1, "Fengshui conflict fixture missing")
    _finding(
        findings,
        categories["low_quality"] >= 3,
        "Fengshui low-quality fixtures are incomplete",
    )
    reported_boundary_categories: set[str] = set()
    if complete_cases:
        reported_boundary_categories.add("complete")
    if categories["partial"]:
        reported_boundary_categories.add("missing")
    if categories["conflict"]:
        reported_boundary_categories.add("conflict")
    if categories["low_quality"]:
        reported_boundary_categories.add("low_quality")
    if confirmed_correction_cases:
        reported_boundary_categories.add("correction")
    if categories["school_isolation"]:
        reported_boundary_categories.add("school_isolation")

    for case in fixture.get("bazhai_source_examples") or ():
        if fengshui.bazhai_star_map(case["house_gua"]) != case["expected_star_map"]:
            fixture_mismatches += 1
            findings.append(
                f"Fengshui Bazhai mnemonic mismatch: {case.get('house_gua')}"
            )

    rules = [rule for rule in production_evidence_rules() if rule.system == "fengshui"]
    rules_without_predicates = sum(
        not _has_exact_fengshui_predicates(rule) for rule in rules
    )
    _finding(findings, len(rules) == 179, "Fengshui evidence-rule count mismatch")
    _finding(
        findings,
        rules_without_predicates == 0,
        "Fengshui evidence rules lack exact fact predicates",
    )

    algorithm_report = audit_algorithm_sources.audit_matrix(
        matrix,
        root=ROOT,
        systems=("fengshui",),
    )
    findings.extend(algorithm_report["findings"])
    aggregate_fixture_mismatches = (
        fixture_mismatches
        + oracle_mismatches
        + deterministic_mismatches
        + special_mismatches
        + compass_reference_mismatches
        + asset_mismatches
        + annotation_mismatches
    )
    return {
        "schema_version": "mingli-fengshui-provider-audit-v1",
        "system": "fengshui",
        "provider_ready": not findings,
        "status": "pass" if not findings else "fail",
        "provider": {
            "provider_id": FengshuiProvider.provider_id,
            "provider_version": FengshuiProvider.provider_version,
            "capability_mode": PROVIDER_CAPABILITIES["fengshui"].mode,
        },
        "route_owned_case_ids": [
            str(case.get("id") or "") for case in complete_cases
        ],
        "counts": {
            "qualifying_cases": qualifying_cases,
            "route_owned_cases": len(complete_cases),
            "boundary_case_count": sum(categories.values()),
            "provider_calculations": provider_calculations,
            "provider_extensions": provider_extensions,
            "determinism_checks": determinism_checks,
            "invented_observations": invented_observations,
            "observation_fact_key_mismatches": observation_fact_key_mismatches,
            "complete_observation_fixtures": len(complete_cases),
            "distinct_observation_scenarios": len(scenario_digests),
            "partial_fixtures": categories["partial"],
            "conflict_fixtures": categories["conflict"],
            "low_quality_fixtures": categories["low_quality"],
            "compass_boundary_checks": 48,
            "compass_boundary_mismatches": boundary_mismatches,
            "compass_reference_mismatches": compass_reference_mismatches,
            "fixture_mismatches": aggregate_fixture_mismatches,
            "oracle_mismatches": oracle_mismatches,
            "deterministic_mismatches": deterministic_mismatches,
            "special_case_mismatches": special_mismatches,
            "asset_hash_mismatches": asset_mismatches,
            "annotation_mismatches": annotation_mismatches,
            "source_profile_mismatches": source_mismatches,
            "source_excerpt_mismatches": excerpt_mismatches,
            "algorithm_dependencies": algorithm_report["dependency_count"],
            "evidence_rules": len(rules),
            "evidence_rules_without_exact_predicates": rules_without_predicates,
        },
        "source_table_sha256": _sha256(source_table_path),
        "fixture": {
            "path": str(fixture_path),
            "sha256": _sha256(fixture_path),
            "expected_sha256": FIXTURE_SHA256,
        },
        "fixture_sha256": _sha256(fixture_path),
        "boundary_categories": sorted(reported_boundary_categories),
        "source_verification": source_verification,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--source-table", type=Path, default=SOURCE_TABLE)
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    args = parser.parse_args()
    report = audit_fengshui_provider(
        fixture_path=args.fixture,
        source_table_path=args.source_table,
        matrix_path=args.matrix,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
