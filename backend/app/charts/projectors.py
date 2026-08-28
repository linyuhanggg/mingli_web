from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Final, Literal, Protocol, cast

from pydantic import ValidationError

from app.charts.contracts import (
    DALIUREN_LESSON_UPPERS,
    VIEW_MODEL_TYPES,
    ArtSignal,
    BaziBoundaryTerm,
    BaziBranchRelation,
    BaziCalendarNormalization,
    BaziChartV1,
    BaziCoreFacts,
    BaziDayMaster,
    BaziElementCount,
    BaziElementInventory,
    BaziFollowingTransformationCandidate,
    BaziGrowthStage,
    BaziHiddenStems,
    BaziInterpretiveCandidates,
    BaziLuckCycle,
    BaziLuckCycles,
    BaziMonthCommand,
    BaziMonthOrderAdjudication,
    BaziMonthOrderSourceRef,
    BaziNayin,
    BaziReasoningTool,
    BaziSalienceSignal,
    BaziSanYuan,
    BaziSeasonalProfile,
    BaziShenshaAuxiliary,
    BaziShenshaItem,
    BaziShenshaRule,
    BaziSourcePattern,
    BaziStemCombinationCandidate,
    BaziStrengthEvidence,
    BaziStructureCandidate,
    BaziTemporalLayer,
    BaziTenGodEntry,
    BaziTenGods,
    BaziTiaohouMarkers,
    BaziXunKong,
    BaziYearLayer,
    BaziYearRelation,
    BaziYearRuleTrace,
    BaziYearSegment,
    BaziYearStructuralChanges,
    BaziYearTenGod,
    CanwenViewV1,
    ChartSimilarityPillarComparison,
    ChartSimilarityViewV1,
    ContractModel,
    DaliurenChartV1,
    DaliurenCoreFacts,
    DaliurenLesson,
    DaliurenLessonMethod,
    DaliurenSourcePattern,
    DaliurenTransmission,
    DimensionSynthesis,
    ElementBalance,
    FengshuiSourcePattern,
    FengshuiViewV1,
    FiveElementsFactsViewV1,
    FiveElementsSourceIdentity,
    FortuneCalendarNormalization,
    FortuneFactsViewV1,
    FortunePeriodMarker,
    FortuneTargetPeriod,
    HecanViewV1,
    HexagramSummary,
    HousePosition,
    LiuyaoChartV1,
    LiuyaoCoreFacts,
    LiuyaoLine,
    LiuyaoSourcePattern,
    LiuyaoUsefulSpiritSelection,
    LumingNayinChartV1,
    LumingNayinPillar,
    LumingNayinRelation,
    LumingNayinRuleApplicabilityAdjudication,
    LumingNayinSourcePattern,
    MeihuaBodyRelationFact,
    MeihuaBodyUse,
    MeihuaChartV1,
    MeihuaCoreFacts,
    MeihuaInterpretiveCandidates,
    MeihuaRelationAdjudication,
    MeihuaRelationCandidate,
    MeihuaSeasonalStrengthFact,
    MeihuaTrigram,
    PhysiognomyObservation,
    PhysiognomySourceComparison,
    PhysiognomySourcePattern,
    PhysiognomyViewV1,
    Pillar,
    PlanetPosition,
    QimenChartV1,
    QimenChief,
    QimenDirector,
    QimenHiddenJia,
    QimenHorse,
    QimenInstrumentsWonders,
    QimenNamedPattern,
    QimenPalace,
    QimenPatternIdentityAdjudication,
    QimenPatternSourceRef,
    QimenPlateStem,
    QimenXunkong,
    QizhengAnnualTransformation,
    QizhengBodyFact,
    QizhengChartV1,
    QizhengCoordinateConvention,
    QizhengCoreFacts,
    QizhengEphemerisEngine,
    QizhengEphemerisSummary,
    QizhengLimit,
    QizhengMingShen,
    QizhengRequestedLimitLayer,
    QizhengSourcePattern,
    QizhengTransformation,
    RhythmFactsPillar,
    RhythmFactsViewV1,
    SelectionCandidate,
    SelectionChartV1,
    SelectionLineagePolicy,
    SelectionRanking,
    SelectionSourcePattern,
    TaiyiBoard,
    TaiyiBoardPredicate,
    TaiyiCalendar,
    TaiyiChartV1,
    TaiyiCycle,
    TaiyiEpoch,
    TaiyiFourGenerals,
    TaiyiLongCycleDeity,
    TaiyiNamedPosition,
    TaiyiPatternIdentityAdjudication,
    TaiyiPatternSourceRef,
    TaiyiScopeContract,
    TimeCheckCandidateEvidenceV1,
    TimeCheckCandidateV1,
    TimeCheckEventMatchV1,
    TimeCheckRectificationConclusionV1,
    TimeCheckViewV1,
    TimeLayer,
    ViewModel,
    WenshiViewV1,
    ZiweiAnnualLayer,
    ZiweiCalendarCoverage,
    ZiweiChartV1,
    ZiweiCoreFacts,
    ZiweiDecadal,
    ZiweiLimit,
    ZiweiMajorLimitDirection,
    ZiweiMajorLimitSegment,
    ZiweiMingShen,
    ZiweiMonthlyLayer,
    ZiweiPalace,
    ZiweiSourcePattern,
    ZiweiStar,
    ZiweiStarFact,
    ZiweiTransformation,
    daliuren_in_range_structural_indices,
    daliuren_source_pattern_structural_index,
)
from app.charts.public_labels import DALIUREN_PUBLIC_LABELS, MEIHUA_PUBLIC_LABELS, public_key_labels
from app.charts.relationship_engine import (
    project_bazi_relationship_view_model,
    project_qizheng_relationship_view_model,
    project_ziwei_relationship_view_model,
)
from app.charts.similarity import (
    ChartSimilarityInputError,
    compare_bazi_four_pillars,
)


def project_view_model(view_model: ContractModel) -> dict[str, Any]:
    """Serialize a validated ViewModel; Runtime fact interpretation stays upstream."""
    if not isinstance(view_model, tuple(VIEW_MODEL_TYPES.values())):
        raise TypeError("project_view_model requires a typed view model")
    return view_model.model_dump(mode="json")


_BAZI_PILLAR_POSITIONS: tuple[Literal["year", "month", "day", "hour"], ...] = (
    "year",
    "month",
    "day",
    "hour",
)
_BAZI_ELEMENTS: tuple[
    tuple[Literal["wood", "fire", "earth", "metal", "water"], str], ...
] = (
    ("wood", "木"),
    ("fire", "火"),
    ("earth", "土"),
    ("metal", "金"),
    ("water", "水"),
)
_BAZI_ELEMENT_IDS = frozenset(item[0] for item in _BAZI_ELEMENTS)


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _text_tuple(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    return result if len(result) == len(value) else None


def _element_id(value: object) -> Literal["wood", "fire", "earth", "metal", "water"] | None:
    if not isinstance(value, str):
        return None
    if value in _BAZI_ELEMENT_IDS:
        return value
    for element, label in _BAZI_ELEMENTS:
        if value == label:
            return element
    return None


def _bazi_day_master(value: object) -> BaziDayMaster | None:
    if not isinstance(value, Mapping):
        return None
    stem = _text(value.get("stem"))
    element = _element_id(value.get("element"))
    polarity = value.get("polarity")
    if stem is None or element is None or polarity not in {"阳", "阴"}:
        return None
    return BaziDayMaster(stem=stem, element=element, polarity=cast(Literal["阳", "阴"], polarity))


def _bazi_hidden_stems(value: object) -> tuple[BaziHiddenStems, ...] | None:
    if not isinstance(value, Mapping):
        return None
    result: list[BaziHiddenStems] = []
    for position in _BAZI_PILLAR_POSITIONS:
        raw = value.get(position)
        if not isinstance(raw, Mapping):
            return None
        branch = _text(raw.get("branch"))
        stems = _text_tuple(raw.get("stems"))
        if branch is None or stems is None or not stems:
            return None
        result.append(BaziHiddenStems(position=position, branch=branch, stems=stems))
    return tuple(result)


def _bazi_ten_gods(value: object) -> BaziTenGods | None:
    if not isinstance(value, Mapping):
        return None
    heavenly_raw = value.get("heavenly_stems")
    hidden_raw = value.get("hidden_stems")
    if not isinstance(heavenly_raw, Mapping) or not isinstance(hidden_raw, Mapping):
        return None
    heavenly: list[BaziTenGodEntry] = []
    hidden: list[BaziTenGodEntry] = []
    for position in _BAZI_PILLAR_POSITIONS:
        visible = heavenly_raw.get(position)
        if not isinstance(visible, Mapping):
            return None
        stem = _text(visible.get("stem"))
        ten_god = _text(visible.get("ten_god"))
        if stem is None or ten_god is None:
            return None
        heavenly.append(
            BaziTenGodEntry(
                position=position,
                layer="heavenly_stem",
                stem=stem,
                ten_god=ten_god,
            )
        )
        hidden_items = hidden_raw.get(position)
        if not isinstance(hidden_items, (list, tuple)):
            return None
        for item in hidden_items:
            if not isinstance(item, Mapping):
                return None
            hidden_stem = _text(item.get("stem"))
            hidden_god = _text(item.get("ten_god"))
            if hidden_stem is None or hidden_god is None:
                return None
            hidden.append(
                BaziTenGodEntry(
                    position=position,
                    layer="hidden_stem",
                    stem=hidden_stem,
                    ten_god=hidden_god,
                )
            )
    if not hidden:
        return None
    return BaziTenGods(heavenly_stems=tuple(heavenly), hidden_stems=tuple(hidden))


def _bazi_nayin(value: object) -> tuple[BaziNayin, ...] | None:
    if not isinstance(value, Mapping):
        return None
    result: list[BaziNayin] = []
    for position in _BAZI_PILLAR_POSITIONS:
        name = _text(value.get(position))
        if name is None:
            return None
        result.append(BaziNayin(position=position, name=name))
    return tuple(result)


def _bazi_growth_stages(value: object) -> tuple[BaziGrowthStage, ...] | None:
    if not isinstance(value, Mapping):
        return None
    result: list[BaziGrowthStage] = []
    for position in _BAZI_PILLAR_POSITIONS:
        raw = value.get(position)
        if not isinstance(raw, Mapping):
            return None
        stage_index = raw.get("stage_index")
        if isinstance(stage_index, bool) or not isinstance(stage_index, int):
            return None
        if (
            raw.get("position") != position
            or raw.get("direction") not in {"forward", "reverse"}
        ):
            return None
        fields = {
            key: _text(raw.get(key))
            for key in (
                "stem",
                "branch",
                "stage",
                "source_dependency_id",
                "boundary",
            )
        }
        if any(item is None for item in fields.values()):
            return None
        result.append(
            BaziGrowthStage(
                position=position,
                stem=cast(str, fields["stem"]),
                branch=cast(str, fields["branch"]),
                stage=cast(str, fields["stage"]),
                stage_index=stage_index,
                direction=cast(Literal["forward", "reverse"], raw["direction"]),
                source_dependency_id=cast(
                    str, fields["source_dependency_id"]
                ),
                boundary=cast(str, fields["boundary"]),
            )
        )
    return tuple(result)


def _bazi_xunkong(value: object) -> BaziXunKong | None:
    if not isinstance(value, Mapping):
        return None
    day_pillar = _text(value.get("day_pillar"))
    xun = _text(value.get("xun"))
    source_dependency_id = _text(value.get("source_dependency_id"))
    boundary = _text(value.get("boundary"))
    branches = value.get("branches")
    if (
        day_pillar is None
        or xun is None
        or source_dependency_id is None
        or boundary is None
        or not isinstance(branches, (list, tuple))
        or len(branches) != 2
        or any(_text(branch) is None for branch in branches)
    ):
        return None
    return BaziXunKong(
        day_pillar=day_pillar,
        xun=xun,
        branches=(str(branches[0]), str(branches[1])),
        source_dependency_id=source_dependency_id,
        boundary=boundary,
    )


def _bazi_san_yuan(value: object) -> BaziSanYuan | None:
    if not isinstance(value, Mapping):
        return None
    fields = {
        key: _text(value.get(key))
        for key in (
            "tai_yuan",
            "ming_gong",
            "shen_gong",
            "source",
            "source_dependency_id",
            "boundary",
        )
    }
    if any(item is None for item in fields.values()):
        return None
    return BaziSanYuan(**cast(dict[str, str], fields))


def _bazi_month_command(value: object) -> BaziMonthCommand | None:
    if not isinstance(value, Mapping):
        return None
    branch = _text(value.get("branch"))
    label = _text(value.get("label"))
    main_qi = _text(value.get("main_qi"))
    element = _element_id(value.get("main_qi_element"))
    if branch is None or label is None or main_qi is None or element is None:
        return None
    return BaziMonthCommand(
        branch=branch,
        label=label,
        main_qi=main_qi,
        main_qi_element=element,
    )


def _bazi_seasonal_profile(value: object) -> BaziSeasonalProfile | None:
    if not isinstance(value, Mapping):
        return None
    fields = {
        key: _text(value.get(key))
        for key in ("season", "month_qi", "temperature", "moisture")
    }
    if not all(fields.values()):
        return None
    return BaziSeasonalProfile(
        season=cast(str, fields["season"]),
        month_qi=cast(str, fields["month_qi"]),
        temperature=cast(str, fields["temperature"]),
        moisture=cast(str, fields["moisture"]),
    )


def _bazi_tiaohou(value: object) -> BaziTiaohouMarkers | None:
    if not isinstance(value, Mapping):
        return None
    temperature = _text(value.get("temperature"))
    moisture = _text(value.get("moisture"))
    markers = _text_tuple(value.get("markers"))
    scope = _text(value.get("scope"))
    identity = value.get("applicability_identity")
    if not isinstance(identity, Mapping):
        identity = {}
    if temperature is None or moisture is None or markers is None or scope is None:
        return None
    return BaziTiaohouMarkers(
        temperature=temperature,
        moisture=moisture,
        markers=markers,
        day_stem=_text(identity.get("day_stem")),
        month_branch=_text(identity.get("month_branch")),
        scope=scope,
    )


def _bazi_element_counts(value: object) -> tuple[BaziElementCount, ...] | None:
    if not isinstance(value, Mapping):
        return None
    counts: list[BaziElementCount] = []
    for element, label in _BAZI_ELEMENTS:
        raw = value.get(label)
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            continue
        counts.append(BaziElementCount(element=element, value=raw))
    return tuple(counts)


def _bazi_element_inventory(value: object) -> BaziElementInventory | None:
    if not isinstance(value, Mapping):
        return None
    visible = _bazi_element_counts(value.get("visible_stem_branch_counts"))
    hidden = _bazi_element_counts(value.get("hidden_stem_occurrence_counts"))
    scope = _text(value.get("scope"))
    if visible is None or hidden is None or scope is None:
        return None
    return BaziElementInventory(
        visible_stem_branch_counts=visible,
        hidden_stem_occurrence_counts=hidden,
        scope=scope,
    )


def _bazi_month_order_adjudication(
    value: object,
) -> BaziMonthOrderAdjudication | None:
    if not isinstance(value, Mapping):
        return None
    day_element = _element_id(value.get("day_master_element"))
    month_element = _element_id(value.get("month_command_element"))
    seasonal_state = value.get("seasonal_state")
    source_raw = value.get("source_ref")
    unresolved = _text_tuple(value.get("unresolved_checks"))
    if not isinstance(source_raw, Mapping):
        return None
    try:
        source_ref = BaziMonthOrderSourceRef.model_validate(dict(source_raw))
    except ValueError:
        return None
    if (
        value.get("status") != "adjudicated_month_order_state"
        or value.get("decision_scope") != "bazi_month_order_seasonal_state"
        or day_element is None
        or month_element is None
        or seasonal_state not in {"旺", "相", "休", "囚", "死"}
        or value.get("whole_chart_strength_verdict") is not None
        or value.get("useful_god_verdict") is not None
        or unresolved is None
        or not unresolved
    ):
        return None
    return BaziMonthOrderAdjudication(
        status="adjudicated_month_order_state",
        decision_scope="bazi_month_order_seasonal_state",
        day_master_element=day_element,
        month_command_element=month_element,
        seasonal_state=cast(
            Literal["旺", "相", "休", "囚", "死"], seasonal_state
        ),
        source_ref=source_ref,
        unresolved_checks=unresolved,
    )


def _bazi_strength_evidence(value: object) -> BaziStrengthEvidence | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("status") != "evidence_only" or value.get("hard_verdict") is not None:
        return None
    day_element = _element_id(value.get("day_element"))
    month_command_element = _element_id(value.get("month_command_element"))
    seasonal_state = value.get("seasonal_state")
    seasonal_state_source_rule_id = _text(value.get("seasonal_state_source_rule_id"))
    resource_element = _element_id(value.get("resource_element"))
    all_counts = _bazi_element_counts(value.get("all_element_occurrences"))
    integer_fields = {
        key: value.get(key)
        for key in ("same_element_occurrences", "resource_occurrences")
    }
    month_order_adjudication = _bazi_month_order_adjudication(
        value.get("month_order_adjudication")
    )
    boundary = _text(value.get("boundary"))
    if (
        day_element is None
        or month_command_element is None
        or seasonal_state not in {"旺", "相", "休", "囚", "死"}
        or seasonal_state_source_rule_id is None
        or resource_element is None
        or all_counts is None
        or len(all_counts) != len(_BAZI_ELEMENTS)
        or month_order_adjudication is None
        or month_order_adjudication.day_master_element != day_element
        or month_order_adjudication.month_command_element
        != month_command_element
        or month_order_adjudication.seasonal_state != seasonal_state
        or boundary is None
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in integer_fields.values()
        )
    ):
        return None
    return BaziStrengthEvidence(
        status="evidence_only",
        day_element=day_element,
        month_command_element=month_command_element,
        seasonal_state=cast(
            Literal["旺", "相", "休", "囚", "死"], seasonal_state
        ),
        seasonal_state_source_rule_id=seasonal_state_source_rule_id,
        same_element_occurrences=cast(int, integer_fields["same_element_occurrences"]),
        resource_element=resource_element,
        resource_occurrences=cast(int, integer_fields["resource_occurrences"]),
        all_element_occurrences=all_counts,
        month_order_adjudication=month_order_adjudication,
        boundary=boundary,
    )


def _bazi_structure_candidate(value: object) -> BaziStructureCandidate | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("status") != "candidate_only" or value.get("hard_verdict") is not None:
        return None
    month_main_qi = _text(value.get("month_main_qi"))
    month_main_qi_ten_god = _text(value.get("month_main_qi_ten_god"))
    visible_positions = _text_tuple(value.get("visible_positions"))
    boundary = _text(value.get("boundary"))
    if (
        month_main_qi is None
        or month_main_qi_ten_god is None
        or not isinstance(value.get("main_qi_visible"), bool)
        or visible_positions is None
        or boundary is None
    ):
        return None
    return BaziStructureCandidate(
        status="candidate_only",
        month_main_qi=month_main_qi,
        month_main_qi_ten_god=month_main_qi_ten_god,
        main_qi_visible=cast(bool, value["main_qi_visible"]),
        visible_positions=visible_positions,
        boundary=boundary,
    )


def _bazi_stem_combination_candidates(
    value: object,
) -> tuple[BaziStemCombinationCandidate, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[BaziStemCombinationCandidate] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        with_position = _text(raw.get("with_position"))
        stems = _text_tuple(raw.get("stems"))
        candidate_element = _element_id(raw.get("candidate_element"))
        status = _text(raw.get("status"))
        if (
            with_position is None
            or stems is None
            or candidate_element is None
            or status is None
        ):
            return None
        result.append(
            BaziStemCombinationCandidate(
                with_position=with_position,
                stems=stems,
                candidate_element=candidate_element,
                status=status,
            )
        )
    return tuple(result)


def _bazi_following_transformation(
    value: object,
) -> BaziFollowingTransformationCandidate | None:
    if not isinstance(value, Mapping):
        return None
    if (
        value.get("status") != "requires_classical_adjudication"
        or value.get("hard_verdict") is not None
    ):
        return None
    stem_candidates = _bazi_stem_combination_candidates(
        value.get("stem_combination_candidates")
    )
    branch_candidates = _bazi_branch_relations(
        value.get("branch_formation_candidates")
    )
    boundary = _text(value.get("boundary"))
    if stem_candidates is None or branch_candidates is None or boundary is None:
        return None
    return BaziFollowingTransformationCandidate(
        status="requires_classical_adjudication",
        stem_combination_candidates=stem_candidates,
        branch_formation_candidates=branch_candidates,
        boundary=boundary,
    )


def _bazi_salience_signals(value: object) -> tuple[BaziSalienceSignal, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[BaziSalienceSignal] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        signal_id = _text(raw.get("signal_id"))
        status = raw.get("status")
        hard_verdict = raw.get("hard_verdict")
        basis = raw.get("basis")
        boundary = _text(raw.get("boundary"))
        if (
            signal_id is None
            or status != "mechanical_candidate"
            or hard_verdict is not None
            or not isinstance(basis, Mapping)
            or boundary is None
        ):
            return None
        result.append(
            BaziSalienceSignal(
                signal_id=signal_id,
                status="mechanical_candidate",
                basis={str(key): item for key, item in basis.items()},
                boundary=boundary,
            )
        )
    return tuple(result)


def _bazi_reasoning_tools(value: object) -> dict[str, BaziReasoningTool] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return None
    result: dict[str, BaziReasoningTool] = {}

    def plain_json(item: object) -> object:
        if isinstance(item, Mapping):
            return {str(key): plain_json(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [plain_json(child) for child in item]
        return item

    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, Mapping):
            return None
        try:
            result[key] = BaziReasoningTool.model_validate(plain_json(raw))
        except (TypeError, ValueError):
            return None
    return result


def _bazi_interpretive_candidates(value: object) -> BaziInterpretiveCandidates | None:
    if not isinstance(value, Mapping):
        return None
    strength = _bazi_strength_evidence(value.get("strength"))
    structure = _bazi_structure_candidate(value.get("structure"))
    following = _bazi_following_transformation(
        value.get("following_and_transformation")
    )
    salience = _bazi_salience_signals(value.get("salience_signals"))
    reasoning_tools = _bazi_reasoning_tools(value.get("reasoning_tools"))
    if strength is None or structure is None or following is None or salience is None:
        return None
    return BaziInterpretiveCandidates(
        strength=strength,
        structure=structure,
        following_and_transformation=following,
        salience_signals=salience,
        reasoning_tools=reasoning_tools,
    )


def _bazi_branch_relations(value: object) -> tuple[BaziBranchRelation, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[BaziBranchRelation] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        relation_type = _text(raw.get("type"))
        branches = _text_tuple(raw.get("branches"))
        positions = _text_tuple(raw.get("positions")) or ()
        if relation_type is None or branches is None or len(branches) < 2:
            continue
        result.append(
            BaziBranchRelation(
                relation_type=relation_type,
                positions=positions,
                branches=branches,
            )
        )
    return tuple(result)


def _bazi_boundary_term(value: object) -> BaziBoundaryTerm | None:
    if not isinstance(value, Mapping):
        return None
    name = _text(value.get("name"))
    index = value.get("index")
    month_boundary = value.get("is_month_boundary_jie")
    datetime_value = _text(value.get("datetime"))
    instant_utc = _text(value.get("instant_utc"))
    if (
        name is None
        or isinstance(index, bool)
        or not isinstance(index, int)
        or not isinstance(month_boundary, bool)
        or datetime_value is None
        or instant_utc is None
    ):
        return None
    return BaziBoundaryTerm(
        name=name,
        index=index,
        is_month_boundary_jie=month_boundary,
        datetime=datetime_value,
        instant_utc=instant_utc,
    )


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number >= 0 else None


def _bazi_luck_cycles(value: object) -> BaziLuckCycles | None:
    if not isinstance(value, Mapping):
        return None
    status = value.get("status")
    if status not in {"calculated", "sequence_only", "not_calculated_missing_gender"}:
        return None
    direction = value.get("direction")
    if direction not in {None, "forward", "reverse"}:
        direction = None
    direction_rule = _text(value.get("direction_rule"))
    start_age_rule = _text(value.get("start_age_rule"))
    boundary_term = _bazi_boundary_term(value.get("boundary_term"))
    interval_days = _number(value.get("interval_days"))
    start_age_years = _number(value.get("start_age_years"))
    approximate_start = _text(value.get("approximate_start_datetime"))
    unavailable = _text_tuple(value.get("unavailable")) or ()
    raw_cycles = value.get("cycles")
    if not isinstance(raw_cycles, (list, tuple)):
        return None
    cycles: list[BaziLuckCycle] = []
    for raw in raw_cycles:
        if not isinstance(raw, Mapping):
            return None
        sequence = raw.get("sequence")
        pillar = _text(raw.get("pillar"))
        if isinstance(sequence, bool) or not isinstance(sequence, int) or pillar is None:
            return None
        cycle_start = _number(raw.get("start_age_years"))
        cycle_end = _number(raw.get("end_age_years"))
        cycles.append(
            BaziLuckCycle(
                sequence=sequence,
                pillar=pillar,
                start_age_years=cycle_start,
                end_age_years=cycle_end,
            )
        )
    return BaziLuckCycles(
        status=cast(
            Literal["calculated", "sequence_only", "not_calculated_missing_gender"],
            status,
        ),
        direction=cast(Literal["forward", "reverse"] | None, direction),
        direction_rule=direction_rule,
        start_age_rule=start_age_rule,
        boundary_term=boundary_term,
        interval_days=interval_days,
        start_age_years=start_age_years,
        approximate_start_datetime=approximate_start,
        cycles=tuple(cycles),
        unavailable=unavailable,
    )


def _bazi_shensha(value: object) -> BaziShenshaAuxiliary | None:
    if not isinstance(value, Mapping):
        return None
    status = _text(value.get("status"))
    temporal_scope = _text(value.get("temporal_scope"))
    precedence = _text(value.get("precedence"))
    boundary = _text(value.get("boundary"))
    cannot_override = _text_tuple(value.get("cannot_override")) or ()
    if status is None or temporal_scope is None or precedence is None or boundary is None:
        return None
    evaluated: list[BaziShenshaRule] = []
    for raw in value.get("evaluated_rules") or ():
        if not isinstance(raw, Mapping):
            continue
        rule_id = _text(raw.get("id"))
        name = _text(raw.get("name"))
        anchor_position = _text(raw.get("anchor_position"))
        anchor_branch = _text(raw.get("anchor_branch"))
        target_branch = _text(raw.get("target_branch"))
        matched = raw.get("matched")
        if (
            rule_id is None
            or name is None
            or anchor_position is None
            or anchor_branch is None
            or target_branch is None
            or not isinstance(matched, bool)
        ):
            continue
        evaluated.append(
            BaziShenshaRule(
                rule_id=rule_id,
                name=name,
                anchor_position=anchor_position,
                anchor_branch=anchor_branch,
                target_branch=target_branch,
                matched=matched,
            )
        )
    calculated: list[BaziShenshaItem] = []
    for raw in value.get("calculated_items") or ():
        if not isinstance(raw, Mapping):
            continue
        item_id = _text(raw.get("id"))
        name = _text(raw.get("name"))
        target_branch = _text(raw.get("target_branch"))
        anchor_positions = _text_tuple(raw.get("anchor_positions"))
        anchor_branches = _text_tuple(raw.get("anchor_branches"))
        matched_positions = _text_tuple(raw.get("matched_positions"))
        item_status = _text(raw.get("status"))
        if not all(
            (
                item_id,
                name,
                target_branch,
                anchor_positions,
                anchor_branches,
                matched_positions,
                item_status,
            )
        ):
            continue
        calculated.append(
            BaziShenshaItem(
                item_id=cast(str, item_id),
                name=cast(str, name),
                target_branch=cast(str, target_branch),
                anchor_positions=cast(tuple[str, ...], anchor_positions),
                anchor_branches=cast(tuple[str, ...], anchor_branches),
                matched_positions=cast(tuple[str, ...], matched_positions),
                status=cast(str, item_status),
            )
        )
    return BaziShenshaAuxiliary(
        status=status,
        temporal_scope=temporal_scope,
        precedence=precedence,
        evaluated_rules=tuple(evaluated),
        calculated_items=tuple(calculated),
        cannot_override=cannot_override,
        boundary=boundary,
    )


def _calculated_value(
    calculated: Mapping[str, tuple[str, object] | None],
    key: str,
) -> object:
    item = calculated[key]
    return item[1] if item is not None else None


def _mapping_copy(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return {str(key): item for key, item in value.items()}


def _plain_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json_value(item) for item in value]
    return value


def _plain_mapping_copy(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return {
        str(key): _plain_json_value(item)
        for key, item in value.items()
    }


def _bazi_year_ten_gods(value: object) -> tuple[BaziYearTenGod, ...] | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    result: list[BaziYearTenGod] = []
    for item in value:
        if not isinstance(item, Mapping):
            return None
        stem = _text(item.get("stem"))
        ten_god = _text(item.get("ten_god"))
        if stem is None or ten_god is None:
            return None
        result.append(BaziYearTenGod(stem=stem, ten_god=ten_god))
    return tuple(result)


def _bazi_year_relation(value: object) -> BaziYearRelation | None:
    if not isinstance(value, Mapping):
        return None
    relation_type = _text(value.get("type") or value.get("relation_type"))
    natal_position = _text(value.get("natal_position"))
    natal_branch = _text(value.get("natal_branch"))
    transit_branch = _text(value.get("transit_branch"))
    if not all((relation_type, natal_position, natal_branch, transit_branch)):
        return None
    return BaziYearRelation(
        relation_type=cast(str, relation_type),
        natal_position=cast(str, natal_position),
        natal_branch=cast(str, natal_branch),
        transit_branch=cast(str, transit_branch),
    )


def _bazi_year_relations(value: object) -> tuple[BaziYearRelation, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[BaziYearRelation] = []
    for item in value:
        relation = _bazi_year_relation(item)
        if relation is None:
            return None
        result.append(relation)
    return tuple(result)


def _bazi_year_structural_changes(value: object) -> BaziYearStructuralChanges | None:
    if not isinstance(value, Mapping):
        return None
    status = _text(value.get("status"))
    transit_pillar = _text(value.get("transit_pillar"))
    stem_ten_god = _text(value.get("stem_ten_god"))
    relations = _bazi_year_relations(value.get("branch_relations"))
    if (
        status != "mechanical_candidates_only"
        or transit_pillar is None
        or stem_ten_god is None
        or relations is None
        or value.get("hard_verdict") is not None
    ):
        return None
    return BaziYearStructuralChanges(
        status="mechanical_candidates_only",
        transit_pillar=transit_pillar,
        stem_ten_god=stem_ten_god,
        branch_relations=relations,
    )


def _bazi_year_segment(value: object) -> BaziYearSegment | None:
    if not isinstance(value, Mapping):
        return None
    start_inclusive = _text(value.get("start_inclusive"))
    end_exclusive = _text(value.get("end_exclusive"))
    ganzhi = _text(value.get("ganzhi"))
    stem_ten_god = _text(value.get("stem_ten_god"))
    hidden_ten_gods = _bazi_year_ten_gods(value.get("branch_hidden_ten_gods"))
    branch_relations = _bazi_year_relations(value.get("branch_relations"))
    seasonal_effect = _mapping_copy(value.get("seasonal_effect"))
    tiaohou_effect = _mapping_copy(value.get("tiaohou_effect"))
    structural_changes = _bazi_year_structural_changes(value.get("structural_changes"))
    seasonal_tiaohou_delta = _mapping_copy(value.get("seasonal_tiaohou_delta"))
    shensha_auxiliary = _bazi_shensha(value.get("shensha_auxiliary"))
    if not all(
        (
            start_inclusive,
            end_exclusive,
            ganzhi,
            stem_ten_god,
            hidden_ten_gods,
            seasonal_effect,
            tiaohou_effect,
            structural_changes,
            seasonal_tiaohou_delta,
            shensha_auxiliary,
        )
    ) or branch_relations is None:
        return None
    return BaziYearSegment(
        start_inclusive=cast(str, start_inclusive),
        end_exclusive=cast(str, end_exclusive),
        ganzhi=cast(str, ganzhi),
        stem_ten_god=cast(str, stem_ten_god),
        branch_hidden_ten_gods=cast(tuple[BaziYearTenGod, ...], hidden_ten_gods),
        branch_relations=branch_relations,
        seasonal_effect=cast(dict[str, object], seasonal_effect),
        tiaohou_effect=cast(dict[str, object], tiaohou_effect),
        structural_changes=cast(BaziYearStructuralChanges, structural_changes),
        seasonal_tiaohou_delta=cast(dict[str, object], seasonal_tiaohou_delta),
        shensha_auxiliary=cast(BaziShenshaAuxiliary, shensha_auxiliary),
    )


def _bazi_year_layer(value: object) -> BaziYearLayer | None:
    if not isinstance(value, Mapping):
        return None
    year = value.get("year")
    if isinstance(year, bool) or not isinstance(year, int) or not 1800 <= year <= 2199:
        return None
    ganzhi = _text(value.get("ganzhi"))
    stem_ten_god = _text(value.get("stem_ten_god"))
    hidden_ten_gods = _bazi_year_ten_gods(value.get("branch_hidden_ten_gods"))
    branch_relations = _bazi_year_relations(value.get("branch_relations"))
    structural_changes = _bazi_year_structural_changes(value.get("structural_changes"))
    shensha_auxiliary = _bazi_shensha(value.get("shensha_auxiliary"))
    active_luck_cycle = _mapping_copy(value.get("active_luck_cycle"))
    seasonal_effect = _mapping_copy(value.get("seasonal_effect"))
    tiaohou_effect = _mapping_copy(value.get("tiaohou_effect"))
    seasonal_tiaohou_delta = _mapping_copy(value.get("seasonal_tiaohou_delta"))
    calendar_normalization = _mapping_copy(value.get("calendar_normalization"))
    rule_trace_raw = value.get("rule_trace")
    segments_raw = value.get("ganzhi_segments")
    if not isinstance(rule_trace_raw, (list, tuple)) or not rule_trace_raw:
        return None
    rule_trace: list[BaziYearRuleTrace] = []
    for item in rule_trace_raw:
        if not isinstance(item, Mapping):
            return None
        rule_id = _text(item.get("rule_id"))
        source_dependency_id = _text(item.get("source_dependency_id"))
        operation = _text(item.get("operation"))
        if not all((rule_id, source_dependency_id, operation)):
            return None
        rule_trace.append(
            BaziYearRuleTrace(
                rule_id=cast(str, rule_id),
                source_dependency_id=cast(str, source_dependency_id),
                operation=cast(str, operation),
            )
        )
    if not isinstance(segments_raw, (list, tuple)) or len(segments_raw) != 2:
        return None
    segments = tuple(_bazi_year_segment(item) for item in segments_raw)
    if any(item is None for item in segments):
        return None
    if not all(
        (
            ganzhi,
            stem_ten_god,
            hidden_ten_gods,
            structural_changes,
            shensha_auxiliary,
            active_luck_cycle,
            seasonal_effect,
            tiaohou_effect,
            seasonal_tiaohou_delta,
            calendar_normalization,
        )
    ) or branch_relations is None:
        return None
    return BaziYearLayer(
        year=year,
        ganzhi=cast(str, ganzhi),
        stem_ten_god=cast(str, stem_ten_god),
        branch_hidden_ten_gods=cast(tuple[BaziYearTenGod, ...], hidden_ten_gods),
        branch_relations=branch_relations,
        structural_changes=cast(BaziYearStructuralChanges, structural_changes),
        shensha_auxiliary=cast(BaziShenshaAuxiliary, shensha_auxiliary),
        active_luck_cycle=cast(dict[str, object], active_luck_cycle),
        seasonal_effect=cast(dict[str, object], seasonal_effect),
        tiaohou_effect=cast(dict[str, object], tiaohou_effect),
        seasonal_tiaohou_delta=cast(dict[str, object], seasonal_tiaohou_delta),
        calendar_normalization=cast(dict[str, object], calendar_normalization),
        rule_trace=tuple(rule_trace),
        ganzhi_segments=tuple(cast(BaziYearSegment, item) for item in segments),
    )


def _bazi_year_layers(value: object) -> tuple[BaziYearLayer, ...] | None:
    if not isinstance(value, Mapping) or not value:
        return None
    layers: list[BaziYearLayer] = []
    for key, raw_layer in sorted(value.items(), key=lambda item: str(item[0])):
        layer = _bazi_year_layer(raw_layer)
        if layer is None or str(layer.year) != str(key):
            return None
        layers.append(layer)
    return tuple(layers)


def _bazi_temporal_layers(
    value: object,
    *,
    granularity: Literal["month", "day"],
) -> tuple[BaziTemporalLayer, ...] | None:
    if not isinstance(value, Mapping) or not value:
        return None
    result: list[BaziTemporalLayer] = []
    for key, raw in sorted(value.items(), key=lambda item: str(item[0])):
        if not isinstance(raw, Mapping):
            return None
        period = str(key)
        year = _integer(raw.get("year"))
        month = _integer(raw.get("month"))
        raw_date = _text(raw.get("date"))
        if granularity == "day" and raw_date is not None:
            date_parts = raw_date.split("-")
            if len(date_parts) == 3:
                if year is None:
                    year = _integer(int(date_parts[0])) if date_parts[0].isdigit() else None
                if month is None:
                    month = _integer(int(date_parts[1])) if date_parts[1].isdigit() else None
        segments_raw = raw.get("ganzhi_segments")
        segments = (
            tuple(_mapping_copy(item) for item in segments_raw)
            if isinstance(segments_raw, (list, tuple))
            else ()
        )
        structural_changes = _mapping_copy(raw.get("structural_changes"))
        seasonal_tiaohou_delta = _mapping_copy(raw.get("seasonal_tiaohou_delta"))
        shensha_auxiliary = _mapping_copy(raw.get("shensha_auxiliary"))
        active_luck_cycle = _mapping_copy(raw.get("active_luck_cycle"))
        calendar_normalization = _mapping_copy(raw.get("calendar_normalization"))
        rule_trace_raw = raw.get("rule_trace")
        rule_trace = (
            tuple(_mapping_copy(item) for item in rule_trace_raw)
            if isinstance(rule_trace_raw, (list, tuple))
            else ()
        )
        active_transits = _mapping_copy(raw.get("active_transits"))
        representative_instant = _text(raw.get("representative_instant"))
        if (
            year is None
            or not 1800 <= year <= 2199
            or (granularity == "month" and (month is None or not 1 <= month <= 12))
            or (granularity == "day" and raw_date is None)
            or not segments
            or any(item is None for item in segments)
            or structural_changes is None
            or seasonal_tiaohou_delta is None
            or shensha_auxiliary is None
            or active_luck_cycle is None
            or calendar_normalization is None
            or not rule_trace
            or any(item is None for item in rule_trace)
        ):
            return None
        result.append(
            BaziTemporalLayer(
                granularity=granularity,
                period=period,
                year=year,
                month=month,
                date=raw_date,
                ganzhi_segments=tuple(cast(dict[str, object], item) for item in segments),
                active_transits=active_transits,
                structural_changes=structural_changes,
                seasonal_tiaohou_delta=seasonal_tiaohou_delta,
                shensha_auxiliary=shensha_auxiliary,
                active_luck_cycle=active_luck_cycle,
                calendar_normalization=calendar_normalization,
                representative_instant=representative_instant,
                rule_trace=tuple(cast(dict[str, object], item) for item in rule_trace),
            )
        )
    return tuple(result)


def _bazi_calendar_normalization(value: object) -> BaziCalendarNormalization | None:
    plain = _plain_mapping_copy(value)
    if plain is None:
        return None
    try:
        return BaziCalendarNormalization.model_validate(plain)
    except (TypeError, ValueError):
        return None


def _bazi_exact_evidence_rule_id(raw: Mapping[object, object], ref: str) -> str | None:
    if raw.get("verification_status") != "verified_exact":
        return None
    evidence_ref = raw.get("evidence_ref")
    rule_id = raw.get("rule_id")
    verbatim_excerpt = raw.get("verbatim_excerpt")
    source_title = raw.get("source_title")
    locator = raw.get("locator")
    citations = raw.get("verbatim_citations")
    if (
        evidence_ref != ref
        or not isinstance(rule_id, str)
        or not rule_id.strip()
        or ref != f"evidence:bazi/{rule_id}"
        or not isinstance(verbatim_excerpt, str)
        or not verbatim_excerpt.strip()
        or not isinstance(source_title, str)
        or not source_title.strip()
        or not isinstance(locator, str)
        or not locator.strip()
        or not isinstance(citations, (list, tuple))
        or not citations
    ):
        return None
    normalized: list[tuple[str, str, str]] = []
    for citation in citations:
        if not isinstance(citation, Mapping):
            return None
        citation_title = citation.get("source_title")
        citation_locator = citation.get("locator")
        citation_excerpt = citation.get("verbatim_excerpt")
        if (
            citation.get("verification_status") != "verified_exact"
            or not isinstance(citation_title, str)
            or not citation_title.strip()
            or not isinstance(citation_locator, str)
            or not citation_locator.strip()
            or not isinstance(citation_excerpt, str)
            or not citation_excerpt.strip()
        ):
            return None
        normalized.append((citation_title, citation_locator, citation_excerpt))
    if normalized[0] != (source_title, locator, verbatim_excerpt):
        return None
    legacy_excerpt = raw.get("excerpt")
    if legacy_excerpt is not None and legacy_excerpt != normalized[0][2]:
        return None
    return rule_id


def _bazi_evidence_refs(value: object) -> dict[str, str]:
    if not isinstance(value, (list, tuple)):
        return {}
    refs: dict[str, str] = {}
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        ref = raw.get("ref")
        if not isinstance(ref, str) or not ref.strip():
            continue
        rule_id = _bazi_exact_evidence_rule_id(raw, ref)
        if rule_id is not None:
            refs[rule_id] = ref
    return refs


def _bazi_source_conditioned_patterns(
    value: object,
    evidence: object,
) -> tuple[BaziSourcePattern, ...] | None:
    patterns = _source_conditioned_patterns(value, BaziSourcePattern)
    if patterns is None:
        return None
    evidence_refs = _bazi_evidence_refs(evidence)
    return tuple(
        pattern.model_copy(
            update={
                "evidence_ref": evidence_refs.get(pattern.rule_id),
            }
        )
        for pattern in patterns
    )


def _bazi_core_facts(
    facts: object,
    *,
    evidence: object = None,
) -> BaziCoreFacts | None:
    calculated = {
        key: _brief_fact_value(facts, key)
        for key in (
            "day_master",
            "hidden_stems",
            "ten_gods",
            "nayin",
            "twelve_growth_stages",
            "xunkong",
            "san_yuan",
            "month_command",
            "seasonal_profile",
            "tiaohou_markers",
            "element_inventory",
            "interpretive_candidates",
            "source_conditioned_patterns",
            "branch_relations",
            "shensha_auxiliary",
            "luck_cycles",
            "calendar_normalization",
            "year_layers",
            "month_layers",
            "day_layers",
        )
    }
    core = BaziCoreFacts(
        day_master=_bazi_day_master(_calculated_value(calculated, "day_master")),
        hidden_stems=_bazi_hidden_stems(_calculated_value(calculated, "hidden_stems")),
        ten_gods=_bazi_ten_gods(_calculated_value(calculated, "ten_gods")),
        nayin=_bazi_nayin(_calculated_value(calculated, "nayin")),
        twelve_growth_stages=_bazi_growth_stages(
            _calculated_value(calculated, "twelve_growth_stages")
        ),
        xunkong=_bazi_xunkong(_calculated_value(calculated, "xunkong")),
        san_yuan=_bazi_san_yuan(_calculated_value(calculated, "san_yuan")),
        month_command=_bazi_month_command(
            _calculated_value(calculated, "month_command")
        ),
        seasonal_profile=_bazi_seasonal_profile(
            _calculated_value(calculated, "seasonal_profile")
        ),
        tiaohou_markers=_bazi_tiaohou(
            _calculated_value(calculated, "tiaohou_markers")
        ),
        element_inventory=_bazi_element_inventory(
            _calculated_value(calculated, "element_inventory")
        ),
        interpretive_candidates=_bazi_interpretive_candidates(
            _calculated_value(calculated, "interpretive_candidates")
        ),
        source_conditioned_patterns=_bazi_source_conditioned_patterns(
            _calculated_value(calculated, "source_conditioned_patterns"),
            evidence,
        )
        or (),
        branch_relations=_bazi_branch_relations(
            _calculated_value(calculated, "branch_relations")
        ),
        shensha_auxiliary=_bazi_shensha(
            _calculated_value(calculated, "shensha_auxiliary")
        ),
        luck_cycles=_bazi_luck_cycles(_calculated_value(calculated, "luck_cycles")),
        calendar_normalization=_bazi_calendar_normalization(
            _calculated_value(calculated, "calendar_normalization")
        ),
        year_layers=_bazi_year_layers(_calculated_value(calculated, "year_layers")),
        month_layers=_bazi_temporal_layers(
            _calculated_value(calculated, "month_layers"),
            granularity="month",
        ),
        day_layers=_bazi_temporal_layers(
            _calculated_value(calculated, "day_layers"),
            granularity="day",
        ),
    )
    return core if any(value is not None for value in core.model_dump().values()) else None


def _five_elements_source_identity(value: object) -> FiveElementsSourceIdentity | None:
    if not isinstance(value, Mapping):
        return None
    raw_identity = value.get("applicability_identity")
    identity = raw_identity if isinstance(raw_identity, Mapping) else value
    fields = {
        "day_stem": _text(identity.get("day_stem")),
        "month_branch": _text(identity.get("month_branch")),
        "source_dependency_id": _text(identity.get("source_dependency_id")),
        "source_section_id": _text(
            identity.get("source_section_id")
            or identity.get("section_id")
            or identity.get("chapter_id")
            or identity.get("chapter")
        ),
        "source_rule_id": _text(
            identity.get("source_rule_id")
            or identity.get("rule_id")
            or identity.get("active_source_rule_id")
        ),
    }
    if not any(fields.values()):
        return None
    return FiveElementsSourceIdentity(**fields)


def _five_elements_source_ids(
    value: object,
) -> tuple[tuple[str, ...], tuple[str, ...], FiveElementsSourceIdentity | None]:
    identity = _five_elements_source_identity(value)
    active_rule_ids: list[str] = []
    dependency_ids: list[str] = []
    if isinstance(value, Mapping):
        for key in ("active_source_rule_ids", "source_rule_ids", "active_rule_ids"):
            raw_ids = value.get(key)
            if isinstance(raw_ids, (list, tuple)):
                active_rule_ids.extend(
                    item.strip()
                    for item in raw_ids
                    if isinstance(item, str) and item.strip()
                )
        if identity is not None:
            if identity.source_rule_id is not None:
                active_rule_ids.append(identity.source_rule_id)
            if identity.source_dependency_id is not None:
                dependency_ids.append(identity.source_dependency_id)
    return (
        tuple(dict.fromkeys(active_rule_ids)),
        tuple(dict.fromkeys(dependency_ids)),
        identity,
    )


def project_five_elements_facts_view_model(
    brief: Mapping[str, object] | None,
) -> FiveElementsFactsViewV1 | None:
    """Project only calculated element/seasonal facts, never a verdict."""

    if brief is None or not _capability_is(brief, "bazi"):
        return None
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    if subject_ref is None:
        return None
    calculated = {
        key: _brief_fact_value(facts, key)
        for key in (
            "day_master",
            "month_command",
            "seasonal_profile",
            "tiaohou_markers",
            "element_inventory",
            "interpretive_candidates",
        )
    }
    day_master = _bazi_day_master(_calculated_value(calculated, "day_master"))
    month_command = _bazi_month_command(
        _calculated_value(calculated, "month_command")
    )
    seasonal_profile = _bazi_seasonal_profile(
        _calculated_value(calculated, "seasonal_profile")
    )
    tiaohou_value = _calculated_value(calculated, "tiaohou_markers")
    tiaohou_markers = _bazi_tiaohou(tiaohou_value)
    inventory = _bazi_element_inventory(
        _calculated_value(calculated, "element_inventory")
    )
    interpretive_candidates = _bazi_interpretive_candidates(
        _calculated_value(calculated, "interpretive_candidates")
    )
    active_rule_ids, dependency_ids, source_identity = _five_elements_source_ids(
        tiaohou_value
    )
    source_status: Literal["exact_rule_bound", "identity_only", "unavailable"] = (
        "exact_rule_bound"
        if active_rule_ids
        else "identity_only"
        if source_identity is not None
        else "unavailable"
    )
    source_gaps = tuple(
        [
            f"Runtime 未返回 {field_id} 事实。"
            for field_id, value in (
                ("day_master", day_master),
                ("month_command", month_command),
                ("seasonal_profile", seasonal_profile),
                ("tiaohou_markers", tiaohou_markers),
                ("element_inventory", inventory),
            )
            if value is None
        ]
        + (
            ["当前 Runtime 只返回调候适用性身份，未返回逐条来源规则 ID。"]
            if tiaohou_markers is not None and not active_rule_ids
            else []
        )
    )
    return FiveElementsFactsViewV1(
        subject_ref=subject_ref,
        day_master=day_master,
        month_command=month_command,
        seasonal_profile=seasonal_profile,
        tiaohou_markers=tiaohou_markers,
        element_inventory=inventory,
        interpretive_candidates=interpretive_candidates,
        source_identity=source_identity,
        active_source_rule_ids=active_rule_ids,
        source_dependency_ids=dependency_ids,
        source_status=source_status,
        source_gaps=source_gaps,
        limitations=(
            "五行计数只表示盘面库存，不直接决定旺衰、喜忌或用神。",
            "调候标记只表示月令气候事实，不单独形成调候用神结论。",
            "强弱证据、结构候选与合冲信号只展示 Runtime 机械输出，不形成最终格局或吉凶结论。",
        ),
    )


def _brief_fact_value(facts: object, field_id: str) -> tuple[str, object] | None:
    """Find one calculated fact without reading caller input facts."""

    if not isinstance(facts, (list, tuple)):
        return None
    for item in facts:
        if not isinstance(item, Mapping):
            continue
        ref = item.get("ref")
        if not isinstance(ref, str) or "/input/" in ref:
            continue
        if ref.rstrip("/").rsplit("/", 1)[-1] == field_id:
            subject_ref = item.get("subject_ref")
            return (
                str(subject_ref) if isinstance(subject_ref, str) else "",
                item.get("value"),
            )
    return None


def _subject_ref(payload: Mapping[str, object], facts: object) -> str | None:
    pillar_fact = _brief_fact_value(facts, "four_pillars")
    if pillar_fact is not None and pillar_fact[0].strip():
        return pillar_fact[0]
    request_view = payload.get("request_view")
    if isinstance(request_view, Mapping):
        subjects = request_view.get("subject_refs")
        if isinstance(subjects, (list, tuple)) and subjects:
            subject = subjects[0]
            if isinstance(subject, str) and subject.strip():
                return subject
    return None


def _capability_is(brief: Mapping[str, object], capability_id: str) -> bool:
    request_view = brief.get("request_view")
    if not isinstance(request_view, Mapping):
        return False
    capability_ids = request_view.get("capability_ids")
    return isinstance(capability_ids, (list, tuple)) and capability_id in capability_ids


def _request_horizon_kind(brief: Mapping[str, object]) -> str | None:
    request_view = brief.get("request_view")
    if not isinstance(request_view, Mapping):
        return None
    horizon = request_view.get("horizon")
    if not isinstance(horizon, Mapping):
        return None
    kind = horizon.get("kind_id")
    return kind if isinstance(kind, str) else None


def _question(brief: Mapping[str, object]) -> str | None:
    question = brief.get("question")
    return question if isinstance(question, str) and question.strip() else None


def _wenshi_liuren_rule_evidence_signals(
    *,
    fact_ref: str,
    fact_value: object,
    subject_ref: str,
    dimension_id: str,
) -> tuple[ArtSignal, ...]:
    """Project only Runtime-declared, source-bound Liuren rule evidence.

    ``rule_evidence`` is deliberately an evidence lane, not an adjudication
    result.  A matched row is publishable only when Runtime supplied its rule
    identity, source references, and fact paths.  The host does not infer
    polarity, combine rules, or turn this lane into cross-art convergence.
    """

    if not isinstance(fact_value, Mapping):
        return ()
    rule_evidence = fact_value.get("rule_evidence")
    if not isinstance(rule_evidence, Mapping):
        return ()
    matched = rule_evidence.get("matched")
    if not isinstance(matched, (list, tuple)):
        return ()
    signals: list[ArtSignal] = []
    seen_rule_keys: set[str] = set()
    for raw_row in matched:
        if not isinstance(raw_row, Mapping):
            continue
        if raw_row.get("status") != "matched":
            continue
        rule_key = raw_row.get("rule_key")
        rule_id = raw_row.get("rule_id")
        source_refs = raw_row.get("source_refs")
        fact_paths = raw_row.get("fact_paths")
        if (
            not isinstance(rule_key, str)
            or not rule_key.strip()
            or not isinstance(rule_id, str)
            or not rule_id.strip()
            or not isinstance(source_refs, (list, tuple))
            or not all(isinstance(item, Mapping) for item in source_refs)
            or not isinstance(fact_paths, (list, tuple))
            or not all(isinstance(item, str) and item.strip() for item in fact_paths)
            or rule_key in seen_rule_keys
        ):
            continue
        seen_rule_keys.add(rule_key)
        signals.append(
            ArtSignal(
                art_id="daliuren",
                subject_refs=(subject_ref,),
                signal_id=f"daliuren.{dimension_id}.rule_evidence.{rule_key}",
                display_text=(
                    f"大六壬已提供来源绑定规则证据（{rule_id}）；"
                    "当前仍不形成问事合参结论。"
                ),
                fact_refs=(fact_ref,),
            )
        )
    return tuple(signals)


def _wenshi_liuren_timing_candidate_signals(
    *,
    fact_ref: str,
    fact_value: object,
    subject_ref: str,
    dimension_id: str,
) -> tuple[ArtSignal, ...]:
    """Expose Runtime timing candidates without turning them into an outcome."""

    if not isinstance(fact_value, Mapping) or dimension_id != "timing":
        return ()
    present_fields = tuple(
        field
        for field in ("relative_speed", "candidate_branch", "candidate_date")
        if isinstance(fact_value.get(field), str)
        and bool(fact_value[field].strip())
    )
    if not present_fields:
        return ()
    return (
        ArtSignal(
            art_id="daliuren",
            subject_refs=(subject_ref,),
            signal_id="daliuren.timing.timing_candidate_evidence",
            display_text=(
                "大六壬已提供应期候选/迟速材料（"
                + "、".join(present_fields)
                + "）；当前仅保留候选事实，不形成问事合参结论。"
            ),
            fact_refs=(fact_ref,),
        ),
    )


def _wenshi_liuyao_candidate_signals(
    *,
    fact_ref: str,
    fact_value: object,
    subject_ref: str,
    dimension_id: str,
) -> tuple[ArtSignal, ...]:
    """Project Liuyao's calculated candidate pools into Wenshi.

    The Runtime always labels these rows as candidate facts.  Wenshi may show
    that a six-relative pool exists, but it must not select a useful spirit or
    turn the pool into an outcome judgment without a separate school contract.
    """

    if not isinstance(fact_value, Mapping):
        return ()
    candidates = fact_value
    signals: list[ArtSignal] = []
    seen_relatives: set[str] = set()
    for raw_relative, raw_rows in candidates.items():
        relative = raw_relative if isinstance(raw_relative, str) else None
        if (
            relative is None
            or not relative.strip()
            or relative in seen_relatives
            or not isinstance(raw_rows, (list, tuple))
        ):
            continue
        row_count = sum(isinstance(row, Mapping) for row in raw_rows)
        if row_count == 0:
            continue
        seen_relatives.add(relative)
        signals.append(
            ArtSignal(
                art_id="liuyao",
                subject_refs=(subject_ref,),
                signal_id=(
                    f"liuyao.{dimension_id}.useful_spirit_candidates.{relative}"
                ),
                display_text=(
                    f"六爻已提供“{relative}”候选池（{row_count}条）；"
                    "当前仅保留候选事实，不形成问事合参结论。"
                ),
                fact_refs=(fact_ref,),
            )
        )
    return tuple(signals)


def _wenshi_liuyao_selection_signals(
    *,
    fact_ref: str,
    fact_value: object,
    subject_ref: str,
    dimension_id: str,
) -> tuple[ArtSignal, ...]:
    """Project Liuyao's bounded useful-spirit evidence into Wenshi.

    Candidate chain and strength lanes remain non-verdict evidence.  A checked
    Runtime role adjudication may identify six-relative roles for an explicit
    question class and may identify either a sole visible line or the only
    moving line among exactly two visible candidates. Strength, event result,
    and timing remain unresolved.
    """

    if not isinstance(fact_value, Mapping):
        return ()
    if fact_value.get("status") not in {"evidence_bound", "candidate_only"}:
        return ()
    if fact_value.get("hard_verdict") is not None:
        return ()
    source_dependency_id = fact_value.get("source_dependency_id")
    if not isinstance(source_dependency_id, str) or not source_dependency_id.strip():
        return ()
    signals: list[ArtSignal] = []
    role_adjudication = fact_value.get("role_adjudication")
    if isinstance(role_adjudication, Mapping):
        source_ref = role_adjudication.get("source_ref")
        supporting = role_adjudication.get("supporting_relatives")
        line_adjudication = role_adjudication.get("specific_line_adjudication")
        line_selection = role_adjudication.get("specific_line_selection")
        line_text: str | None = None
        if isinstance(line_adjudication, Mapping):
            raw_visible_lines = line_adjudication.get("visible_candidate_lines")
            visible_lines = (
                tuple(
                    item
                    for item in raw_visible_lines
                    if isinstance(item, int)
                    and not isinstance(item, bool)
                    and item in range(1, 7)
                )
                if isinstance(raw_visible_lines, (list, tuple))
                else ()
            )
            raw_moving_lines = line_adjudication.get(
                "moving_visible_candidate_lines"
            )
            moving_lines = (
                tuple(
                    item
                    for item in raw_moving_lines
                    if isinstance(item, int)
                    and not isinstance(item, bool)
                    and item in range(1, 7)
                    and item in visible_lines
                )
                if isinstance(raw_moving_lines, (list, tuple))
                else ()
            )
            counts_match = (
                line_adjudication.get("visible_candidate_count")
                == len(visible_lines)
                and line_adjudication.get("moving_visible_candidate_count")
                == len(moving_lines)
            )
            if (
                line_adjudication.get("status")
                == "adjudicated_unique_visible_line"
                and len(visible_lines) == 1
                and counts_match
                and line_selection == visible_lines[0]
                and line_adjudication.get("specific_line_selection")
                == line_selection
                and line_adjudication.get("hard_verdict") is None
            ):
                line_text = f"盘内唯一可见妻财为第{line_selection}爻"
            elif (
                line_adjudication.get("status")
                == "adjudicated_single_moving_visible_line"
                and len(visible_lines) == 2
                and len(moving_lines) == 1
                and counts_match
                and line_selection == moving_lines[0]
                and line_adjudication.get("specific_line_selection")
                == line_selection
                and line_adjudication.get("hard_verdict") is None
                and isinstance(
                    line_adjudication.get("selection_source_ref"), Mapping
                )
                and line_adjudication["selection_source_ref"].get("rule_id")
                == "ZR-04-04"
                and line_adjudication["selection_source_ref"].get(
                    "verification_status"
                )
                == "verified"
            ):
                line_text = (
                    f"妻财两现且仅第{line_selection}爻发动，"
                    f"按核验规则取第{line_selection}爻"
                )
            elif (
                line_adjudication.get("status")
                == "unresolved_multiple_visible_lines"
                and len(visible_lines) >= 2
                and counts_match
                and line_selection is None
                and line_adjudication.get("specific_line_selection") is None
            ):
                line_text = "多个可见妻财爻同动静，仍待完整旺衰裁定取舍"
            elif (
                line_adjudication.get("status") == "unresolved_no_visible_line"
                and not visible_lines
                and not moving_lines
                and counts_match
                and line_selection is None
                and line_adjudication.get("specific_line_selection") is None
            ):
                line_text = "盘内无可见妻财爻，伏神或变爻取用仍未裁定"
        if (
            role_adjudication.get("status")
            == "adjudicated_question_role_set"
            and role_adjudication.get("question_class") == "finance"
            and role_adjudication.get("primary_relative") == "妻财"
            and isinstance(supporting, (list, tuple))
            and tuple(supporting) == ("子孙",)
            and role_adjudication.get("hard_verdict") is None
            and line_text is not None
            and isinstance(source_ref, Mapping)
            and source_ref.get("rule_id") == "HJC-R009"
            and source_ref.get("verification_status") == "verified"
        ):
            signals.append(
                ArtSignal(
                    art_id="liuyao",
                    subject_refs=(subject_ref,),
                    signal_id=(
                        f"liuyao.{dimension_id}."
                        "useful_spirit_selection.role_adjudication"
                    ),
                    display_text=(
                        "六爻已按核验来源裁定求财问题角色："
                        f"妻财为主、子孙为辅；{line_text}；"
                        "不形成问事合参结论。"
                    ),
                    fact_refs=(fact_ref,),
                )
            )
    for lane, label in (
        ("chain_candidates", "用神链候选"),
        ("strength_evidence", "旺衰证据"),
    ):
        lane_value = fact_value.get(lane)
        if not isinstance(lane_value, (Mapping, list, tuple)) or not lane_value:
            continue
        signals.append(
            ArtSignal(
                art_id="liuyao",
                subject_refs=(subject_ref,),
                signal_id=f"liuyao.{dimension_id}.useful_spirit_selection.{lane}",
                display_text=(
                    f"六爻已提供{label}（证据绑定）；"
                    "当前仅保留候选事实，不形成问事合参结论。"
                ),
                fact_refs=(fact_ref,),
            )
        )
    return tuple(signals)


def _wenshi_qimen_pattern_signals(
    *,
    fact_ref: str,
    fact_value: object,
    subject_ref: str,
    dimension_id: str,
) -> tuple[ArtSignal, ...]:
    """Project source-adjudicated Qimen identities without event polarity."""

    if not isinstance(fact_value, (list, tuple)):
        return ()
    signals: list[ArtSignal] = []
    seen_pattern_ids: set[str] = set()
    for raw_pattern in fact_value:
        if not isinstance(raw_pattern, Mapping):
            continue
        pattern_id = raw_pattern.get("id")
        name = raw_pattern.get("name")
        status = raw_pattern.get("status")
        palace = raw_pattern.get("palace")
        adjudication = raw_pattern.get("identity_adjudication")
        source_ref = (
            adjudication.get("source_ref")
            if isinstance(adjudication, Mapping)
            else None
        )
        if (
            not isinstance(pattern_id, str)
            or not pattern_id.strip()
            or pattern_id in seen_pattern_ids
            or not isinstance(name, str)
            or not name.strip()
            or status != "predicate_matched_not_verdict"
            or isinstance(palace, bool)
            or (palace is not None and not isinstance(palace, int))
            or not isinstance(adjudication, Mapping)
            or adjudication.get("status") != "adjudicated_pattern_identity"
            or adjudication.get("pattern_id") != pattern_id
            or adjudication.get("pattern_name") != name
            or adjudication.get("palace") != palace
            or adjudication.get("hard_verdict") is not None
            or adjudication.get("event_verdict") is not None
            or not isinstance(source_ref, Mapping)
            or source_ref.get("rule_id") != pattern_id
            or source_ref.get("verification_status") != "verified"
        ):
            continue
        seen_pattern_ids.add(pattern_id)
        scope = "全局" if palace is None else f"第{palace}宫"
        signals.append(
            ArtSignal(
                art_id="qimen",
                subject_refs=(subject_ref,),
                signal_id=f"qimen.{dimension_id}.named_pattern.{pattern_id}",
                display_text=(
                    f"奇门已按核验来源裁定格局身份“{name}”"
                    f"（{pattern_id}，{scope}）；仍未裁定格局强弱或事项吉凶，"
                    "不形成问事合参结论。"
                ),
                fact_refs=(fact_ref,),
            )
        )
    return tuple(signals)


def _natal_time_layers(
    art_name: str,
    *,
    year_available: bool = False,
    month_available: bool = False,
    day_available: bool = False,
) -> tuple[TimeLayer, ...]:
    return (
        TimeLayer(layer_id="life", label="本命", available=True),
        TimeLayer(
            layer_id="year",
            label="流年",
            available=year_available,
            unavailable_reason=(
                None
                if year_available
                else f"本次{art_name}结果只返回本命盘，尚未返回逐年盘面。"
            ),
        ),
        TimeLayer(
            layer_id="month",
            label="流月",
            available=month_available,
            unavailable_reason=(
                None
                if month_available
                else f"本次{art_name}结果只返回本命盘，尚未返回逐月盘面。"
            ),
        ),
        TimeLayer(
            layer_id="day",
            label="流日",
            available=day_available,
            unavailable_reason=(
                None
                if day_available
                else f"本次{art_name}结果未返回逐日盘面。"
            ),
        ),
    )


def _pillars(value: object) -> tuple[Pillar, ...] | None:
    if not isinstance(value, Mapping):
        return None
    result: list[Pillar] = []
    for position in _BAZI_PILLAR_POSITIONS:
        raw = value.get(position)
        if not isinstance(raw, str) or len(raw) < 2:
            return None
        result.append(Pillar(position=position, stem=raw[0], branch=raw[1]))
    return tuple(result)


def _element_balance(value: object) -> tuple[ElementBalance, ...]:
    if not isinstance(value, Mapping):
        return ()
    counts = value.get("visible_stem_branch_counts")
    if not isinstance(counts, Mapping):
        return ()
    result: list[ElementBalance] = []
    for element_id, label in _BAZI_ELEMENTS:
        raw_count = counts.get(label)
        if isinstance(raw_count, bool) or not isinstance(raw_count, (int, float)):
            continue
        if not math.isfinite(float(raw_count)) or raw_count < 0:
            continue
        result.append(
            ElementBalance(
                element=element_id,
                value=float(raw_count),
                display_text=f"{label} · 可见干支计数 {raw_count:g}（不等同旺衰裁决）",
            )
        )
    return tuple(result)


def _time_layers(
    *,
    year_available: bool = False,
    month_available: bool = False,
    day_available: bool = False,
) -> tuple[TimeLayer, ...]:
    return (
        TimeLayer(layer_id="life", label="本命", available=True),
        TimeLayer(
            layer_id="year",
            label="流年",
            available=year_available,
            unavailable_reason=(
                None
                if year_available
                else "本次结果只返回本命四柱，尚未返回逐年盘面。"
            ),
        ),
        TimeLayer(
            layer_id="month",
            label="流月",
            available=month_available,
            unavailable_reason=(
                None if month_available else "本次结果只返回本命四柱，尚未返回逐月盘面。"
            ),
        ),
        TimeLayer(
            layer_id="day",
            label="流日",
            available=day_available,
            unavailable_reason=(
                None if day_available else "本次结果只返回本命四柱，尚未返回逐日盘面。"
            ),
        ),
    )


def project_bazi_view_model(
    brief: Mapping[str, object] | None,
) -> BaziChartV1 | None:
    """Project calculated Runtime facts into the typed Bazi chart contract.

    The projector ignores input facts and interpretive findings. Runtime stays
    the authority for calculation; this layer only validates and arranges
    values for rendering.
    """

    if brief is None:
        return None
    facts = brief.get("facts")
    request_view = brief.get("request_view")
    if not isinstance(request_view, Mapping):
        return None
    capability_ids = request_view.get("capability_ids")
    if not isinstance(capability_ids, (list, tuple)) or "bazi" not in capability_ids:
        return None
    pillars_fact = _brief_fact_value(facts, "four_pillars")
    if pillars_fact is None:
        return None
    subject_ref = _subject_ref(brief, facts)
    pillars = _pillars(pillars_fact[1])
    if subject_ref is None or pillars is None:
        return None
    inventory = _brief_fact_value(facts, "element_inventory")
    year_fact = _brief_fact_value(facts, "year_layers")
    month_fact = _brief_fact_value(facts, "month_layers")
    day_fact = _brief_fact_value(facts, "day_layers")
    year_layers = _bazi_year_layers(year_fact[1] if year_fact is not None else None)
    month_layers = _bazi_temporal_layers(
        month_fact[1] if month_fact is not None else None,
        granularity="month",
    )
    day_layers = _bazi_temporal_layers(
        day_fact[1] if day_fact is not None else None,
        granularity="day",
    )
    return BaziChartV1(
        subject_ref=subject_ref,
        pillars=pillars,
        element_balance=_element_balance(inventory[1] if inventory else None),
        time_layers=_time_layers(
            year_available=year_layers is not None,
            month_available=month_layers is not None,
            day_available=day_layers is not None,
        ),
        core_facts=_bazi_core_facts(facts, evidence=brief.get("evidence")),
    )


def _calculated_fact_for_subject(
    facts: object,
    *,
    subject_ref: str,
    suffix: str,
) -> tuple[str, object] | None:
    if not isinstance(facts, (list, tuple)):
        return None
    for item in facts:
        if not isinstance(item, Mapping):
            continue
        ref = item.get("ref")
        if (
            not isinstance(ref, str)
            or "/input/" in ref
            or not ref.endswith(suffix)
            or item.get("subject_ref") != subject_ref
        ):
            continue
        return ref, item.get("value")
    return None


def project_chart_similarity_view_model(
    brief: Mapping[str, object] | None,
) -> ChartSimilarityViewV1 | None:
    """Project the bounded exact Bazi four-pillar comparison."""

    if brief is None:
        return None
    request_view = brief.get("request_view")
    if not isinstance(request_view, Mapping):
        return None
    subjects = request_view.get("subject_refs")
    if (
        not isinstance(subjects, (list, tuple))
        or len(subjects) != 2
        or not all(isinstance(item, str) and item.strip() for item in subjects)
        or subjects[0] == subjects[1]
    ):
        return None
    left_subject_ref, right_subject_ref = subjects
    left_fact = _calculated_fact_for_subject(
        brief.get("facts"),
        subject_ref=left_subject_ref,
        suffix="/calculated/bazi/four_pillars",
    )
    right_fact = _calculated_fact_for_subject(
        brief.get("facts"),
        subject_ref=right_subject_ref,
        suffix="/calculated/bazi/four_pillars",
    )
    if left_fact is None or right_fact is None:
        return None
    if not isinstance(left_fact[1], Mapping) or not isinstance(right_fact[1], Mapping):
        return None
    try:
        raw_comparisons = compare_bazi_four_pillars(left_fact[1], right_fact[1])
    except ChartSimilarityInputError:
        return None
    comparisons = tuple(
        ChartSimilarityPillarComparison(
            position=position,
            left=Pillar(position=position, stem=left_value[0], branch=left_value[1]),
            right=Pillar(position=position, stem=right_value[0], branch=right_value[1]),
            exact_match=exact_match,
        )
        for position, left_value, right_value, exact_match in raw_comparisons
    )
    matched_positions = tuple(
        position for position, _left, _right, exact_match in raw_comparisons if exact_match
    )
    differing_positions = tuple(
        position for position, _left, _right, exact_match in raw_comparisons if not exact_match
    )
    return ChartSimilarityViewV1(
        left_subject_ref=left_subject_ref,
        right_subject_ref=right_subject_ref,
        basis="bazi.four_pillars.exact",
        left_fact_ref=left_fact[0],
        right_fact_ref=right_fact[0],
        comparisons=comparisons,
        exact_match=not differing_positions,
        matched_positions=matched_positions,
        differing_positions=differing_positions,
        limitations=(
            "只比较 Runtime 已计算的八字四柱原值，不比较出生资料、姓名或解释候选。",
            "本结果不表示缘分、合婚、性格相似度，也不生成百分比评分。",
        ),
    )


def project_time_check_view_model(
    brief: Mapping[str, object] | None,
) -> TimeCheckViewV1 | None:
    """Project Runtime-owned candidates and bounded event evidence."""

    if brief is None or not _capability_is(brief, "time-check"):
        return None
    facts = brief.get("facts")
    candidate_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="candidates",
    )
    count_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="candidate_count",
    )
    range_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="known_time_range",
    )
    basis_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="time_basis_policy",
    )
    event_count_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="known_event_count",
    )
    ranking_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="ranking_status",
    )
    matching_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="event_matching_status",
    )
    event_input_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="event_input_status",
    )
    ranking_rows_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="candidate_rankings",
    )
    event_matches_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="event_matches",
    )
    rectification_status_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="rectification_status",
    )
    rectification_conclusion_fact = _brief_fact_value_for_capability(
        facts,
        capability_id="time-check",
        field_id="rectification_conclusion",
    )
    if (
        candidate_fact is None
        or count_fact is None
        or range_fact is None
        or basis_fact is None
        or event_count_fact is None
        or ranking_fact is None
        or matching_fact is None
        or not isinstance(candidate_fact[1], (list, tuple))
        or not isinstance(count_fact[1], int)
        or count_fact[1] != 12
        or len(candidate_fact[1]) != 12
        or not isinstance(range_fact[1], Mapping)
        or not isinstance(basis_fact[1], str)
        or not isinstance(event_count_fact[1], int)
        or ranking_fact[1] not in {"not_ranked", "candidate_evidence_ranked"}
        or matching_fact[1] not in {"not_calculated", "structured_evidence"}
    ):
        return None
    try:
        candidates = tuple(
            TimeCheckCandidateV1.model_validate(item)
            for item in candidate_fact[1]
        )
    except (TypeError, ValueError):
        return None
    if len(candidates) != 12:
        return None
    event_input_status = (
        event_input_fact[1]
        if event_input_fact is not None
        else "not_supplied"
    )
    if event_input_status not in {
        "not_supplied",
        "invalid_structured_events",
        "structured_valid",
    }:
        return None
    ranking_rows: tuple[TimeCheckCandidateEvidenceV1, ...] = ()
    if ranking_rows_fact is not None:
        if not isinstance(ranking_rows_fact[1], (list, tuple)):
            return None
        try:
            ranking_rows = tuple(
                TimeCheckCandidateEvidenceV1.model_validate(item)
                for item in ranking_rows_fact[1]
            )
        except (TypeError, ValueError):
            return None
    event_matches: tuple[TimeCheckEventMatchV1, ...] = ()
    if event_matches_fact is not None:
        if not isinstance(event_matches_fact[1], (list, tuple)):
            return None
        try:
            event_matches = tuple(
                TimeCheckEventMatchV1.model_validate(item)
                for item in event_matches_fact[1]
            )
        except (TypeError, ValueError):
            return None
    if ranking_fact[1] == "candidate_evidence_ranked" and len(ranking_rows) != 12:
        return None
    if ranking_fact[1] == "not_ranked" and ranking_rows:
        return None
    rectification_status: (
        Literal[
            "hour_determined",
            "no_valid_candidate",
            "not_attempted",
            "remaining_ambiguous",
        ]
        | None
    ) = None
    rectification_conclusion: TimeCheckRectificationConclusionV1 | None = None
    if rectification_status_fact is None and rectification_conclusion_fact is None:
        pass
    elif rectification_status_fact is None or rectification_conclusion_fact is None:
        return None
    else:
        allowed_status = {
            "hour_determined",
            "no_valid_candidate",
            "not_attempted",
            "remaining_ambiguous",
        }
        if rectification_status_fact[1] not in allowed_status:
            return None
        if not isinstance(rectification_conclusion_fact[1], Mapping):
            return None
        if any(
            key in rectification_conclusion_fact[1]
            for key in ("outcome", "verdict")
        ):
            return None
        try:
            rectification_conclusion = TimeCheckRectificationConclusionV1.model_validate(
                rectification_conclusion_fact[1]
            )
        except (TypeError, ValueError):
            return None
        if rectification_conclusion.status != rectification_status_fact[1]:
            return None
        rectification_status = rectification_status_fact[1]
    subject_ref = candidate_fact[0] or _subject_ref(brief, facts)
    if not subject_ref:
        return None
    limitations = (
        (
            "Runtime 依据结构化事件的年份干支、支关系与事件领域十神角色输出候选证据排序，"
            "不等于古法断定。",
            "候选代表时辰中点；出生地真太阳时归一化由 Runtime 计算，浏览器不重新排盘。",
        )
        if ranking_fact[1] == "candidate_evidence_ranked"
        else (
            "当前只输出十二个时辰候选的八字与时间口径事实；没有足够的结构化事件时不做事件匹配或候选淘汰。",
            "候选代表时辰中点；出生地真太阳时归一化由 Runtime 计算，浏览器不重新排盘。",
        )
    )
    return TimeCheckViewV1(
        subject_ref=subject_ref,
        candidate_count=count_fact[1],
        candidates=candidates,
        known_time_range=dict(range_fact[1]),
        time_basis_policy=basis_fact[1],
        known_event_count=event_count_fact[1],
        event_input_status=event_input_status,
        candidate_rankings=ranking_rows,
        event_matches=event_matches,
        ranking_status=ranking_fact[1],
        event_matching_status=matching_fact[1],
        rectification_status=rectification_status,
        rectification_conclusion=rectification_conclusion,
        limitations=limitations,
    )


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _ziwei_star(value: object) -> ZiweiStar | None:
    if not isinstance(value, Mapping):
        return None
    name = _text(value.get("name"))
    if name is None:
        return None
    return ZiweiStar(
        name=name,
        star_type=_text(value.get("type")),
        scope=_text(value.get("scope")),
        brightness=_text(value.get("brightness")),
    )


def _ziwei_stars(value: object) -> tuple[ZiweiStar, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[ZiweiStar] = []
    for raw in value:
        star = _ziwei_star(raw)
        if star is None:
            return None
        result.append(star)
    return tuple(result)


def _ziwei_decadal(value: object) -> ZiweiDecadal | None:
    if not isinstance(value, Mapping):
        return None
    ranges = value.get("range")
    if not isinstance(ranges, (list, tuple)) or len(ranges) != 2:
        return None
    age_start = _integer(value.get("age_start", ranges[0]))
    age_end = _integer(value.get("age_end", ranges[1]))
    heavenly_stem = _text(value.get("heavenlyStem"))
    earthly_branch = _text(value.get("earthlyBranch"))
    if (
        age_start is None
        or age_end is None
        or heavenly_stem is None
        or earthly_branch is None
    ):
        return None
    return ZiweiDecadal(
        age_start=age_start,
        age_end=age_end,
        heavenly_stem=heavenly_stem,
        earthly_branch=earthly_branch,
    )


def _ziwei_palaces(value: object) -> tuple[tuple[ZiweiPalace, ...], str, str] | None:
    if not isinstance(value, list) or len(value) != 12:
        return None
    palaces: list[ZiweiPalace] = []
    life_id: str | None = None
    body_id: str | None = None
    for offset, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            return None
        index = raw.get("index", offset)
        if isinstance(index, bool) or not isinstance(index, int):
            index = offset
        label = raw.get("name")
        stem = raw.get("heavenlyStem")
        branch = raw.get("earthlyBranch")
        if not all(isinstance(item, str) and item.strip() for item in (label, stem, branch)):
            return None
        label = cast(str, label)
        stem = cast(str, stem)
        branch = cast(str, branch)
        major_stars_raw = raw.get("majorStars")
        major_star_objects = _ziwei_stars(major_stars_raw)
        if major_star_objects is None:
            return None
        minor_stars = _ziwei_stars(raw.get("minorStars", []))
        adjective_stars = _ziwei_stars(raw.get("adjectiveStars", []))
        if minor_stars is None or adjective_stars is None:
            return None
        ages_raw = raw.get("ages", [])
        ages = tuple(
            item
            for item in ages_raw
            if isinstance(item, int) and not isinstance(item, bool)
        ) if isinstance(ages_raw, (list, tuple)) else ()
        palace_id = str(index)
        palaces.append(
            ZiweiPalace(
                palace_id=palace_id,
                label=label,
                heavenly_stem=stem,
                earthly_branch=branch,
                major_stars=tuple(star.name for star in major_star_objects),
                minor_stars=minor_stars,
                adjective_stars=adjective_stars,
                changsheng12=_text(raw.get("changsheng12")),
                boshi12=_text(raw.get("boshi12")),
                jiangqian12=_text(raw.get("jiangqian12")),
                suiqian12=_text(raw.get("suiqian12")),
                decadal=_ziwei_decadal(raw.get("decadal")),
                ages=ages,
            )
        )
        if label == "命宫":
            life_id = palace_id
        if raw.get("isBodyPalace") is True:
            body_id = palace_id
    if life_id is None or body_id is None:
        return None
    return tuple(palaces), life_id, body_id


def _ziwei_limits(value: object) -> tuple[ZiweiLimit, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[ZiweiLimit] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        ranges = raw.get("range")
        if not isinstance(ranges, (list, tuple)) or len(ranges) != 2:
            return None
        palace = _text(raw.get("palace"))
        palace_index = _integer(raw.get("palace_index"))
        palace_branch = _text(raw.get("palace_branch"))
        age_start = _integer(raw.get("age_start", ranges[0]))
        age_end = _integer(raw.get("age_end", ranges[1]))
        sequence = _integer(raw.get("sequence"))
        heavenly_stem = _text(raw.get("heavenlyStem"))
        earthly_branch = _text(raw.get("earthlyBranch"))
        if not all(
            (
                palace,
                palace_index is not None,
                palace_branch,
                age_start is not None,
                age_end is not None,
                sequence is not None,
                heavenly_stem,
                earthly_branch,
            )
        ):
            return None
        result.append(
            ZiweiLimit(
                palace=cast(str, palace),
                palace_index=cast(int, palace_index),
                palace_branch=cast(str, palace_branch),
                age_start=cast(int, age_start),
                age_end=cast(int, age_end),
                sequence=cast(int, sequence),
                heavenly_stem=cast(str, heavenly_stem),
                earthly_branch=cast(str, earthly_branch),
                direction=_text(raw.get("direction")),
            )
        )
    return tuple(result)


def _ziwei_direction(value: object) -> ZiweiMajorLimitDirection | None:
    if not isinstance(value, Mapping):
        return None
    fields = {
        key: _text(value.get(key))
        for key in ("direction", "gender", "year_polarity", "year_stem")
    }
    if not all(fields.values()):
        return None
    return ZiweiMajorLimitDirection(
        direction=cast(str, fields["direction"]),
        gender=cast(str, fields["gender"]),
        year_polarity=cast(str, fields["year_polarity"]),
        year_stem=cast(str, fields["year_stem"]),
    )


def _ziwei_ming_shen(value: object) -> ZiweiMingShen | None:
    if not isinstance(value, Mapping):
        return None
    fields = {
        key: _text(value.get(key))
        for key in ("body_star", "ming_branch", "shen_branch", "soul_star")
    }
    if not all(fields.values()):
        return None
    return ZiweiMingShen(
        body_star=cast(str, fields["body_star"]),
        ming_branch=cast(str, fields["ming_branch"]),
        shen_branch=cast(str, fields["shen_branch"]),
        soul_star=cast(str, fields["soul_star"]),
    )


def _ziwei_transformations(value: object) -> tuple[ZiweiTransformation, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[ZiweiTransformation] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        star = _text(raw.get("star"))
        transformation = _text(raw.get("transformation"))
        palace = _text(raw.get("palace"))
        palace_branch = _text(raw.get("palace_branch"))
        scope = _text(raw.get("scope"))
        if not all((star, transformation, palace, palace_branch, scope)):
            continue
        result.append(
            ZiweiTransformation(
                star=cast(str, star),
                transformation=cast(str, transformation),
                palace=cast(str, palace),
                palace_branch=cast(str, palace_branch),
                scope=cast(str, scope),
            )
        )
    return tuple(result)


def _ziwei_star_facts(value: object) -> tuple[ZiweiStarFact, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[ZiweiStarFact] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        star = _ziwei_star(raw)
        palace = _text(raw.get("palace"))
        palace_branch = _text(raw.get("palace_branch"))
        palace_index = _integer(raw.get("palace_index"))
        if star is None or palace is None or palace_branch is None or palace_index is None:
            continue
        result.append(
            ZiweiStarFact(
                **star.model_dump(),
                palace=palace,
                palace_branch=palace_branch,
                palace_index=palace_index,
            )
        )
    return tuple(result)


def _ziwei_major_limit_segments(
    value: object,
) -> tuple[ZiweiMajorLimitSegment, ...] | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    result: list[ZiweiMajorLimitSegment] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        major_limit = _mapping_copy(raw.get("major_limit"))
        if not major_limit:
            return None
        try:
            result.append(
                ZiweiMajorLimitSegment(
                    start_inclusive=raw.get("start_inclusive"),
                    end_exclusive=raw.get("end_exclusive"),
                    major_limit=major_limit,
                )
            )
        except ValidationError:
            return None
    return tuple(result)


def _ziwei_calendar_coverage(value: object) -> ZiweiCalendarCoverage | None:
    if not isinstance(value, Mapping):
        return None
    try:
        return ZiweiCalendarCoverage(
            start_inclusive=value.get("start_inclusive"),
            end_exclusive=value.get("end_exclusive"),
            requested_target_date=value.get("requested_target_date"),
        )
    except ValidationError:
        return None


def _ziwei_annual_layers(value: object) -> tuple[ZiweiAnnualLayer, ...] | None:
    if not isinstance(value, Mapping) or not value:
        return None
    result: list[ZiweiAnnualLayer] = []
    for key, raw in sorted(value.items(), key=lambda item: str(item[0])):
        if not isinstance(raw, Mapping):
            return None
        year = raw.get("year")
        if (
            isinstance(year, bool)
            or not isinstance(year, int)
            or not 1800 <= year <= 2199
            or str(year) != str(key)
        ):
            return None
        coverage_start = _text(raw.get("coverage_start"))
        coverage_end = _text(raw.get("coverage_end_exclusive"))
        liu_nian = _mapping_copy(raw.get("liu_nian"))
        raw_segments = raw.get("segments")
        representative_scope = _text(raw.get("representative_scope"))
        if not isinstance(raw_segments, (list, tuple)) or not raw_segments:
            return None
        segments = tuple(_mapping_copy(item) for item in raw_segments)
        if (
            coverage_start is None
            or coverage_end is None
            or liu_nian is None
            or representative_scope is None
            or any(item is None for item in segments)
        ):
            return None
        result.append(
            ZiweiAnnualLayer(
                year=year,
                coverage_start=coverage_start,
                coverage_end_exclusive=coverage_end,
                liu_nian=liu_nian,
                segments=tuple(cast(dict[str, object], item) for item in segments),
                representative_scope=representative_scope,
            )
        )
    return tuple(result)


def _ziwei_monthly_layers(value: object) -> tuple[ZiweiMonthlyLayer, ...] | None:
    if not isinstance(value, Mapping) or not value:
        return None
    result: list[ZiweiMonthlyLayer] = []
    for key, raw in sorted(value.items(), key=lambda item: str(item[0])):
        if not isinstance(raw, Mapping):
            return None
        year = _integer(raw.get("year"))
        month = _integer(raw.get("month"))
        liu_yue = _mapping_copy(raw.get("liu_yue"))
        raw_segments = raw.get("segments")
        representative_scope = _text(raw.get("representative_scope"))
        if (
            year is None
            or not 1800 <= year <= 2199
            or month is None
            or not 1 <= month <= 12
            or str(key) != f"{year:04d}-{month:02d}"
            or liu_yue is None
            or not isinstance(raw_segments, (list, tuple))
            or not raw_segments
            or representative_scope is None
        ):
            return None
        segments = tuple(_mapping_copy(item) for item in raw_segments)
        if any(item is None for item in segments):
            return None
        result.append(
            ZiweiMonthlyLayer(
                year=year,
                month=month,
                liu_yue=liu_yue,
                segments=tuple(cast(dict[str, object], item) for item in segments),
                representative_scope=representative_scope,
            )
        )
    return tuple(result)


def _ziwei_core_facts(facts: object) -> ZiweiCoreFacts | None:
    values = {
        key: _brief_fact_value(facts, key)
        for key in (
            "chart_convention",
            "chinese_date",
            "active_major_limit",
            "active_major_limit_segments",
            "calendar_coverage",
            "five_elements_class",
            "interpretive_candidates",
            "source_conditioned_patterns",
            "ming_shen",
            "major_limit_direction",
            "major_limit_starting_age",
            "major_limit_sequence",
            "major_limits",
            "natal_transformation_facts",
            "star_facts",
            "annual_layers",
            "monthly_layers",
        )
    }
    segments_fact = values["active_major_limit_segments"]
    active_major_limit_segments = _ziwei_major_limit_segments(
        _calculated_value(values, "active_major_limit_segments")
    )
    if segments_fact is not None and active_major_limit_segments is None:
        return None
    coverage_fact = values["calendar_coverage"]
    calendar_coverage = _ziwei_calendar_coverage(
        _calculated_value(values, "calendar_coverage")
    )
    if coverage_fact is not None and calendar_coverage is None:
        return None
    core_values: dict[str, object] = {
        "chart_convention": _mapping_copy(
            _calculated_value(values, "chart_convention")
        ),
        "chinese_date": _text(_calculated_value(values, "chinese_date")),
        "active_major_limit": _mapping_copy(
            _calculated_value(values, "active_major_limit")
        ),
        "five_elements_class": _text(
            _calculated_value(values, "five_elements_class")
        ),
        "interpretive_candidates": _mapping_copy(
            _calculated_value(values, "interpretive_candidates")
        ),
        "source_conditioned_patterns": _source_conditioned_patterns(
            _calculated_value(values, "source_conditioned_patterns"),
            ZiweiSourcePattern,
        )
        or (),
        "ming_shen": _ziwei_ming_shen(_calculated_value(values, "ming_shen")),
        "major_limit_direction": _ziwei_direction(
            _calculated_value(values, "major_limit_direction")
        ),
        "major_limit_starting_age": _integer(
            _calculated_value(values, "major_limit_starting_age")
        ),
        "major_limit_sequence": _ziwei_limits(
            _calculated_value(values, "major_limit_sequence")
        ),
        "major_limits": _ziwei_limits(_calculated_value(values, "major_limits")),
        "transformations": _ziwei_transformations(
            _calculated_value(values, "natal_transformation_facts")
        ),
        "star_facts": _ziwei_star_facts(_calculated_value(values, "star_facts")),
        "annual_layers": _ziwei_annual_layers(
            _calculated_value(values, "annual_layers")
        ),
        "monthly_layers": _ziwei_monthly_layers(
            _calculated_value(values, "monthly_layers")
        ),
    }
    if segments_fact is not None:
        core_values["active_major_limit_segments"] = active_major_limit_segments
    if coverage_fact is not None:
        core_values["calendar_coverage"] = calendar_coverage
    core = ZiweiCoreFacts.model_validate(core_values)
    return core if any(value is not None for value in core.model_dump().values()) else None


def project_ziwei_view_model(
    brief: Mapping[str, object] | None,
) -> ZiweiChartV1 | None:
    """Project only Runtime-calculated Ziwei palace and star facts."""

    if brief is None or not _capability_is(brief, "ziwei"):
        return None
    facts = brief.get("facts")
    palaces_fact = _brief_fact_value(facts, "palaces")
    subject_ref = _subject_ref(brief, facts)
    if palaces_fact is None or subject_ref is None:
        return None
    parsed = _ziwei_palaces(palaces_fact[1])
    if parsed is None:
        return None
    palaces, life_id, body_id = parsed
    core_facts = _ziwei_core_facts(facts)
    return ZiweiChartV1(
        subject_ref=subject_ref,
        life_palace_id=life_id,
        body_palace_id=body_id,
        palaces=palaces,
        time_layers=_natal_time_layers(
            "紫微",
            year_available=bool(core_facts and core_facts.annual_layers),
            month_available=bool(core_facts and core_facts.monthly_layers),
        ),
        core_facts=core_facts,
    )


_ZODIAC_SIGNS = (
    "白羊",
    "金牛",
    "双子",
    "巨蟹",
    "狮子",
    "处女",
    "天秤",
    "天蝎",
    "射手",
    "摩羯",
    "水瓶",
    "双鱼",
)


def _zodiac_sign(longitude: float) -> str:
    return _ZODIAC_SIGNS[min(11, int((longitude % 360) // 30))]


def _finite_longitude(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    longitude = float(value) % 360
    return longitude if math.isfinite(longitude) else None


def _qizheng_positions(
    value: object,
) -> tuple[tuple[PlanetPosition, ...], tuple[HousePosition, ...]] | None:
    if not isinstance(value, (list, tuple)):
        return None
    planets: list[PlanetPosition] = []
    houses: list[HousePosition] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        longitude = _finite_longitude(raw.get("longitude_degrees", raw.get("longitude")))
        if longitude is None:
            continue
        planet_id = raw.get("classical_name") or raw.get("body")
        house_id = raw.get("house_sequence") or raw.get("house")
        if not isinstance(planet_id, str) or not planet_id.strip():
            continue
        if not isinstance(house_id, (str, int)) or isinstance(house_id, bool):
            house_id = "未分宫"
        planets.append(
            PlanetPosition(
                planet_id=planet_id,
                sign_id=_zodiac_sign(longitude),
                house_id=str(house_id),
                longitude=longitude,
            )
        )
    return tuple(planets), tuple(houses)


def _qizheng_houses(value: object) -> tuple[HousePosition, ...]:
    if not isinstance(value, list):
        return ()
    houses: list[HousePosition] = []
    for offset, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            continue
        longitude = _finite_longitude(raw.get("start_degree"))
        if longitude is None:
            continue
        house_id = raw.get("sequence", offset)
        houses.append(
            HousePosition(
                house_id=str(house_id),
                sign_id=_zodiac_sign(longitude),
                cusp_longitude=longitude,
            )
        )
    return tuple(houses)


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _bounded_number(value: object, *, lower: float, upper: float) -> float | None:
    number = _finite_number(value)
    if number is None or number < lower or number >= upper:
        return None
    return number


def _qizheng_body_facts(value: object) -> tuple[QizhengBodyFact, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[QizhengBodyFact] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        body_id = _text(raw.get("body"))
        classical_name = _text(raw.get("classical_name"))
        longitude = _finite_longitude(raw.get("longitude_degrees", raw.get("longitude")))
        fact_status = _text(raw.get("fact_status"))
        if body_id is None or classical_name is None or longitude is None or fact_status is None:
            continue
        latitude = _finite_number(raw.get("latitude_degrees"))
        degree_in_sign = _bounded_number(
            raw.get("degree_in_zodiac_sign"), lower=0, upper=30
        )
        house_value = raw.get("house_sequence", raw.get("house"))
        house_id = (
            str(house_value)
            if isinstance(house_value, (str, int)) and not isinstance(house_value, bool)
            else None
        )
        house_degree = _finite_number(raw.get("degree_in_house"))
        point_kind = _text(raw.get("point_kind"))
        observed_body = raw.get("observed_body")
        if not isinstance(observed_body, bool):
            observed_body = None
        source_dependency_id = _text(raw.get("source_dependency_id"))
        trace = _mapping_copy(raw.get("trace"))
        result.append(
            QizhengBodyFact(
                body_id=body_id,
                classical_name=classical_name,
                longitude=longitude,
                latitude_degrees=latitude,
                degree_in_zodiac_sign=degree_in_sign,
                house_id=house_id,
                house_degree=house_degree if house_degree is None or house_degree >= 0 else None,
                motion_state=_text(raw.get("motion_state")),
                fact_status=fact_status,
                point_kind=point_kind,
                observed_body=observed_body,
                source_dependency_id=source_dependency_id,
                trace=trace,
            )
        )
    return tuple(result)


def _qizheng_ephemeris(value: object) -> QizhengEphemerisSummary | None:
    if not isinstance(value, Mapping):
        return None
    schema_version = _text(value.get("schema_version"))
    engine = value.get("engine")
    convention = value.get("coordinate_convention")
    if (
        schema_version is None
        or not isinstance(engine, Mapping)
        or not isinstance(convention, Mapping)
    ):
        return None
    engine_name = _text(engine.get("name"))
    engine_version = _text(engine.get("version"))
    engine_license = _text(engine.get("license"))
    frame = _text(convention.get("frame"))
    zodiac = _text(convention.get("zodiac"))
    aberration = convention.get("aberration")
    precession = _text(convention.get("precession"))
    if (
        engine_name is None
        or engine_version is None
        or engine_license is None
        or frame is None
        or zodiac is None
        or not isinstance(aberration, bool)
        or precession is None
    ):
        return None
    return QizhengEphemerisSummary(
        schema_version=schema_version,
        engine=QizhengEphemerisEngine(
            name=engine_name,
            version=engine_version,
            license=engine_license,
        ),
        coordinate_convention=QizhengCoordinateConvention(
            frame=frame,
            zodiac=zodiac,
            aberration=aberration,
            precession=precession,
        ),
    )


def _qizheng_ming_shen(value: object) -> QizhengMingShen | None:
    if not isinstance(value, Mapping):
        return None
    ming_degree = _finite_longitude(value.get("ming_degree"))
    shen_degree = _finite_longitude(value.get("shen_degree"))
    separation = _finite_number(value.get("separation_degrees"))
    profile = _text(value.get("profile"))
    fact_status = _text(value.get("fact_status"))
    if (
        ming_degree is None
        or shen_degree is None
        or separation is None
        or separation < 0
        or profile is None
        or fact_status is None
    ):
        return None
    local_sidereal = _bounded_number(
        value.get("local_apparent_sidereal_degrees"), lower=0, upper=360
    )
    return QizhengMingShen(
        ming_degree=ming_degree,
        shen_degree=shen_degree,
        separation_degrees=separation,
        local_apparent_sidereal_degrees=local_sidereal,
        profile=profile,
        fact_status=fact_status,
    )


def _qizheng_limits(value: object) -> tuple[QizhengLimit, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[QizhengLimit] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        sequence = _integer(raw.get("sequence"))
        house = _text(raw.get("house"))
        age_start = _finite_number(raw.get("age_start_years"))
        age_end = _finite_number(raw.get("age_end_years"))
        start_degree = _finite_longitude(raw.get("start_degree"))
        end_degree = _finite_longitude(raw.get("end_degree"))
        status = _text(raw.get("status"))
        if (
            sequence is None
            or house is None
            or age_start is None
            or age_end is None
            or age_start < 0
            or age_end < 0
            or start_degree is None
            or end_degree is None
            or status is None
        ):
            continue
        result.append(
            QizhengLimit(
                sequence=sequence,
                house=house,
                age_start_years=age_start,
                age_end_years=age_end,
                start_degree=start_degree,
                end_degree=end_degree,
                status=status,
            )
        )
    return tuple(result)


def _qizheng_transformations(value: object) -> tuple[QizhengTransformation, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[QizhengTransformation] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        sequence = _integer(raw.get("sequence"))
        fields = {
            key: _text(raw.get(key))
            for key in (
                "transformation",
                "label",
                "classical_body",
                "body",
                "year_stem",
                "status",
            )
        }
        if sequence is None or sequence < 1 or not all(fields.values()):
            continue
        result.append(
            QizhengTransformation(
                sequence=sequence,
                transformation=cast(str, fields["transformation"]),
                label=cast(str, fields["label"]),
                classical_body=cast(str, fields["classical_body"]),
                body=cast(str, fields["body"]),
                year_stem=cast(str, fields["year_stem"]),
                status=cast(str, fields["status"]),
            )
        )
    return tuple(result)


def _qizheng_annual_transformations(
    value: object,
) -> tuple[QizhengAnnualTransformation, ...] | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    result: list[QizhengAnnualTransformation] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        year = _integer(raw.get("year"))
        year_ganzhi = _text(raw.get("year_ganzhi"))
        transformations = _qizheng_transformations(raw.get("transformations"))
        calendar_digest = _text(raw.get("calendar_digest"))
        fact_status = _text(raw.get("fact_status"))
        if (
            year is None
            or not 1800 <= year <= 2199
            or year_ganzhi is None
            or transformations is None
            or calendar_digest is None
            or fact_status is None
        ):
            return None
        result.append(
            QizhengAnnualTransformation(
                year=year,
                year_ganzhi=year_ganzhi,
                transformations=transformations,
                calendar_digest=calendar_digest,
                fact_status=fact_status,
            )
        )
    return tuple(result)


def _qizheng_requested_limit_layers(
    value: object,
) -> tuple[QizhengRequestedLimitLayer, ...] | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    result: list[QizhengRequestedLimitLayer] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        date = _text(raw.get("date"))
        age_years = _finite_number(raw.get("age_years"))
        house = _text(raw.get("house"))
        segment_index = _integer(raw.get("segment_index"))
        segment = _mapping_copy(raw.get("segment"))
        status = _text(raw.get("status"))
        if (
            date is None
            or age_years is None
            or age_years < 0
            or house is None
            or segment_index is None
            or segment_index < 0
            or segment is None
            or status is None
        ):
            return None
        result.append(
            QizhengRequestedLimitLayer(
                date=date,
                age_years=age_years,
                house=house,
                segment_index=segment_index,
                segment=segment,
                status=status,
            )
        )
    return tuple(result)


def _qizheng_core_facts(facts: object) -> QizhengCoreFacts | None:
    values = {
        key: _brief_fact_value(facts, key)
        for key in (
            "ephemeris",
            "conventions",
            "classical_bodies",
            "ming_shen",
            "major_limits",
            "transformations",
            "source_conditioned_patterns",
            "annual_transformations",
            "requested_limit_layers",
        )
    }
    core = QizhengCoreFacts(
        ephemeris=_qizheng_ephemeris(_calculated_value(values, "ephemeris")),
        conventions=_mapping_copy(_calculated_value(values, "conventions")),
        classical_bodies=_qizheng_body_facts(
            _calculated_value(values, "classical_bodies")
        ),
        ming_shen=_qizheng_ming_shen(_calculated_value(values, "ming_shen")),
        major_limits=_qizheng_limits(_calculated_value(values, "major_limits")),
        transformations=_qizheng_transformations(
            _calculated_value(values, "transformations")
        ),
        source_conditioned_patterns=_source_conditioned_patterns(
            _calculated_value(values, "source_conditioned_patterns"),
            QizhengSourcePattern,
        )
        or (),
        annual_transformations=_qizheng_annual_transformations(
            _calculated_value(values, "annual_transformations")
        ),
        requested_limit_layers=_qizheng_requested_limit_layers(
            _calculated_value(values, "requested_limit_layers")
        ),
    )
    return core if any(value is not None for value in core.model_dump().values()) else None


def project_qizheng_view_model(
    brief: Mapping[str, object] | None,
) -> QizhengChartV1 | None:
    """Project Runtime's observed celestial positions without interpretation."""

    if brief is None or not _capability_is(brief, "xingming"):
        return None
    facts = brief.get("facts")
    positions = _brief_fact_value(facts, "positions")
    houses = _brief_fact_value(facts, "houses")
    subject_ref = _subject_ref(brief, facts)
    if positions is None or houses is None or subject_ref is None:
        return None
    parsed_positions = _qizheng_positions(positions[1])
    parsed_houses = _qizheng_houses(houses[1])
    if parsed_positions is None or not parsed_positions[0] or len(parsed_houses) != 12:
        return None
    core_facts = _qizheng_core_facts(facts)
    return QizhengChartV1(
        subject_ref=subject_ref,
        planets=parsed_positions[0],
        houses=parsed_houses,
        aspects=(),
        time_layers=_natal_time_layers(
            "七政",
            year_available=bool(
                core_facts
                and (
                    core_facts.annual_transformations
                    or core_facts.requested_limit_layers
                )
            ),
            month_available=bool(
                core_facts
                and core_facts.requested_limit_layers
                and _request_horizon_kind(brief) == "month"
            ),
            day_available=bool(
                core_facts
                and core_facts.requested_limit_layers
                and _request_horizon_kind(brief) == "day"
            ),
        ),
        core_facts=core_facts,
    )


def _hexagram_summary(value: object) -> HexagramSummary | None:
    if not isinstance(value, Mapping):
        return None
    name = value.get("name")
    upper = value.get("upper_trigram")
    lower = value.get("lower_trigram")
    if not all(isinstance(item, str) and item.strip() for item in (name, upper, lower)):
        return None
    name = cast(str, name)
    upper = cast(str, upper)
    lower = cast(str, lower)
    return HexagramSummary(name=name, upper_trigram=upper, lower_trigram=lower)


_LIUYAO_STATES: dict[str, Literal[6, 7, 8, 9]] = {
    "老阴": 6,
    "少阳": 7,
    "少阴": 8,
    "老阳": 9,
}


def _liuyao_lines(value: object) -> tuple[LiuyaoLine, ...] | None:
    if not isinstance(value, list):
        return None
    result: list[LiuyaoLine] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        position = raw.get("line", raw.get("position"))
        state = raw.get("state")
        line_value = _LIUYAO_STATES.get(state) if isinstance(state, str) else None
        if line_value is None:
            candidate = raw.get("value")
            if isinstance(candidate, int) and candidate in {6, 7, 8, 9}:
                line_value = cast(Literal[6, 7, 8, 9], candidate)
        if (
            isinstance(position, bool)
            or not isinstance(position, int)
            or position not in range(1, 7)
            or line_value is None
        ):
            return None
        result.append(
            LiuyaoLine(
                position=position,
                value=line_value,
                moving=raw.get("moving") is True or line_value in {6, 9},
            )
        )
    if len(result) != 6 or {line.position for line in result} != set(range(1, 7)):
        return None
    return tuple(sorted(result, key=lambda line: line.position))


def _mapping_tuple(value: object) -> tuple[dict[str, object], ...] | None:
    if not isinstance(value, list):
        return None
    result: list[dict[str, object]] = []
    for item in value:
        parsed = _mapping_copy(item)
        if parsed is None:
            return None
        result.append(parsed)
    return tuple(result)


def _int_tuple(value: object) -> tuple[int, ...] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) for item in value
    ):
        return None
    return tuple(cast(int, item) for item in value)


def _liuyao_core_facts(facts: object) -> LiuyaoCoreFacts | None:
    mapping_fields = (
        "calendar",
        "casting",
        "changed_najia",
        "changed_plate_lines",
        "hidden_lines",
        "line_facts",
        "lines",
        "month_day_strength",
        "najia",
        "relation_facts",
        "returning_relations",
        "requested_useful_spirit_candidates",
        "shi_ying",
        "shi_ying_moving_relations",
        "six_spirit_profile",
        "useful_spirit_candidates",
        "useful_spirit_selection",
        "xunkong",
    )
    kwargs: dict[str, object] = {}
    for field in mapping_fields:
        fact = _brief_fact_value(facts, field)
        if fact is None:
            continue
        parsed = (
            _mapping_tuple(fact[1])
            if field
            in {
                "changed_najia",
                "changed_plate_lines",
                "hidden_lines",
                "line_facts",
                "lines",
                "month_day_strength",
                "najia",
                "relation_facts",
                "returning_relations",
            }
            else _mapping_copy(fact[1])
        )
        if parsed is not None:
            kwargs[field] = parsed

    for field in ("changed_six_relatives", "six_relatives", "six_spirits"):
        fact = _brief_fact_value(facts, field)
        if fact is None:
            continue
        parsed_strings = _text_tuple(fact[1])
        if parsed_strings is not None:
            kwargs[field] = parsed_strings

    for field in ("casting_method", "interpretation_status"):
        fact = _brief_fact_value(facts, field)
        if fact is not None and isinstance(fact[1], str) and fact[1].strip():
            kwargs[field] = fact[1]

    moving_lines = _brief_fact_value(facts, "moving_lines")
    if moving_lines is not None:
        parsed_moving_lines = _int_tuple(moving_lines[1])
        if parsed_moving_lines is not None:
            kwargs["moving_lines"] = parsed_moving_lines

    source_patterns = _brief_fact_value(facts, "source_conditioned_patterns")
    if source_patterns is not None:
        parsed_source_patterns = _source_conditioned_patterns(
            source_patterns[1], LiuyaoSourcePattern
        )
        if parsed_source_patterns is not None:
            kwargs["source_conditioned_patterns"] = parsed_source_patterns

    selection = kwargs.get("useful_spirit_selection")
    if selection is not None:
        try:
            LiuyaoUsefulSpiritSelection.model_validate(selection)
        except ValidationError:
            kwargs.pop("useful_spirit_selection")
    if not kwargs:
        return None
    try:
        return LiuyaoCoreFacts.model_validate(kwargs)
    except ValidationError:
        return None


def project_liuyao_view_model(
    brief: Mapping[str, object] | None,
) -> LiuyaoChartV1 | None:
    """Project Runtime's hexagram and six-line facts without judging the event."""

    if brief is None or not _capability_is(brief, "liuyao"):
        return None
    facts = brief.get("facts")
    primary = _brief_fact_value(facts, "primary_hexagram")
    lines = _brief_fact_value(facts, "lines")
    subject_ref = _subject_ref(brief, facts)
    question = _question(brief)
    if primary is None or lines is None or subject_ref is None or question is None:
        return None
    primary_summary = _hexagram_summary(primary[1])
    parsed_lines = _liuyao_lines(lines[1])
    if primary_summary is None or parsed_lines is None:
        return None
    changed = _brief_fact_value(facts, "changed_hexagram")
    changed_summary = _hexagram_summary(changed[1]) if changed is not None else None
    return LiuyaoChartV1(
        subject_ref=subject_ref,
        question=question,
        primary_hexagram=primary_summary,
        changed_hexagram=changed_summary,
        lines=parsed_lines,
        core_facts=_liuyao_core_facts(facts),
    )


def _meihua_trigram(value: object) -> MeihuaTrigram | None:
    if not isinstance(value, Mapping):
        return None
    position = value.get("position")
    trigram = value.get("trigram")
    element = value.get("element")
    if position not in {"upper", "lower"} or not all(
        isinstance(item, str) and item.strip() for item in (trigram, element)
    ):
        return None
    return MeihuaTrigram(
        position=position,
        trigram=cast(str, trigram),
        element=cast(str, element),
    )


def _meihua_body_use(value: object) -> MeihuaBodyUse | None:
    if not isinstance(value, Mapping):
        return None
    body = _meihua_trigram(value.get("body"))
    use = _meihua_trigram(value.get("use"))
    relation = value.get("relation")
    status = value.get("status")
    if body is None or use is None or not all(
        isinstance(item, str) and item.strip() for item in (relation, status)
    ):
        return None
    return MeihuaBodyUse(
        body=body,
        use=use,
        relation=cast(str, relation),
        status=cast(str, status),
    )


def _meihua_body_relation_facts(
    value: object,
) -> tuple[MeihuaBodyRelationFact, ...] | None:
    if not isinstance(value, list):
        return None
    result: list[MeihuaBodyRelationFact] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        body = _meihua_trigram(raw.get("body"))
        strings = {
            key: raw.get(key)
            for key in (
                "element",
                "position",
                "relation",
                "source_dependency_id",
                "source_plate",
                "status",
                "trigram",
            )
        }
        if body is None or not all(
            isinstance(item, str) and item.strip() for item in strings.values()
        ):
            return None
        result.append(
            MeihuaBodyRelationFact(
                body=body,
                element=cast(str, strings["element"]),
                position=cast(str, strings["position"]),
                relation=cast(str, strings["relation"]),
                source_dependency_id=cast(str, strings["source_dependency_id"]),
                source_plate=cast(str, strings["source_plate"]),
                status=cast(str, strings["status"]),
                trigram=cast(str, strings["trigram"]),
            )
        )
    return tuple(result)


def _meihua_seasonal_strength(
    value: object,
) -> dict[str, MeihuaSeasonalStrengthFact] | None:
    if not isinstance(value, Mapping):
        return None
    result: dict[str, MeihuaSeasonalStrengthFact] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(raw, Mapping):
            return None
        strings = {
            field: raw.get(field)
            for field in (
                "month_branch",
                "season",
                "source_dependency_id",
                "state",
                "status",
                "trigram",
            )
        }
        if not all(isinstance(item, str) and item.strip() for item in strings.values()):
            return None
        result[key] = MeihuaSeasonalStrengthFact(
            month_branch=cast(str, strings["month_branch"]),
            season=cast(str, strings["season"]),
            source_dependency_id=cast(str, strings["source_dependency_id"]),
            state=cast(str, strings["state"]),
            status=cast(str, strings["status"]),
            trigram=cast(str, strings["trigram"]),
        )
    return result


def _meihua_interpretive_candidates(
    value: object,
) -> MeihuaInterpretiveCandidates | None:
    if not isinstance(value, Mapping):
        return None
    if (
        value.get("schema_version") != "mingli-meihua-interpretive-candidates-v1"
        or value.get("status") != "source_adjudicated_relations"
        or value.get("hard_verdict") is not None
        or value.get("verification_status") != "verified"
        or not isinstance(value.get("relation_candidates"), list)
        or value.get("requires_classical_adjudication") is not False
        or value.get("requires_synthesis_adjudication") is not True
        or not isinstance(value.get("boundary"), str)
        or not str(value.get("boundary") or "").strip()
    ):
        return None
    candidates: list[MeihuaRelationCandidate] = []
    for raw in value["relation_candidates"]:
        if not isinstance(raw, Mapping):
            return None
        actor_raw = raw.get("actor")
        body = _meihua_trigram(raw.get("body"))
        position = raw.get("position")
        if not isinstance(actor_raw, Mapping) or position not in {"upper", "lower"}:
            return None
        actor = _meihua_trigram(
            {
                "position": position,
                "trigram": actor_raw.get("trigram"),
                "element": actor_raw.get("element"),
            }
        )
        strings = {
            key: raw.get(key)
            for key in (
                "candidate_id",
                "source_plate",
                "relation",
                "relation_key",
                "rule_id",
                "status",
                "verification_status",
                "source_pack",
                "source_anchor",
                "source_dependency_id",
            )
        }
        seasonal_state = raw.get("seasonal_state")
        adjudication = raw.get("relation_adjudication")
        if not isinstance(adjudication, Mapping):
            return None
        try:
            parsed_adjudication = MeihuaRelationAdjudication.model_validate(
                dict(adjudication)
            )
        except ValueError:
            return None
        if (
            actor is None
            or body is None
            or not all(isinstance(item, str) and item.strip() for item in strings.values())
            or strings["status"] != "relation_adjudicated_not_event_verdict"
            or strings["verification_status"] != "verified"
            or raw.get("hard_verdict") is not None
            or parsed_adjudication.relation_key != strings["relation_key"]
            or parsed_adjudication.source_refs[0].pack != strings["source_pack"]
            or parsed_adjudication.source_refs[0].rule_id != strings["rule_id"]
            or (
                seasonal_state is not None
                and (not isinstance(seasonal_state, str) or not seasonal_state.strip())
            )
        ):
            return None
        candidates.append(
            MeihuaRelationCandidate(
                candidate_id=cast(str, strings["candidate_id"]),
                source_plate=cast(str, strings["source_plate"]),
                position=position,
                relation=cast(str, strings["relation"]),
                relation_key=cast(str, strings["relation_key"]),
                actor=actor,
                body=body,
                seasonal_state=seasonal_state,
                rule_id=cast(str, strings["rule_id"]),
                status="relation_adjudicated_not_event_verdict",
                verification_status="verified",
                source_pack=cast(str, strings["source_pack"]),
                source_anchor=cast(str, strings["source_anchor"]),
                source_dependency_id=cast(str, strings["source_dependency_id"]),
                relation_adjudication=parsed_adjudication,
            )
        )
    return MeihuaInterpretiveCandidates(
        schema_version="mingli-meihua-interpretive-candidates-v1",
        status="source_adjudicated_relations",
        verification_status="verified",
        relation_candidates=tuple(candidates),
        requires_classical_adjudication=False,
        requires_synthesis_adjudication=True,
        boundary=cast(str, value["boundary"]),
    )


def _meihua_core_facts(facts: object) -> MeihuaCoreFacts | None:
    body_relations = _brief_fact_value(facts, "body_relation_facts")
    seasonal_strength = _brief_fact_value(facts, "seasonal_strength")
    interpretive_candidates = _brief_fact_value(facts, "interpretive_candidates")
    interpretation_status = _brief_fact_value(facts, "interpretation_status")
    parsed_body_relations = (
        _meihua_body_relation_facts(body_relations[1])
        if body_relations is not None
        else None
    )
    parsed_seasonal_strength = (
        _meihua_seasonal_strength(seasonal_strength[1])
        if seasonal_strength is not None
        else None
    )
    parsed_interpretive_candidates = (
        _meihua_interpretive_candidates(interpretive_candidates[1])
        if interpretive_candidates is not None
        else None
    )
    parsed_status = (
        interpretation_status[1]
        if interpretation_status is not None
        and isinstance(interpretation_status[1], str)
        and interpretation_status[1].strip()
        else None
    )
    if (
        parsed_body_relations is None
        and parsed_seasonal_strength is None
        and parsed_interpretive_candidates is None
        and parsed_status is None
    ):
        return None
    return MeihuaCoreFacts(
        body_relation_facts=parsed_body_relations,
        seasonal_strength=parsed_seasonal_strength,
        interpretive_candidates=parsed_interpretive_candidates,
        interpretation_status=parsed_status,
    )


def _meihua_moving_lines(value: object) -> tuple[int, ...] | None:
    if not isinstance(value, list):
        return None
    lines: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or item not in range(1, 7):
            return None
        lines.append(item)
    if len(lines) != len(set(lines)):
        return None
    return tuple(sorted(lines))


def project_meihua_view_model(
    brief: Mapping[str, object] | None,
) -> MeihuaChartV1 | None:
    """Project Meihua's structural plate facts without turning relations into verdicts."""

    if brief is None or not _capability_is(brief, "meihua"):
        return None
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    question = _question(brief)
    primary = _brief_fact_value(facts, "primary_hexagram")
    mutual = _brief_fact_value(facts, "mutual_hexagram")
    changed = _brief_fact_value(facts, "changed_hexagram")
    moving_lines = _brief_fact_value(facts, "moving_lines")
    body_use = _brief_fact_value(facts, "body_use")
    casting_method = _brief_fact_value(facts, "casting_method")
    if (
        subject_ref is None
        or question is None
        or primary is None
        or moving_lines is None
        or body_use is None
        or casting_method is None
    ):
        return None
    primary_summary = _hexagram_summary(primary[1])
    mutual_summary = _hexagram_summary(mutual[1]) if mutual is not None else None
    changed_summary = _hexagram_summary(changed[1]) if changed is not None else None
    parsed_lines = _meihua_moving_lines(moving_lines[1])
    parsed_body_use = _meihua_body_use(body_use[1])
    method = casting_method[1]
    if (
        primary_summary is None
        or parsed_lines is None
        or parsed_body_use is None
        or method
        not in {"time", "supplied_number", "sound_count", "observation", "supplied_hexagram"}
    ):
        return None
    method = cast(
        Literal["time", "supplied_number", "sound_count", "observation", "supplied_hexagram"],
        method,
    )
    return MeihuaChartV1(
        subject_ref=subject_ref,
        question=question,
        casting_method=method,
        primary_hexagram=primary_summary,
        mutual_hexagram=mutual_summary,
        changed_hexagram=changed_summary,
        moving_lines=parsed_lines,
        body_use=parsed_body_use,
        core_facts=_meihua_core_facts(facts),
        public_labels=public_key_labels(MEIHUA_PUBLIC_LABELS),
    )


_LUMING_PILLAR_POSITIONS: tuple[Literal["year", "month", "day", "hour"], ...] = (
    "year",
    "month",
    "day",
    "hour",
)


def _luming_pillars(value: object) -> tuple[LumingNayinPillar, ...] | None:
    if not isinstance(value, Mapping):
        return None
    result: list[LumingNayinPillar] = []
    for position in _LUMING_PILLAR_POSITIONS:
        raw = value.get(position)
        if not isinstance(raw, Mapping):
            return None
        stem = raw.get("stem")
        branch = raw.get("branch")
        nayin = raw.get("nayin")
        nayin_name = nayin.get("name") if isinstance(nayin, Mapping) else None
        if not all(
            isinstance(item, str) and item.strip()
            for item in (stem, branch, nayin_name)
        ):
            return None
        result.append(
            LumingNayinPillar(
                position=position,
                stem=cast(str, stem),
                branch=cast(str, branch),
                nayin=cast(str, nayin_name),
            )
        )
    return tuple(result)


def _luming_relations(value: object) -> tuple[LumingNayinRelation, ...] | None:
    if not isinstance(value, Mapping):
        return None
    result: list[LumingNayinRelation] = []
    for category in ("lu", "ma", "gui"):
        rows = value.get(category)
        if not isinstance(rows, list):
            return None
        for raw in rows:
            if not isinstance(raw, Mapping):
                return None
            relation = raw.get("relation")
            anchor = raw.get("anchor")
            anchor_pillar = raw.get("anchor_pillar")
            status = raw.get("status")
            candidates = raw.get("candidates", [])
            matched_positions = raw.get("matched_positions", [])
            target_branch = raw.get("target_branch")
            recension = raw.get("recension")
            if not all(
                isinstance(item, str) and item.strip()
                for item in (relation, anchor, anchor_pillar, status)
            ):
                return None
            if not isinstance(candidates, list) or not all(
                isinstance(item, str) and item.strip() for item in candidates
            ):
                return None
            if not isinstance(matched_positions, list) or not all(
                isinstance(item, str) and item.strip() for item in matched_positions
            ):
                return None
            if target_branch is not None and (
                not isinstance(target_branch, str) or not target_branch.strip()
            ):
                return None
            if recension is not None and (
                not isinstance(recension, str) or not recension.strip()
            ):
                return None
            result.append(
                LumingNayinRelation(
                    category=category,
                    relation=cast(str, relation),
                    anchor=cast(str, anchor),
                    anchor_pillar=cast(str, anchor_pillar),
                    status=cast(str, status),
                    target_branch=target_branch,
                    candidates=tuple(cast(list[str], candidates)),
                    matched_positions=tuple(cast(list[str], matched_positions)),
                    recension=recension,
                )
            )
    return tuple(result)


class _SourcePatternFactory[SourcePatternT](Protocol):
    def __call__(
        self,
        *,
        rule_id: str,
        local_rule_id: str,
        title: str,
        source_pack: str,
        source_anchor: str,
        status: str,
        fact_paths: tuple[str, ...],
        predicate_audit: tuple[str, ...],
    ) -> SourcePatternT: ...


def _source_conditioned_patterns[SourcePatternT](
    value: object,
    pattern_type: _SourcePatternFactory[SourcePatternT],
) -> tuple[SourcePatternT, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[SourcePatternT] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        rule_id = raw.get("rule_id")
        local_rule_id = raw.get("local_rule_id")
        title = raw.get("title")
        source_pack = raw.get("source_pack")
        source_anchor = raw.get("source_anchor")
        status = raw.get("status")
        fact_paths = raw.get("fact_paths")
        predicate_audit = raw.get("predicate_audit")
        if not all(
            isinstance(item, str) and item.strip()
            for item in (
                rule_id,
                local_rule_id,
                title,
                source_pack,
                source_anchor,
                status,
            )
        ):
            return None
        if status != "predicate_matched_not_verdict":
            return None
        if not isinstance(fact_paths, (list, tuple)) or not all(
            isinstance(item, str) and item.strip() for item in fact_paths
        ):
            return None
        if not isinstance(predicate_audit, (list, tuple)) or not all(
            isinstance(item, str) and item.strip() for item in predicate_audit
        ):
            return None
        if "verdict" in raw:
            return None
        result.append(
            pattern_type(
                rule_id=cast(str, rule_id),
                local_rule_id=cast(str, local_rule_id),
                title=cast(str, title),
                source_pack=cast(str, source_pack),
                source_anchor=cast(str, source_anchor),
                status=cast(str, status),
                fact_paths=cast(tuple[str, ...], tuple(fact_paths)),
                predicate_audit=cast(
                    tuple[str, ...], tuple(predicate_audit)
                ),
            )
        )
    return tuple(result)


def _luming_source_patterns(
    value: object,
) -> tuple[LumingNayinSourcePattern, ...] | None:
    common_patterns = _source_conditioned_patterns(value, BaziSourcePattern)
    if common_patterns is None or not isinstance(value, (list, tuple)):
        return None
    result: list[LumingNayinSourcePattern] = []
    for common, raw in zip(common_patterns, value, strict=True):
        if not isinstance(raw, Mapping):
            return None
        adjudication = raw.get("applicability_adjudication")
        if not isinstance(adjudication, Mapping):
            return None
        try:
            parsed = LumingNayinRuleApplicabilityAdjudication.model_validate(
                dict(adjudication)
            )
        except ValueError:
            return None
        if (
            parsed.rule_id != common.rule_id
            or parsed.local_rule_id != common.local_rule_id
            or parsed.rule_title != common.title
            or parsed.source_ref.pack != common.source_pack
            or parsed.source_ref.rule_id != common.local_rule_id
        ):
            return None
        result.append(
            LumingNayinSourcePattern(
                **common.model_dump(),
                applicability_adjudication=parsed,
            )
        )
    return tuple(result)


def project_luming_nayin_view_model(
    brief: Mapping[str, object] | None,
) -> LumingNayinChartV1 | None:
    """Project early-Luming facts without expanding them into Bazi judgments."""

    if brief is None or not _capability_is(brief, "luming-nayin"):
        return None
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    pillars = _brief_fact_value(facts, "pillars")
    three_yuan = _brief_fact_value(facts, "three_yuan_profiles")
    relations = _brief_fact_value(facts, "relations")
    if (
        subject_ref is None
        or pillars is None
        or three_yuan is None
        or relations is None
        or not isinstance(three_yuan[1], Mapping)
    ):
        return None
    parsed_pillars = _luming_pillars(pillars[1])
    parsed_relations = _luming_relations(relations[1])
    if parsed_pillars is None or parsed_relations is None:
        return None
    source_patterns_fact = _brief_fact_value(facts, "source_conditioned_patterns")
    parsed_source_patterns = (
        ()
        if source_patterns_fact is None
        else _luming_source_patterns(source_patterns_fact[1])
        if isinstance(source_patterns_fact[1], list)
        else None
    )
    if parsed_source_patterns is None:
        return None
    taiyuan_fact = _brief_fact_value(facts, "taiyuan")
    taiyuan = taiyuan_fact[1] if taiyuan_fact is not None else None
    if taiyuan is not None and not isinstance(taiyuan, Mapping):
        return None
    return LumingNayinChartV1(
        subject_ref=subject_ref,
        pillars=parsed_pillars,
        three_yuan_profiles=dict(three_yuan[1]),
        taiyuan=dict(taiyuan) if isinstance(taiyuan, Mapping) else None,
        relations=parsed_relations,
        source_conditioned_patterns=parsed_source_patterns,
    )


def project_rhythm_facts_view_model(
    brief: Mapping[str, object] | None,
) -> RhythmFactsViewV1 | None:
    """Project only the Nayin facts promised by the public Rhythm tool."""

    if brief is None or not _capability_is(brief, "luming-nayin"):
        return None
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    pillars = _brief_fact_value(facts, "pillars")
    lineage = _brief_fact_value(facts, "independent_lineage")
    fact_scope = _brief_fact_value(facts, "fact_scope")
    interpretation_status = _brief_fact_value(facts, "interpretation_status")
    if (
        subject_ref is None
        or pillars is None
        or lineage is None
        or fact_scope is None
        or interpretation_status is None
        or not isinstance(lineage[1], str)
        or not isinstance(fact_scope[1], str)
        or interpretation_status[1] != "facts_only"
    ):
        return None
    parsed_pillars = _luming_pillars(pillars[1])
    if parsed_pillars is None:
        return None
    return RhythmFactsViewV1(
        subject_ref=subject_ref,
        pillars=tuple(
            RhythmFactsPillar(
                position=pillar.position,
                stem=pillar.stem,
                branch=pillar.branch,
                nayin=pillar.nayin,
            )
            for pillar in parsed_pillars
        ),
        independent_lineage=lineage[1],
        fact_scope=fact_scope[1],
        interpretation_status="facts_only",
        source_boundary="只展示 Runtime 四柱纳音事实，不生成音色、频率、姓名学、性格或吉凶结论。",
    )


def _fortune_natal_pillars(value: object) -> dict[str, str] | None:
    if not isinstance(value, Mapping) or set(value) != set(_BAZI_PILLAR_POSITIONS):
        return None
    result: dict[str, str] = {}
    for position in _BAZI_PILLAR_POSITIONS:
        pillar = _text(value.get(position))
        if pillar is None:
            return None
        result[position] = pillar
    return result


def _fortune_target_period(value: object) -> FortuneTargetPeriod | None:
    if not isinstance(value, Mapping):
        return None
    kind = _text(value.get("kind"))
    start = _text(value.get("start"))
    end = _text(value.get("end"))
    if kind is None or start is None or end is None:
        return None
    return FortuneTargetPeriod(kind=kind, start=start, end=end)


def _fortune_period_markers(value: object) -> tuple[FortunePeriodMarker, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[FortunePeriodMarker] = []
    for item in value:
        if not isinstance(item, Mapping):
            return None
        date = _text(item.get("date"))
        day_pillar = _text(item.get("day_pillar"))
        day_role = _text(item.get("day_role"))
        active_luck_cycle = _text(item.get("active_luck_cycle"))
        primary_mechanism_ids = _text_tuple(item.get("primary_mechanism_ids"))
        decisive_mechanism_ids = _text_tuple(item.get("decisive_mechanism_ids"))
        relations = _mapping_tuple(item.get("relations"))
        specific_event_policy = _text(item.get("specific_event_policy"))
        unresolved_boundaries = _text_tuple(item.get("unresolved_boundaries"))
        if (
            date is None
            or day_pillar is None
            or day_role is None
            or active_luck_cycle is None
            or primary_mechanism_ids is None
            or decisive_mechanism_ids is None
            or relations is None
            or specific_event_policy is None
            or unresolved_boundaries is None
        ):
            return None
        result.append(
            FortunePeriodMarker(
                date=date,
                day_pillar=day_pillar,
                day_role=day_role,
                active_luck_cycle=active_luck_cycle,
                primary_mechanism_ids=primary_mechanism_ids,
                decisive_mechanism_ids=decisive_mechanism_ids,
                relations=relations,
                specific_event_policy=specific_event_policy,
                unresolved_boundaries=unresolved_boundaries,
            )
        )
    return tuple(result)


_FORTUNE_CALENDAR_NORMALIZATION_FIELDS = (
    "status",
    "algorithm_version",
    "time_basis",
    "true_solar_time",
    "calendar_convention",
    "effective_datetime",
    "day_boundary",
    "changed_pillars",
    "solar_terms",
)


def _fortune_calendar_normalization(
    value: object,
) -> FortuneCalendarNormalization | None:
    plain = _plain_mapping_copy(value)
    if plain is None:
        return None
    allowed_fields = frozenset(_FORTUNE_CALENDAR_NORMALIZATION_FIELDS)
    if not set(plain) <= allowed_fields:
        return None
    projected = {
        field: plain[field]
        for field in _FORTUNE_CALENDAR_NORMALIZATION_FIELDS
        if field in plain
    }
    try:
        return FortuneCalendarNormalization.model_validate(projected)
    except (TypeError, ValueError):
        return None


def project_fortune_view_model(
    brief: Mapping[str, object] | None,
) -> FortuneFactsViewV1 | None:
    """Project Runtime fortune facts without adding a daily verdict."""

    if brief is None or not _capability_is(brief, "fortune"):
        return None
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    calculated = {
        key: _brief_fact_value(facts, key)
        for key in (
            "natal_pillars",
            "day_master",
            "month_command",
            "active_luck_cycle",
            "target_day",
            "target_period",
            "available_periods",
            "period_markers",
            "calendar_normalization",
        )
    }
    natal_pillars = _fortune_natal_pillars(_calculated_value(calculated, "natal_pillars"))
    day_master = _bazi_day_master(_calculated_value(calculated, "day_master"))
    month_command = _bazi_month_command(
        _calculated_value(calculated, "month_command")
    )
    active_luck_cycle = _text(_calculated_value(calculated, "active_luck_cycle"))
    target_day = _text(_calculated_value(calculated, "target_day"))
    target_period = _fortune_target_period(
        _calculated_value(calculated, "target_period")
    )
    available_periods = _text_tuple(_calculated_value(calculated, "available_periods"))
    period_markers = _fortune_period_markers(
        _calculated_value(calculated, "period_markers")
    )
    calendar_normalization = _fortune_calendar_normalization(
        _calculated_value(calculated, "calendar_normalization")
    )
    if (
        subject_ref is None
        or natal_pillars is None
        or day_master is None
        or month_command is None
        or active_luck_cycle is None
        or target_day is None
        or target_period is None
        or available_periods is None
        or period_markers is None
        or calendar_normalization is None
    ):
        return None
    return FortuneFactsViewV1(
        subject_ref=subject_ref,
        natal_pillars=natal_pillars,
        day_master=day_master,
        month_command=month_command,
        active_luck_cycle=active_luck_cycle,
        target_day=target_day,
        target_period=target_period,
        available_periods=available_periods,
        period_markers=period_markers,
        calendar_normalization=calendar_normalization,
    )


def _taiyi_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _taiyi_string_tuple(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        return None
    return tuple(cast(list[str], value))


def _selection_date_time_ids(value: object) -> tuple[str, ...] | None:
    """Project Runtime time summaries to the public ID-only contract."""

    if not isinstance(value, list):
        return None
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item)
            continue
        if isinstance(item, Mapping):
            candidate_time_id = item.get("candidate_time_id")
            if isinstance(candidate_time_id, str) and candidate_time_id.strip():
                result.append(candidate_time_id)
                continue
        return None
    return tuple(result)


def _taiyi_calendar(value: object) -> TaiyiCalendar | None:
    if not isinstance(value, Mapping):
        return None
    annual_boundary = value.get("annual_boundary")
    lunar_year = _taiyi_int(value.get("lunar_year"))
    year_ganzhi = value.get("year_ganzhi")
    if (
        not isinstance(annual_boundary, str)
        or not annual_boundary.strip()
        or lunar_year is None
        or not isinstance(year_ganzhi, str)
        or not year_ganzhi.strip()
    ):
        return None
    return TaiyiCalendar(
        annual_boundary=annual_boundary,
        lunar_year=lunar_year,
        year_ganzhi=year_ganzhi,
    )


def _taiyi_epoch(value: object) -> TaiyiEpoch | None:
    if not isinstance(value, Mapping):
        return None
    integer_fields = (
        "accumulated_year",
        "anchor_accumulated_year",
        "anchor_lunar_year_ce",
        "derived_ce_offset",
    )
    integers = [_taiyi_int(value.get(field)) for field in integer_fields]
    profile_id = value.get("profile_id")
    source_anchor = value.get("source_anchor")
    if (
        any(item is None for item in integers)
        or not isinstance(value.get("one_based"), bool)
        or not isinstance(profile_id, str)
        or not profile_id.strip()
        or not isinstance(source_anchor, str)
        or not source_anchor.strip()
    ):
        return None
    return TaiyiEpoch(
        accumulated_year=cast(int, integers[0]),
        anchor_accumulated_year=cast(int, integers[1]),
        anchor_lunar_year_ce=cast(int, integers[2]),
        derived_ce_offset=cast(int, integers[3]),
        one_based=value["one_based"],
        profile_id=profile_id,
        source_anchor=source_anchor,
    )


def _taiyi_cycle(value: object) -> TaiyiCycle | None:
    if not isinstance(value, Mapping):
        return None
    fields = (
        "bureau",
        "ji",
        "position_360",
        "year_in_ji",
        "year_in_zi_yuan",
        "zi_yuan",
    )
    integers = [_taiyi_int(value.get(field)) for field in fields]
    governance = value.get("governance")
    zi_yuan_head = value.get("zi_yuan_head")
    if (
        any(item is None for item in integers)
        or not isinstance(governance, str)
        or not governance.strip()
        or not isinstance(zi_yuan_head, str)
        or not zi_yuan_head.strip()
    ):
        return None
    return TaiyiCycle(
        bureau=cast(int, integers[0]),
        governance=governance,
        ji=cast(int, integers[1]),
        position_360=cast(int, integers[2]),
        year_in_ji=cast(int, integers[3]),
        year_in_zi_yuan=cast(int, integers[4]),
        zi_yuan=cast(int, integers[5]),
        zi_yuan_head=zi_yuan_head,
    )


def _taiyi_board(value: object) -> TaiyiBoard | None:
    if not isinstance(value, Mapping):
        return None
    strings = [
        value.get(field)
        for field in (
            "heshen",
            "jishen",
            "taisui",
            "taiyi_position",
        )
    ]
    strings.insert(2, value.get("shiji_kemu", value.get("shiji")))
    marker = value.get("tianmu_wenchang")
    if not all(isinstance(item, str) and item.strip() for item in strings):
        return None
    if not isinstance(marker, Mapping):
        return None
    name = marker.get("name")
    position = marker.get("position")
    if not all(isinstance(item, str) and item.strip() for item in (name, position)):
        return None
    return TaiyiBoard(
        heshen=cast(str, strings[0]),
        jishen=cast(str, strings[1]),
        shiji=cast(str, strings[2]),
        taisui=cast(str, strings[3]),
        taiyi_position=cast(str, strings[4]),
        tianmu_wenchang=TaiyiNamedPosition(
            name=cast(str, name),
            position=cast(str, position),
        ),
    )


def _taiyi_four_generals(value: object) -> TaiyiFourGenerals | None:
    if not isinstance(value, Mapping):
        return None
    fields = ("guest_assistant", "guest_major", "host_assistant", "host_major")
    integers = [_taiyi_int(value.get(field)) for field in fields]
    if any(item is None for item in integers):
        return None
    return TaiyiFourGenerals(
        guest_assistant=cast(int, integers[0]),
        guest_major=cast(int, integers[1]),
        host_assistant=cast(int, integers[2]),
        host_major=cast(int, integers[3]),
    )


def _taiyi_long_cycle_deities(value: object) -> tuple[TaiyiLongCycleDeity, ...] | None:
    if not isinstance(value, Mapping):
        return None
    result: list[TaiyiLongCycleDeity] = []
    for deity_id in sorted(value):
        raw = value[deity_id]
        if not isinstance(raw, Mapping):
            return None
        integers = [
            _taiyi_int(raw.get("accumulated_year")),
            _taiyi_int(raw.get("cycle_position")),
        ]
        text_fields = [
            raw.get("epoch_profile"),
            raw.get("name"),
            raw.get("source_anchor"),
            raw.get("status"),
        ]
        position = raw.get("position")
        if (
            any(item is None for item in integers)
            or not all(isinstance(item, str) and item.strip() for item in text_fields)
            or not isinstance(position, (str, int))
            or isinstance(position, bool)
        ):
            return None
        result.append(
            TaiyiLongCycleDeity(
                deity_id=str(deity_id),
                accumulated_year=cast(int, integers[0]),
                cycle_position=cast(int, integers[1]),
                epoch_profile=cast(str, text_fields[0]),
                name=cast(str, text_fields[1]),
                position=str(position),
                source_anchor=cast(str, text_fields[2]),
                status=cast(str, text_fields[3]),
            )
        )
    return tuple(result)


def _taiyi_predicates(value: object) -> tuple[TaiyiBoardPredicate, ...] | None:
    if not isinstance(value, list):
        return None
    result: list[TaiyiBoardPredicate] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        predicate_id = raw.get("id")
        name = raw.get("name")
        predicate = raw.get("predicate")
        fact_paths = _taiyi_string_tuple(raw.get("fact_paths"))
        source_anchor = raw.get("source_anchor")
        source_dependency_id = raw.get("source_dependency_id")
        status = raw.get("status")
        adjudication = raw.get("identity_adjudication")
        if (
            not all(
                isinstance(item, str) and item.strip()
                for item in (
                    predicate_id,
                    name,
                    predicate,
                    source_anchor,
                    source_dependency_id,
                    status,
                )
            )
            or fact_paths is None
            or status != "predicate_matched_not_verdict"
            or not isinstance(adjudication, Mapping)
        ):
            return None
        source_ref = adjudication.get("source_ref")
        unresolved_checks = _taiyi_string_tuple(
            adjudication.get("unresolved_checks")
        )
        if (
            adjudication.get("status") != "adjudicated_pattern_identity"
            or adjudication.get("decision_scope")
            != "taiyi_board_pattern_identity"
            or adjudication.get("pattern_id") != predicate_id
            or adjudication.get("pattern_name") != name
            or adjudication.get("hard_verdict") is not None
            or adjudication.get("event_verdict") is not None
            or not isinstance(source_ref, Mapping)
            or source_ref.get("verification_status") != "verified"
            or source_ref.get("rule_id") != predicate_id
            or unresolved_checks is None
            or not unresolved_checks
        ):
            return None
        source_pack = source_ref.get("pack")
        adjudication_source_anchor = source_ref.get("source_anchor")
        binding_digest = source_ref.get("binding_digest")
        if not all(
            isinstance(item, str) and item.strip()
            for item in (
                source_pack,
                adjudication_source_anchor,
                binding_digest,
            )
        ) or not (
            isinstance(binding_digest, str)
            and len(binding_digest) == 64
            and set(binding_digest) <= set("0123456789abcdef")
        ):
            return None
        result.append(
            TaiyiBoardPredicate(
                predicate_id=cast(str, predicate_id),
                name=cast(str, name),
                predicate=cast(str, predicate),
                fact_paths=fact_paths,
                source_anchor=cast(str, source_anchor),
                source_dependency_id=cast(str, source_dependency_id),
                status="predicate_matched_not_verdict",
                identity_adjudication=TaiyiPatternIdentityAdjudication(
                    status="adjudicated_pattern_identity",
                    decision_scope="taiyi_board_pattern_identity",
                    pattern_id=cast(str, predicate_id),
                    pattern_name=cast(str, name),
                    hard_verdict=None,
                    event_verdict=None,
                    source_ref=TaiyiPatternSourceRef(
                        pack=cast(str, source_pack),
                        rule_id=cast(str, predicate_id),
                        source_anchor=cast(str, adjudication_source_anchor),
                        verification_status="verified",
                        binding_digest=binding_digest,
                    ),
                    unresolved_checks=unresolved_checks,
                ),
            )
        )
    return tuple(result)


def _taiyi_scope_contract(value: object) -> TaiyiScopeContract | None:
    if not isinstance(value, Mapping):
        return None
    strings = [
        value.get("declared_scope"),
        value.get("interpretation_policy"),
    ]
    horizons = _taiyi_string_tuple(value.get("supported_horizons"))
    objects = _taiyi_string_tuple(value.get("supported_objects"))
    unsupported = _taiyi_string_tuple(value.get("unsupported_scopes"))
    if (
        not all(isinstance(item, str) and item.strip() for item in strings)
        or horizons is None
        or objects is None
        or unsupported is None
    ):
        return None
    return TaiyiScopeContract(
        declared_scope=cast(str, strings[0]),
        interpretation_policy=cast(str, strings[1]),
        supported_horizons=horizons,
        supported_objects=objects,
        unsupported_scopes=unsupported,
    )


def project_taiyi_view_model(
    brief: Mapping[str, object] | None,
) -> TaiyiChartV1 | None:
    """Project Taiyi's annual macro board and keep predicates non-verdictive."""

    if brief is None or not _capability_is(brief, "taiyi"):
        return None
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    required = {
        field: _brief_fact_value(facts, field)
        for field in (
            "calendar",
            "epoch",
            "cycle",
            "board",
            "host_guest",
            "four_generals",
            "long_cycle_deities",
            "board_predicates",
            "scope_contract",
        )
    }
    if subject_ref is None or any(value is None for value in required.values()):
        return None
    calendar = _taiyi_calendar(cast(tuple[str, object], required["calendar"])[1])
    epoch = _taiyi_epoch(cast(tuple[str, object], required["epoch"])[1])
    cycle = _taiyi_cycle(cast(tuple[str, object], required["cycle"])[1])
    board = _taiyi_board(cast(tuple[str, object], required["board"])[1])
    host_guest_value = cast(tuple[str, object], required["host_guest"])[1]
    host_guest = dict(host_guest_value) if isinstance(host_guest_value, Mapping) else None
    four_generals = _taiyi_four_generals(
        cast(tuple[str, object], required["four_generals"])[1]
    )
    long_cycle_deities = _taiyi_long_cycle_deities(
        cast(tuple[str, object], required["long_cycle_deities"])[1]
    )
    predicates = _taiyi_predicates(
        cast(tuple[str, object], required["board_predicates"])[1]
    )
    scope_contract = _taiyi_scope_contract(
        cast(tuple[str, object], required["scope_contract"])[1]
    )
    if (
        calendar is None
        or epoch is None
        or cycle is None
        or board is None
        or host_guest is None
        or four_generals is None
        or long_cycle_deities is None
        or predicates is None
        or scope_contract is None
    ):
        return None
    return TaiyiChartV1(
        subject_ref=subject_ref,
        calendar=calendar,
        epoch=epoch,
        cycle=cycle,
        board=board,
        host_guest=host_guest,
        four_generals=four_generals,
        long_cycle_deities=long_cycle_deities,
        board_predicates=predicates,
        scope_contract=scope_contract,
    )


def _selection_candidates(value: object) -> tuple[SelectionCandidate, ...] | None:
    if not isinstance(value, list):
        return None
    result: list[SelectionCandidate] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        candidate_id = raw.get("candidate_id")
        civil_date = raw.get("civil_date")
        best_time_id = raw.get("best_candidate_time_id")
        eligibility = raw.get("eligibility")
        rejection_reasons = raw.get("rejection_reasons")
        ranking_components = raw.get("ranking_components")
        if (
            not all(
                isinstance(item, str) and item.strip()
                for item in (candidate_id, civil_date, best_time_id)
            )
            or not isinstance(eligibility, Mapping)
            or not isinstance(rejection_reasons, list)
            or not isinstance(ranking_components, Mapping)
            or not all(isinstance(item, Mapping) for item in rejection_reasons)
        ):
            return None
        result.append(
            SelectionCandidate(
                candidate_id=cast(str, candidate_id),
                civil_date=cast(str, civil_date),
                best_candidate_time_id=cast(str, best_time_id),
                eligibility=dict(eligibility),
                rejection_reasons=tuple(dict(item) for item in rejection_reasons),
                ranking_components=dict(ranking_components),
            )
        )
    return tuple(result)


def _selection_ranking(value: object) -> SelectionRanking | None:
    if not isinstance(value, Mapping):
        return None
    tuples = {
        field: _taiyi_string_tuple(value.get(field))
        for field in (
            "component_order",
            "eligible_candidate_ids",
            "eligible_date_time_candidate_ids",
            "ordered_candidate_ids",
            "ordered_date_time_candidate_ids",
        )
    }
    if any(items is None for items in tuples.values()):
        return None
    method = value.get("method")
    folk_affects_rank = value.get("folk_affects_rank")
    opaque_numeric_score = value.get("opaque_numeric_score")
    if (
        not isinstance(method, str)
        or not method.strip()
        or not isinstance(folk_affects_rank, bool)
        or not isinstance(opaque_numeric_score, bool)
    ):
        return None
    return SelectionRanking(
        component_order=cast(tuple[str, ...], tuples["component_order"]),
        eligible_candidate_ids=cast(tuple[str, ...], tuples["eligible_candidate_ids"]),
        eligible_date_time_candidate_ids=cast(
            tuple[str, ...], tuples["eligible_date_time_candidate_ids"]
        ),
        folk_affects_rank=folk_affects_rank,
        method=method,
        opaque_numeric_score=opaque_numeric_score,
        ordered_candidate_ids=cast(tuple[str, ...], tuples["ordered_candidate_ids"]),
        ordered_date_time_candidate_ids=cast(
            tuple[str, ...], tuples["ordered_date_time_candidate_ids"]
        ),
    )


def _selection_lineage(value: object) -> SelectionLineagePolicy | None:
    if not isinstance(value, Mapping):
        return None
    text_fields = ("folk", "folk_priority", "official", "official_priority")
    values = [value.get(field) for field in text_fields]
    booleans = [value.get(field) for field in ("merge_verdicts", "preserve_disagreement")]
    if not all(isinstance(item, str) and item.strip() for item in values) or not all(
        isinstance(item, bool) for item in booleans
    ):
        return None
    return SelectionLineagePolicy(
        folk=cast(str, values[0]),
        folk_priority=cast(str, values[1]),
        merge_verdicts=cast(bool, booleans[0]),
        official=cast(str, values[2]),
        official_priority=cast(str, values[3]),
        preserve_disagreement=cast(bool, booleans[1]),
    )


def project_selection_view_model(
    brief: Mapping[str, object] | None,
) -> SelectionChartV1 | None:
    """Project bounded public selection facts and ranking mechanics."""

    if brief is None or not _capability_is(brief, "selection"):
        return None
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    fields = {
        field: _brief_fact_value(facts, field)
        for field in (
            "event_profile",
            "eligible_candidates",
            "eligible_date_time_candidates",
            "eliminations",
            "ranking",
            "lineage_policy",
            "no_valid_candidate",
            "basis_projection",
            "source_conditioned_patterns",
        )
    }
    if subject_ref is None or any(value is None for value in fields.values()):
        return None
    event_profile = cast(tuple[str, object], fields["event_profile"])[1]
    eligible_candidates = _selection_candidates(
        cast(tuple[str, object], fields["eligible_candidates"])[1]
    )
    eligible_date_times = _selection_date_time_ids(
        cast(tuple[str, object], fields["eligible_date_time_candidates"])[1]
    )
    eliminations_value = cast(tuple[str, object], fields["eliminations"])[1]
    eliminations = (
        tuple(dict(item) for item in eliminations_value)
        if isinstance(eliminations_value, list)
        and all(isinstance(item, Mapping) for item in eliminations_value)
        else None
    )
    ranking = _selection_ranking(cast(tuple[str, object], fields["ranking"])[1])
    lineage = _selection_lineage(
        cast(tuple[str, object], fields["lineage_policy"])[1]
    )
    no_valid = cast(tuple[str, object], fields["no_valid_candidate"])[1]
    basis = cast(tuple[str, object], fields["basis_projection"])[1]
    source_patterns_fact = fields["source_conditioned_patterns"]
    source_patterns = (
        ()
        if source_patterns_fact is None
        else _source_conditioned_patterns(
            source_patterns_fact[1], SelectionSourcePattern
        )
    )
    if (
        not isinstance(event_profile, str)
        or not event_profile.strip()
        or eligible_candidates is None
        or eligible_date_times is None
        or eliminations is None
        or ranking is None
        or lineage is None
        or not isinstance(no_valid, bool)
        or not isinstance(basis, Mapping)
        or source_patterns is None
    ):
        return None
    return SelectionChartV1(
        subject_ref=subject_ref,
        event_profile=event_profile,
        eligible_candidates=eligible_candidates,
        eligible_date_time_candidates=eligible_date_times,
        eliminations=eliminations,
        ranking=ranking,
        lineage_policy=lineage,
        no_valid_candidate=no_valid,
        basis_projection=dict(basis),
        source_conditioned_patterns=source_patterns,
    )


def project_fengshui_view_model(
    brief: Mapping[str, object] | None,
) -> FengshuiViewV1 | None:
    """Project measured spatial facts without vision or outcome judgments."""

    if brief is None or not _capability_is(brief, "fengshui"):
        return None
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    fields = {
        field: _brief_fact_value(facts, field)
        for field in (
            "active_subprofiles",
            "observation_provenance",
            "compass",
            "building_chronology",
            "layout_graph",
            "form",
            "liqi",
            "active_source_rule_ids",
            "conflicts",
            "uncertainties",
            "critical_missing",
        )
    }
    if subject_ref is None or any(value is None for value in fields.values()):
        return None
    active = cast(tuple[str, object], fields["active_subprofiles"])[1]
    active_values = _taiyi_string_tuple(active)
    provenance = cast(tuple[str, object], fields["observation_provenance"])[1]
    compass = cast(tuple[str, object], fields["compass"])[1]
    building = cast(tuple[str, object], fields["building_chronology"])[1]
    layout = cast(tuple[str, object], fields["layout_graph"])[1]
    form = cast(tuple[str, object], fields["form"])[1]
    liqi = cast(tuple[str, object], fields["liqi"])[1]
    source_ids = _taiyi_string_tuple(
        cast(tuple[str, object], fields["active_source_rule_ids"])[1]
    )
    conflicts = cast(tuple[str, object], fields["conflicts"])[1]
    uncertainties = cast(tuple[str, object], fields["uncertainties"])[1]
    missing = _taiyi_string_tuple(
        cast(tuple[str, object], fields["critical_missing"])[1]
    )
    source_patterns_fact = _brief_fact_value(facts, "source_conditioned_patterns")
    source_patterns = (
        ()
        if source_patterns_fact is None
        else _source_conditioned_patterns(
            source_patterns_fact[1], FengshuiSourcePattern
        )
    )
    lists = (conflicts, uncertainties)
    if (
        active_values is None
        or not set(active_values) <= {"form", "liqi"}
        or not all(
            isinstance(item, Mapping)
            for item in (provenance, compass, building, layout, form, liqi)
        )
        or source_ids is None
        or any(
            not isinstance(items, list)
            or not all(isinstance(item, Mapping) for item in items)
            for items in lists
        )
        or missing is None
        or source_patterns is None
    ):
        return None
    return FengshuiViewV1(
        subject_ref=subject_ref,
        active_subprofiles=cast(tuple[Literal["form", "liqi"], ...], active_values),
        observation_provenance=dict(cast(Mapping[str, object], provenance)),
        compass=dict(cast(Mapping[str, object], compass)),
        building_chronology=dict(cast(Mapping[str, object], building)),
        layout_graph=dict(cast(Mapping[str, object], layout)),
        form=dict(cast(Mapping[str, object], form)),
        liqi=dict(cast(Mapping[str, object], liqi)),
        active_source_rule_ids=source_ids,
        conflicts=tuple(dict(item) for item in cast(list[Mapping[str, object]], conflicts)),
        uncertainties=tuple(dict(item) for item in cast(list[Mapping[str, object]], uncertainties)),
        critical_missing=missing,
        source_conditioned_patterns=source_patterns,
    )


def _qimen_int(value: object, *, minimum: int, maximum: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if minimum <= value <= maximum else None


def _qimen_strings(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    if not all(isinstance(item, str) and item.strip() for item in value):
        return None
    return tuple(cast(str, item) for item in value)


def _qimen_plate_stems(value: object) -> tuple[QimenPlateStem, ...] | None:
    if not isinstance(value, list):
        return None
    result: list[QimenPlateStem] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        palace = _qimen_int(raw.get("palace"), minimum=1, maximum=9)
        stem = raw.get("stem")
        kind = raw.get("kind")
        if palace is None or not isinstance(stem, str) or not stem.strip():
            return None
        if kind not in {"six_instrument", "three_wonder"}:
            return None
        result.append(QimenPlateStem(palace=palace, stem=stem, kind=kind))
    return tuple(result)


def _qimen_instruments_wonders(value: object) -> QimenInstrumentsWonders | None:
    if not isinstance(value, Mapping):
        return None
    six_instruments = _qimen_strings(value.get("six_instruments"))
    three_wonders = _qimen_strings(value.get("three_wonders"))
    earth_plate = _qimen_plate_stems(value.get("earth_plate"))
    heaven_plate = _qimen_plate_stems(value.get("heaven_plate"))
    hidden_jia = value.get("hidden_jia")
    if not isinstance(hidden_jia, Mapping):
        return None
    hidden_xun = hidden_jia.get("xun")
    hidden_instrument = hidden_jia.get("instrument")
    if (
        six_instruments is None
        or three_wonders is None
        or earth_plate is None
        or heaven_plate is None
        or not isinstance(hidden_xun, str)
        or not hidden_xun.strip()
        or not isinstance(hidden_instrument, str)
        or not hidden_instrument.strip()
    ):
        return None
    return QimenInstrumentsWonders(
        six_instruments=six_instruments,
        three_wonders=three_wonders,
        earth_plate=earth_plate,
        heaven_plate=heaven_plate,
        hidden_jia=QimenHiddenJia(xun=hidden_xun, instrument=hidden_instrument),
    )


def _qimen_named_patterns(value: object) -> tuple[QimenNamedPattern, ...] | None:
    if not isinstance(value, list):
        return None
    result: list[QimenNamedPattern] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        pattern_id = raw.get("id")
        name = raw.get("name")
        status = raw.get("status")
        raw_palace = raw.get("palace")
        palace = (
            None
            if raw_palace is None
            else _qimen_int(raw_palace, minimum=1, maximum=9)
        )
        adjudication = raw.get("identity_adjudication")
        if (
            not isinstance(pattern_id, str)
            or not pattern_id.strip()
            or not isinstance(name, str)
            or not name.strip()
            or status != "predicate_matched_not_verdict"
            or (raw_palace is not None and palace is None)
            or not isinstance(adjudication, Mapping)
        ):
            return None
        source_ref = adjudication.get("source_ref")
        unresolved_checks = _qimen_strings(adjudication.get("unresolved_checks"))
        if (
            adjudication.get("status") != "adjudicated_pattern_identity"
            or adjudication.get("decision_scope")
            != "qimen_named_pattern_identity"
            or adjudication.get("pattern_id") != pattern_id
            or adjudication.get("pattern_name") != name
            or adjudication.get("palace") != palace
            or adjudication.get("hard_verdict") is not None
            or adjudication.get("event_verdict") is not None
            or not isinstance(source_ref, Mapping)
            or source_ref.get("verification_status") != "verified"
            or source_ref.get("rule_id") != pattern_id
            or unresolved_checks is None
            or not unresolved_checks
        ):
            return None
        source_pack = source_ref.get("pack")
        source_anchor = source_ref.get("source_anchor")
        binding_digest = source_ref.get("binding_digest")
        if not all(
            isinstance(item, str) and item.strip()
            for item in (source_pack, source_anchor, binding_digest)
        ) or not (
            isinstance(binding_digest, str)
            and len(binding_digest) == 64
            and set(binding_digest) <= set("0123456789abcdef")
        ):
            return None
        result.append(
            QimenNamedPattern(
                id=pattern_id,
                name=name,
                status="predicate_matched_not_verdict",
                palace=palace,
                identity_adjudication=QimenPatternIdentityAdjudication(
                    status="adjudicated_pattern_identity",
                    decision_scope="qimen_named_pattern_identity",
                    pattern_id=pattern_id,
                    pattern_name=name,
                    palace=palace,
                    hard_verdict=None,
                    event_verdict=None,
                    source_ref=QimenPatternSourceRef(
                        pack=cast(str, source_pack),
                        rule_id=pattern_id,
                        source_anchor=cast(str, source_anchor),
                        verification_status="verified",
                        binding_digest=binding_digest,
                    ),
                    unresolved_checks=unresolved_checks,
                ),
            )
        )
    return tuple(result)


def project_qimen_view_model(
    brief: Mapping[str, object] | None,
) -> QimenChartV1 | None:
    """Project the Qimen board and bounded source-adjudicated pattern identities."""

    if brief is None or not _capability_is(brief, "qimen"):
        return None
    facts = brief.get("facts")
    ju = _brief_fact_value(facts, "ju")
    chief = _brief_fact_value(facts, "chief")
    director = _brief_fact_value(facts, "director")
    palaces = _brief_fact_value(facts, "palaces")
    instruments_wonders = _brief_fact_value(facts, "instruments_wonders")
    xunkong = _brief_fact_value(facts, "xunkong")
    horse = _brief_fact_value(facts, "horse")
    named_patterns = _brief_fact_value(facts, "named_patterns")
    subject_ref = _subject_ref(brief, facts)
    question = _question(brief)
    if (
        ju is None
        or chief is None
        or director is None
        or palaces is None
        or instruments_wonders is None
        or xunkong is None
        or horse is None
        or named_patterns is None
        or subject_ref is None
        or question is None
    ):
        return None

    ju_value = ju[1]
    if not isinstance(ju_value, Mapping):
        return None
    dun = ju_value.get("dun")
    number = _qimen_int(ju_value.get("number"), minimum=1, maximum=9)
    if dun not in {"yin", "yang"} or number is None:
        return None

    chief_value = chief[1]
    if not isinstance(chief_value, Mapping):
        return None
    chief_strings = [chief_value.get(key) for key in ("star", "door", "hidden_instrument")]
    chief_ints = [
        _qimen_int(chief_value.get(key), minimum=1, maximum=9)
        for key in ("xun_palace", "hosted_xun_palace", "destination_palace")
    ]
    if not all(isinstance(item, str) and item.strip() for item in chief_strings) or not all(
        item is not None for item in chief_ints
    ):
        return None

    director_value = director[1]
    if not isinstance(director_value, Mapping):
        return None
    director_door = director_value.get("door")
    director_ints = [
        _qimen_int(director_value.get(key), minimum=1, maximum=9)
        for key in ("xun_palace", "destination_palace")
    ]
    hour_offset = _qimen_int(
        director_value.get("hour_offset_in_xun"), minimum=0, maximum=9
    )
    if (
        not isinstance(director_door, str)
        or not director_door.strip()
        or not all(item is not None for item in director_ints)
        or hour_offset is None
    ):
        return None

    raw_palaces = palaces[1]
    if not isinstance(raw_palaces, list) or len(raw_palaces) != 9:
        return None
    result: list[QimenPalace] = []
    for raw in raw_palaces:
        if not isinstance(raw, Mapping):
            return None
        palace_id = _qimen_int(raw.get("palace"), minimum=1, maximum=9)
        earth_stem = raw.get("earth_stem")
        heaven_stems = _qimen_strings(raw.get("heaven_stems", []))
        if palace_id is None or not isinstance(earth_stem, str) or not earth_stem.strip():
            return None
        if heaven_stems is None:
            return None
        stars = _qimen_strings(raw.get("stars", []))
        if stars is None:
            return None
        star = stars[0] if stars else None
        door = raw.get("door") if isinstance(raw.get("door"), str) else None
        deity = raw.get("deity") if isinstance(raw.get("deity"), str) else None
        result.append(
            QimenPalace(
                palace_id=str(palace_id),
                stem=earth_stem,
                heaven_stems=heaven_stems,
                stars=stars,
                star=star,
                door=door,
                deity=deity,
            )
        )
    result.sort(key=lambda palace: int(palace.palace_id))
    if [palace.palace_id for palace in result] != [str(item) for item in range(1, 10)]:
        return None

    xunkong_value = xunkong[1]
    horse_value = horse[1]
    if not isinstance(xunkong_value, Mapping) or not isinstance(horse_value, Mapping):
        return None
    xun = xunkong_value.get("xun")
    xunkong_branches = _qimen_strings(xunkong_value.get("branches"))
    xunkong_palaces = xunkong_value.get("palaces")
    if not isinstance(xun, str) or not xun.strip() or xunkong_branches is None:
        return None
    if not isinstance(xunkong_palaces, list):
        return None
    parsed_xunkong_palaces = tuple(
        _qimen_int(item, minimum=1, maximum=9) for item in xunkong_palaces
    )
    if any(item is None for item in parsed_xunkong_palaces):
        return None
    horse_strings = [horse_value.get("hour_branch"), horse_value.get("branch")]
    horse_palace = _qimen_int(horse_value.get("palace"), minimum=1, maximum=9)
    if (
        not all(isinstance(item, str) and item.strip() for item in horse_strings)
        or horse_palace is None
    ):
        return None
    parsed_instruments_wonders = _qimen_instruments_wonders(instruments_wonders[1])
    parsed_named_patterns = _qimen_named_patterns(named_patterns[1])
    if parsed_instruments_wonders is None or parsed_named_patterns is None:
        return None

    return QimenChartV1(
        subject_ref=subject_ref,
        question=question,
        dun_type=dun,
        ju_number=number,
        palaces=tuple(result),
        chief=QimenChief(
            star=cast(str, chief_strings[0]),
            door=cast(str, chief_strings[1]),
            hidden_instrument=cast(str, chief_strings[2]),
            xun_palace=cast(int, chief_ints[0]),
            hosted_xun_palace=cast(int, chief_ints[1]),
            destination_palace=cast(int, chief_ints[2]),
        ),
        director=QimenDirector(
            door=director_door,
            xun_palace=cast(int, director_ints[0]),
            destination_palace=cast(int, director_ints[1]),
            hour_offset_in_xun=hour_offset,
        ),
        instruments_wonders=parsed_instruments_wonders,
        xunkong=QimenXunkong(
            xun=xun,
            branches=xunkong_branches,
            palaces=cast(tuple[int, ...], parsed_xunkong_palaces),
        ),
        horse=QimenHorse(
            hour_branch=cast(str, horse_strings[0]),
            branch=cast(str, horse_strings[1]),
            palace=horse_palace,
        ),
        named_patterns=parsed_named_patterns,
    )


_DALIUREN_RUNTIME_CORE_FACTS_VERSION = "mingli-liuren-runtime-core-facts-v1"
_DALIUREN_RUNTIME_REQUIRED_FIELDS = (
    "day_hour",
    "earth_plate",
    "heaven_plate",
    "heavenly_generals",
    "month_general",
    "noble_person",
    "lesson_method",
    "four_lessons",
    "three_transmissions",
    "plate_offset",
    "xunkong",
    "structural_patterns",
    "dimension_facts",
)
_DALIUREN_RUNTIME_OPTIONAL_FIELDS = (
    "source_conditioned_patterns",
    "timing_candidates",
)
_DALIUREN_RUNTIME_ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        *_DALIUREN_RUNTIME_REQUIRED_FIELDS,
        *_DALIUREN_RUNTIME_OPTIONAL_FIELDS,
    }
)
_DALIUREN_RUNTIME_TRANSMISSION_FIELDS = frozenset(
    {"stage", "branch", "heavenly_general", "six_relative"}
)
_DALIUREN_RUNTIME_TRANSMISSION_STAGES = ("initial", "middle", "final")
_DALIUREN_SOURCE_PATTERN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "rule_id",
        "local_rule_id",
        "title",
        "source_pack",
        "source_anchor",
        "status",
        "fact_paths",
        "predicate_audit",
        "source_dependency_id",
    }
)
_DALIUREN_SOURCE_PATTERN_METADATA: Final[
    dict[str, tuple[str, str, str, str, str]]
] = {
    "四课不备": (
        "DLR-S01",
        "liuren.structural.incomplete-four-lessons",
        "san-shi/daliuren-daquan",
        "fulltext.md#L58",
        "liuren.source-conditioned-structural-patterns-v1",
    ),
    "八专日": (
        "DLR-08",
        "liuren.structural.bazhuan-day",
        "san-shi/daliuren-daquan",
        "fulltext.md#L7556",
        "liuren.source-conditioned-structural-patterns-v1",
    ),
    "伏吟": (
        "DLR-09",
        "liuren.structural.fuyin",
        "san-shi/daliuren-daquan",
        "fulltext.md#L7696",
        "liuren.source-conditioned-structural-patterns-v1",
    ),
    "反吟": (
        "DLR-10",
        "liuren.structural.fanyin",
        "san-shi/daliuren-daquan",
        "fulltext.md#L7874",
        "liuren.source-conditioned-structural-patterns-v1",
    ),
}
_DALIUREN_SOURCE_PATTERN_STATUS = "predicate_matched_not_verdict"


def _daliuren_filter_lesson_method(value: object) -> object:
    if not isinstance(value, Mapping):
        return value
    allowed = set(DaliurenLessonMethod.model_fields)
    return {key: value[key] for key in allowed if key in value}


def _daliuren_runtime_core_facts_payload(facts: object) -> Mapping[str, object] | None:
    """Read the additive Runtime contract from the published brief fact."""

    fact = _brief_fact_value(facts, "runtime_core_facts")
    if fact is None:
        return None
    payload = fact[1]
    if not isinstance(payload, Mapping):
        return None
    if payload.get("schema_version") != _DALIUREN_RUNTIME_CORE_FACTS_VERSION:
        return None
    if set(payload) - _DALIUREN_RUNTIME_ENVELOPE_FIELDS:
        return None
    if "timing_candidates" in payload and not isinstance(
        payload["timing_candidates"], list
    ):
        return None
    return payload


def _daliuren_individual_facts_payload(facts: object) -> Mapping[str, object] | None:
    """Assemble v51 Liuren plate facts published as individual brief rows."""

    payload: dict[str, object] = {
        "schema_version": _DALIUREN_RUNTIME_CORE_FACTS_VERSION,
    }
    for field in (
        *_DALIUREN_RUNTIME_REQUIRED_FIELDS,
        *_DALIUREN_RUNTIME_OPTIONAL_FIELDS,
    ):
        fact = _brief_fact_value(facts, field)
        if fact is None:
            continue
        value: object = fact[1]
        if field == "lesson_method":
            value = _daliuren_filter_lesson_method(value)
        payload[field] = value
    if set(payload) - _DALIUREN_RUNTIME_ENVELOPE_FIELDS:
        return None
    if "timing_candidates" in payload and not isinstance(
        payload["timing_candidates"], list
    ):
        return None
    if not _daliuren_required_fields_present(payload):
        return None
    return payload


def _daliuren_required_fields_present(payload: Mapping[str, object]) -> bool:
    """Reject v1 Runtime bundles that omit a required contract field."""

    return all(
        field in payload and payload[field] is not None
        for field in _DALIUREN_RUNTIME_REQUIRED_FIELDS
    )


def _daliuren_lessons_from_runtime(raw_lessons: object) -> tuple[DaliurenLesson, ...] | None:
    if not isinstance(raw_lessons, list):
        return None
    lessons: list[DaliurenLesson] = []
    for offset, raw in enumerate(raw_lessons, start=1):
        if not isinstance(raw, Mapping):
            return None
        lesson_id = raw.get("lesson", offset)
        upper = raw.get("upper")
        lower = raw.get("lower")
        if not isinstance(lesson_id, (str, int)) or isinstance(lesson_id, bool):
            return None
        if not isinstance(upper, str) or upper not in DALIUREN_LESSON_UPPERS:
            return None
        if not isinstance(lower, str) or not lower.strip():
            return None
        lessons.append(
            DaliurenLesson(
                lesson_id=str(lesson_id),
                upper=upper,
                lower=lower,
            )
        )
    if len(lessons) != 4:
        return None
    return tuple(lessons)


def _daliuren_transmissions_from_runtime(
    raw_transmissions: object,
) -> tuple[DaliurenTransmission, ...] | None:
    if not isinstance(raw_transmissions, list):
        return None
    if len(raw_transmissions) != len(_DALIUREN_RUNTIME_TRANSMISSION_STAGES):
        return None
    transmissions: list[DaliurenTransmission] = []
    for expected_stage, raw in zip(
        _DALIUREN_RUNTIME_TRANSMISSION_STAGES,
        raw_transmissions,
        strict=True,
    ):
        if not isinstance(raw, Mapping) or set(raw) != _DALIUREN_RUNTIME_TRANSMISSION_FIELDS:
            return None
        stage = raw.get("stage")
        branch = raw.get("branch")
        general = raw.get("heavenly_general")
        six_relative = raw.get("six_relative")
        if stage != expected_stage:
            return None
        if not all(
            isinstance(item, str) and item.strip()
            for item in (branch, general, six_relative)
        ):
            return None
        transmissions.append(
            DaliurenTransmission(
                stage=cast(Literal["initial", "middle", "final"], stage),
                branch=cast(str, branch),
                general=cast(str, general),
            )
        )
    return tuple(transmissions)


def _daliuren_source_conditioned_patterns(
    value: object,
    *,
    structural_patterns: object,
    four_lessons: object,
) -> tuple[DaliurenSourcePattern, ...] | None:
    """Accept only MING-17's audited source objects as a complete block."""

    if not isinstance(value, (list, tuple)):
        return None
    if not value:
        return ()
    if not isinstance(structural_patterns, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in structural_patterns
    ):
        return None

    result: list[DaliurenSourcePattern] = []
    seen_titles: set[str] = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != _DALIUREN_SOURCE_PATTERN_FIELDS:
            return None
        title = raw.get("title")
        metadata = (
            _DALIUREN_SOURCE_PATTERN_METADATA.get(title)
            if isinstance(title, str)
            else None
        )
        if metadata is None or not isinstance(title, str) or title in seen_titles:
            return None
        (
            expected_rule_id,
            expected_local_rule_id,
            expected_source_pack,
            expected_source_anchor,
            expected_dependency_id,
        ) = metadata
        if (
            raw.get("rule_id") != expected_rule_id
            or raw.get("local_rule_id") != expected_local_rule_id
            or raw.get("source_pack") != expected_source_pack
            or raw.get("source_anchor") != expected_source_anchor
            or raw.get("status") != _DALIUREN_SOURCE_PATTERN_STATUS
            or raw.get("source_dependency_id") != expected_dependency_id
        ):
            return None

        fact_paths = raw.get("fact_paths")
        predicate_audit = raw.get("predicate_audit")
        if not isinstance(fact_paths, (list, tuple)) or not isinstance(
            predicate_audit, (list, tuple)
        ):
            return None
        if not all(
            isinstance(item, str) and item.strip()
            for item in (*fact_paths, *predicate_audit)
        ):
            return None
        matching_indices = daliuren_in_range_structural_indices(
            structural_patterns,
            title,
        )
        if len(matching_indices) != 1:
            return None
        if len(set(fact_paths)) != len(fact_paths) or len(set(predicate_audit)) != len(
            predicate_audit
        ):
            return None

        matching_index = matching_indices[0]
        structural_fact_path = (
            f"fact:/chart_facts/output/structural_patterns/{matching_index}"
        )
        structural_predicate_audit = (
            f"/chart_facts/output/structural_patterns/{matching_index}:eq:{title}"
        )
        if (
            structural_fact_path not in fact_paths
            or structural_predicate_audit not in predicate_audit
        ):
            return None

        allowed_fact_paths = {structural_fact_path}
        allowed_predicate_audits = {structural_predicate_audit}

        if title == "四课不备":
            if not isinstance(four_lessons, (list, tuple)) or len(four_lessons) != 4:
                return None
            lesson_uppers: set[str] = set()
            for lesson in four_lessons:
                if not isinstance(lesson, Mapping):
                    return None
                upper = cast(object, lesson.get("upper"))
                if not isinstance(upper, str) or upper not in DALIUREN_LESSON_UPPERS:
                    return None
                lesson_uppers.add(upper)
            if len(lesson_uppers) != 3:
                return None
            four_lesson_fact_paths = {
                f"fact:/chart_facts/output/four_lessons/{index}/upper"
                for index in range(4)
            }
            four_lesson_audit = (
                "/chart_facts/output/four_lessons/*/upper:distinct_count_eq:3"
            )
            if not four_lesson_fact_paths.issubset(set(fact_paths)):
                return None
            if four_lesson_audit not in predicate_audit:
                return None
            allowed_fact_paths.update(four_lesson_fact_paths)
            allowed_predicate_audits.add(four_lesson_audit)

        if not set(fact_paths).issubset(allowed_fact_paths):
            return None
        if not set(predicate_audit).issubset(allowed_predicate_audits):
            return None

        try:
            parsed_pattern = DaliurenSourcePattern(
                rule_id=expected_rule_id,
                local_rule_id=expected_local_rule_id,
                title=title,
                source_pack=expected_source_pack,
                source_anchor=expected_source_anchor,
                status=_DALIUREN_SOURCE_PATTERN_STATUS,
                fact_paths=tuple(fact_paths),
                predicate_audit=tuple(predicate_audit),
                source_dependency_id=expected_dependency_id,
            )
        except ValueError:
            return None
        if daliuren_source_pattern_structural_index(parsed_pattern) != matching_index:
            return None
        result.append(parsed_pattern)
        seen_titles.add(title)

    return tuple(result)


def _daliuren_core_facts_from_runtime(
    payload: Mapping[str, object],
) -> DaliurenCoreFacts | None:
    """Project pinned core facts from the validated Runtime bundle."""

    required_core_fields = (
        "day_hour",
        "dimension_facts",
        "earth_plate",
        "heaven_plate",
        "heavenly_generals",
        "lesson_method",
        "month_general",
        "noble_person",
        "plate_offset",
        "structural_patterns",
        "xunkong",
    )
    # Required Runtime fields must be handed to Pydantic unchanged. Filtering
    # by shape here would silently turn malformed required facts into defaults.
    kwargs = {field: payload[field] for field in required_core_fields}
    if "timing_candidates" in payload:
        kwargs["timing_candidates"] = payload["timing_candidates"]
    source_patterns = payload.get("source_conditioned_patterns")
    if source_patterns is not None:
        parsed_source_patterns = _daliuren_source_conditioned_patterns(
            source_patterns,
            structural_patterns=payload["structural_patterns"],
            four_lessons=payload["four_lessons"],
        )
        if parsed_source_patterns is not None:
            kwargs["source_conditioned_patterns"] = parsed_source_patterns
    try:
        return DaliurenCoreFacts.model_validate(kwargs)
    except ValidationError:
        return None


def project_daliuren_view_model(
    brief: Mapping[str, object] | None,
) -> DaliurenChartV1 | None:
    """Project daliuren-chart/v1 from mingli-liuren-runtime-core-facts-v1 only."""

    if brief is None or not _capability_is(brief, "liuren"):
        return None
    facts = brief.get("facts")
    runtime_core = _daliuren_runtime_core_facts_payload(facts)
    if runtime_core is None:
        runtime_core = _daliuren_individual_facts_payload(facts)
    subject_ref = _subject_ref(brief, facts)
    question = _question(brief)
    if runtime_core is None or subject_ref is None or question is None:
        return None
    if not _daliuren_required_fields_present(runtime_core):
        return None

    lessons = _daliuren_lessons_from_runtime(runtime_core.get("four_lessons"))
    transmissions = _daliuren_transmissions_from_runtime(
        runtime_core.get("three_transmissions")
    )
    if lessons is None or transmissions is None:
        return None

    return DaliurenChartV1(
        subject_ref=subject_ref,
        question=question,
        lessons=lessons,
        transmissions=transmissions,
        core_facts=_daliuren_core_facts_from_runtime(runtime_core),
        public_labels=public_key_labels(DALIUREN_PUBLIC_LABELS),
    )


def _physiognomy_observations(value: object) -> tuple[PhysiognomyObservation, ...] | None:
    """Map only the Runtime public observation fields into the UI contract.

    Runtime observation IDs, asset IDs, capture IDs, source references, and
    quality internals are deliberately not copied into the public ViewModel.
    The generated IDs are local render keys, not claims about Runtime facts.
    """

    if not isinstance(value, list):
        return None
    observations: list[PhysiognomyObservation] = []
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            return None
        region = raw.get("region")
        feature_kind = raw.get("feature_kind")
        descriptor = raw.get("descriptor")
        visibility = raw.get("visibility")
        uncertainty = raw.get("uncertainty")
        if not all(
            isinstance(item, str) and item.strip()
            for item in (region, feature_kind, descriptor, visibility)
        ):
            return None
        region = cast(str, region)
        feature_kind = cast(str, feature_kind)
        descriptor = cast(str, descriptor)
        visibility = cast(str, visibility)
        if (
            isinstance(uncertainty, bool)
            or not isinstance(uncertainty, (int, float))
            or not math.isfinite(float(uncertainty))
            or not 0 <= float(uncertainty) <= 1
        ):
            return None
        observations.append(
            PhysiognomyObservation(
                observation_id=f"observation-{index}",
                region_id=region,
                feature_id=feature_kind,
                confidence=1.0 - float(uncertainty),
                display_text=f"{region}：{descriptor}（{visibility}）",
            )
        )
    return tuple(observations)


def _physiognomy_public_records(
    value: object,
    *,
    allowed_fields: frozenset[str],
) -> tuple[dict[str, object], ...] | None:
    """Keep only the Runtime's public, non-identity metadata for a record list."""

    if value is None:
        return ()
    if not isinstance(value, list):
        return None
    records: list[dict[str, object]] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        records.append(
            {
                key: raw[key]
                for key in allowed_fields
                if key in raw
            }
        )
    return tuple(records)


def _physiognomy_source_comparison(
    value: object,
) -> PhysiognomySourceComparison | None:
    if value is None:
        return PhysiognomySourceComparison()
    if not isinstance(value, Mapping):
        return None
    sources = _physiognomy_public_records(
        value.get("sources"),
        allowed_fields=frozenset({"title", "edition_caveat"}),
    )
    disagreements = _physiognomy_public_records(
        value.get("disagreements"),
        allowed_fields=frozenset({"sources", "summary"}),
    )
    retained = value.get("disagreements_retained")
    forced_resolution = value.get("forced_resolution")
    if (
        sources is None
        or disagreements is None
        or not isinstance(retained, bool)
        or not isinstance(forced_resolution, bool)
    ):
        return None
    return PhysiognomySourceComparison(
        sources=sources,
        disagreements_retained=retained,
        disagreements=disagreements,
        forced_resolution=forced_resolution,
    )


def project_physiognomy_view_model(
    brief: Mapping[str, object] | None,
) -> PhysiognomyViewV1 | None:
    """Project structured visible observations without interpreting a person."""

    if brief is None or not _capability_is(brief, "physiognomy"):
        return None
    facts = brief.get("facts")
    observations_fact = _brief_fact_value(facts, "normalized_visible_observations")
    subject_ref = _subject_ref(brief, facts)
    if observations_fact is None or subject_ref is None:
        return None
    observations = _physiognomy_observations(observations_fact[1])
    if observations is None:
        return None
    scope_fact = _brief_fact_value(facts, "observation_scope")
    mode_value = "face" if scope_fact is None else scope_fact[1]
    if not isinstance(mode_value, str) or mode_value not in {
        "face",
        "palm",
        "posture",
        "combined",
    }:
        return None
    mode = cast(Literal["face", "palm", "posture", "combined"], mode_value)
    field_values = {
        field: _brief_fact_value(facts, field)
        for field in (
            "missing_targets",
            "uncertainties",
            "observation_conflicts",
            "cross_capture_variations",
            "source_comparison",
            "active_source_rule_ids",
            "source_conditioned_patterns",
        )
    }
    missing_targets = _physiognomy_public_records(
        field_values["missing_targets"][1]
        if field_values["missing_targets"] is not None
        else None,
        allowed_fields=frozenset({"region", "feature_kind", "required", "reason"}),
    )
    uncertainties = _physiognomy_public_records(
        field_values["uncertainties"][1]
        if field_values["uncertainties"] is not None
        else None,
        allowed_fields=frozenset({"region", "feature_kind", "reason_codes"}),
    )
    conflicts = _physiognomy_public_records(
        field_values["observation_conflicts"][1]
        if field_values["observation_conflicts"] is not None
        else None,
        allowed_fields=frozenset(
            {"region", "feature_kind", "capture_scope", "observation_count", "blocking", "resolved"}
        ),
    )
    cross_capture_variations = _physiognomy_public_records(
        field_values["cross_capture_variations"][1]
        if field_values["cross_capture_variations"] is not None
        else None,
        allowed_fields=frozenset(
            {"region", "feature_kind", "capture_count", "descriptor_count", "auto_equivalent"}
        ),
    )
    source_comparison = _physiognomy_source_comparison(
        field_values["source_comparison"][1]
        if field_values["source_comparison"] is not None
        else None
    )
    active_source_rule_ids = (
        ()
        if field_values["active_source_rule_ids"] is None
        else _text_tuple(field_values["active_source_rule_ids"][1])
    )
    source_patterns = (
        ()
        if field_values["source_conditioned_patterns"] is None
        else _source_conditioned_patterns(
            field_values["source_conditioned_patterns"][1],
            PhysiognomySourcePattern,
        )
    )
    if (
        missing_targets is None
        or uncertainties is None
        or conflicts is None
        or cross_capture_variations is None
        or source_comparison is None
        or active_source_rule_ids is None
        or source_patterns is None
    ):
        return None
    return PhysiognomyViewV1(
        subject_ref=subject_ref,
        mode=mode,
        observations=observations,
        missing_targets=missing_targets,
        uncertainties=uncertainties,
        conflicts=conflicts,
        cross_capture_variations=cross_capture_variations,
        source_comparison=source_comparison,
        active_source_rule_ids=active_source_rule_ids,
        source_conditioned_patterns=source_patterns,
    )


_CANWEN_RUNTIME_TO_ART = {
    "bazi": "bazi",
    "ziwei": "ziwei",
    "xingming": "qizheng",
}
_CANWEN_ART_LABELS = {
    "bazi": "八字",
    "ziwei": "紫微",
    "qizheng": "七政",
}

_WENSHI_RUNTIME_TO_ART = {
    "liuyao": "liuyao",
    "qimen": "qimen",
    "liuren": "daliuren",
}
_WENSHI_ART_LABELS = {
    "liuyao": "六爻",
    "qimen": "奇门",
    "daliuren": "大六壬",
}
_ART_LABELS = {**_CANWEN_ART_LABELS, **_WENSHI_ART_LABELS}


def _brief_fact_value_for_capability(
    facts: object,
    *,
    capability_id: str,
    field_id: str,
) -> tuple[str, object] | None:
    if not isinstance(facts, (list, tuple)):
        return None
    suffix = f"/calculated/{capability_id}/{field_id}"
    for item in facts:
        if not isinstance(item, Mapping):
            continue
        ref = item.get("ref")
        if not isinstance(ref, str) or "/input/" in ref or not ref.endswith(suffix):
            continue
        return (
            ref,
            item.get("value"),
        )
    return None


def _canwen_selected_art_ids(request_view: Mapping[str, object]) -> tuple[str, ...] | None:
    raw = request_view.get("capability_ids")
    if not isinstance(raw, (list, tuple)):
        return None
    selected = tuple(
        _CANWEN_RUNTIME_TO_ART[item]
        for item in raw
        if isinstance(item, str) and item in _CANWEN_RUNTIME_TO_ART
    )
    if len(selected) not in {2, 3} or len(selected) != len(raw):
        return None
    if selected[0] != "bazi" or len(set(selected)) != len(selected):
        return None
    return selected


_CANWEN_BAZI_CANDIDATE_LABELS: Final[dict[str, str]] = {
    "strength": "强弱证据",
    "structure": "结构候选",
    "following_and_transformation": "从格/合化候选",
    "reasoning_tools": "推理工具",
    "salience_signals": "显著性信号",
}


def _canwen_bazi_candidate_signals(
    *,
    fact_ref: str,
    fact_value: object,
    subject_ref: str,
    dimension_id: str,
) -> tuple[ArtSignal, ...]:
    """Expose Bazi candidate lanes without turning them into cross-art claims."""

    if not isinstance(fact_value, Mapping) or fact_value.get("hard_verdict") is not None:
        return ()
    signals: list[ArtSignal] = []
    for raw_lane, raw_value in fact_value.items():
        lane = raw_lane if isinstance(raw_lane, str) else None
        if lane not in _CANWEN_BAZI_CANDIDATE_LABELS:
            continue
        available = bool(raw_value) if isinstance(raw_value, (Mapping, list, tuple)) else False
        if not available:
            continue
        signals.append(
            ArtSignal(
                art_id="bazi",
                subject_refs=(subject_ref,),
                signal_id=f"bazi.{dimension_id}.candidate_scope.{lane}",
                display_text=(
                    f"八字已提供{_CANWEN_BAZI_CANDIDATE_LABELS[lane]}；"
                    "当前仅保留候选事实，不形成跨术结论。"
                ),
                fact_refs=(fact_ref,),
            )
        )
    return tuple(signals)


def _source_pattern_signals(
    *,
    fact_ref: str,
    fact_value: object,
    subject_ref: str,
    dimension_id: str,
    art_id: Literal[
        "bazi",
        "ziwei",
        "qizheng",
        "liuyao",
        "qimen",
        "daliuren",
    ],
) -> tuple[ArtSignal, ...]:
    """Expose only source-bound predicate matches from a Runtime Provider."""

    if not isinstance(fact_value, (list, tuple)):
        return ()
    signals: list[ArtSignal] = []
    seen_rule_ids: set[str] = set()
    for raw_pattern in fact_value:
        if not isinstance(raw_pattern, Mapping):
            continue
        rule_id = raw_pattern.get("local_rule_id") or raw_pattern.get("rule_id")
        title = raw_pattern.get("title") or raw_pattern.get("name")
        if (
            not isinstance(rule_id, str)
            or not rule_id.strip()
            or rule_id in seen_rule_ids
            or not isinstance(title, str)
            or not title.strip()
            or raw_pattern.get("status") != "predicate_matched_not_verdict"
        ):
            continue
        seen_rule_ids.add(rule_id)
        signals.append(
            ArtSignal(
                art_id=art_id,
                subject_refs=(subject_ref,),
                signal_id=f"{art_id}.{dimension_id}.source_pattern.{rule_id}",
                display_text=(
                    f"{_ART_LABELS[art_id]}已匹配来源谓词“{title}”（{rule_id}）；"
                    "当前仅保留候选事实，不形成跨术结论。"
                ),
                fact_refs=(fact_ref,),
            )
        )
    return tuple(signals)


def project_canwen_view_model(
    brief: Mapping[str, object] | None,
) -> CanwenViewV1 | None:
    """Project only shared Runtime dimension scopes into a Canwen view.

    A dimension scope proves that a provider calculated facts for the requested
    dimension; it does not prove that two arts reached the same substantive
    conclusion.  The first Canwen slice therefore exposes scope alignment and
    missing cross-art scopes, while leaving interpretive convergence empty.
    """

    if brief is None:
        return None
    request_view = brief.get("request_view")
    if not isinstance(request_view, Mapping):
        return None
    selected_art_ids = _canwen_selected_art_ids(request_view)
    question = _question(brief)
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    raw_dimensions = request_view.get("dimension_ids")
    if (
        selected_art_ids is None
        or question is None
        or subject_ref is None
        or not isinstance(raw_dimensions, (list, tuple))
    ):
        return None
    dimensions: list[DimensionSynthesis] = []
    for raw_dimension in raw_dimensions:
        if not isinstance(raw_dimension, str) or not raw_dimension.strip():
            return None
        signals: list[ArtSignal] = []
        missing: list[str] = []
        scopes: list[str] = []
        for art_id in selected_art_ids:
            runtime_id = next(
                capability
                for capability, mapped_art in _CANWEN_RUNTIME_TO_ART.items()
                if mapped_art == art_id
            )
            scope_fact = _brief_fact_value_for_capability(
                facts,
                capability_id=runtime_id,
                field_id="dimension_fact_scope",
            )
            scope_value = scope_fact[1] if scope_fact is not None else None
            scope_row = scope_value.get(raw_dimension) if isinstance(scope_value, Mapping) else None
            scope = scope_row.get("scope") if isinstance(scope_row, Mapping) else None
            if scope_fact is None or not isinstance(scope, str) or not scope.strip():
                missing.append(art_id)
                continue
            scopes.append(scope)
            signals.append(
                ArtSignal(
                    art_id=cast(
                        Literal["bazi", "ziwei", "qizheng", "liuyao", "qimen", "daliuren"],
                        art_id,
                    ),
                    subject_refs=(subject_ref,),
                    signal_id=f"{art_id}.dimension_scope",
                    display_text=(
                        f"{_CANWEN_ART_LABELS[art_id]}已提供“{raw_dimension}”的"
                        f"计算事实范围：{scope}。"
                    ),
                    fact_refs=(scope_fact[0],),
                )
            )
            if runtime_id == "bazi":
                candidate_fact = _brief_fact_value_for_capability(
                    facts,
                    capability_id=runtime_id,
                    field_id="interpretive_candidates",
                )
                if candidate_fact is not None:
                    signals.extend(
                        _canwen_bazi_candidate_signals(
                            fact_ref=candidate_fact[0],
                            fact_value=candidate_fact[1],
                            subject_ref=subject_ref,
                            dimension_id=raw_dimension,
                        )
                    )
                pattern_fact = _brief_fact_value_for_capability(
                    facts,
                    capability_id=runtime_id,
                    field_id="source_conditioned_patterns",
                )
                if pattern_fact is not None:
                    signals.extend(
                        _source_pattern_signals(
                            fact_ref=pattern_fact[0],
                            fact_value=pattern_fact[1],
                            subject_ref=subject_ref,
                            dimension_id=raw_dimension,
                            art_id="bazi",
                        )
                    )
            else:
                pattern_fact = _brief_fact_value_for_capability(
                    facts,
                    capability_id=runtime_id,
                    field_id="source_conditioned_patterns",
                )
                if pattern_fact is not None:
                    signals.extend(
                        _source_pattern_signals(
                            fact_ref=pattern_fact[0],
                            fact_value=pattern_fact[1],
                            subject_ref=subject_ref,
                            dimension_id=raw_dimension,
                            art_id=cast(
                                Literal["bazi", "ziwei", "qizheng"],
                                art_id,
                            ),
                        )
                    )
        convergence: tuple[str, ...] = ()
        disagreements: tuple[str, ...] = ()
        if len(scopes) == len(selected_art_ids):
            convergence = ("所选术数的计算事实范围均已提供；尚未形成实质性互证结论。",)
        dimensions.append(
            DimensionSynthesis(
                dimension_id=raw_dimension,
                signals=tuple(signals),
                convergence=convergence,
                disagreements=disagreements,
                missing_art_ids=tuple(missing),
            )
        )
    if not dimensions:
        return None
    return CanwenViewV1(
        subject_ref=subject_ref,
        question=question,
        selected_art_ids=cast(
            tuple[Literal["bazi", "ziwei", "qizheng"], ...],
            selected_art_ids,
        ),
        dimensions=tuple(dimensions),
    )


def project_hecan_view_model(
    brief: Mapping[str, object] | None,
) -> HecanViewV1 | None:
    """Project the structure-only natal Hecan surface.

    Hecan intentionally shares the Runtime comparison facts with Canwen, but
    its contract has no question field.  Reusing the scope projector keeps
    convergence and disagreement empty unless Runtime itself has declared
    those facts; this slice does not invent substantive cross-art judgment.
    """

    canwen = project_canwen_view_model(brief)
    if canwen is None:
        return None
    return HecanViewV1(
        subject_ref=canwen.subject_ref,
        selected_art_ids=canwen.selected_art_ids,
        dimensions=canwen.dimensions,
    )


def project_wenshi_view_model(
    brief: Mapping[str, object] | None,
) -> WenshiViewV1 | None:
    """Project the native three-art event brief without inventing synthesis."""

    if brief is None:
        return None
    request_view = brief.get("request_view")
    if not isinstance(request_view, Mapping):
        return None
    raw_capabilities = request_view.get("capability_ids")
    if tuple(raw_capabilities or ()) != ("liuyao", "qimen", "liuren"):
        return None
    question = _question(brief)
    facts = brief.get("facts")
    subject_ref = _subject_ref(brief, facts)
    raw_dimensions = request_view.get("dimension_ids")
    if (
        question is None
        or subject_ref is None
        or not isinstance(raw_dimensions, (list, tuple))
    ):
        return None

    dimensions: list[DimensionSynthesis] = []
    for raw_dimension in raw_dimensions:
        if not isinstance(raw_dimension, str) or not raw_dimension.strip():
            return None
        signals: list[ArtSignal] = []
        missing: list[str] = []

        liuyao_fact = _brief_fact_value_for_capability(
            facts,
            capability_id="liuyao",
            field_id="relation_facts",
        )
        if liuyao_fact is None:
            missing.append("liuyao")
        else:
            signals.append(
                ArtSignal(
                    art_id="liuyao",
                    subject_refs=(subject_ref,),
                    signal_id=f"liuyao.{raw_dimension}.structure",
                    display_text=(
                        f"六爻已计算本卦关系事实；当前未把它解释为“{raw_dimension}”结论。"
                    ),
                    fact_refs=(liuyao_fact[0],),
                )
            )
            liuyao_patterns = _brief_fact_value_for_capability(
                facts,
                capability_id="liuyao",
                field_id="source_conditioned_patterns",
            )
            if liuyao_patterns is not None:
                signals.extend(
                    _source_pattern_signals(
                        fact_ref=liuyao_patterns[0],
                        fact_value=liuyao_patterns[1],
                        subject_ref=subject_ref,
                        dimension_id=raw_dimension,
                        art_id="liuyao",
                    )
                )
            liuyao_candidates = _brief_fact_value_for_capability(
                facts,
                capability_id="liuyao",
                field_id="useful_spirit_candidates",
            )
            if liuyao_candidates is not None:
                signals.extend(
                    _wenshi_liuyao_candidate_signals(
                        fact_ref=liuyao_candidates[0],
                        fact_value=liuyao_candidates[1],
                        subject_ref=subject_ref,
                        dimension_id=raw_dimension,
                    )
                )
            liuyao_selection = _brief_fact_value_for_capability(
                facts,
                capability_id="liuyao",
                field_id="useful_spirit_selection",
            )
            if liuyao_selection is not None:
                signals.extend(
                    _wenshi_liuyao_selection_signals(
                        fact_ref=liuyao_selection[0],
                        fact_value=liuyao_selection[1],
                        subject_ref=subject_ref,
                        dimension_id=raw_dimension,
                    )
                )

        qimen_fact = _brief_fact_value_for_capability(
            facts,
            capability_id="qimen",
            field_id="calculated_board_scope",
        )
        if qimen_fact is None:
            missing.append("qimen")
        else:
            signals.append(
                ArtSignal(
                    art_id="qimen",
                    subject_refs=(subject_ref,),
                    signal_id=f"qimen.{raw_dimension}.structure",
                    display_text=(
                        f"奇门已计算局面范围与盘面事实；当前未把它解释为“{raw_dimension}”结论。"
                    ),
                    fact_refs=(qimen_fact[0],),
                )
            )
            qimen_patterns = _brief_fact_value_for_capability(
                facts,
                capability_id="qimen",
                field_id="named_patterns",
            )
            if qimen_patterns is not None:
                signals.extend(
                    _wenshi_qimen_pattern_signals(
                        fact_ref=qimen_patterns[0],
                        fact_value=qimen_patterns[1],
                        subject_ref=subject_ref,
                        dimension_id=raw_dimension,
                    )
                )

        liuren_fact = _brief_fact_value_for_capability(
            facts,
            capability_id="liuren",
            field_id="dimension_facts",
        )
        liuren_value = liuren_fact[1] if liuren_fact is not None else None
        if (
            liuren_fact is None
            or not isinstance(liuren_value, Mapping)
            or not isinstance(liuren_value.get(raw_dimension), Mapping)
        ):
            missing.append("daliuren")
        else:
            signals.append(
                ArtSignal(
                    art_id="daliuren",
                    subject_refs=(subject_ref,),
                    signal_id=f"daliuren.{raw_dimension}.structure",
                    display_text=(
                        f"大六壬已计算“{raw_dimension}”维度事实；当前未把它解释为合参结论。"
                    ),
                    fact_refs=(liuren_fact[0],),
                )
            )
            signals.extend(
                _wenshi_liuren_timing_candidate_signals(
                    fact_ref=liuren_fact[0],
                    fact_value=(
                        liuren_value.get(raw_dimension)
                        if isinstance(liuren_value, Mapping)
                        else None
                    ),
                    subject_ref=subject_ref,
                    dimension_id=raw_dimension,
                )
            )
            signals.extend(
                _wenshi_liuren_rule_evidence_signals(
                    fact_ref=liuren_fact[0],
                    fact_value=(
                        liuren_value.get(raw_dimension)
                        if isinstance(liuren_value, Mapping)
                        else None
                    ),
                    subject_ref=subject_ref,
                    dimension_id=raw_dimension,
                )
            )

        dimensions.append(
            DimensionSynthesis(
                dimension_id=raw_dimension,
                signals=tuple(signals),
                convergence=(),
                disagreements=(),
                missing_art_ids=tuple(missing),
            )
        )

    if not dimensions:
        return None
    return WenshiViewV1(
        subject_ref=subject_ref,
        question=question,
        selected_art_ids=("liuyao", "qimen", "daliuren"),
        dimensions=tuple(dimensions),
    )


RUNTIME_PROVIDER_VIEW_MODEL_SCHEMAS: Final[dict[str, str]] = {
    "bazi": "bazi-chart/v1",
    "ziwei": "ziwei-chart/v1",
    "xingming": "qizheng-chart/v1",
    "liuyao": "liuyao-chart/v1",
    "meihua": "meihua-chart/v1",
    "luming-nayin": "luming-nayin-chart/v1",
    "taiyi": "taiyi-chart/v1",
    "selection": "selection-chart/v1",
    "fengshui": "fengshui-view/v1",
    "qimen": "qimen-chart/v1",
    "liuren": "daliuren-chart/v1",
    "physiognomy": "physiognomy-view/v1",
    "time-check": "time-check-view/v1",
    "fortune": "fortune-facts-view/v1",
}

_RUNTIME_PROVIDER_PROJECTORS: Final = {
    "bazi": project_bazi_view_model,
    "ziwei": project_ziwei_view_model,
    "xingming": project_qizheng_view_model,
    "liuyao": project_liuyao_view_model,
    "meihua": project_meihua_view_model,
    "luming-nayin": project_luming_nayin_view_model,
    "taiyi": project_taiyi_view_model,
    "selection": project_selection_view_model,
    "fengshui": project_fengshui_view_model,
    "qimen": project_qimen_view_model,
    "liuren": project_daliuren_view_model,
    "physiognomy": project_physiognomy_view_model,
    "time-check": project_time_check_view_model,
    "fortune": project_fortune_view_model,
}


def project_runtime_view_model(
    brief: Mapping[str, object] | None,
    *,
    product_id: str | None = None,
    relationship_type: str | None = None,
) -> ViewModel | None:
    """Dispatch a Runtime brief to its strict public ViewModel."""

    if brief is None:
        return None
    relationship_projectors = {
        "bazi-relationship": project_bazi_relationship_view_model,
        "ziwei-relationship": project_ziwei_relationship_view_model,
        "qizheng-relationship": project_qizheng_relationship_view_model,
    }
    relationship_projector = relationship_projectors.get(product_id or "")
    if relationship_projector is not None:
        return relationship_projector(brief, relationship_type=relationship_type)
    request_view = brief.get("request_view")
    capabilities = request_view.get("capability_ids") if isinstance(request_view, Mapping) else None
    if isinstance(capabilities, (list, tuple)) and tuple(capabilities) == (
        "liuyao",
        "qimen",
        "liuren",
    ):
        return project_wenshi_view_model(brief)
    if product_id == "five-elements-facts":
        return project_five_elements_facts_view_model(brief)
    if product_id == "rhythm":
        return project_rhythm_facts_view_model(brief)
    if product_id == "chart-similarity":
        return project_chart_similarity_view_model(brief)
    if product_id == "time-check":
        return project_time_check_view_model(brief)
    # Only the current natal Canwen brief has a Runtime comparison contract.
    # Do not route a future or unsupported multi-art brief into Canwen merely
    # because it happens to contain more than one capability.
    if (
        isinstance(capabilities, (list, tuple))
        and len(capabilities) in {2, 3}
        and capabilities[0] == "bazi"
        and set(capabilities) <= {"bazi", "ziwei", "xingming"}
    ):
        if product_id == "hecan":
            return project_hecan_view_model(brief)
        return project_canwen_view_model(brief)
    if not isinstance(capabilities, (list, tuple)) or len(capabilities) != 1:
        return None
    capability = capabilities[0]
    projector = _RUNTIME_PROVIDER_PROJECTORS.get(capability)
    return projector(brief) if projector is not None else None
