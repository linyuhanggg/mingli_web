#!/usr/bin/env python3
"""Canonical digests and applicability bindings shared by Mingli evidence gates."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


def canonical_digest(value: Any) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def facts_digest_payload(facts: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable fact projection used by evidence bindings.

    Mechanism bridges are interpretation-layer attestations added after source
    retrieval. Excluding that one field avoids a self-referential digest while
    keeping every calculated fact, calendar value, and claim contract field
    bound to the evidence.
    """

    projected = copy.deepcopy(facts)
    contract = projected.get("public_claim_contract")
    if isinstance(contract, dict):
        contract.pop("mechanism_bridges", None)
    return projected


def canonical_facts_digest(facts: dict[str, Any]) -> str:
    return canonical_digest(facts_digest_payload(facts))


def applicability_condition_index(
    evidence_bundle: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(evidence_bundle, dict):
        return {}
    conditions = evidence_bundle.get("applicability_conditions")
    if not isinstance(conditions, list):
        return {}
    return {
        item["id"]: item
        for item in conditions
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item["id"]
    }
