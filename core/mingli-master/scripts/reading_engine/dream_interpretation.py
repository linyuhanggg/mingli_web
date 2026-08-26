"""《玉匣记》占梦 lookup. Empty table is fail-closed. Not catalogued."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


_CORE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _CORE_ROOT.parents[1]
_RULES_PATH = _CORE_ROOT / "references" / "matrices" / "dream-interpretation-source-rules-v1.yaml"
_INPUT_SCHEMA_PATH = (
    _REPO_ROOT
    / "contracts"
    / "schemas"
    / "inputs"
    / "dream-interpretation-input-v1.schema.json"
)

_LIMITATION = (
    "v1 只做玉匣记占梦查找；当前版本查找表为空，不输出周公网典、模型文案或吉凶。"
)
_EMPTY_TABLE_GAP = "current yuqia-ji fulltext has no 占梦 omen table"
_FRONT_MATTER_RULE_ID = "dream-interpretation/yuqia-ji#DI-YQ-01"
_GAP_RULE_ID = "dream-interpretation/yuqia-ji#DI-YQ-02"
_LOOKUP_RULE_ID = "dream-interpretation/yuqia-ji#DI-YQ-03"
_SOURCE_PACK = "selection/yuqia-ji"
_SOURCE_DEPENDENCY_ID = "dream.yuqia-zhanmeng"
_FRONT_MATTER_TOKENS = frozenset({"占夢", "占梦"})


class DreamInterpretationProvider:
    """Exact omen-token lookup. Current recension lookup is empty."""

    provider_id = "mingli-master.dream-interpretation.v1"
    provider_version = "yuqia-ji-zhanmeng-lookup-v1"

    def __init__(self, skill_dir: str | Path | None = None) -> None:
        self.skill_dir = Path(skill_dir).resolve() if skill_dir else _CORE_ROOT
        rules_path = (
            self.skill_dir
            / "references"
            / "matrices"
            / "dream-interpretation-source-rules-v1.yaml"
        )
        if not rules_path.is_file():
            rules_path = _RULES_PATH
        self._rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        input_schema = json.loads(_INPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self._input_validator = Draft202012Validator(input_schema)
        self._rule_meta: dict[str, tuple[str, str]] = {}
        self._lookup: dict[str, tuple[str, str, str]] = {}
        for rule in self._rules.get("rules") or []:
            rule_id = str(rule["id"])
            anchor = str(rule.get("source_anchor") or "")
            excerpt = str(rule.get("exact_excerpt") or "")
            self._rule_meta[rule_id] = (anchor, excerpt)
            mapping = rule.get("lookup") or {}
            for key, value in mapping.items():
                row = value if isinstance(value, str) and value else excerpt
                self._lookup[str(key)] = (rule_id, str(row), anchor)
        for key, value in dict(self._rules.get("lookup") or {}).items():
            if str(key) in self._lookup:
                continue
            self._lookup[str(key)] = (
                _LOOKUP_RULE_ID,
                str(value),
                self._rule_meta.get(_LOOKUP_RULE_ID, ("fulltext.md#L12", ""))[0],
            )

    def project(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._input_validator.validate(dict(payload))
        except ValidationError as error:
            raise ValueError(error.message) from error

        dream_text = str(payload["dream_text"])
        omen_key = payload.get("omen_key")
        subject_ref = payload.get("subject_ref") or f"dream:{omen_key or dream_text[:16]}"
        lookup_key = omen_key if isinstance(omen_key, str) and omen_key else None
        hit = self._lookup.get(lookup_key) if lookup_key else None

        if hit is not None:
            rule_id, excerpt, anchor = hit
            return self._view(
                dream_text=dream_text,
                omen_key=omen_key,
                subject_ref=subject_ref,
                omen_match={
                    "lookup_key": lookup_key,
                    "match_status": "exact",
                    "source_rule_id": rule_id,
                    "source_excerpt": excerpt,
                },
                source_rule_id=rule_id,
                source_anchor=anchor,
                source_status="exact_rule_bound",
            )

        if (
            (isinstance(omen_key, str) and omen_key in _FRONT_MATTER_TOKENS)
            or dream_text in _FRONT_MATTER_TOKENS
        ):
            rule_id = _FRONT_MATTER_RULE_ID
        else:
            rule_id = _LOOKUP_RULE_ID
        anchor, _excerpt = self._rule_meta.get(rule_id, ("fulltext.md#L12", ""))
        return self._view(
            dream_text=dream_text,
            omen_key=omen_key,
            subject_ref=subject_ref,
            omen_match=None,
            source_rule_id=rule_id,
            source_anchor=anchor,
            source_status="unmatched",
        )

    def _view(
        self,
        *,
        dream_text: str,
        omen_key: str | None,
        subject_ref: str,
        omen_match: dict[str, Any] | None,
        source_rule_id: str,
        source_anchor: str,
        source_status: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": "dream-interpretation-view/v1",
            "subject_ref": subject_ref,
            "normalized": {
                "dream_text": dream_text,
                "omen_key": omen_key,
                "script": "hanzi",
            },
            "omen_match": omen_match,
            "source_identity": {
                "source_pack": _SOURCE_PACK,
                "source_dependency_id": _SOURCE_DEPENDENCY_ID,
                "source_rule_id": source_rule_id,
                "source_anchor": source_anchor,
            },
            "active_source_rule_ids": [
                _FRONT_MATTER_RULE_ID,
                _GAP_RULE_ID,
                _LOOKUP_RULE_ID,
            ],
            "source_dependency_ids": [_SOURCE_DEPENDENCY_ID],
            "source_status": source_status,
            "source_gaps": [_EMPTY_TABLE_GAP],
            "limitations": [_LIMITATION],
            "hard_verdict": None,
        }
