"""Retain-disagreement 合参裁决. Not catalogued; not a fusion engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


_CORE_ROOT = Path(__file__).resolve().parents[2]
_RULES_PATH = (
    _CORE_ROOT / "references" / "matrices" / "cross-art-synthesis-source-rules-v1.yaml"
)

_LIMITATION = "v1 只输出比较行，不输出平均吉凶、选边赢家或硬裁定。"
_SCOPE_GAP = "dimension_fact_scope is not 互证"
_SLOGAN_GAP = "理无二致 is compilation slogan"
_SCOPE_NAME_GAP = "provider scope names are not 分歧"
_GX_RULE_ID = "cross-art-synthesis/guotian-jing#CAS-GX-01"
_ZW_RULE_ID = "cross-art-synthesis/ziwei-doushu-quanshu#CAS-ZW-01"
_HZ_RULE_ID = "cross-art-synthesis/huozhu-lin#CAS-HZ-01"
_BS_RULE_ID = "cross-art-synthesis/bushi-zhengzong#CAS-BS-01"
_ACTIVE_RULE_IDS = (_GX_RULE_ID, _ZW_RULE_ID, _HZ_RULE_ID, _BS_RULE_ID)
_SOURCE_DEPENDENCY_ID = "cross-art.retain-disagreement"
_FUSION_SLOGANS = frozenset({"理无二致", "归一理"})
_FORBIDDEN_KEYS = frozenset(
    {
        "fused_score",
        "winner",
        "arbitration",
        "weighted_average",
        "luck",
        "verdict",
        "llm",
        "hard_verdict",
        "forced_resolution",
    }
)
_PRODUCT_ARTS = {
    "hecan": frozenset({"bazi", "ziwei", "qizheng"}),
    "canwen": frozenset({"bazi", "ziwei", "qizheng"}),
    "wenshi": frozenset({"liuyao", "qimen", "daliuren"}),
}
_REQUIRED_INPUT = (
    "product_id",
    "selected_art_ids",
    "dimension_id",
    "present_art_ids",
)
_OPTIONAL_INPUT = frozenset(
    {
        "schema_version",
        "subject_ref",
        "scope_names",
        "art_signals",
        "region_label",
        "lookup_key",
    }
)


def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item)
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


class CrossArtSynthesisProvider:
    """Compare per-art predicates. Never average, pick a winner, or invent arts."""

    provider_id = "mingli-master.cross-art-synthesis.v1"
    provider_version = "retain-disagreement-no-fusion-v1"

    def __init__(self, skill_dir: str | Path | None = None) -> None:
        self.skill_dir = Path(skill_dir).resolve() if skill_dir else _CORE_ROOT
        rules_path = (
            self.skill_dir
            / "references"
            / "matrices"
            / "cross-art-synthesis-source-rules-v1.yaml"
        )
        if not rules_path.is_file():
            rules_path = _RULES_PATH
        self._anchors: dict[str, str] = {}
        if not rules_path.is_file():
            return
        try:
            import yaml
        except ImportError:
            return
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        lookup: dict[str, str] = dict(rules.get("lookup") or {})
        for rule in rules.get("rules") or []:
            lookup.update(rule.get("lookup") or {})
        if lookup:
            raise ValueError("cross-art synthesis luck lookup must stay empty")
        self._anchors = {
            str(rule["id"]): str(rule.get("source_anchor") or "")
            for rule in rules.get("rules") or []
        }

    def project(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        data = dict(payload)
        extra = set(data) - set(_REQUIRED_INPUT) - _OPTIONAL_INPUT
        forbidden = extra & _FORBIDDEN_KEYS
        if forbidden:
            raise ValueError(f"fusion fields are not allowed: {sorted(forbidden)}")
        if extra:
            raise ValueError(f"unexpected input fields: {sorted(extra)}")
        missing = [key for key in _REQUIRED_INPUT if key not in data]
        if missing:
            raise ValueError(f"missing input fields: {missing}")

        product_id = str(data["product_id"])
        allowed = _PRODUCT_ARTS.get(product_id)
        if allowed is None:
            raise ValueError(f"unsupported product_id: {product_id}")
        selected = _as_text_list(data["selected_art_ids"])
        present = _as_text_list(data["present_art_ids"])
        if len(selected) < 2 or len(selected) > 3:
            raise ValueError("selected_art_ids must contain 2 or 3 arts")
        if not set(selected) <= allowed:
            raise ValueError("selected_art_ids are not valid for this product")
        if not set(present) <= set(selected):
            raise ValueError("present_art_ids must be a subset of selected_art_ids")

        dimension_id = str(data["dimension_id"])
        if not dimension_id:
            raise ValueError("dimension_id must be non-empty")
        missing_arts = [art for art in selected if art not in set(present)]
        region_label = data.get("region_label")
        slogan = str(region_label) if isinstance(region_label, str) else ""
        art_signals = data.get("art_signals") or {}
        if art_signals and not isinstance(art_signals, Mapping):
            raise ValueError("art_signals must be an object")
        scope_names = data.get("scope_names") or {}

        if slogan in _FUSION_SLOGANS:
            source_rule_id = _BS_RULE_ID
            source_status = "unmatched"
            convergence: list[dict[str, Any]] = []
            disagreements: list[dict[str, Any]] = []
        else:
            source_status = "exact_rule_bound"
            convergence, disagreements = self._compare(
                selected=selected,
                present=present,
                dimension_id=dimension_id,
                art_signals=dict(art_signals) if isinstance(art_signals, Mapping) else {},
            )
            if scope_names and not convergence and not disagreements:
                source_rule_id = _ZW_RULE_ID if product_id != "wenshi" else _HZ_RULE_ID
            elif product_id == "wenshi":
                source_rule_id = _HZ_RULE_ID
            else:
                source_rule_id = _GX_RULE_ID

        present_count = len(present)
        if present_count < 2:
            status = "insufficient_for_corroboration"
            if not disagreements:
                disagreements = [
                    self._row(
                        arts=present or selected[:1],
                        kind="insufficient_arts",
                        display_text="在场术数不足两门，不能作互证",
                        fact_refs=[],
                        source_rule_id=source_rule_id,
                    )
                ]
        elif missing_arts:
            status = "partial"
        else:
            status = "all_selected_present"

        pack, default_anchor = self._identity(product_id, source_rule_id)
        subject_ref = data.get("subject_ref") or f"cross-art:{product_id}:{dimension_id}"
        view = {
            "schema_version": "cross-art-synthesis-view/v1",
            "product_id": product_id,
            "subject_ref": str(subject_ref),
            "dimension_id": dimension_id,
            "selected_art_ids": selected,
            "present_art_ids": present,
            "missing_art_ids": missing_arts,
            "convergence": convergence,
            "disagreements": disagreements,
            "evidence_sufficiency": {
                "present_count": present_count,
                "missing_art_ids": missing_arts,
                "status": status,
            },
            "source_identity": {
                "source_pack": pack,
                "source_dependency_id": _SOURCE_DEPENDENCY_ID,
                "source_rule_id": source_rule_id,
                "source_anchor": self._anchors.get(source_rule_id) or default_anchor,
            },
            "active_source_rule_ids": list(_ACTIVE_RULE_IDS),
            "source_dependency_ids": [_SOURCE_DEPENDENCY_ID],
            "source_status": source_status,
            "source_gaps": [_SCOPE_GAP, _SLOGAN_GAP, _SCOPE_NAME_GAP],
            "limitations": [_LIMITATION],
            "forced_resolution": False,
            "hard_verdict": None,
        }
        dumped = json.dumps(view, ensure_ascii=False)
        if any(key in dumped for key in ("fused_score", "winner", "weighted_average")):
            raise ValueError("fusion fields leaked into synthesis view")
        return view

    def _identity(self, product_id: str, source_rule_id: str) -> tuple[str, str]:
        if source_rule_id == _BS_RULE_ID:
            return "divination/bushi-zhengzong", "fulltext.md#L1872"
        if source_rule_id == _ZW_RULE_ID:
            return "ziwei/ziwei-doushu-quanshu", "fulltext.md#L952"
        if product_id == "wenshi" or source_rule_id == _HZ_RULE_ID:
            return "divination/huozhu-lin", "fulltext.md#L23"
        return "xingming/guotian-jing", "fulltext.md#L1530"

    def _compare(
        self,
        *,
        selected: list[str],
        present: list[str],
        dimension_id: str,
        art_signals: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        grouped: dict[str, list[tuple[str, str, list[str], list[str]]]] = {}
        for art in selected:
            if art not in present:
                continue
            raw = art_signals.get(art)
            if not isinstance(raw, Mapping):
                continue
            predicate_id = str(raw.get("predicate_id") or raw.get("signal_id") or "")
            value = raw.get("value")
            if not predicate_id or value is None or value == "":
                continue
            fact_refs = _as_text_list(raw.get("fact_refs"))
            signal_ids = _as_text_list(raw.get("signal_ids"))
            grouped.setdefault(predicate_id, []).append(
                (art, str(value), fact_refs, signal_ids)
            )

        convergence: list[dict[str, Any]] = []
        disagreements: list[dict[str, Any]] = []
        for _predicate, rows in grouped.items():
            if len(rows) < 2:
                continue
            arts = [item[0] for item in rows]
            values = {item[1] for item in rows}
            fact_refs: list[str] = []
            signal_ids: list[str] = []
            for _art, _value, refs, ids in rows:
                for ref in refs:
                    if ref not in fact_refs:
                        fact_refs.append(ref)
                for signal_id in ids:
                    if signal_id not in signal_ids:
                        signal_ids.append(signal_id)
            if not fact_refs:
                fact_refs = [f"fact:cross-art/{art}/{dimension_id}" for art in arts]
            if len(values) == 1:
                row = self._row(
                    arts=arts,
                    kind="source_bound_corroboration",
                    display_text=f"{len(arts)}术对 {dimension_id} 来源谓词一致，仅作印证，不作融合结论",
                    fact_refs=fact_refs,
                    source_rule_id=_GX_RULE_ID if arts[0] in {"bazi", "ziwei", "qizheng"} else _HZ_RULE_ID,
                    signal_ids=signal_ids or None,
                )
                convergence.append(row)
            else:
                row = self._row(
                    arts=arts,
                    kind="source_disagreement_retained",
                    display_text=f"{len(arts)}术对 {dimension_id} 来源谓词不一致，分歧保留",
                    fact_refs=fact_refs,
                    source_rule_id=_GX_RULE_ID if arts[0] in {"bazi", "ziwei", "qizheng"} else _HZ_RULE_ID,
                    signal_ids=signal_ids or None,
                )
                disagreements.append(row)
        return convergence, disagreements

    def _row(
        self,
        *,
        arts: list[str],
        kind: str,
        display_text: str,
        fact_refs: list[str],
        source_rule_id: str,
        signal_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "arts": arts,
            "kind": kind,
            "display_text": display_text,
            "fact_refs": fact_refs,
            "source_rule_id": source_rule_id,
        }
        if signal_ids:
            row["signal_ids"] = signal_ids
        return row
