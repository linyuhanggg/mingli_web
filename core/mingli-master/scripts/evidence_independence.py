#!/usr/bin/env python3
"""Conservative accounting for independent classical source lineages."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from reading_engine.contracts import EvidenceNode, SourceRelationship


REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "inference"
    / "source-lineages-v1.json"
)
SCHEMA_VERSION = "mingli-source-lineages-v1"


@lru_cache(maxsize=1)
def _registry() -> dict[str, Any]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported source-lineage registry")
    packs = payload.get("packs")
    if not isinstance(packs, dict) or not packs:
        raise ValueError("source-lineage registry has no packs")
    for pack, entry in packs.items():
        if not isinstance(pack, str) or not pack:
            raise ValueError("source-lineage registry has an invalid pack")
        if not isinstance(entry, dict) or not isinstance(entry.get("lineage"), str):
            raise ValueError(f"source-lineage registry has an invalid entry: {pack}")
        if not isinstance(entry.get("counts_for_interpretive_independence"), bool):
            raise ValueError(f"source-lineage registry has no independence policy: {pack}")
    return payload


def source_profile(pack: str) -> dict[str, Any]:
    entry = (_registry().get("packs") or {}).get(str(pack or ""))
    if not isinstance(entry, dict):
        raise ValueError(f"unregistered source pack: {pack}")
    return dict(entry)


def source_lineage(pack: str) -> str:
    return str(source_profile(pack)["lineage"])


def independent_lineages(source_refs: list[dict[str, Any]]) -> set[str]:
    lineages: set[str] = set()
    for source in source_refs:
        if not isinstance(source, dict) or not isinstance(source.get("pack"), str):
            raise ValueError("source reference requires a pack")
        profile = source_profile(source["pack"])
        if profile["counts_for_interpretive_independence"]:
            lineages.add(str(profile["lineage"]))
    return lineages


def source_relationships(
    evidence: tuple[EvidenceNode, ...],
    counter_evidence: tuple[EvidenceNode, ...] = (),
) -> tuple[SourceRelationship, ...]:
    """Describe provenance relationships without turning counts into confidence."""

    relationships: list[SourceRelationship] = []

    def profile(node: EvidenceNode) -> dict[str, Any] | None:
        if "#" not in node.rule_id:
            return None
        try:
            return source_profile(node.rule_id.split("#", 1)[0])
        except ValueError:
            return None
    supporting = list(evidence)
    counters = list(counter_evidence)
    same_side_pairs = [
        *(
            (supporting[left], supporting[right])
            for left in range(len(supporting))
            for right in range(left + 1, len(supporting))
        ),
        *(
            (counters[left], counters[right])
            for left in range(len(counters))
            for right in range(left + 1, len(counters))
        ),
    ]
    for left, right in same_side_pairs:
        if left.lineage == right.lineage:
            relation = "derived"
        elif (
            profile(left) is not None
            and profile(right) is not None
            and (
                not profile(left)["counts_for_interpretive_independence"]
                or not profile(right)["counts_for_interpretive_independence"]
            )
        ):
            relation = "parallel"
        elif (
            not left.lineage
            or not right.lineage
            or left.lineage.startswith("unregistered:")
            or right.lineage.startswith("unregistered:")
        ):
            relation = "parallel"
        else:
            relation = "independent"
        relationships.append(
            SourceRelationship(left.rule_id, right.rule_id, relation)
        )
    for left in supporting:
        for right in counters:
            relationships.append(
                SourceRelationship(left.rule_id, right.rule_id, "conflict")
            )
    return tuple(relationships)


__all__ = [
    "independent_lineages",
    "source_lineage",
    "source_profile",
    "source_relationships",
]
