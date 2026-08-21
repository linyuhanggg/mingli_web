#!/usr/bin/env python3
"""Resolve the shared public-reading contract for a system and query."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "global-public-reading-contract-v1"
CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "matrices" / "public-reading-contract.yaml"
REQUIRED_SYSTEM_FIELDS = {
    "display_basis",
    "current_event_resolution",
    "location_resolution",
    "direct_scope",
}


@lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    payload = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid public reading contract schema")
    defaults = payload.get("defaults")
    systems = payload.get("systems")
    if not isinstance(defaults, dict) or not isinstance(systems, dict):
        raise ValueError("invalid public reading contract sections")
    for system, profile in systems.items():
        if not isinstance(profile, dict) or not REQUIRED_SYSTEM_FIELDS.issubset(profile):
            raise ValueError(f"invalid public reading contract system: {system}")
    return payload


def available_systems() -> set[str]:
    return set(load_contract()["systems"])


def canonical_system(system: str) -> str:
    contract = load_contract()
    aliases = contract.get("aliases") or {}
    canonical = aliases.get(system, system)
    if canonical not in contract["systems"]:
        raise ValueError(f"unsupported public reading system: {system}")
    return str(canonical)


def _question_shapes(query: str) -> list[str]:
    shapes: list[str] = []
    for name, rule in (load_contract().get("question_shapes") or {}).items():
        patterns = rule.get("patterns") if isinstance(rule, dict) else []
        if any(str(pattern) in query for pattern in patterns or []):
            shapes.append(str(name))
    return shapes


def compile_answer_profile(system: str, query: str, *, subsystem: str | None = None) -> dict[str, Any]:
    """Return the display and directness rules without interpreting facts."""

    contract = load_contract()
    canonical = canonical_system(system)
    profile: dict[str, Any] = deepcopy(contract["defaults"])
    profile.update(deepcopy(contract["systems"][canonical]))
    shapes = _question_shapes(query)
    axes = list(profile.get("required_detail_axes") or [])
    for shape in shapes:
        shape_rule = (contract.get("question_shapes") or {}).get(shape) or {}
        for axis in shape_rule.get("required_detail_axes") or []:
            if axis not in axes:
                axes.append(axis)
        if shape_rule.get("followup_mode"):
            profile["followup_mode"] = shape_rule["followup_mode"]

    profile.update({
        "schema_version": SCHEMA_VERSION,
        "system": canonical,
        "subsystem": subsystem,
        "question_shapes": shapes,
        "required_detail_axes": axes,
        "category_taboo": bool(profile.get("category_taboo", False)),
    })
    if profile["category_taboo"]:
        raise ValueError("public reading contract must not declare a category taboo")
    return profile
