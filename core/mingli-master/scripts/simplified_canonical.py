"""Project-owned simplified-text canonical for classical source derivatives.

OpenCC's Apache-2.0 ``t2s`` configuration is the public foundation.  The
small project layer is loaded from a provenance-bearing manifest; it must not
be inferred from a legacy converter or from migration output differences.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "references/matrices/simplified-canonical-v1.json"
SCHEMA_VERSION = "mingli-simplified-canonical-v1"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported simplified canonical schema")
    if payload.get("canonical_id") != "mingli-product-simplified-v1":
        raise ValueError("unexpected simplified canonical identity")
    foundation = payload.get("foundation")
    if not isinstance(foundation, dict) or foundation != {
        "distribution": "OpenCC",
        "version": "1.4.2",
        "config": "t2s",
        "license": "Apache-2.0",
        "upstream": "https://github.com/BYVoid/OpenCC/tree/ver.1.4.2",
    }:
        raise ValueError("simplified canonical foundation drift")
    if payload.get("operation_order") != [
        "opencc:t2s_to_fixed_point",
        "project_editorial_rules",
    ]:
        raise ValueError("simplified canonical operation order drift")
    acceptance = payload.get("passage_acceptance")
    if not isinstance(acceptance, dict) or acceptance != {
        "minimum_normalized_characters": 3,
        "quoted_two_character_passages": (
            "accept_if_raw_contains_classical_quote_delimiter"
        ),
        "classical_quote_delimiters": ["「", "」", "『", "』"],
        "decision_ref": "Raft #mingli-dev task #22",
        "rationale": (
            "Release 5.1 contains seven real two-character quoted passages. "
            "Their classical quote delimiters are raw structural evidence, so "
            "they remain accepted after punctuation removal without depending "
            "on a legacy converter's punctuation output."
        ),
    }:
        raise ValueError("simplified canonical passage acceptance drift")
    rules = payload.get("editorial_rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("simplified canonical editorial rules are empty")
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("invalid simplified canonical editorial rule")
        rule_id = rule.get("id")
        source = rule.get("source")
        target = rule.get("target")
        if (
            not isinstance(rule_id, str)
            or not rule_id
            or rule_id in seen_ids
            or not isinstance(source, str)
            or not source
            or source in seen_sources
            or not isinstance(target, str)
            or not target
            or rule.get("scope") != "global"
            or not isinstance(rule.get("decision_ref"), str)
            or not rule["decision_ref"]
            or not isinstance(rule.get("rationale"), str)
            or not rule["rationale"]
            or not isinstance(rule.get("evidence"), list)
            or not rule["evidence"]
        ):
            raise ValueError(f"invalid simplified canonical editorial rule: {rule_id}")
        seen_ids.add(rule_id)
        seen_sources.add(source)
    return payload


@lru_cache(maxsize=1)
def _converter() -> Any:
    foundation = _load_config()["foundation"]
    try:
        installed = version(str(foundation["distribution"]))
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "缺少 OpenCC==1.4.2；产品简体 canonical 无法确定性执行"
        ) from exc
    if installed != foundation["version"]:
        raise RuntimeError(
            "OpenCC 版本不匹配："
            f"需要 {foundation['version']}，实际 {installed}"
        )
    from opencc import OpenCC

    return OpenCC(str(foundation["config"]))


def canonicalize(text: str) -> str:
    """Return the deterministic product simplified derivative of ``text``."""

    if not isinstance(text, str):
        raise TypeError("canonicalize expects text")
    rendered = text
    while True:
        converted = _converter().convert(rendered)
        if converted == rendered:
            break
        rendered = converted
    for rule in _load_config()["editorial_rules"]:
        rendered = rendered.replace(str(rule["source"]), str(rule["target"]))
    return rendered


def canonical_metadata() -> dict[str, Any]:
    """Return the stable identity needed by builders and audit reports."""

    payload = _load_config()
    return {
        "canonical_id": payload["canonical_id"],
        "foundation": dict(payload["foundation"]),
        "operation_order": list(payload["operation_order"]),
        "passage_acceptance": dict(payload["passage_acceptance"]),
        "editorial_rules": [
            {
                "id": rule["id"],
                "source": rule["source"],
                "target": rule["target"],
                "scope": rule["scope"],
                "decision_ref": rule["decision_ref"],
            }
            for rule in payload["editorial_rules"]
        ],
    }


def passage_is_accepted(raw_text: str, normalized_text: str) -> bool:
    """Apply the source-authored release 5.1 passage acceptance contract."""

    if not isinstance(raw_text, str) or not isinstance(normalized_text, str):
        raise TypeError("passage acceptance expects text")
    acceptance = _load_config()["passage_acceptance"]
    minimum = int(acceptance["minimum_normalized_characters"])
    if len(normalized_text) >= minimum:
        return True
    return len(normalized_text) == 2 and any(
        delimiter in raw_text
        for delimiter in acceptance["classical_quote_delimiters"]
    )


__all__ = [
    "CONFIG_PATH",
    "canonical_metadata",
    "canonicalize",
    "passage_is_accepted",
]
