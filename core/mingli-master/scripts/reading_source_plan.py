#!/usr/bin/env python3
"""Compile deterministic classical-source plans for Mingli reading routes."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from simplified_canonical import canonicalize


SCHEMA_VERSION = "mingli-reading-source-plan-v1"
ROOT = Path(__file__).resolve().parents[1]

BLOCKED_PACKS = {
    "ziwei/doushu-guanjian",
    "xingming/qizheng-siyu-tianjing",
    "xingming/qizheng-quanshu-dacheng",
    "xingming/minghai-quanbian",
}

# Section 5 / audit P1-2 hardening: applicability filter for Qiongtong Baojian.
# The matrix is stored in references/matrices/qiongtong-applicability.yaml.
# Loading it here (rather than hard-coding the 40 chapter labels in Python)
# turns the YAML into a real source dependency whose hash we bind into the
# generated plan. If the file is missing or malformed, plan compilation fails
# loudly rather than silently falling back to a hidden default.
RUNTIME_SOURCE_REGISTRY_PATH = (
    ROOT / "references" / "matrices" / "runtime-source-families-v1.yaml"
)
RUNTIME_SOURCE_REGISTRY_RELATIVE = (
    "references/matrices/runtime-source-families-v1.yaml"
)
RUNTIME_SOURCE_REGISTRY_SCHEMA = "mingli-runtime-source-families-v1"
EXPECTED_RUNTIME_SOURCE_REGISTRY_SHA256 = (
    "6f0a8627aaa5a96a229af15e4d16a15eec5d3fb099ebb1b51d8745599ef94816"
)
RUNTIME_SOURCE_ROUTES = {
    "bazi", "fortune", "ziwei", "luming-nayin", "xingming", "liuyao",
    "meihua", "liuren", "qimen", "taiyi", "selection", "fengshui",
    "physiognomy", "time-check",
}
RUNTIME_SOURCE_EVIDENCE_ROLES = {
    "casting_rule",
    "imagery_correspondence",
    "issue_specific_judgment_rule",
    "methodology_rule",
    "terminology_only",
    "edition_boundary",
    "timing_rule",
    "verdict_prohibited",
}
_PACK_IDENTITY = re.compile(r"^[a-z0-9-]+/[a-z0-9-]+$")
_ROUTE_PACK_NAMESPACES = {
    "bazi": {"bazi"},
    "fortune": {"bazi"},
    "ziwei": {"ziwei"},
    "luming-nayin": {"luming-nayin"},
    "xingming": {"xingming"},
    "liuyao": {"divination"},
    "meihua": {"divination"},
    "liuren": {"san-shi"},
    "qimen": {"san-shi"},
    "taiyi": {"san-shi"},
    "selection": {"selection"},
    "fengshui": {"fengshui"},
    "physiognomy": {"physiognomy"},
    "time-check": {"bazi"},
}


_RUNTIME_SOURCE_REGISTRY_CACHE: dict[str, Any] | None = None


def _validated_pack_list(
    value: Any,
    *,
    context: str,
    ready_packs: set[str],
    namespaces: set[str],
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    if any(
        not isinstance(pack, str)
        or not _PACK_IDENTITY.fullmatch(pack)
        or pack.split("/", 1)[0] not in namespaces
        for pack in value
    ):
        raise ValueError(f"{context} has invalid pack identity")
    if len(value) != len(set(value)):
        raise ValueError(f"{context} has duplicate pack identity")
    unknown = sorted(set(value) - ready_packs)
    if unknown:
        raise ValueError(
            f"{context} references pack identity absent from ready catalog: "
            + ", ".join(unknown)
        )
    return list(value)


def load_runtime_source_registry(path: Path | None = None) -> dict[str, Any]:
    """Load the fail-closed runtime source-family authority.

    Conditional families use ``activated_rule_packs``: their pack lists are
    the closed set that a fact-bound provider may activate, not a demand that
    every representative chart cite every pack in the family.
    """
    global _RUNTIME_SOURCE_REGISTRY_CACHE
    registry_path = path or RUNTIME_SOURCE_REGISTRY_PATH
    if path is None and _RUNTIME_SOURCE_REGISTRY_CACHE is not None:
        return copy.deepcopy(_RUNTIME_SOURCE_REGISTRY_CACHE)
    if not registry_path.is_file():
        raise ValueError(f"runtime source registry is missing: {registry_path}")
    raw = registry_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if path is None and digest != EXPECTED_RUNTIME_SOURCE_REGISTRY_SHA256:
        raise ValueError("runtime source registry sha256 mismatch")
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise ValueError("PyYAML required to load runtime source registry") from exc
    payload = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "required_always_semantics",
        "routes",
    }:
        raise ValueError(
            "runtime source registry must contain only schema_version/semantics/routes"
        )
    if payload.get("schema_version") != RUNTIME_SOURCE_REGISTRY_SCHEMA:
        raise ValueError("runtime source registry schema_version mismatch")
    if payload.get("required_always_semantics") != (
        "route_readiness_required_goal_may_select_subset"
    ):
        raise ValueError("runtime source registry required_always semantics mismatch")
    routes = payload.get("routes")
    if not isinstance(routes, dict) or set(routes) != RUNTIME_SOURCE_ROUTES:
        raise ValueError("runtime source registry must contain exactly the 13 runtime routes")

    catalog = json.loads(
        (ROOT / "references" / "catalog" / "catalog.json").read_text(encoding="utf-8")
    )
    ready_packs = {
        f"{item['system']}/{item['slug']}"
        for item in catalog.get("ready_reference_packs", [])
        if isinstance(item, dict) and item.get("system") and item.get("slug")
    }
    normalized_routes: dict[str, Any] = {}
    for route_name in sorted(RUNTIME_SOURCE_ROUTES):
        route = routes[route_name]
        if not isinstance(route, dict) or set(route) != {
            "required_always",
            "required_when_active_subprofile",
            "comparison_only",
            "required_roles_by_pack",
        }:
            raise ValueError(f"runtime source route {route_name} has invalid fields")
        namespaces = _ROUTE_PACK_NAMESPACES[route_name]
        required_always = _validated_pack_list(
            route["required_always"],
            context=f"routes.{route_name}.required_always",
            ready_packs=ready_packs,
            namespaces=namespaces,
        )
        comparison_only = _validated_pack_list(
            route["comparison_only"],
            context=f"routes.{route_name}.comparison_only",
            ready_packs=ready_packs,
            namespaces=namespaces,
        )
        conditional_raw = route["required_when_active_subprofile"]
        if not isinstance(conditional_raw, dict):
            raise ValueError(
                f"routes.{route_name}.required_when_active_subprofile must be an object"
            )
        conditional: dict[str, Any] = {}
        conditional_packs: set[str] = set()
        for subprofile, family in conditional_raw.items():
            if not isinstance(subprofile, str) or not subprofile.strip():
                raise ValueError(f"routes.{route_name} has invalid subprofile identity")
            if not isinstance(family, dict) or set(family) != {"selection_mode", "packs"}:
                raise ValueError(
                    f"routes.{route_name}.{subprofile} has invalid conditional family"
                )
            if family.get("selection_mode") != "activated_rule_packs":
                raise ValueError(
                    f"routes.{route_name}.{subprofile} has unsupported selection_mode"
                )
            family_packs = _validated_pack_list(
                family.get("packs"),
                context=f"routes.{route_name}.{subprofile}.packs",
                ready_packs=ready_packs,
                namespaces=namespaces,
            )
            if not family_packs:
                raise ValueError(f"routes.{route_name}.{subprofile}.packs must not be empty")
            conditional_packs.update(family_packs)
            conditional[subprofile] = {
                "selection_mode": "activated_rule_packs",
                "packs": family_packs,
            }
        required = set(required_always) | conditional_packs
        overlap = required & set(comparison_only)
        if overlap:
            raise ValueError(
                f"routes.{route_name} pack is both required and comparison-only: "
                + ", ".join(sorted(overlap))
            )
        roles_raw = route["required_roles_by_pack"]
        if not isinstance(roles_raw, dict) or set(roles_raw) != required:
            raise ValueError(
                f"routes.{route_name} role contract must cover every required pack"
            )
        required_roles_by_pack: dict[str, list[str]] = {}
        for pack in sorted(required):
            roles = roles_raw.get(pack)
            if (
                not isinstance(roles, list)
                or not roles
                or any(
                    not isinstance(role, str)
                    or role not in RUNTIME_SOURCE_EVIDENCE_ROLES
                    for role in roles
                )
                or len(roles) != len(set(roles))
            ):
                raise ValueError(
                    f"routes.{route_name}.{pack} has invalid required evidence roles"
                )
            required_roles_by_pack[pack] = list(roles)
        normalized_routes[route_name] = {
            "required_always": required_always,
            "required_when_active_subprofile": conditional,
            "comparison_only": comparison_only,
            "required_roles_by_pack": required_roles_by_pack,
        }
    normalized = {
        "schema_version": RUNTIME_SOURCE_REGISTRY_SCHEMA,
        "required_always_semantics": payload["required_always_semantics"],
        "path": (
            RUNTIME_SOURCE_REGISTRY_RELATIVE
            if path is None
            else str(registry_path)
        ),
        "sha256": digest,
        "routes": normalized_routes,
    }
    if path is None:
        _RUNTIME_SOURCE_REGISTRY_CACHE = normalized
    return copy.deepcopy(normalized)


def _runtime_source_family_contract(
    route_name: str,
    required_packs: list[str],
    comparison_packs: list[str],
) -> dict[str, Any]:
    registry = load_runtime_source_registry()
    family = registry["routes"].get(route_name)
    if family is None:
        raise ValueError(f"runtime source registry has no route: {route_name}")
    conditional_packs = {
        pack
        for subprofile in family["required_when_active_subprofile"].values()
        for pack in subprofile["packs"]
    }
    permitted_required = set(family["required_always"]) | conditional_packs
    comparison_only = set(family["comparison_only"])
    forbidden_support = set(required_packs) & comparison_only
    if forbidden_support:
        raise ValueError(
            "comparison-only source pack cannot be selected as required support: "
            + ", ".join(sorted(forbidden_support))
        )
    unauthorized = set(required_packs) - permitted_required
    if unauthorized:
        raise ValueError(
            f"runtime source registry rejects {route_name} required pack(s): "
            + ", ".join(sorted(unauthorized))
        )
    permitted_comparison = permitted_required | comparison_only
    unauthorized_comparison = set(comparison_packs) - permitted_comparison
    if unauthorized_comparison:
        raise ValueError(
            f"runtime source registry rejects {route_name} comparison pack(s): "
            + ", ".join(sorted(unauthorized_comparison))
        )
    return {
        "schema_version": registry["schema_version"],
        "registry_path": registry["path"],
        "registry_sha256": registry["sha256"],
        "route": route_name,
        "required_always_semantics": registry["required_always_semantics"],
        "required_always": list(family["required_always"]),
        "required_when_active_subprofile": family["required_when_active_subprofile"],
        "comparison_only": list(family["comparison_only"]),
        "required_roles_by_pack": copy.deepcopy(
            family["required_roles_by_pack"]
        ),
        "selected_required_packs": list(required_packs),
        "selected_comparison_packs": list(comparison_packs),
    }


def _source_paths(packs: list[str]) -> tuple[list[str], list[str]]:
    rules: list[str] = []
    quotes: list[str] = []
    for pack in packs:
        if pack in BLOCKED_PACKS:
            raise ValueError(f"blocked pack selected: {pack}")
        rule_path = f"references/books/{pack}/rules.md"
        quote_path = f"references/books/{pack}/quote-index.md"
        for relpath in (rule_path, quote_path):
            path = ROOT / relpath
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f"source file missing or empty: {relpath}")
        rules.append(rule_path)
        quotes.append(quote_path)
    return rules, quotes


def _book_titles(packs: list[str]) -> list[str]:
    catalog_path = ROOT / "references/catalog/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    titles = {
        f"{item['system']}/{item['slug']}": canonicalize(str(item["title"]))
        for item in catalog.get("ready_reference_packs", [])
    }
    missing = [pack for pack in packs if pack not in titles]
    if missing:
        raise ValueError("ready pack title missing from catalog: " + ", ".join(missing))
    return [titles[pack] for pack in packs]


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _resolve_fact_path(facts: dict[str, Any], dotted: str) -> Any:
    node: Any = facts
    wrapped = node.get("chart_facts") if isinstance(node, dict) else None
    if isinstance(wrapped, dict):
        node = wrapped
    for part in dotted.split("."):
        node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return None
    return node


def _compile_applicability_conditions(
    facts: dict[str, Any],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    """Required-fact conditions come from the provider-owned chart contract."""

    contract = plan.get("chart_contract") or {}
    fact_paths = contract.get("fact_paths") or {}
    conditions: list[dict[str, Any]] = []
    for field in contract.get("required_fields") or []:
        dotted = str(fact_paths.get(str(field)) or f"output.{field}")
        value = _resolve_fact_path(facts, dotted)
        conditions.append({
            "id": f"fact:{field}",
            "kind": "required_fact",
            "fact_path": dotted,
            "satisfied": _present(value),
        })
    return conditions


def _fact_ids(value: Any, path: str = "") -> list[str]:
    if isinstance(value, dict) and value:
        found: list[str] = []
        for key in sorted(value, key=str):
            token = str(key).replace("~", "~0").replace("/", "~1")
            found.extend(_fact_ids(value[key], f"{path}/{token}"))
        return found
    if isinstance(value, (list, tuple)) and value:
        found = []
        for index, item in enumerate(value):
            found.extend(_fact_ids(item, f"{path}/{index}"))
        return found
    return [f"fact:{path or '/'}"]


def compile_plan(
    route: dict[str, Any],
    goal: dict[str, Any],
    facts: dict[str, Any] | None = None,
    *,
    extend: Any = None,
) -> dict[str, Any]:
    """Compile one plan from a provider-owned route payload; no system branches."""

    if not isinstance(goal, dict):
        raise ValueError("source planning goal must be an object")
    if not isinstance(route, dict):
        raise ValueError("source route payload must be an object")
    plan_system = str(route.get("plan_system") or "")
    registry_route = str(route.get("registry_route") or "")
    if not plan_system or not registry_route:
        raise ValueError("source route payload is missing its identity")
    identity = route.get("provider_identity")
    if not isinstance(identity, dict) or not identity.get("provider_id"):
        raise ValueError("source route payload is missing provider identity")

    requested_packs = goal.get("source_packs")
    if requested_packs is not None and (
        not isinstance(requested_packs, list)
        or not all(isinstance(item, str) and item for item in requested_packs)
    ):
        raise ValueError("goal.source_packs must be a list of pack ids")
    pack_policy = str(route.get("pack_policy") or "caller")
    if pack_policy == "locked" or requested_packs is None:
        packs = list(route["packs"])
    else:
        packs = list(dict.fromkeys(requested_packs))
        if pack_policy == "subset" and not set(packs) <= set(route["packs"]):
            raise ValueError(
                str(
                    route.get("pack_scope_error")
                    or "goal.source_packs exceeds the active source scope"
                )
            )

    requested_comparison_packs = goal.get("comparison_packs")
    if requested_comparison_packs is None:
        comparison_packs = list(
            route.get("active_default_comparison_packs") or ()
        )
    else:
        comparison_packs = requested_comparison_packs or []
    if not isinstance(comparison_packs, list) or not all(
        isinstance(item, str) and item for item in comparison_packs
    ):
        raise ValueError("goal.comparison_packs must be a list of pack ids")
    comparison_packs = list(dict.fromkeys(comparison_packs))
    if comparison_packs and route.get("comparison_allowed") is False:
        raise ValueError(
            str(
                route.get("comparison_error")
                or "comparison packs are not supported for this capability"
            )
        )

    runtime_source_family = _runtime_source_family_contract(
        registry_route,
        packs,
        comparison_packs,
    )
    all_packs = list(dict.fromkeys([*packs, *comparison_packs]))
    rules, quotes = _source_paths(all_packs)
    all_titles = _book_titles(all_packs)
    evidence_questions = goal.get("evidence_questions") or []
    if not isinstance(evidence_questions, list) or not all(
        isinstance(item, str) and item.strip() for item in evidence_questions
    ):
        raise ValueError("goal.evidence_questions must be a list of text questions")
    counter_evidence_questions = goal.get("counter_evidence_questions") or []
    if not isinstance(counter_evidence_questions, list) or not all(
        isinstance(item, str) and item.strip()
        for item in counter_evidence_questions
    ):
        raise ValueError(
            "goal.counter_evidence_questions must be a list of text questions"
        )
    question_dimensions = goal.get("question_dimensions") or []
    if not isinstance(question_dimensions, list) or not all(
        isinstance(item, str) and item.strip() for item in question_dimensions
    ):
        raise ValueError("goal.question_dimensions must be a list of text values")
    requested_dimensions = goal.get("requested_dimensions") or question_dimensions
    if not isinstance(requested_dimensions, list) or not all(
        isinstance(item, str) and item.strip() for item in requested_dimensions
    ):
        raise ValueError("goal.requested_dimensions must be a list of text values")
    sources = []
    for pack, title, rule_file, quote_file in zip(
        all_packs,
        all_titles,
        rules,
        quotes,
    ):
        sources.append(
            {
                "pack": pack,
                "title": title,
                "role": "counter" if pack in comparison_packs else "support",
                "rule_file": rule_file,
                "quote_index_file": quote_file,
            }
        )
    scope_requirement = route.get("scope_requirement")
    scope_compatible = True
    if isinstance(scope_requirement, dict) and scope_requirement.get(
        "calculation_object"
    ):
        scope_compatible = (
            str(goal.get("calculation_object") or "")
            == str(scope_requirement["calculation_object"])
        )
    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "system": plan_system,
        "subsystem": route.get("subsystem"),
        "registry_route": registry_route,
        "provider_identity": {
            "provider_id": str(identity.get("provider_id")),
            "provider_version": str(identity.get("provider_version")),
        },
        "compatible_rule_systems": list(
            route.get("compatible_rule_systems") or (plan_system,)
        ),
        "requested_resolution": str(goal.get("requested_resolution") or ""),
        "evidence_questions": list(evidence_questions),
        "counter_evidence_questions": list(counter_evidence_questions),
        "requested_dimensions": list(requested_dimensions),
        "question_dimensions": list(question_dimensions),
        "required_packs": packs,
        "required_book_titles": _book_titles(packs),
        "comparison_packs": comparison_packs,
        "comparison_book_titles": _book_titles(comparison_packs),
        "runtime_source_family": runtime_source_family,
        "required_rule_files": rules,
        "required_quote_indexes": quotes,
        "sources": sources,
        "fact_ids": _fact_ids(facts or {}),
        "decision_layers": list(route["layers"]),
        "chart_contract": copy.deepcopy(dict(route["chart"])),
        "fact_status": (
            ((facts or {}).get("chart_facts") or {}).get("fact_layer_status")
            if isinstance((facts or {}).get("chart_facts"), dict)
            else (facts or {}).get("fact_layer_status")
        ),
        "calculation_object": str(goal.get("calculation_object") or ""),
        "scope_compatible": scope_compatible,
        "goal_digest": hashlib.sha256(
            json.dumps(
                goal,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "source_caveats": [
            "A D2-ready pack is textual evidence, not empirical validation.",
            "Only current reads after the current fact layer authorize interpretation.",
        ],
    }
    if route.get("allowed_evidence_roles") is not None:
        plan["allowed_evidence_roles"] = list(route["allowed_evidence_roles"])
    if route.get("semantic_term_projections"):
        plan["semantic_term_projections"] = copy.deepcopy(
            list(route["semantic_term_projections"])
        )

    if extend is not None:
        extend(plan, facts)

    conditions = _compile_applicability_conditions(facts or {}, plan)
    conditions.extend(plan.pop("extension_applicability_conditions", []) or [])
    plan["applicability_conditions"] = conditions
    canonical_json = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    plan["plan_digest"] = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return plan


_PROVIDER_ADAPTER_CACHE: dict[str, Any] = {}


def _provider_adapter(route_id: str) -> Any:
    cached = _PROVIDER_ADAPTER_CACHE.get(route_id)
    if cached is not None:
        return cached
    from reading_engine.catalog import CatalogLoader
    from reading_engine.provider_registry import ProviderRegistry

    catalog = CatalogLoader(ROOT / "resources/runtime").load()
    registry = ProviderRegistry(
        catalog,
        skill_root=ROOT,
        construction={"skill_dir": ROOT},
    )
    adapter = registry.instantiate(catalog.descriptor(route_id))
    _PROVIDER_ADAPTER_CACHE[route_id] = adapter
    return adapter


def compile_source_plan(
    system: str,
    goal: dict[str, Any],
    facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Delegate to the catalog-selected provider; the compiler stays generic."""

    route_id = str(system or "").strip().lower()
    adapter = _provider_adapter(route_id)
    return adapter.source_plan(goal, facts)


def _read_json(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", required=True)
    parser.add_argument("--goal-file", required=True)
    parser.add_argument("--facts-file")
    parser.add_argument("--output")
    args = parser.parse_args()

    goal = _read_json(args.goal_file)
    if goal is None:
        parser.error("--goal-file must contain an object")
    plan = compile_source_plan(args.system, goal, _read_json(args.facts_file))
    rendered = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
