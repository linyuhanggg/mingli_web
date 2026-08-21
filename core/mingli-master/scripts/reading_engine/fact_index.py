"""Stable JSON-pointer fact references for deterministic calculation output."""

from __future__ import annotations

from typing import Any, Iterator

from .contracts import CalculationResult, FactRef, canonical_digest


def _escape_pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict) and value:
        for key in sorted(value, key=str):
            token = _escape_pointer_token(str(key))
            yield from _leaves(value[key], f"{path}/{token}")
        return
    if isinstance(value, (list, tuple)) and value:
        for index, item in enumerate(value):
            yield from _leaves(item, f"{path}/{index}")
        return
    yield path or "/", value


def _selection_index_payload(calculation: CalculationResult) -> dict[str, Any]:
    chart = calculation.facts.get("chart_facts")
    if not isinstance(chart, dict):
        chart = {}
    output = chart.get("output") if isinstance(chart.get("output"), dict) else {}
    day_rows = []
    for raw in output.get("calendar_candidates") or ():
        if not isinstance(raw, dict):
            continue
        calendar = raw.get("calendar") if isinstance(raw.get("calendar"), dict) else {}
        day_rows.append(
            {
                "candidate_id": raw.get("candidate_id"),
                "civil_date": raw.get("civil_date"),
                "calendar": {
                    "lunar_date": calendar.get("lunar_date"),
                    "ganzhi": calendar.get("ganzhi"),
                    "calendar_digest": calendar.get("calendar_digest"),
                    "boundary_status": calendar.get("boundary_status"),
                    "month_boundary_jie": calendar.get("month_boundary_jie"),
                },
                "jianchu": raw.get("jianchu"),
                "mansion": raw.get("mansion"),
                "day_path": raw.get("day_path"),
                "participant_scope": raw.get("participant_scope"),
                "eligibility": raw.get("eligibility"),
                "rejection_reasons": raw.get("rejection_reasons"),
                "ranking_components": raw.get("ranking_components"),
                "best_candidate_time_id": (
                    (raw.get("best_date_time_basis") or {}).get("candidate_time_id")
                    if isinstance(raw.get("best_date_time_basis"), dict)
                    else None
                ),
                "active_source_rule_ids": raw.get("active_source_rule_ids") or [],
            }
        )
    time_rows = [
        raw["best_date_time_basis"]
        for raw in output.get("calendar_candidates") or ()
        if isinstance(raw, dict) and isinstance(raw.get("best_date_time_basis"), dict)
    ]
    ranking = output.get("ranking") if isinstance(output.get("ranking"), dict) else {}
    compact_chart = {
        "system": chart.get("system"),
        "fact_layer_status": chart.get("fact_layer_status"),
        "adapter": chart.get("adapter"),
        "input": chart.get("input"),
        "calendar_normalization": chart.get("calendar_normalization"),
        "output": {
            "event_profile": output.get("event_profile"),
            "calendar_candidates": day_rows,
            "date_time_candidates": time_rows,
            "eligible_candidates": list(ranking.get("eligible_candidate_ids") or []),
            "eligible_date_time_candidates": list(
                ranking.get("eligible_date_time_candidate_ids") or []
            ),
            "eliminations": output.get("eliminations") or [],
            "no_valid_candidate": output.get("no_valid_candidate"),
            "ranking": ranking,
            "lineage_policy": output.get("lineage_policy") or {},
        },
        "fact_digest": chart.get("fact_digest"),
    }
    indexed = {
        "chart_digest": calculation.facts.get("chart_digest"),
        "fact_digest": calculation.facts.get("fact_digest"),
        "calendar_digest": calculation.facts.get("calendar_digest"),
        "chart_facts": compact_chart,
    }
    if calculation.fact_extension is not None:
        indexed["fact_extensions"] = calculation.fact_extension.to_dict()
    return indexed


def indexed_fact_payload(calculation: CalculationResult) -> dict[str, Any]:
    if calculation.system == "selection":
        return _selection_index_payload(calculation)
    if calculation.system == "physiognomy":
        from . import physiognomy

        chart = calculation.facts.get("chart_facts")
        if not isinstance(chart, dict):
            raise ValueError("Physiognomy calculation is missing its fact layer")
        return {"chart_facts": physiognomy.indexed_fact_payload(chart)}
    if calculation.system == "liuyao":
        from . import liuyao

        indexed = calculation.indexed_facts()
        chart = indexed.get("chart_facts")
        if not isinstance(chart, dict):
            raise ValueError("Liuyao calculation is missing its fact layer")
        indexed["chart_facts"] = liuyao.public_projection(chart)
        return indexed
    if calculation.system == "fengshui":
        from . import fengshui

        indexed = calculation.indexed_facts()
        chart = indexed.get("chart_facts")
        if not isinstance(chart, dict):
            raise ValueError("Fengshui calculation is missing its fact layer")
        return fengshui.public_projection(indexed)
    return calculation.indexed_facts()


def build_fact_index(
    calculation: CalculationResult,
    *,
    reading_id: str,
    version: int,
) -> tuple[FactRef, ...]:
    """Flatten exact provider output without generating explanatory prose."""

    if not isinstance(calculation, CalculationResult):
        raise TypeError("calculation must be a CalculationResult")
    indexed = indexed_fact_payload(calculation)
    return tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id=calculation.provider_id,
            provider_version=calculation.provider_version,
            reading_id=reading_id,
            version=version,
        )
        for path, value in _leaves(indexed)
    )


def fact_index_digest(facts: tuple[FactRef, ...]) -> str:
    return canonical_digest(
        [
            {
                "fact_id": item.fact_id,
                "path": item.path,
                "value": item.value,
                "provider_id": item.provider_id,
                "provider_version": item.provider_version,
                "reading_id": item.reading_id,
                "version": item.version,
            }
            for item in facts
        ]
    )


def retrieval_values(facts: tuple[FactRef, ...], *, limit: int = 96) -> list[str]:
    """Return bounded factual values suitable for corpus retrieval."""

    values: list[str] = []
    for item in facts:
        if isinstance(item.value, (str, int, float, bool)):
            text = str(item.value).strip()
            if text and text not in values:
                values.append(text)
        if len(values) >= limit:
            break
    return values


__all__ = [
    "build_fact_index",
    "fact_index_digest",
    "indexed_fact_payload",
    "retrieval_values",
]
