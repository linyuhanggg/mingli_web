from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from app.charts.contracts import BaziChartV1, ZiweiChartV1
from app.readings.public_fact_panel import project_public_fact_panel
from app.readings.runtime_contracts import ReadingBrief

_CALCULATED_FACT_REF = re.compile(
    r"/calculated/(?P<capability>bazi|ziwei)/(?P<field_id>[^/]+)$"
)
_RAW_TEXT_MARKERS = re.compile(r"[{}\[\]]|schema_version|source_dependency_id", re.I)
_ENGINE_TEXT_MARKERS = re.compile(
    r"(?:sxtwl|lunar[-_ ]typescript|runtime_core_facts|"
    r"(?:^|[\s/_.-])(?:bazi|ziwei)(?:$|[\s/_.-]))",
    re.I,
)
_POSITION_LABELS = {
    "year": "年柱",
    "month": "月柱",
    "day": "日柱",
    "hour": "时柱",
}
_ELEMENT_LABELS = {
    "wood": "木",
    "fire": "火",
    "earth": "土",
    "metal": "金",
    "water": "水",
}
_DIRECTION_LABELS = {"forward": "顺排", "reverse": "逆排"}
def _sentence(label: str, value: str) -> str:
    return f"{label}：{value}。"


def _safe_display_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or _RAW_TEXT_MARKERS.search(text) or _ENGINE_TEXT_MARKERS.search(text):
        return None
    return text


def _position(value: str) -> str:
    return _POSITION_LABELS.get(value, value)


def _element(value: str) -> str:
    return _ELEMENT_LABELS.get(value, value)


def _mapping_text(value: object, *keys: str) -> str | None:
    if not isinstance(value, Mapping):
        return None
    for key in keys:
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, int) and not isinstance(item, bool):
            return str(item)
    return None


def _join_nonempty(values: Sequence[str], *, separator: str = "、") -> str | None:
    kept = tuple(value.strip() for value in values if value.strip())
    return separator.join(kept) if kept else None


def _bazi_four_pillars(view: BaziChartV1) -> str:
    values = [
        f"{_position(item.position)}{item.stem}{item.branch}"
        for item in view.pillars
    ]
    return _sentence("四柱", "、".join(values))


def _bazi_element_inventory(view: BaziChartV1) -> str | None:
    core = view.core_facts
    inventory = core.element_inventory if core is not None else None
    counts = (
        inventory.visible_stem_branch_counts
        if inventory is not None
        else view.element_balance
    )
    values = [f"{_element(item.element)}{item.value:g}" for item in counts]
    joined = _join_nonempty(values)
    return None if joined is None else _sentence("五行可见干支计数", joined)


def _bazi_day_master(view: BaziChartV1) -> str | None:
    fact = view.core_facts.day_master if view.core_facts is not None else None
    if fact is None:
        return None
    return _sentence("日主", f"{fact.stem}{_element(fact.element)}（{fact.polarity}）")


def _bazi_hidden_stems(view: BaziChartV1) -> str | None:
    rows = view.core_facts.hidden_stems if view.core_facts is not None else None
    if not rows:
        return None
    return _sentence(
        "藏干",
        "；".join(
            f"{_position(row.position)}{row.branch}藏{'、'.join(row.stems)}"
            for row in rows
        ),
    )


def _bazi_ten_gods(view: BaziChartV1) -> str | None:
    fact = view.core_facts.ten_gods if view.core_facts is not None else None
    if fact is None:
        return None
    visible = "、".join(
        f"{_position(row.position)}{row.stem}·{row.ten_god}"
        for row in fact.heavenly_stems
    )
    hidden = "、".join(
        f"{_position(row.position)}藏{row.stem}·{row.ten_god}"
        for row in fact.hidden_stems
    )
    return _sentence("十神", f"天干{visible}；藏干{hidden}")


def _bazi_nayin(view: BaziChartV1) -> str | None:
    rows = view.core_facts.nayin if view.core_facts is not None else None
    if not rows:
        return None
    return _sentence(
        "纳音",
        "、".join(f"{_position(row.position)}{row.name}" for row in rows),
    )


def _bazi_growth_stages(view: BaziChartV1) -> str | None:
    rows = (
        view.core_facts.twelve_growth_stages
        if view.core_facts is not None
        else None
    )
    if not rows:
        return None
    return _sentence(
        "十二长生",
        "、".join(
            f"{_position(row.position)}{row.stem}{row.branch}·{row.stage}"
            for row in rows
        ),
    )


def _bazi_xunkong(view: BaziChartV1) -> str | None:
    fact = view.core_facts.xunkong if view.core_facts is not None else None
    if fact is None:
        return None
    return _sentence(
        "旬空",
        f"日柱{fact.day_pillar} · {fact.xun}旬 · 旬空{'/'.join(fact.branches)}",
    )


def _bazi_san_yuan(view: BaziChartV1) -> str | None:
    fact = view.core_facts.san_yuan if view.core_facts is not None else None
    if fact is None:
        return None
    return _sentence(
        "胎元·命宫·身宫",
        f"胎元{fact.tai_yuan}、命宫{fact.ming_gong}、身宫{fact.shen_gong}",
    )


def _bazi_month_command(view: BaziChartV1) -> str | None:
    fact = view.core_facts.month_command if view.core_facts is not None else None
    if fact is None:
        return None
    return _sentence(
        "月令",
        f"{fact.label} · 主气{fact.main_qi}（{_element(fact.main_qi_element)}）",
    )


def _bazi_seasonal_profile(view: BaziChartV1) -> str | None:
    fact = view.core_facts.seasonal_profile if view.core_facts is not None else None
    if fact is None:
        return None
    return _sentence(
        "季节画像",
        f"{fact.season} · {fact.month_qi} · 温度{fact.temperature} · 湿度{fact.moisture}",
    )


def _bazi_tiaohou(view: BaziChartV1) -> str | None:
    fact = view.core_facts.tiaohou_markers if view.core_facts is not None else None
    if fact is None:
        return None
    markers = _join_nonempty(fact.markers)
    if markers is None:
        return None
    return _sentence(
        "调候标记",
        f"{markers}（温度{fact.temperature}、湿度{fact.moisture}）",
    )


def _bazi_interpretive_candidates(view: BaziChartV1) -> str | None:
    fact = (
        view.core_facts.interpretive_candidates
        if view.core_facts is not None
        else None
    )
    if fact is None:
        return None
    return _sentence(
        "候选依据",
        (
            f"月令季节状态{fact.strength.seasonal_state}；"
            f"月令主气{fact.structure.month_main_qi}·"
            f"{fact.structure.month_main_qi_ten_god}；"
            f"干合候选{len(fact.following_and_transformation.stem_combination_candidates)}项、"
            f"地支成局候选{len(fact.following_and_transformation.branch_formation_candidates)}项"
        ),
    )


def _bazi_source_patterns(view: BaziChartV1) -> str | None:
    rows = (
        view.core_facts.source_conditioned_patterns
        if view.core_facts is not None
        else ()
    )
    titles = _join_nonempty(tuple(row.title for row in rows))
    return None if titles is None else _sentence("来源条件候选", titles)


def _bazi_branch_relations(view: BaziChartV1) -> str | None:
    rows = view.core_facts.branch_relations if view.core_facts is not None else None
    if not rows:
        return None
    return _sentence(
        "地支关系",
        "、".join(
            f"{'/'.join(row.branches)}·{row.relation_type}"
            f"（{'/'.join(_position(item) for item in row.positions)}）"
            for row in rows
        ),
    )


def _bazi_shensha(view: BaziChartV1) -> str | None:
    fact = view.core_facts.shensha_auxiliary if view.core_facts is not None else None
    if fact is None:
        return None
    items = [
        f"{item.name}（{'/'.join(_position(value) for value in item.matched_positions)}）"
        for item in fact.calculated_items
    ]
    joined = _join_nonempty(items)
    return None if joined is None else _sentence("神煞辅助", joined)


def _bazi_luck_cycles(view: BaziChartV1) -> str | None:
    fact = view.core_facts.luck_cycles if view.core_facts is not None else None
    if fact is None:
        return None
    cycles: list[str] = []
    for cycle in fact.cycles:
        age = ""
        if cycle.start_age_years is not None and cycle.end_age_years is not None:
            age = f"·{cycle.start_age_years:g}至{cycle.end_age_years:g}岁"
        cycles.append(f"第{cycle.sequence}运{cycle.pillar}{age}")
    joined = _join_nonempty(cycles)
    if joined is None:
        return _sentence("大运", "因资料条件不足，本次未返回大运序列")
    direction = _DIRECTION_LABELS.get(fact.direction or "", "")
    return _sentence("大运", f"{direction}{'；' if direction else ''}{joined}")


def _bazi_calendar(view: BaziChartV1) -> str | None:
    fact = (
        view.core_facts.calendar_normalization
        if view.core_facts is not None
        else None
    )
    if fact is None or fact.changed_pillars is None:
        return None
    status = "已完成历法与时间归一" if fact.status == "calculated" else "已返回时间口径"
    changes = (
        "、".join(_position(item) for item in fact.changed_pillars)
        if fact.changed_pillars
        else "四柱未因校正变更"
    )
    return _sentence("时间口径", f"{status}；{changes}")


def _bazi_year_layers(view: BaziChartV1) -> str | None:
    rows = view.core_facts.year_layers if view.core_facts is not None else None
    if not rows:
        return None
    return _sentence(
        "流年",
        "、".join(
            f"{row.year}年{row.ganzhi}（天干十神{row.stem_ten_god}）"
            for row in rows
        ),
    )


def _bazi_temporal_layers(
    view: BaziChartV1,
    *,
    granularity: str,
) -> str | None:
    core = view.core_facts
    rows = (
        core.month_layers
        if core is not None and granularity == "month"
        else core.day_layers
        if core is not None
        else None
    )
    if not rows:
        return None
    label = "流月" if granularity == "month" else "流日"
    values: list[str] = []
    for row in rows:
        ganzhi = _join_nonempty(
            tuple(
                value
                for item in row.ganzhi_segments
                if (value := _mapping_text(item, "ganzhi")) is not None
            )
        )
        values.append(f"{row.period}{f'·{ganzhi}' if ganzhi else ''}")
    return _sentence(label, "、".join(values))


def _ziwei_palaces(view: ZiweiChartV1) -> str:
    values: list[str] = []
    for palace in view.palaces:
        stars = "、".join(palace.major_stars) if palace.major_stars else "无主星"
        values.append(
            f"{palace.label}（{palace.heavenly_stem}{palace.earthly_branch}）主星{stars}"
        )
    return _sentence("十二宫", "；".join(values))


def _ziwei_chart_convention(view: ZiweiChartV1) -> str | None:
    value = view.core_facts.chart_convention if view.core_facts is not None else None
    return None if value is None else _sentence("排盘口径", "服务端已确认本盘历法与宫位口径")


def _ziwei_chinese_date(view: ZiweiChartV1) -> str | None:
    value = view.core_facts.chinese_date if view.core_facts is not None else None
    return None if value is None else _sentence("农历日期", value)


def _ziwei_active_major_limit(view: ZiweiChartV1) -> str | None:
    value = view.core_facts.active_major_limit if view.core_facts is not None else None
    if value is None:
        return None
    palace = _mapping_text(value, "palace", "palace_name", "temporal_palace")
    age_start = _mapping_text(value, "age_start")
    age_end = _mapping_text(value, "age_end")
    details = palace or "服务端已返回当前大限定位"
    if age_start is not None and age_end is not None:
        details = f"{details} · {age_start}至{age_end}岁"
    return _sentence("当前大限", details)


def _ziwei_major_limit_segments(view: ZiweiChartV1) -> str | None:
    rows = (
        view.core_facts.active_major_limit_segments
        if view.core_facts is not None
        else None
    )
    if not rows:
        return None
    return _sentence(
        "当前大限区间",
        "、".join(f"{row.start_inclusive}至{row.end_exclusive}" for row in rows),
    )


def _ziwei_calendar_coverage(view: ZiweiChartV1) -> str | None:
    fact = view.core_facts.calendar_coverage if view.core_facts is not None else None
    if fact is None:
        return None
    target = (
        f" · 目标日{fact.requested_target_date}"
        if fact.requested_target_date is not None
        else ""
    )
    return _sentence(
        "历法覆盖",
        f"{fact.start_inclusive}至{fact.end_exclusive}{target}",
    )


def _ziwei_five_elements_class(view: ZiweiChartV1) -> str | None:
    value = view.core_facts.five_elements_class if view.core_facts is not None else None
    return None if value is None else _sentence("五行局", value)


def _ziwei_interpretive_candidates(view: ZiweiChartV1) -> str | None:
    value = (
        view.core_facts.interpretive_candidates
        if view.core_facts is not None
        else None
    )
    return None if value is None else _sentence("判读候选", "已返回结构化候选依据，尚非定论")


def _ziwei_source_patterns(view: ZiweiChartV1) -> str | None:
    rows = (
        view.core_facts.source_conditioned_patterns
        if view.core_facts is not None
        else ()
    )
    titles = _join_nonempty(tuple(row.title for row in rows))
    return None if titles is None else _sentence("来源条件候选", titles)


def _ziwei_ming_shen(view: ZiweiChartV1) -> str | None:
    fact = view.core_facts.ming_shen if view.core_facts is not None else None
    if fact is None:
        return None
    return _sentence(
        "命身信息",
        (
            f"命主{fact.soul_star}、身主{fact.body_star}，"
            f"命宫{fact.ming_branch}、身宫{fact.shen_branch}"
        ),
    )


def _ziwei_major_limit_direction(view: ZiweiChartV1) -> str | None:
    fact = (
        view.core_facts.major_limit_direction
        if view.core_facts is not None
        else None
    )
    if fact is None:
        return None
    direction = _DIRECTION_LABELS.get(fact.direction, fact.direction)
    return _sentence("大限方向", f"{direction} · 年干{fact.year_stem}")


def _ziwei_major_limit_starting_age(view: ZiweiChartV1) -> str | None:
    age = (
        view.core_facts.major_limit_starting_age
        if view.core_facts is not None
        else None
    )
    return None if age is None else _sentence("大限起始年龄", f"{age}岁")


def _ziwei_limits(view: ZiweiChartV1, *, field_id: str) -> str | None:
    core = view.core_facts
    rows = (
        core.major_limit_sequence
        if core is not None and field_id == "major_limit_sequence"
        else core.major_limits
        if core is not None
        else None
    )
    if not rows:
        return None
    return _sentence(
        "大限序列" if field_id == "major_limit_sequence" else "大限",
        "、".join(
            f"第{row.sequence}限{row.palace}·{row.age_start}至{row.age_end}岁·{row.heavenly_stem}{row.earthly_branch}"
            for row in rows
        ),
    )


def _ziwei_transformations(view: ZiweiChartV1) -> str | None:
    rows = view.core_facts.transformations if view.core_facts is not None else None
    if not rows:
        return None
    return _sentence(
        "四化",
        "、".join(
            f"{row.star}化{row.transformation}入{row.palace}（{row.palace_branch}）"
            for row in rows
        ),
    )


def _ziwei_star_facts(view: ZiweiChartV1) -> str | None:
    rows = view.core_facts.star_facts if view.core_facts is not None else None
    if not rows:
        return None
    return _sentence(
        "星曜",
        "、".join(
            f"{row.palace}{row.name}{f'·{row.brightness}' if row.brightness else ''}"
            for row in rows
        ),
    )


def _ziwei_annual_layers(view: ZiweiChartV1) -> str | None:
    rows = view.core_facts.annual_layers if view.core_facts is not None else None
    if not rows:
        return None
    return _sentence(
        "流年",
        "、".join(
            f"{row.year}年（{row.coverage_start}至{row.coverage_end_exclusive}）"
            for row in rows
        ),
    )


def _ziwei_monthly_layers(view: ZiweiChartV1) -> str | None:
    rows = view.core_facts.monthly_layers if view.core_facts is not None else None
    if not rows:
        return None
    return _sentence("流月", "、".join(f"{row.year}年{row.month}月" for row in rows))


_BAZI_FORMATTERS: dict[str, Callable[[BaziChartV1], str | None]] = {
    "four_pillars": _bazi_four_pillars,
    "element_inventory": _bazi_element_inventory,
    "day_master": _bazi_day_master,
    "hidden_stems": _bazi_hidden_stems,
    "ten_gods": _bazi_ten_gods,
    "nayin": _bazi_nayin,
    "twelve_growth_stages": _bazi_growth_stages,
    "xunkong": _bazi_xunkong,
    "san_yuan": _bazi_san_yuan,
    "month_command": _bazi_month_command,
    "seasonal_profile": _bazi_seasonal_profile,
    "tiaohou_markers": _bazi_tiaohou,
    "interpretive_candidates": _bazi_interpretive_candidates,
    "source_conditioned_patterns": _bazi_source_patterns,
    "branch_relations": _bazi_branch_relations,
    "shensha_auxiliary": _bazi_shensha,
    "luck_cycles": _bazi_luck_cycles,
    "calendar_normalization": _bazi_calendar,
    "year_layers": _bazi_year_layers,
    "month_layers": lambda view: _bazi_temporal_layers(view, granularity="month"),
    "day_layers": lambda view: _bazi_temporal_layers(view, granularity="day"),
}

_ZIWEI_FORMATTERS: dict[str, Callable[[ZiweiChartV1], str | None]] = {
    "palaces": _ziwei_palaces,
    "chart_convention": _ziwei_chart_convention,
    "chinese_date": _ziwei_chinese_date,
    "active_major_limit": _ziwei_active_major_limit,
    "active_major_limit_segments": _ziwei_major_limit_segments,
    "calendar_coverage": _ziwei_calendar_coverage,
    "five_elements_class": _ziwei_five_elements_class,
    "interpretive_candidates": _ziwei_interpretive_candidates,
    "source_conditioned_patterns": _ziwei_source_patterns,
    "ming_shen": _ziwei_ming_shen,
    "major_limit_direction": _ziwei_major_limit_direction,
    "major_limit_starting_age": _ziwei_major_limit_starting_age,
    "major_limit_sequence": lambda view: _ziwei_limits(
        view, field_id="major_limit_sequence"
    ),
    "major_limits": lambda view: _ziwei_limits(view, field_id="major_limits"),
    "natal_transformation_facts": _ziwei_transformations,
    "star_facts": _ziwei_star_facts,
    "annual_layers": _ziwei_annual_layers,
    "monthly_layers": _ziwei_monthly_layers,
}


def project_presented_view_model(
    view_model: BaziChartV1 | ZiweiChartV1,
) -> BaziChartV1 | ZiweiChartV1:
    """Expose every fact already supported by the typed Runtime ViewModel."""

    return view_model


def _project_display_text(
    *,
    capability_id: str,
    field_id: str,
    view_model: object,
) -> str | None:
    if capability_id == "bazi" and isinstance(view_model, BaziChartV1):
        bazi_formatter = _BAZI_FORMATTERS.get(field_id)
        return (
            None
            if bazi_formatter is None
            else _safe_display_text(bazi_formatter(view_model))
        )
    if capability_id == "ziwei" and isinstance(view_model, ZiweiChartV1):
        ziwei_formatter = _ZIWEI_FORMATTERS.get(field_id)
        return (
            None
            if ziwei_formatter is None
            else _safe_display_text(ziwei_formatter(view_model))
        )
    return None


def _string_refs(values: object) -> tuple[str, ...] | None:
    if not isinstance(values, list) or not all(
        isinstance(item, str) for item in values
    ):
        return None
    return tuple(values)


def _closed_dependency_pairs(
    *,
    original: object,
    projected: object,
    fact_ref_field: str,
    kept_fact_refs: frozenset[str],
) -> list[tuple[Mapping[str, object], dict[str, Any]]]:
    if not isinstance(original, list) or not isinstance(projected, list):
        return []
    original_items = [item for item in original if isinstance(item, Mapping)]
    projected_items = [item for item in projected if isinstance(item, Mapping)]
    if len(original_items) != len(projected_items):
        return []

    kept: list[tuple[Mapping[str, object], dict[str, Any]]] = []
    for source, item in zip(original_items, projected_items, strict=True):
        required_fact_refs = _string_refs(source.get(fact_ref_field))
        if required_fact_refs is None or not set(required_fact_refs).issubset(
            kept_fact_refs
        ):
            continue
        kept.append((source, dict(item)))
    return kept


def _retain_closed_dependencies(
    panel: dict[str, Any],
    *,
    original: Mapping[str, object],
    kept_fact_refs: frozenset[str],
) -> None:
    evidence_pairs = _closed_dependency_pairs(
        original=original.get("evidence"),
        projected=panel.get("evidence"),
        fact_ref_field="supports_fact_refs",
        kept_fact_refs=kept_fact_refs,
    )
    panel["evidence"] = [item for _source, item in evidence_pairs]
    retained_evidence_refs = frozenset(
        item["ref"]
        for _source, item in evidence_pairs
        if isinstance(item.get("ref"), str)
    )

    for collection_name in ("claim_scopes", "findings"):
        dependency_pairs = _closed_dependency_pairs(
            original=original.get(collection_name),
            projected=panel.get(collection_name),
            fact_ref_field="fact_refs",
            kept_fact_refs=kept_fact_refs,
        )
        panel[collection_name] = [
            item
            for source, item in dependency_pairs
            if (
                evidence_refs := _string_refs(source.get("evidence_refs"))
            )
            is not None
            and set(evidence_refs).issubset(retained_evidence_refs)
        ]


def project_presented_fact_panel(
    brief: ReadingBrief | Mapping[str, object] | None,
    *,
    view_model: object,
) -> dict[str, Any] | None:
    """Project API-safe facts with stable user-facing text for Bazi and Ziwei.

    Runtime values and the typed ViewModel remain authoritative. Unsupported
    calculated facts and unsafe display strings are removed together with every
    dependent record. Billing state does not hide supported facts.
    """

    original = brief.to_dict() if isinstance(brief, ReadingBrief) else dict(brief or {})
    panel = project_public_fact_panel(brief)
    if panel is None:
        return None
    facts = panel.get("facts")
    if not isinstance(facts, list):
        return panel

    kept: list[dict[str, Any]] = []
    for item in facts:
        if not isinstance(item, Mapping):
            continue
        next_item = dict(item)
        ref = next_item.get("ref")
        match = _CALCULATED_FACT_REF.search(ref) if isinstance(ref, str) else None
        if match is None:
            display_text = _safe_display_text(next_item.get("display_text"))
        else:
            display_text = _project_display_text(
                capability_id=match.group("capability"),
                field_id=match.group("field_id"),
                view_model=view_model,
            )
        if display_text is None:
            continue
        next_item["display_text"] = display_text
        kept.append(next_item)

    panel["facts"] = kept
    kept_fact_refs = frozenset(
        ref
        for item in kept
        if isinstance((ref := item.get("ref")), str)
    )
    _retain_closed_dependencies(
        panel,
        original=original,
        kept_fact_refs=kept_fact_refs,
    )
    return panel
