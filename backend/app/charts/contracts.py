from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicKeyLabel(ContractModel):
    """Chinese label for one internal ViewModel key that must not be shown raw."""

    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=80)


class TimeLayer(ContractModel):
    layer_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    available: bool
    unavailable_reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _availability_matches_reason(self) -> TimeLayer:
        if self.available == (self.unavailable_reason is not None):
            raise ValueError("unavailable time layers require a reason")
        return self


class Pillar(ContractModel):
    position: Literal["year", "month", "day", "hour"]
    stem: str = Field(min_length=1)
    branch: str = Field(min_length=1)


class ElementBalance(ContractModel):
    element: Literal["wood", "fire", "earth", "metal", "water"]
    value: float
    display_text: str = Field(min_length=1)


class BaziDayMaster(ContractModel):
    stem: str = Field(min_length=1)
    element: Literal["wood", "fire", "earth", "metal", "water"]
    polarity: Literal["阳", "阴"]


class BaziHiddenStems(ContractModel):
    position: Literal["year", "month", "day", "hour"]
    branch: str = Field(min_length=1)
    stems: tuple[str, ...] = Field(min_length=1)


class BaziTenGodEntry(ContractModel):
    position: Literal["year", "month", "day", "hour"]
    layer: Literal["heavenly_stem", "hidden_stem"]
    stem: str = Field(min_length=1)
    ten_god: str = Field(min_length=1)


class BaziTenGods(ContractModel):
    heavenly_stems: tuple[BaziTenGodEntry, ...] = Field(min_length=4, max_length=4)
    hidden_stems: tuple[BaziTenGodEntry, ...] = Field(min_length=1)


class BaziNayin(ContractModel):
    position: Literal["year", "month", "day", "hour"]
    name: str = Field(min_length=1)


class BaziGrowthStage(ContractModel):
    position: Literal["year", "month", "day", "hour"]
    stem: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    stage_index: int = Field(ge=1, le=12)
    direction: Literal["forward", "reverse"]
    source_dependency_id: str = Field(min_length=1)
    boundary: str = Field(min_length=1)


class BaziXunKong(ContractModel):
    day_pillar: str = Field(min_length=1)
    xun: str = Field(min_length=1)
    branches: tuple[str, str]
    source_dependency_id: str = Field(min_length=1)
    boundary: str = Field(min_length=1)


class BaziSanYuan(ContractModel):
    tai_yuan: str = Field(min_length=2)
    ming_gong: str = Field(min_length=2)
    shen_gong: str = Field(min_length=2)
    source: str = Field(min_length=1)
    source_dependency_id: str = Field(min_length=1)
    boundary: str = Field(min_length=1)


class BaziMonthCommand(ContractModel):
    branch: str = Field(min_length=1)
    label: str = Field(min_length=1)
    main_qi: str = Field(min_length=1)
    main_qi_element: Literal["wood", "fire", "earth", "metal", "water"]


class BaziSeasonalProfile(ContractModel):
    season: str = Field(min_length=1)
    month_qi: str = Field(min_length=1)
    temperature: str = Field(min_length=1)
    moisture: str = Field(min_length=1)


class BaziTiaohouMarkers(ContractModel):
    temperature: str = Field(min_length=1)
    moisture: str = Field(min_length=1)
    markers: tuple[str, ...] = Field(min_length=1)
    day_stem: str | None = Field(default=None, min_length=1)
    month_branch: str | None = Field(default=None, min_length=1)
    scope: str = Field(min_length=1)


class BaziElementCount(ContractModel):
    element: Literal["wood", "fire", "earth", "metal", "water"]
    value: int = Field(ge=0)


class BaziElementInventory(ContractModel):
    visible_stem_branch_counts: tuple[BaziElementCount, ...]
    hidden_stem_occurrence_counts: tuple[BaziElementCount, ...]
    scope: str = Field(min_length=1)


class BaziBranchRelation(ContractModel):
    relation_type: str = Field(min_length=1)
    positions: tuple[str, ...]
    branches: tuple[str, ...] = Field(min_length=2)


class BaziMonthOrderSourceRef(ContractModel):
    pack: Literal["bazi/sanming-tonghui"]
    rule_id: Literal["R-02-04"]
    source_anchor: str = Field(min_length=1)
    verification_status: Literal["verified"]
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class BaziMonthOrderAdjudication(ContractModel):
    """Verified seasonal state under the month command, not total strength."""

    status: Literal["adjudicated_month_order_state"]
    decision_scope: Literal["bazi_month_order_seasonal_state"]
    day_master_element: Literal["wood", "fire", "earth", "metal", "water"]
    month_command_element: Literal["wood", "fire", "earth", "metal", "water"]
    seasonal_state: Literal["旺", "相", "休", "囚", "死"]
    whole_chart_strength_verdict: None = None
    useful_god_verdict: None = None
    source_ref: BaziMonthOrderSourceRef
    unresolved_checks: tuple[str, ...] = Field(min_length=1)


class BaziStrengthEvidence(ContractModel):
    """Runtime evidence for strength, without a categorical strong/weak verdict."""

    status: Literal["evidence_only"]
    hard_verdict: None = None
    day_element: Literal["wood", "fire", "earth", "metal", "water"]
    month_command_element: Literal["wood", "fire", "earth", "metal", "water"]
    seasonal_state: Literal["旺", "相", "休", "囚", "死"]
    seasonal_state_source_rule_id: str = Field(min_length=1)
    same_element_occurrences: int = Field(ge=0)
    resource_element: Literal["wood", "fire", "earth", "metal", "water"]
    resource_occurrences: int = Field(ge=0)
    all_element_occurrences: tuple[BaziElementCount, ...] = Field(min_length=1)
    month_order_adjudication: BaziMonthOrderAdjudication
    boundary: str = Field(min_length=1)


class BaziStructureCandidate(ContractModel):
    """Runtime month-structure candidate, not a finished 格局 judgment."""

    status: Literal["candidate_only"]
    hard_verdict: None = None
    month_main_qi: str = Field(min_length=1)
    month_main_qi_ten_god: str = Field(min_length=1)
    main_qi_visible: bool
    visible_positions: tuple[str, ...]
    boundary: str = Field(min_length=1)


class BaziStemCombinationCandidate(ContractModel):
    with_position: str = Field(min_length=1)
    stems: tuple[str, ...] = Field(min_length=1)
    candidate_element: Literal["wood", "fire", "earth", "metal", "water"]
    status: str = Field(min_length=1)


class BaziFollowingTransformationCandidate(ContractModel):
    """Mechanical combination candidates that still require adjudication."""

    status: Literal["requires_classical_adjudication"]
    hard_verdict: None = None
    stem_combination_candidates: tuple[BaziStemCombinationCandidate, ...]
    branch_formation_candidates: tuple[BaziBranchRelation, ...]
    boundary: str = Field(min_length=1)


class BaziSalienceSignal(ContractModel):
    signal_id: str = Field(min_length=1)
    status: Literal["mechanical_candidate"]
    hard_verdict: None = None
    basis: dict[str, object]
    boundary: str = Field(min_length=1)


class BaziReasoningTool(ContractModel):
    """Source-aware Bazi evidence synthesis, never a final verdict."""

    schema_version: str = Field(min_length=1)
    tool_id: str = Field(min_length=1)
    tool_kind: str = Field(min_length=1)
    confidence_bucket: Literal["low", "medium", "high"]
    confidence_ceiling: Literal["low", "medium", "high"]
    visibility_class: Literal["auto_injected", "on_demand", "translated", "trigger_only"]
    fact_refs: tuple[dict[str, object], ...] = Field(min_length=1)
    source_refs: tuple[dict[str, str], ...] = Field(min_length=1)
    output: dict[str, object]
    caveats: tuple[str, ...] = Field(min_length=1)
    tool_digest: str = Field(min_length=1)


class BaziInterpretiveCandidates(ContractModel):
    """Typed bridge for Runtime evidence that is not yet a final interpretation."""

    strength: BaziStrengthEvidence
    structure: BaziStructureCandidate
    following_and_transformation: BaziFollowingTransformationCandidate
    salience_signals: tuple[BaziSalienceSignal, ...]
    reasoning_tools: dict[str, BaziReasoningTool] | None = None


class BaziBoundaryTerm(ContractModel):
    name: str = Field(min_length=1)
    index: int
    is_month_boundary_jie: bool
    datetime: str = Field(min_length=1)
    instant_utc: str = Field(min_length=1)


class BaziLuckCycle(ContractModel):
    sequence: int = Field(ge=1, le=10)
    pillar: str = Field(min_length=2)
    start_age_years: float | None = Field(default=None, ge=0)
    end_age_years: float | None = Field(default=None, ge=0)


class BaziLuckCycles(ContractModel):
    status: Literal["calculated", "sequence_only", "not_calculated_missing_gender"]
    direction: Literal["forward", "reverse"] | None = None
    direction_rule: str | None = Field(default=None, min_length=1)
    start_age_rule: str | None = Field(default=None, min_length=1)
    boundary_term: BaziBoundaryTerm | None = None
    interval_days: float | None = Field(default=None, ge=0)
    start_age_years: float | None = Field(default=None, ge=0)
    approximate_start_datetime: str | None = Field(default=None, min_length=1)
    cycles: tuple[BaziLuckCycle, ...]
    unavailable: tuple[str, ...]


class BaziShenshaRule(ContractModel):
    rule_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    anchor_position: str = Field(min_length=1)
    anchor_branch: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    matched: bool


class BaziShenshaItem(ContractModel):
    item_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    anchor_positions: tuple[str, ...]
    anchor_branches: tuple[str, ...]
    matched_positions: tuple[str, ...]
    status: str = Field(min_length=1)


class BaziShenshaAuxiliary(ContractModel):
    status: str = Field(min_length=1)
    temporal_scope: str = Field(min_length=1)
    precedence: str = Field(min_length=1)
    evaluated_rules: tuple[BaziShenshaRule, ...]
    calculated_items: tuple[BaziShenshaItem, ...]
    cannot_override: tuple[str, ...]
    boundary: str = Field(min_length=1)


class BaziYearTenGod(ContractModel):
    """Runtime-owned transit hidden-stem Ten God fact."""

    stem: str = Field(min_length=1)
    ten_god: str = Field(min_length=1)


class BaziYearRelation(ContractModel):
    """Mechanical natal/transit branch relation, not a judgment."""

    relation_type: str = Field(min_length=1)
    natal_position: str = Field(min_length=1)
    natal_branch: str = Field(min_length=1)
    transit_branch: str = Field(min_length=1)


class BaziYearStructuralChanges(ContractModel):
    """Runtime candidates for annual structural changes."""

    status: Literal["mechanical_candidates_only"]
    transit_pillar: str = Field(min_length=2)
    stem_ten_god: str = Field(min_length=1)
    branch_relations: tuple[BaziYearRelation, ...]
    hard_verdict: None = None


class BaziYearRuleTrace(ContractModel):
    rule_id: str = Field(min_length=1)
    source_dependency_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)


class BaziYearSegment(ContractModel):
    """One exact civil-year segment split at the Runtime's jie boundary."""

    start_inclusive: str = Field(min_length=1)
    end_exclusive: str = Field(min_length=1)
    ganzhi: str = Field(min_length=2)
    stem_ten_god: str = Field(min_length=1)
    branch_hidden_ten_gods: tuple[BaziYearTenGod, ...] = Field(min_length=1)
    branch_relations: tuple[BaziYearRelation, ...]
    seasonal_effect: dict[str, object]
    tiaohou_effect: dict[str, object]
    structural_changes: BaziYearStructuralChanges
    seasonal_tiaohou_delta: dict[str, object]
    shensha_auxiliary: BaziShenshaAuxiliary


class BaziYearLayer(ContractModel):
    """Facts-only annual Bazi layer returned by the Runtime."""

    year: int = Field(ge=1800, le=2199)
    ganzhi: str = Field(min_length=2)
    stem_ten_god: str = Field(min_length=1)
    branch_hidden_ten_gods: tuple[BaziYearTenGod, ...] = Field(min_length=1)
    branch_relations: tuple[BaziYearRelation, ...]
    structural_changes: BaziYearStructuralChanges
    shensha_auxiliary: BaziShenshaAuxiliary
    active_luck_cycle: dict[str, object]
    seasonal_effect: dict[str, object]
    tiaohou_effect: dict[str, object]
    seasonal_tiaohou_delta: dict[str, object]
    calendar_normalization: dict[str, object]
    rule_trace: tuple[BaziYearRuleTrace, ...] = Field(min_length=1)
    ganzhi_segments: tuple[BaziYearSegment, ...] = Field(min_length=2, max_length=2)


class BaziTemporalLayer(ContractModel):
    """Runtime-owned facts for one exact Bazi month or day layer."""

    granularity: Literal["month", "day"]
    period: str = Field(min_length=1)
    year: int = Field(ge=1800, le=2199)
    month: int | None = Field(default=None, ge=1, le=12)
    date: str | None = Field(default=None, min_length=1)
    ganzhi_segments: tuple[dict[str, object], ...] = Field(min_length=1)
    active_transits: dict[str, object] | None = None
    structural_changes: dict[str, object]
    seasonal_tiaohou_delta: dict[str, object]
    shensha_auxiliary: dict[str, object]
    active_luck_cycle: dict[str, object]
    calendar_normalization: dict[str, object]
    representative_instant: str | None = Field(default=None, min_length=1)
    rule_trace: tuple[dict[str, object], ...] = Field(min_length=1)


class BaziSourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)
    evidence_ref: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )


class BaziSolarTerm(ContractModel):
    """One Runtime solar-term boundary exposed to the Bazi chart."""

    name: str = Field(min_length=1)
    index: int
    is_month_boundary_jie: bool
    datetime: str = Field(min_length=1)
    instant_utc: str = Field(min_length=1)


class BaziSolarTerms(ContractModel):
    """The adjacent solar terms and the Runtime month-switch policy."""

    previous: BaziSolarTerm | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    next: BaziSolarTerm | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    month_switch_policy: str = Field(min_length=1)


class BaziCalendarDayBoundary(ContractModel):
    """Explicit day-boundary effects of the Runtime calendar correction."""

    correction_crossed_date: bool
    zi_policy_advanced_day_pillar: bool


class BaziCalendarNormalization(ContractModel):
    """Typed Bazi calendar facts with no inferred effective instant."""

    status: str = Field(min_length=1)
    algorithm_version: str = Field(min_length=1)
    time_basis: FortuneCalendarTimeBasis
    true_solar_time: FortuneTrueSolarTime
    calendar_convention: FortuneCalendarConvention
    effective_datetime: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    day_boundary: BaziCalendarDayBoundary | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    changed_pillars: tuple[Literal["year", "month", "day", "hour"], ...] | None = Field(
        default=None,
        min_length=0,
        max_length=4,
        exclude_if=lambda value: value is None,
    )
    solar_terms: BaziSolarTerms | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def _changed_pillars_are_stable(
        self,
    ) -> BaziCalendarNormalization:
        if self.changed_pillars is None:
            return self
        if len(set(self.changed_pillars)) != len(self.changed_pillars):
            raise ValueError("changed Bazi pillars must be unique")
        order = {position: index for index, position in enumerate(("year", "month", "day", "hour"))}
        if tuple(sorted(self.changed_pillars, key=order.__getitem__)) != self.changed_pillars:
            raise ValueError("changed Bazi pillars must use year-month-day-hour order")
        return self


class BaziCoreFacts(ContractModel):
    """Calculated Bazi facts exposed without findings or input material."""

    day_master: BaziDayMaster | None = None
    hidden_stems: tuple[BaziHiddenStems, ...] | None = None
    ten_gods: BaziTenGods | None = None
    nayin: tuple[BaziNayin, ...] | None = None
    twelve_growth_stages: tuple[BaziGrowthStage, ...] | None = None
    xunkong: BaziXunKong | None = None
    san_yuan: BaziSanYuan | None = None
    month_command: BaziMonthCommand | None = None
    seasonal_profile: BaziSeasonalProfile | None = None
    tiaohou_markers: BaziTiaohouMarkers | None = None
    element_inventory: BaziElementInventory | None = None
    interpretive_candidates: BaziInterpretiveCandidates | None = None
    source_conditioned_patterns: tuple[BaziSourcePattern, ...] = ()
    branch_relations: tuple[BaziBranchRelation, ...] | None = None
    shensha_auxiliary: BaziShenshaAuxiliary | None = None
    luck_cycles: BaziLuckCycles | None = None
    calendar_normalization: BaziCalendarNormalization | None = None
    year_layers: tuple[BaziYearLayer, ...] | None = None
    month_layers: tuple[BaziTemporalLayer, ...] | None = None
    day_layers: tuple[BaziTemporalLayer, ...] | None = None


class FiveElementsSourceIdentity(ContractModel):
    day_stem: str | None = Field(default=None, min_length=1)
    month_branch: str | None = Field(default=None, min_length=1)
    source_dependency_id: str | None = Field(default=None, min_length=1)
    source_section_id: str | None = Field(default=None, min_length=1)
    source_rule_id: str | None = Field(default=None, min_length=1)


class FiveElementsFactsViewV1(ContractModel):
    """Facts-only projection for element inventory and seasonal anchors."""

    schema_version: Literal["five-elements-facts-view/v1"] = "five-elements-facts-view/v1"
    subject_ref: str = Field(min_length=1)
    day_master: BaziDayMaster | None = None
    month_command: BaziMonthCommand | None = None
    seasonal_profile: BaziSeasonalProfile | None = None
    tiaohou_markers: BaziTiaohouMarkers | None = None
    element_inventory: BaziElementInventory | None = None
    interpretive_candidates: BaziInterpretiveCandidates | None = None
    source_identity: FiveElementsSourceIdentity | None = None
    active_source_rule_ids: tuple[str, ...]
    source_dependency_ids: tuple[str, ...]
    source_status: Literal["exact_rule_bound", "identity_only", "unavailable"]
    source_gaps: tuple[str, ...]
    limitations: tuple[str, ...]


class LifeKlineSeriesIdentity(ContractModel):
    """Opaque Runtime-bound identity for the life K-line series projection."""

    subject_ref: str = Field(min_length=1, max_length=256)
    profile_version_id: str = Field(min_length=1, max_length=256)
    runtime_release: str = Field(min_length=1, max_length=256)
    runtime_source_commit: str = Field(min_length=40, max_length=40, pattern=r"^[0-9a-f]{40}$")
    runtime_manifest_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    source_fact_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    cache_identity: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class LifeKlineCandidateTimeAxis(ContractModel):
    kind: Literal["major_luck", "gregorian_year", "gregorian_month", "civil_day"]
    unit: str = Field(min_length=1)
    source_schema_version: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    role: Literal["temporal_key_only"] = "temporal_key_only"
    series_ready: Literal[False] = False


# Frozen v1 candidate time axes — must stay exact with Runtime life-kline authority.
LIFE_KLINE_CANDIDATE_TIME_AXES: tuple[LifeKlineCandidateTimeAxis, ...] = (
    LifeKlineCandidateTimeAxis(
        kind="major_luck",
        unit="age_years",
        source_schema_version="mingli-bazi-fact-v1",
        source_path="output.luck_cycles.cycles[]",
    ),
    LifeKlineCandidateTimeAxis(
        kind="gregorian_year",
        unit="calendar_year",
        source_schema_version="mingli-bazi-fact-v1",
        source_path="fact_extension.facts.year_layers",
    ),
    LifeKlineCandidateTimeAxis(
        kind="gregorian_month",
        unit="calendar_month",
        source_schema_version="mingli-bazi-fact-v1",
        source_path="fact_extension.facts.month_layers",
    ),
    LifeKlineCandidateTimeAxis(
        kind="civil_day",
        unit="civil_day",
        source_schema_version="mingli-bazi-fact-v1",
        source_path="fact_extension.facts.day_layers",
    ),
)


class LifeKlineUnavailableValueAxis(ContractModel):
    available: Literal[False] = False
    measure_id: None = None
    unit: None = None
    range: None = None
    comparability_key: None = None
    unavailable_reason: Literal["missing_versioned_comparable_measure"] = (
        "missing_versioned_comparable_measure"
    )


class LifeKlineUnavailableCandles(ContractModel):
    available: Literal[False] = False
    field_set: None = None
    sampling_rule_id: None = None
    sampling_rule_version: None = None
    unavailable_reason: Literal["missing_versioned_candle_sampling_semantics"] = (
        "missing_versioned_candle_sampling_semantics"
    )


class LifeKlineUnavailableChange(ContractModel):
    available: Literal[False] = False
    direction_rule_id: None = None
    delta_unit: None = None
    unavailable_reason: Literal["missing_authoritative_close_values"] = (
        "missing_authoritative_close_values"
    )


# Frozen v1 algorithm-gap lists — must stay exact with Runtime life-kline authority.
LIFE_KLINE_ALGORITHM_GAP_MISSING_INPUTS: tuple[str, ...] = (
    "versioned_comparable_measure_definition",
    "calibration_and_validation_corpus",
)
LIFE_KLINE_ALGORITHM_GAP_MISSING_SEMANTICS: tuple[str, ...] = (
    "measure_unit_and_range",
    "measure_polarity",
    "cross_period_comparability",
    "open_and_close_sampling_points",
    "high_and_low_intra_period_resolution",
    "flat_direction_threshold",
    "missing_observation_policy",
)
LIFE_KLINE_ALGORITHM_GAP_REQUIRED_VERSIONED_FIELDS: tuple[str, ...] = (
    "measure.id",
    "measure.version",
    "measure.unit",
    "measure.range",
    "measure.polarity",
    "sampling.rule_id",
    "sampling.rule_version",
    "comparability.key",
    "series[].fact_refs",
    "meta.profile_version_id",
    "meta.reading_document_version",
    "meta.runtime_release",
    "meta.runtime_manifest_digest",
    "meta.source_fact_digest",
)
LIFE_KLINE_ALGORITHM_GAP_MINIMUM_IMPLEMENTATION_SLICE: tuple[str, ...] = (
    "freeze_one_comparable_measure_and_its_evidence_authority",
    "implement_the_measure_as_a_deterministic_versioned_pure_function",
    "freeze_candle_sampling_semantics_or_remove_ohlc_from_the_product_contract",
    "derive_direction_and_delta_only_from_authoritative_close_values",
    "validate_boundaries_missingness_idempotency_and_calibration_before_ready",
)


class LifeKlineAlgorithmGap(ContractModel):
    gap_id: Literal["life-kline.comparable-measure-and-candle-sampling.v1"] = (
        "life-kline.comparable-measure-and-candle-sampling.v1"
    )
    user_input_can_resolve: Literal[False] = False
    missing_inputs: tuple[str, ...]
    missing_semantics: tuple[str, ...]
    required_versioned_fields: tuple[str, ...]
    minimum_implementation_slice: tuple[str, ...]


class LifeKlineSeriesV1(ContractModel):
    """Fail-closed product projection of Runtime life-kline authority facts."""

    schema_version: Literal["life-kline-series/v1"] = "life-kline-series/v1"
    subject_ref: str = Field(min_length=1)
    status: Literal["unavailable_algorithm_gap"] = "unavailable_algorithm_gap"
    source_runtime_schema_version: Literal["mingli-life-kline-facts-v1"] = (
        "mingli-life-kline-facts-v1"
    )
    source_contract_version: Literal["life-kline-authority-v1"] = (
        "life-kline-authority-v1"
    )
    identity: LifeKlineSeriesIdentity
    candidate_time_axes: tuple[LifeKlineCandidateTimeAxis, ...]
    value_axis: LifeKlineUnavailableValueAxis
    candles: LifeKlineUnavailableCandles
    change: LifeKlineUnavailableChange
    series: tuple[()] = ()
    algorithm_gap: LifeKlineAlgorithmGap
    limitations: tuple[str, ...]


class FortuneTargetPeriod(ContractModel):
    kind: str = Field(min_length=1)
    start: str = Field(min_length=1)
    end: str = Field(min_length=1)


class FortunePeriodMarker(ContractModel):
    date: str = Field(min_length=1)
    day_pillar: str = Field(min_length=1)
    day_role: str = Field(min_length=1)
    active_luck_cycle: str = Field(min_length=1)
    primary_mechanism_ids: tuple[str, ...]
    decisive_mechanism_ids: tuple[str, ...]
    relations: tuple[dict[str, object], ...]
    specific_event_policy: str = Field(min_length=1)
    unresolved_boundaries: tuple[str, ...]


class FortuneCalendarAlgorithm(ContractModel):
    id: str | None = Field(default=None, min_length=1)
    version: str | None = Field(default=None, min_length=1)
    source: str | None = Field(default=None, min_length=1)
    uncertainty_seconds: float | None = None


class FortuneCalendarBoundary(ContractModel):
    distance_seconds: float | None = None
    correction_changes_hour_branch: bool | None = None
    within_uncertainty: bool | None = None


class FortuneCalendarTimeBasis(ContractModel):
    policy: str = Field(min_length=1)
    standard_meridian_degrees: float | None = None
    longitude_correction_seconds: float | None = None
    equation_of_time_seconds: float | None = None
    total_correction_seconds: float | None = None
    algorithm: FortuneCalendarAlgorithm
    boundary: FortuneCalendarBoundary


class FortuneTrueSolarTime(ContractModel):
    status: str = Field(min_length=1)
    policy: str | None = Field(default=None, min_length=1)
    longitude_correction_seconds: float | None = None
    equation_of_time_seconds: float | None = None
    total_correction_seconds: float | None = None


class FortuneCalendarConvention(ContractModel):
    id: str | None = Field(default=None, min_length=1)
    version: str | None = Field(default=None, min_length=1)
    year_boundary: str | None = Field(default=None, min_length=1)
    month_boundary: str | None = Field(default=None, min_length=1)
    day_rollover: str | None = Field(default=None, min_length=1)
    hour_basis: str | None = Field(default=None, min_length=1)
    zi_hour_policy: str | None = Field(default=None, min_length=1)


class FortuneSolarTerm(ContractModel):
    """One adjacent solar-term boundary exposed by the Fortune provider."""

    name: str = Field(min_length=1)
    index: int
    is_month_boundary_jie: bool
    datetime: str = Field(min_length=1)
    instant_utc: str = Field(min_length=1)


class FortuneSolarTerms(ContractModel):
    """Adjacent solar terms and the exact month-switch policy."""

    previous: FortuneSolarTerm | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    next: FortuneSolarTerm | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    month_switch_policy: str = Field(min_length=1)


class FortuneCalendarDayBoundary(ContractModel):
    """Day-boundary effects calculated by the Runtime calendar correction."""

    correction_crossed_date: bool
    zi_policy_advanced_day_pillar: bool


class FortuneCalendarNormalization(ContractModel):
    status: str = Field(min_length=1)
    algorithm_version: str = Field(min_length=1)
    time_basis: FortuneCalendarTimeBasis
    true_solar_time: FortuneTrueSolarTime
    calendar_convention: FortuneCalendarConvention
    effective_datetime: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    day_boundary: FortuneCalendarDayBoundary | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    changed_pillars: tuple[Literal["year", "month", "day", "hour"], ...] | None = Field(
        default=None,
        min_length=0,
        max_length=4,
        exclude_if=lambda value: value is None,
    )
    solar_terms: FortuneSolarTerms | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def _changed_pillars_are_stable(
        self,
    ) -> FortuneCalendarNormalization:
        if self.changed_pillars is None:
            return self
        if len(set(self.changed_pillars)) != len(self.changed_pillars):
            raise ValueError("changed Fortune pillars must be unique")
        order = {
            position: index
            for index, position in enumerate(("year", "month", "day", "hour"))
        }
        if (
            tuple(sorted(self.changed_pillars, key=order.__getitem__))
            != self.changed_pillars
        ):
            raise ValueError(
                "changed Fortune pillars must use year-month-day-hour order"
            )
        return self


class FortuneFactsViewV1(ContractModel):
    """Facts-only projection for Runtime daily and period calculations."""

    schema_version: Literal["fortune-facts-view/v1"] = "fortune-facts-view/v1"
    subject_ref: str = Field(min_length=1)
    natal_pillars: dict[str, str]
    day_master: BaziDayMaster
    month_command: BaziMonthCommand
    active_luck_cycle: str = Field(min_length=1)
    target_day: str = Field(min_length=1)
    target_period: FortuneTargetPeriod
    available_periods: tuple[str, ...]
    period_markers: tuple[FortunePeriodMarker, ...]
    calendar_normalization: FortuneCalendarNormalization


class BaziChartV1(ContractModel):
    schema_version: Literal["bazi-chart/v1"] = "bazi-chart/v1"
    subject_ref: str = Field(min_length=1)
    pillars: tuple[Pillar, ...] = Field(min_length=4, max_length=4)
    element_balance: tuple[ElementBalance, ...]
    time_layers: tuple[TimeLayer, ...]
    core_facts: BaziCoreFacts | None = None


class ChartSimilarityPillarComparison(ContractModel):
    position: Literal["year", "month", "day", "hour"]
    left: Pillar
    right: Pillar
    exact_match: bool


class ChartSimilarityViewV1(ContractModel):
    """A bounded exact comparison of two Runtime-calculated Bazi charts.

    This is deliberately not a score, compatibility verdict, or relationship
    reading.  It only compares the four calculated pillars and keeps the
    source fact references alongside the result.
    """

    schema_version: Literal["chart-similarity-view/v1"] = "chart-similarity-view/v1"
    left_subject_ref: str = Field(min_length=1)
    right_subject_ref: str = Field(min_length=1)
    basis: Literal["bazi.four_pillars.exact"]
    left_fact_ref: str = Field(min_length=1)
    right_fact_ref: str = Field(min_length=1)
    comparisons: tuple[ChartSimilarityPillarComparison, ...] = Field(
        min_length=4,
        max_length=4,
    )
    exact_match: bool
    matched_positions: tuple[Literal["year", "month", "day", "hour"], ...]
    differing_positions: tuple[Literal["year", "month", "day", "hour"], ...]
    limitations: tuple[str, ...] = Field(min_length=1)


class TimeCheckCandidateV1(ContractModel):
    candidate_id: str = Field(min_length=1)
    hour_branch: str = Field(min_length=1)
    local_civil_datetime: str = Field(min_length=1)
    within_known_time_range: bool
    bazi_chart_digest: str | None = Field(default=None, min_length=1)
    four_pillars: object
    day_master: object | None = None
    calendar_normalization: dict[str, object]


class TimeCheckBranchRelationV1(ContractModel):
    """One Runtime-computed natal/event branch relation."""

    natal_position: Literal["year", "month", "day", "hour"]
    natal_branch: str = Field(min_length=1)
    event_branch: str = Field(min_length=1)
    relation_type: str = Field(min_length=1)


class TimeCheckEventEvidenceV1(ContractModel):
    """Typed evidence for one structured life event and one candidate."""

    event_id: str = Field(min_length=1)
    matched: bool
    evidence_score: int
    relations: tuple[TimeCheckBranchRelationV1, ...]
    event_year_ten_god: str | None = Field(default=None, min_length=1)
    reasons: tuple[str, ...] = Field(min_length=1)


class TimeCheckCandidateEvidenceV1(ContractModel):
    """Bounded Runtime evidence attached to one time-check candidate."""

    candidate_id: str = Field(min_length=1)
    hour_branch: str = Field(min_length=1)
    eligible: bool
    evidence_score: int
    matched_event_ids: tuple[str, ...]
    elimination_reasons: tuple[str, ...]
    event_evidence: tuple[TimeCheckEventEvidenceV1, ...]
    rank: int = Field(ge=1, le=12)


class TimeCheckRectificationConclusionV1(ContractModel):
    """Classical rectification conclusion: remaining hour or why it is still open."""

    status: Literal[
        "hour_determined",
        "no_valid_candidate",
        "not_attempted",
        "remaining_ambiguous",
    ]
    selected_candidate_id: str | None = Field(default=None, min_length=1)
    remaining_candidate_ids: tuple[str, ...]
    basis: str = Field(min_length=1)
    rule_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _selected_matches_status(self) -> TimeCheckRectificationConclusionV1:
        if self.status == "hour_determined":
            if self.selected_candidate_id is None:
                raise ValueError("determined hour requires selected_candidate_id")
        elif self.selected_candidate_id is not None:
            raise ValueError("non-determined status cannot select a candidate")
        return self


class TimeCheckEventMatchV1(ContractModel):
    """Runtime evidence showing which candidates matched one dated event."""

    event_id: str = Field(min_length=1)
    domain: Literal[
        "career",
        "education",
        "finance",
        "relationship",
        "family",
        "location",
        "health",
    ]
    occurred_at: str = Field(min_length=1)
    year_pillar: str = Field(min_length=2)
    matched_candidate_ids: tuple[str, ...]


class TimeCheckViewV1(ContractModel):
    """Facts-only projection for candidates and optional event evidence."""

    schema_version: Literal["time-check-view/v1"] = "time-check-view/v1"
    subject_ref: str = Field(min_length=1)
    candidate_count: int = Field(ge=12, le=12)
    candidates: tuple[TimeCheckCandidateV1, ...] = Field(min_length=12, max_length=12)
    known_time_range: dict[str, object]
    time_basis_policy: str = Field(min_length=1)
    known_event_count: int = Field(ge=0)
    event_input_status: Literal[
        "not_supplied",
        "invalid_structured_events",
        "structured_valid",
    ]
    candidate_rankings: tuple[TimeCheckCandidateEvidenceV1, ...]
    event_matches: tuple[TimeCheckEventMatchV1, ...]
    ranking_status: Literal["not_ranked", "candidate_evidence_ranked"]
    event_matching_status: Literal["not_calculated", "structured_evidence"]
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
    limitations: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _rectification_pair_matches(self) -> TimeCheckViewV1:
        conclusion = self.rectification_conclusion
        if conclusion is None:
            return self
        if self.rectification_status != conclusion.status:
            raise ValueError("rectification_status must match conclusion.status")
        return self


class ZiweiPalace(ContractModel):
    palace_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    heavenly_stem: str = Field(min_length=1)
    earthly_branch: str = Field(min_length=1)
    major_stars: tuple[str, ...]
    minor_stars: tuple[ZiweiStar, ...] = ()
    adjective_stars: tuple[ZiweiStar, ...] = ()
    changsheng12: str | None = Field(default=None, min_length=1)
    boshi12: str | None = Field(default=None, min_length=1)
    jiangqian12: str | None = Field(default=None, min_length=1)
    suiqian12: str | None = Field(default=None, min_length=1)
    decadal: ZiweiDecadal | None = None
    ages: tuple[int, ...] = ()


class ZiweiStar(ContractModel):
    name: str = Field(min_length=1)
    star_type: str | None = Field(default=None, min_length=1)
    scope: str | None = Field(default=None, min_length=1)
    brightness: str | None = Field(default=None, min_length=1)


class ZiweiDecadal(ContractModel):
    age_start: int = Field(ge=0)
    age_end: int = Field(ge=0)
    heavenly_stem: str = Field(min_length=1)
    earthly_branch: str = Field(min_length=1)


class ZiweiLimit(ContractModel):
    palace: str = Field(min_length=1)
    palace_index: int = Field(ge=0)
    palace_branch: str = Field(min_length=1)
    age_start: int = Field(ge=0)
    age_end: int = Field(ge=0)
    sequence: int = Field(ge=1, le=12)
    heavenly_stem: str = Field(min_length=1)
    earthly_branch: str = Field(min_length=1)
    direction: str | None = Field(default=None, min_length=1)


class ZiweiMajorLimitDirection(ContractModel):
    direction: str = Field(min_length=1)
    gender: str = Field(min_length=1)
    year_polarity: str = Field(min_length=1)
    year_stem: str = Field(min_length=1)


class ZiweiMingShen(ContractModel):
    body_star: str = Field(min_length=1)
    ming_branch: str = Field(min_length=1)
    shen_branch: str = Field(min_length=1)
    soul_star: str = Field(min_length=1)


class ZiweiTransformation(ContractModel):
    star: str = Field(min_length=1)
    transformation: str = Field(min_length=1)
    palace: str = Field(min_length=1)
    palace_branch: str = Field(min_length=1)
    scope: str = Field(min_length=1)


class ZiweiMajorLimitSegment(ContractModel):
    """One exact Runtime-owned major-limit interval and its placement facts."""

    start_inclusive: str = Field(min_length=1)
    end_exclusive: str = Field(min_length=1)
    major_limit: dict[str, object] = Field(min_length=1)

    @field_validator("start_inclusive", "end_exclusive", mode="before")
    @classmethod
    def _requires_canonical_iso_date(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("major-limit segment boundaries must be ISO dates")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(
                "major-limit segment boundaries must be ISO dates"
            ) from error
        if parsed.isoformat() != value:
            raise ValueError("major-limit segment boundaries must be canonical ISO dates")
        return value

    @model_validator(mode="after")
    def _requires_forward_interval(self) -> ZiweiMajorLimitSegment:
        if date.fromisoformat(self.start_inclusive) >= date.fromisoformat(
            self.end_exclusive
        ):
            raise ValueError("major-limit segment start must precede end")
        return self


class ZiweiCalendarCoverage(ContractModel):
    """Exact Runtime-owned date request and its half-open coverage interval."""

    start_inclusive: str = Field(min_length=1)
    end_exclusive: str = Field(min_length=1)
    requested_target_date: str | None

    @field_validator(
        "start_inclusive",
        "end_exclusive",
        mode="before",
    )
    @classmethod
    def _requires_canonical_iso_date(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("Ziwei calendar coverage dates must be ISO dates")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("Ziwei calendar coverage dates must be ISO dates") from error
        if parsed.isoformat() != value:
            raise ValueError("Ziwei calendar coverage dates must be canonical ISO dates")
        return value

    @field_validator("requested_target_date", mode="before")
    @classmethod
    def _requires_optional_canonical_iso_date(cls, value: object) -> object:
        if value is None:
            return value
        if not isinstance(value, str):
            raise ValueError("Ziwei requested target date must be an ISO date or null")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(
                "Ziwei requested target date must be an ISO date or null"
            ) from error
        if parsed.isoformat() != value:
            raise ValueError("Ziwei requested target date must be canonical")
        return value

    @model_validator(mode="after")
    def _requires_target_inside_forward_interval(self) -> ZiweiCalendarCoverage:
        start = date.fromisoformat(self.start_inclusive)
        end = date.fromisoformat(self.end_exclusive)
        if start >= end:
            raise ValueError("Ziwei calendar coverage start must precede end")
        target = (
            date.fromisoformat(self.requested_target_date)
            if self.requested_target_date is not None
            else None
        )
        if target is not None and not start <= target < end:
            raise ValueError("Ziwei requested target date must fall inside coverage")
        return self


class ZiweiAnnualLayer(ContractModel):
    """Runtime-owned Ziwei annual placement facts."""

    year: int = Field(ge=1800, le=2199)
    coverage_start: str = Field(min_length=1)
    coverage_end_exclusive: str = Field(min_length=1)
    liu_nian: dict[str, object]
    segments: tuple[dict[str, object], ...] = Field(min_length=1)
    representative_scope: str = Field(min_length=1)


class ZiweiMonthlyLayer(ContractModel):
    """Runtime-owned Ziwei monthly placement facts."""

    year: int = Field(ge=1800, le=2199)
    month: int = Field(ge=1, le=12)
    liu_yue: dict[str, object]
    segments: tuple[dict[str, object], ...] = Field(min_length=1)
    representative_scope: str = Field(min_length=1)


class ZiweiStarFact(ZiweiStar):
    palace: str = Field(min_length=1)
    palace_branch: str = Field(min_length=1)
    palace_index: int = Field(ge=0)


class ZiweiSourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)


class ZiweiCoreFacts(ContractModel):
    chart_convention: dict[str, object] | None = None
    chinese_date: str | None = Field(default=None, min_length=1)
    active_major_limit: dict[str, object] | None = None
    active_major_limit_segments: tuple[ZiweiMajorLimitSegment, ...] | None = Field(
        default=None,
        min_length=1,
    )
    calendar_coverage: ZiweiCalendarCoverage | None = None
    five_elements_class: str | None = Field(default=None, min_length=1)
    interpretive_candidates: dict[str, object] | None = None
    source_conditioned_patterns: tuple[ZiweiSourcePattern, ...] = ()
    ming_shen: ZiweiMingShen | None = None
    major_limit_direction: ZiweiMajorLimitDirection | None = None
    major_limit_starting_age: int | None = Field(default=None, ge=0)
    major_limit_sequence: tuple[ZiweiLimit, ...] | None = None
    major_limits: tuple[ZiweiLimit, ...] | None = None
    transformations: tuple[ZiweiTransformation, ...] | None = None
    star_facts: tuple[ZiweiStarFact, ...] | None = None
    annual_layers: tuple[ZiweiAnnualLayer, ...] | None = None
    monthly_layers: tuple[ZiweiMonthlyLayer, ...] | None = None

    @model_validator(mode="before")
    @classmethod
    def _strict_optional_facts_must_be_absent_or_non_null(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        if (
            "active_major_limit_segments" in value
            and value["active_major_limit_segments"] is None
        ):
            raise ValueError("major-limit segments must be omitted or non-null")
        if "calendar_coverage" in value and value["calendar_coverage"] is None:
            raise ValueError("calendar coverage must be omitted or non-null")
        return value

    @model_serializer(mode="wrap")
    def _omit_absent_strict_optional_facts(
        self,
        handler: SerializerFunctionWrapHandler,
    ) -> dict[str, object]:
        """Keep old payloads distinguishable from invalid strict optional facts."""

        serialized: dict[str, object] = handler(self)
        if "active_major_limit_segments" not in self.model_fields_set:
            serialized.pop("active_major_limit_segments", None)
        if "calendar_coverage" not in self.model_fields_set:
            serialized.pop("calendar_coverage", None)
        return serialized


class ZiweiChartV1(ContractModel):
    schema_version: Literal["ziwei-chart/v1"] = "ziwei-chart/v1"
    subject_ref: str = Field(min_length=1)
    life_palace_id: str = Field(min_length=1)
    body_palace_id: str = Field(min_length=1)
    palaces: tuple[ZiweiPalace, ...] = Field(min_length=12, max_length=12)
    time_layers: tuple[TimeLayer, ...]
    core_facts: ZiweiCoreFacts | None = None


class PlanetPosition(ContractModel):
    planet_id: str = Field(min_length=1)
    sign_id: str = Field(min_length=1)
    house_id: str = Field(min_length=1)
    longitude: float = Field(ge=0, lt=360)


class HousePosition(ContractModel):
    house_id: str = Field(min_length=1)
    sign_id: str = Field(min_length=1)
    cusp_longitude: float = Field(ge=0, lt=360)


class Aspect(ContractModel):
    aspect_id: str = Field(min_length=1)
    from_planet_id: str = Field(min_length=1)
    to_planet_id: str = Field(min_length=1)
    orb: float = Field(ge=0)


class QizhengBodyFact(ContractModel):
    body_id: str = Field(min_length=1)
    classical_name: str = Field(min_length=1)
    longitude: float = Field(ge=0, lt=360)
    latitude_degrees: float | None = None
    degree_in_zodiac_sign: float | None = Field(default=None, ge=0, lt=30)
    house_id: str | None = Field(default=None, min_length=1)
    house_degree: float | None = Field(default=None, ge=0)
    motion_state: str | None = Field(default=None, min_length=1)
    fact_status: str = Field(min_length=1)
    point_kind: str | None = Field(default=None, min_length=1)
    observed_body: bool | None = None
    source_dependency_id: str | None = Field(default=None, min_length=1)
    trace: dict[str, object] | None = None


class QizhengEphemerisEngine(ContractModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    license: str = Field(min_length=1)


class QizhengCoordinateConvention(ContractModel):
    frame: str = Field(min_length=1)
    zodiac: str = Field(min_length=1)
    aberration: bool
    precession: str = Field(min_length=1)


class QizhengEphemerisSummary(ContractModel):
    schema_version: str = Field(min_length=1)
    engine: QizhengEphemerisEngine
    coordinate_convention: QizhengCoordinateConvention


class QizhengMingShen(ContractModel):
    ming_degree: float = Field(ge=0, lt=360)
    shen_degree: float = Field(ge=0, lt=360)
    separation_degrees: float = Field(ge=0)
    local_apparent_sidereal_degrees: float | None = Field(default=None, ge=0, lt=360)
    profile: str = Field(min_length=1)
    fact_status: str = Field(min_length=1)


class QizhengLimit(ContractModel):
    sequence: int = Field(ge=1, le=12)
    house: str = Field(min_length=1)
    age_start_years: float = Field(ge=0)
    age_end_years: float = Field(ge=0)
    start_degree: float = Field(ge=0, lt=360)
    end_degree: float = Field(ge=0, lt=360)
    status: str = Field(min_length=1)


class QizhengTransformation(ContractModel):
    sequence: int = Field(ge=1)
    transformation: str = Field(min_length=1)
    label: str = Field(min_length=1)
    classical_body: str = Field(min_length=1)
    body: str = Field(min_length=1)
    year_stem: str = Field(min_length=1)
    status: str = Field(min_length=1)


class QizhengSourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)


class QizhengAnnualTransformation(ContractModel):
    """Runtime-owned annual transformation assignments, not verdicts."""

    year: int = Field(ge=1800, le=2199)
    year_ganzhi: str = Field(min_length=2)
    transformations: tuple[QizhengTransformation, ...] = Field(min_length=1)
    calendar_digest: str = Field(min_length=1)
    fact_status: str = Field(min_length=1)


class QizhengRequestedLimitLayer(ContractModel):
    """Runtime-owned requested time-limit location fact."""

    date: str = Field(min_length=1)
    age_years: float = Field(ge=0)
    house: str = Field(min_length=1)
    segment_index: int = Field(ge=0)
    segment: dict[str, object]
    status: str = Field(min_length=1)


class QizhengCoreFacts(ContractModel):
    ephemeris: QizhengEphemerisSummary | None = None
    conventions: dict[str, object] | None = None
    classical_bodies: tuple[QizhengBodyFact, ...] | None = None
    ming_shen: QizhengMingShen | None = None
    major_limits: tuple[QizhengLimit, ...] | None = None
    transformations: tuple[QizhengTransformation, ...] | None = None
    source_conditioned_patterns: tuple[QizhengSourcePattern, ...] = ()
    annual_transformations: tuple[QizhengAnnualTransformation, ...] | None = None
    requested_limit_layers: tuple[QizhengRequestedLimitLayer, ...] | None = None


class QizhengChartV1(ContractModel):
    schema_version: Literal["qizheng-chart/v1"] = "qizheng-chart/v1"
    subject_ref: str = Field(min_length=1)
    planets: tuple[PlanetPosition, ...]
    houses: tuple[HousePosition, ...]
    aspects: tuple[Aspect, ...]
    time_layers: tuple[TimeLayer, ...]
    core_facts: QizhengCoreFacts | None = None


class HexagramSummary(ContractModel):
    name: str = Field(min_length=1)
    upper_trigram: str = Field(min_length=1)
    lower_trigram: str = Field(min_length=1)


class LiuyaoLine(ContractModel):
    position: int = Field(ge=1, le=6)
    value: Literal[6, 7, 8, 9]
    moving: bool


class LiuyaoSourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)


class LiuyaoSourceRef(ContractModel):
    pack: Literal["divination/huangjin-ce"]
    rule_id: Literal["HJC-R009"]
    source_anchor: str = Field(min_length=1)
    verification_status: Literal["verified"]
    binding_digest: str = Field(min_length=1)


class LiuyaoSpecificLineSourceRef(ContractModel):
    pack: Literal["divination/zengshan-buyi"]
    rule_id: Literal["ZR-04-04"]
    source_anchor: str = Field(min_length=1)
    verification_status: Literal["verified"]
    binding_digest: str = Field(min_length=1)


class LiuyaoSpecificLineAdjudication(ContractModel):
    status: Literal[
        "adjudicated_unique_visible_line",
        "adjudicated_single_moving_visible_line",
        "unresolved_multiple_visible_lines",
        "unresolved_no_visible_line",
    ]
    decision_scope: Literal["finance_primary_relative_line_identity"]
    primary_relative: Literal["妻财"]
    visible_candidate_count: int = Field(ge=0, le=6)
    visible_candidate_lines: tuple[int, ...]
    moving_visible_candidate_count: int = Field(ge=0, le=6)
    moving_visible_candidate_lines: tuple[int, ...]
    specific_line_selection: int | None = Field(default=None, ge=1, le=6)
    derivation_basis: Literal[
        "verified_role_plus_runtime_unique_visible_candidate",
        "verified_two_present_rule_plus_runtime_single_moving_candidate",
        "verified_role_plus_runtime_multiple_visible_candidates",
        "verified_role_plus_runtime_no_visible_candidate",
    ]
    selection_source_ref: LiuyaoSourceRef | LiuyaoSpecificLineSourceRef | None
    hard_verdict: None = None

    @model_validator(mode="after")
    def _line_identity_matches_status(self) -> LiuyaoSpecificLineAdjudication:
        lines = self.visible_candidate_lines
        if tuple(sorted(set(lines))) != lines or any(line not in range(1, 7) for line in lines):
            raise ValueError("visible Liuyao candidate lines must be unique and sorted")
        moving_lines = self.moving_visible_candidate_lines
        if tuple(sorted(set(moving_lines))) != moving_lines or any(
            line not in lines for line in moving_lines
        ):
            raise ValueError("moving Liuyao candidate lines must be sorted visible lines")
        if self.visible_candidate_count != len(lines):
            raise ValueError("visible Liuyao candidate count is inconsistent")
        if self.moving_visible_candidate_count != len(moving_lines):
            raise ValueError("moving Liuyao candidate count is inconsistent")
        if self.status == "adjudicated_unique_visible_line":
            if (
                len(lines) != 1
                or self.specific_line_selection != lines[0]
                or self.derivation_basis
                != "verified_role_plus_runtime_unique_visible_candidate"
                or not isinstance(self.selection_source_ref, LiuyaoSourceRef)
            ):
                raise ValueError("unique visible Liuyao line adjudication is inconsistent")
        elif self.status == "adjudicated_single_moving_visible_line":
            if (
                len(lines) != 2
                or len(moving_lines) != 1
                or self.specific_line_selection != moving_lines[0]
                or self.derivation_basis
                != "verified_two_present_rule_plus_runtime_single_moving_candidate"
                or not isinstance(
                    self.selection_source_ref,
                    LiuyaoSpecificLineSourceRef,
                )
            ):
                raise ValueError("single-moving Liuyao line adjudication is inconsistent")
        elif self.status == "unresolved_multiple_visible_lines":
            if (
                len(lines) < 2
                or self.specific_line_selection is not None
                or self.derivation_basis
                != "verified_role_plus_runtime_multiple_visible_candidates"
                or self.selection_source_ref is not None
                or (len(lines) == 2 and len(moving_lines) == 1)
            ):
                raise ValueError("multiple visible Liuyao lines must remain unresolved")
        elif (
            lines
            or moving_lines
            or self.specific_line_selection is not None
            or self.derivation_basis
            != "verified_role_plus_runtime_no_visible_candidate"
            or self.selection_source_ref is not None
        ):
            raise ValueError("non-visible Liuyao line adjudication is inconsistent")
        return self


class LiuyaoRoleAdjudication(ContractModel):
    status: Literal["adjudicated_question_role_set"]
    decision_scope: Literal["finance_useful_spirit_role_set"]
    question_class: Literal["finance"]
    primary_relative: Literal["妻财"]
    supporting_relatives: tuple[Literal["子孙"], ...]
    obstacle_attention_relatives: tuple[Literal["兄弟", "官鬼", "父母"], ...]
    specific_line_selection: int | None = Field(default=None, ge=1, le=6)
    specific_line_adjudication: LiuyaoSpecificLineAdjudication
    hard_verdict: None = None
    source_ref: LiuyaoSourceRef
    unresolved_checks: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _bounded_finance_contract(self) -> LiuyaoRoleAdjudication:
        if self.supporting_relatives != ("子孙",):
            raise ValueError("finance support relative must be 子孙")
        if self.obstacle_attention_relatives != ("兄弟", "官鬼", "父母"):
            raise ValueError("finance obstacle relatives are inconsistent")
        if (
            self.specific_line_selection
            != self.specific_line_adjudication.specific_line_selection
        ):
            raise ValueError("specific Liuyao line selections do not match")
        return self


class LiuyaoNotRequestedRoleAdjudication(ContractModel):
    status: Literal["not_requested"]
    decision_scope: None = None
    question_class: None = None
    primary_relative: None = None
    supporting_relatives: tuple[()] = ()
    obstacle_attention_relatives: tuple[()] = ()
    specific_line_selection: None = None
    hard_verdict: None = None
    source_ref: None = None
    unresolved_checks: tuple[str, ...] = Field(min_length=1)


class LiuyaoQuestionContext(ContractModel):
    question_class: Literal["finance"]
    classification_source: Literal["explicit_structured_input"]


class LiuyaoSeasonalStrengthSourceRef(ContractModel):
    pack: Literal["divination/zengshan-buyi"]
    rule_id: Literal["ZR-05-05"]
    source_anchor: str = Field(min_length=1)
    verification_status: Literal["verified"]
    binding_digest: str = Field(min_length=1)


class LiuyaoSeasonalStrengthAdjudication(ContractModel):
    status: Literal["adjudicated_seasonal_strength_band"]
    decision_scope: Literal["liuyao_candidate_month_order_strength_band"]
    candidate_source: Literal["visible_line", "changed_line", "hidden_line"]
    line: int = Field(ge=1, le=6)
    line_element: Literal["木", "火", "土", "金", "水"]
    month_element: Literal["木", "火", "土", "金", "水"]
    seasonal_state: Literal["旺", "相", "休", "囚", "死"]
    strength_band: Literal["旺相", "休囚"]
    whole_candidate_strength_verdict: None = None
    outcome_verdict: None = None
    source_ref: LiuyaoSeasonalStrengthSourceRef
    unresolved_checks: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _seasonal_band_matches_state(self) -> LiuyaoSeasonalStrengthAdjudication:
        expected = "旺相" if self.seasonal_state in {"旺", "相"} else "休囚"
        if self.strength_band != expected:
            raise ValueError("Liuyao seasonal strength band conflicts with state")
        return self


class LiuyaoStrengthSignal(ContractModel):
    signal: Literal[
        "seasonal_support",
        "seasonal_weakening",
        "month_break",
        "day_clash",
        "xunkong",
        "moving_line",
    ]
    value: str | bool
    status: Literal["candidate_signal"]


class LiuyaoStrengthCandidate(ContractModel):
    source: Literal["visible_line", "changed_line", "hidden_line"]
    line: int = Field(ge=1, le=6)
    moving: bool
    xunkong: bool
    najia: dict[str, object]
    month_day_strength: dict[str, object]
    seasonal_adjudication: LiuyaoSeasonalStrengthAdjudication
    signals: tuple[LiuyaoStrengthSignal, ...]
    status: Literal["candidate_only"]
    hard_verdict: None = None

    @model_validator(mode="after")
    def _candidate_identity_matches_adjudication(self) -> LiuyaoStrengthCandidate:
        if (
            self.source != self.seasonal_adjudication.candidate_source
            or self.line != self.seasonal_adjudication.line
        ):
            raise ValueError("Liuyao strength candidate identity is inconsistent")
        return self


class LiuyaoRelativeStrengthEvidence(ContractModel):
    status: Literal["candidate_only", "not_available"]
    candidates: tuple[LiuyaoStrengthCandidate, ...]
    hard_verdict: None = None

    @model_validator(mode="after")
    def _candidate_availability_matches_status(self) -> LiuyaoRelativeStrengthEvidence:
        if (self.status == "candidate_only") != bool(self.candidates):
            raise ValueError("Liuyao relative strength availability is inconsistent")
        return self


class LiuyaoStrengthRuleRef(LiuyaoSeasonalStrengthSourceRef):
    role: Literal["useful_spirit_month_order_strength_band"]


class LiuyaoStrengthEvidence(ContractModel):
    status: Literal["candidate_only", "not_requested"]
    by_relative: dict[str, LiuyaoRelativeStrengthEvidence]
    source_rules: tuple[LiuyaoStrengthRuleRef, ...]
    fact_status: Literal["calculated_relation_not_verdict"]
    hard_verdict: None = None
    requires_school_adjudication: Literal[True]
    source_dependency_id: Literal[
        "liuyao.interpretation.useful-spirit-strength-evidence"
    ]

    @model_validator(mode="after")
    def _source_presence_matches_status(self) -> LiuyaoStrengthEvidence:
        if self.status == "candidate_only":
            if len(self.source_rules) != 1 or not self.by_relative:
                raise ValueError("requested Liuyao strength evidence needs one source")
            binding_digest = self.source_rules[0].binding_digest
            if any(
                candidate.seasonal_adjudication.source_ref.binding_digest
                != binding_digest
                for evidence in self.by_relative.values()
                for candidate in evidence.candidates
            ):
                raise ValueError("Liuyao strength source bindings do not match")
        elif self.source_rules or self.by_relative:
            raise ValueError("unrequested Liuyao strength evidence must be empty")
        return self


class LiuyaoUsefulSpiritSelection(ContractModel):
    status: Literal["evidence_bound"]
    reason: str = Field(min_length=1)
    query_word_matching: Literal[False]
    source_dependency_id: str = Field(min_length=1)
    chain_candidates: dict[str, object]
    strength_evidence: LiuyaoStrengthEvidence
    role_adjudication: LiuyaoRoleAdjudication | LiuyaoNotRequestedRoleAdjudication
    question_context: LiuyaoQuestionContext | None = None

    @model_validator(mode="after")
    def _question_context_matches_role(self) -> LiuyaoUsefulSpiritSelection:
        if isinstance(self.role_adjudication, LiuyaoRoleAdjudication):
            if self.question_context is None:
                raise ValueError("finance Liuyao role adjudication requires context")
        elif self.question_context is not None:
            raise ValueError("unrequested Liuyao role adjudication cannot have context")
        return self


class LiuyaoCoreFacts(ContractModel):
    """Runtime-owned six-line structural facts; no divination verdicts."""

    calendar: dict[str, object] | None = None
    casting: dict[str, object] | None = None
    casting_method: str | None = Field(default=None, min_length=1)
    changed_najia: tuple[dict[str, object], ...] | None = None
    changed_plate_lines: tuple[dict[str, object], ...] | None = None
    changed_six_relatives: tuple[str, ...] | None = None
    hidden_lines: tuple[dict[str, object], ...] | None = None
    interpretation_status: str | None = Field(default=None, min_length=1)
    line_facts: tuple[dict[str, object], ...] | None = None
    lines: tuple[dict[str, object], ...] | None = None
    month_day_strength: tuple[dict[str, object], ...] | None = None
    moving_lines: tuple[int, ...] | None = None
    najia: tuple[dict[str, object], ...] | None = None
    relation_facts: tuple[dict[str, object], ...] | None = None
    returning_relations: tuple[dict[str, object], ...] | None = None
    requested_useful_spirit_candidates: dict[str, object] | None = None
    shi_ying: dict[str, object] | None = None
    shi_ying_moving_relations: dict[str, object] | None = None
    six_relatives: tuple[str, ...] | None = None
    six_spirit_profile: dict[str, object] | None = None
    six_spirits: tuple[str, ...] | None = None
    useful_spirit_candidates: dict[str, object] | None = None
    useful_spirit_selection: LiuyaoUsefulSpiritSelection | None = None
    xunkong: dict[str, object] | None = None
    source_conditioned_patterns: tuple[LiuyaoSourcePattern, ...] = ()


class LiuyaoChartV1(ContractModel):
    schema_version: Literal["liuyao-chart/v1"] = "liuyao-chart/v1"
    subject_ref: str = Field(min_length=1)
    question: str = Field(min_length=1)
    primary_hexagram: HexagramSummary
    changed_hexagram: HexagramSummary | None
    lines: tuple[LiuyaoLine, ...] = Field(min_length=6, max_length=6)
    core_facts: LiuyaoCoreFacts | None = None


class MeihuaTrigram(ContractModel):
    position: Literal["upper", "lower"]
    trigram: str = Field(min_length=1)
    element: str = Field(min_length=1)


class MeihuaBodyUse(ContractModel):
    body: MeihuaTrigram
    use: MeihuaTrigram
    relation: str = Field(min_length=1)
    status: str = Field(min_length=1)


class MeihuaBodyRelationFact(ContractModel):
    """Runtime-owned body/use relation detail; it is not an event verdict."""

    body: MeihuaTrigram
    element: str = Field(min_length=1)
    position: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    source_dependency_id: str = Field(min_length=1)
    source_plate: str = Field(min_length=1)
    status: str = Field(min_length=1)
    trigram: str = Field(min_length=1)


class MeihuaSeasonalStrengthFact(ContractModel):
    """Runtime-owned month/season state for one Meihua trigram."""

    month_branch: str = Field(min_length=1)
    season: str = Field(min_length=1)
    source_dependency_id: str = Field(min_length=1)
    state: str = Field(min_length=1)
    status: str = Field(min_length=1)
    trigram: str = Field(min_length=1)


class MeihuaRelationSourceRef(ContractModel):
    pack: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    verification_status: Literal["verified"]
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class MeihuaRelationAdjudication(ContractModel):
    """Classical polarity for one body/use relation, not an event verdict."""

    status: Literal["adjudicated_relation_polarity"]
    decision_scope: Literal["meihua_body_use_relation"]
    relation_key: str = Field(min_length=1)
    source_polarity: Literal[
        "supportive",
        "depleting",
        "adverse",
        "favorable",
        "harmonious",
    ]
    hard_verdict: None = None
    event_verdict: None = None
    source_refs: tuple[MeihuaRelationSourceRef, ...] = Field(min_length=1)
    unresolved_checks: tuple[str, ...] = Field(min_length=1)


class MeihuaRelationCandidate(ContractModel):
    """Source-adjudicated relation polarity, never a final event verdict."""

    candidate_id: str = Field(min_length=1)
    source_plate: str = Field(min_length=1)
    position: Literal["upper", "lower"]
    relation: str = Field(min_length=1)
    relation_key: str = Field(min_length=1)
    actor: MeihuaTrigram
    body: MeihuaTrigram
    seasonal_state: str | None = Field(default=None, min_length=1)
    rule_id: str = Field(min_length=1)
    status: Literal["relation_adjudicated_not_event_verdict"]
    hard_verdict: None = None
    verification_status: Literal["verified"]
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    source_dependency_id: str = Field(min_length=1)
    relation_adjudication: MeihuaRelationAdjudication


class MeihuaInterpretiveCandidates(ContractModel):
    """Bounded source adjudications awaiting multi-relation synthesis."""

    schema_version: Literal["mingli-meihua-interpretive-candidates-v1"]
    status: Literal["source_adjudicated_relations"]
    hard_verdict: None = None
    verification_status: Literal["verified"]
    relation_candidates: tuple[MeihuaRelationCandidate, ...] = Field(min_length=1)
    requires_classical_adjudication: Literal[False]
    requires_synthesis_adjudication: Literal[True]
    boundary: str = Field(min_length=1)


class MeihuaCoreFacts(ContractModel):
    """Additional calculated Meihua structure preserved for the result layer."""

    body_relation_facts: tuple[MeihuaBodyRelationFact, ...] | None = None
    seasonal_strength: dict[str, MeihuaSeasonalStrengthFact] | None = None
    interpretive_candidates: MeihuaInterpretiveCandidates | None = None
    interpretation_status: str | None = Field(default=None, min_length=1)


class MeihuaChartV1(ContractModel):
    schema_version: Literal["meihua-chart/v1"] = "meihua-chart/v1"
    subject_ref: str = Field(min_length=1)
    question: str = Field(min_length=1)
    casting_method: Literal[
        "time", "supplied_number", "sound_count", "observation", "supplied_hexagram"
    ]
    primary_hexagram: HexagramSummary
    mutual_hexagram: HexagramSummary | None
    changed_hexagram: HexagramSummary | None
    moving_lines: tuple[int, ...] = Field(min_length=0, max_length=6)
    body_use: MeihuaBodyUse
    core_facts: MeihuaCoreFacts | None = None
    public_labels: tuple[PublicKeyLabel, ...] = ()


class LumingNayinPillar(ContractModel):
    position: Literal["year", "month", "day", "hour"]
    stem: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    nayin: str = Field(min_length=1)


class LumingNayinRelation(ContractModel):
    category: Literal["lu", "ma", "gui"]
    relation: str = Field(min_length=1)
    anchor: str = Field(min_length=1)
    anchor_pillar: str = Field(min_length=1)
    status: str = Field(min_length=1)
    target_branch: str | None = Field(default=None, min_length=1)
    candidates: tuple[str, ...]
    matched_positions: tuple[str, ...]
    recension: str | None = Field(default=None, min_length=1)


class LumingNayinRuleSourceRef(ContractModel):
    pack: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    verification_status: Literal["verified"]
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class LumingNayinRuleApplicabilityAdjudication(ContractModel):
    status: Literal["adjudicated_rule_applicability"]
    decision_scope: Literal["luming_nayin_source_rule_applicability"]
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    rule_title: str = Field(min_length=1)
    evidence_role: Literal[
        "issue_specific_judgment_rule",
        "methodology_rule",
    ]
    hard_verdict: None = None
    life_verdict: None = None
    source_ref: LumingNayinRuleSourceRef
    unresolved_checks: tuple[str, ...] = Field(min_length=1)


class LumingNayinSourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)
    applicability_adjudication: LumingNayinRuleApplicabilityAdjudication


class LumingNayinChartV1(ContractModel):
    schema_version: Literal["luming-nayin-chart/v1"] = "luming-nayin-chart/v1"
    subject_ref: str = Field(min_length=1)
    pillars: tuple[LumingNayinPillar, ...] = Field(min_length=4, max_length=4)
    three_yuan_profiles: dict[str, object]
    taiyuan: dict[str, object] | None
    relations: tuple[LumingNayinRelation, ...]
    source_conditioned_patterns: tuple[LumingNayinSourcePattern, ...] = ()


class RhythmFactsPillar(ContractModel):
    position: Literal["year", "month", "day", "hour"]
    stem: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    nayin: str = Field(min_length=1)


class RhythmFactsViewV1(ContractModel):
    """Facts-only public projection for the Nayin rhythm tool."""

    schema_version: Literal["rhythm-facts-view/v1"] = "rhythm-facts-view/v1"
    subject_ref: str = Field(min_length=1)
    pillars: tuple[RhythmFactsPillar, ...] = Field(min_length=4, max_length=4)
    independent_lineage: str = Field(min_length=1)
    fact_scope: str = Field(min_length=1)
    interpretation_status: Literal["facts_only"]
    source_boundary: str = Field(min_length=1)


class TaiyiCalendar(ContractModel):
    annual_boundary: str = Field(min_length=1)
    lunar_year: int
    year_ganzhi: str = Field(min_length=1)


class TaiyiEpoch(ContractModel):
    accumulated_year: int
    anchor_accumulated_year: int
    anchor_lunar_year_ce: int
    derived_ce_offset: int
    one_based: bool
    profile_id: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)


class TaiyiCycle(ContractModel):
    bureau: int
    governance: str = Field(min_length=1)
    ji: int
    position_360: int
    year_in_ji: int
    year_in_zi_yuan: int
    zi_yuan: int
    zi_yuan_head: str = Field(min_length=1)


class TaiyiNamedPosition(ContractModel):
    name: str = Field(min_length=1)
    position: str = Field(min_length=1)


class TaiyiBoard(ContractModel):
    heshen: str = Field(min_length=1)
    jishen: str = Field(min_length=1)
    shiji: str = Field(min_length=1)
    taisui: str = Field(min_length=1)
    taiyi_position: str = Field(min_length=1)
    tianmu_wenchang: TaiyiNamedPosition


class TaiyiFourGenerals(ContractModel):
    guest_assistant: int
    guest_major: int
    host_assistant: int
    host_major: int


class TaiyiLongCycleDeity(ContractModel):
    deity_id: str = Field(min_length=1)
    accumulated_year: int
    cycle_position: int
    epoch_profile: str = Field(min_length=1)
    name: str = Field(min_length=1)
    position: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: str = Field(min_length=1)


class TaiyiPatternSourceRef(ContractModel):
    pack: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    verification_status: Literal["verified"]
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class TaiyiPatternIdentityAdjudication(ContractModel):
    status: Literal["adjudicated_pattern_identity"]
    decision_scope: Literal["taiyi_board_pattern_identity"]
    pattern_id: str = Field(min_length=1)
    pattern_name: str = Field(min_length=1)
    hard_verdict: None = None
    event_verdict: None = None
    source_ref: TaiyiPatternSourceRef
    unresolved_checks: tuple[str, ...] = Field(min_length=1)


class TaiyiBoardPredicate(ContractModel):
    predicate_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    fact_paths: tuple[str, ...]
    source_anchor: str = Field(min_length=1)
    source_dependency_id: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    identity_adjudication: TaiyiPatternIdentityAdjudication


class TaiyiScopeContract(ContractModel):
    declared_scope: str = Field(min_length=1)
    interpretation_policy: str = Field(min_length=1)
    supported_horizons: tuple[str, ...]
    supported_objects: tuple[str, ...]
    unsupported_scopes: tuple[str, ...]


class TaiyiChartV1(ContractModel):
    schema_version: Literal["taiyi-chart/v1"] = "taiyi-chart/v1"
    subject_ref: str = Field(min_length=1)
    calendar: TaiyiCalendar
    epoch: TaiyiEpoch
    cycle: TaiyiCycle
    board: TaiyiBoard
    host_guest: dict[str, object]
    four_generals: TaiyiFourGenerals
    long_cycle_deities: tuple[TaiyiLongCycleDeity, ...]
    board_predicates: tuple[TaiyiBoardPredicate, ...]
    scope_contract: TaiyiScopeContract


class SelectionCandidate(ContractModel):
    candidate_id: str = Field(min_length=1)
    civil_date: str = Field(min_length=1)
    best_candidate_time_id: str = Field(min_length=1)
    eligibility: dict[str, object]
    rejection_reasons: tuple[dict[str, object], ...]
    ranking_components: dict[str, object]


class SelectionRanking(ContractModel):
    component_order: tuple[str, ...]
    eligible_candidate_ids: tuple[str, ...]
    eligible_date_time_candidate_ids: tuple[str, ...]
    folk_affects_rank: bool
    method: str = Field(min_length=1)
    opaque_numeric_score: bool
    ordered_candidate_ids: tuple[str, ...]
    ordered_date_time_candidate_ids: tuple[str, ...]


class SelectionLineagePolicy(ContractModel):
    folk: str = Field(min_length=1)
    folk_priority: str = Field(min_length=1)
    merge_verdicts: bool
    official: str = Field(min_length=1)
    official_priority: str = Field(min_length=1)
    preserve_disagreement: bool


class SelectionSourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)


class SelectionChartV1(ContractModel):
    schema_version: Literal["selection-chart/v1"] = "selection-chart/v1"
    subject_ref: str = Field(min_length=1)
    event_profile: str = Field(min_length=1)
    eligible_candidates: tuple[SelectionCandidate, ...]
    eligible_date_time_candidates: tuple[str, ...]
    eliminations: tuple[dict[str, object], ...]
    ranking: SelectionRanking
    lineage_policy: SelectionLineagePolicy
    no_valid_candidate: bool
    basis_projection: dict[str, object]
    source_conditioned_patterns: tuple[SelectionSourcePattern, ...] = ()


class FengshuiSourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)


class FengshuiViewV1(ContractModel):
    schema_version: Literal["fengshui-view/v1"] = "fengshui-view/v1"
    subject_ref: str = Field(min_length=1)
    active_subprofiles: tuple[Literal["form", "liqi"], ...]
    observation_provenance: dict[str, object]
    compass: dict[str, object]
    building_chronology: dict[str, object]
    layout_graph: dict[str, object]
    form: dict[str, object]
    liqi: dict[str, object]
    active_source_rule_ids: tuple[str, ...]
    conflicts: tuple[dict[str, object], ...]
    uncertainties: tuple[dict[str, object], ...]
    critical_missing: tuple[str, ...]
    source_conditioned_patterns: tuple[FengshuiSourcePattern, ...] = ()


class QimenPalace(ContractModel):
    palace_id: str = Field(min_length=1)
    stem: str = Field(min_length=1)
    heaven_stems: tuple[str, ...]
    stars: tuple[str, ...]
    star: str | None = Field(default=None, min_length=1)
    door: str | None = Field(default=None, min_length=1)
    deity: str | None = Field(default=None, min_length=1)


class QimenChief(ContractModel):
    star: str = Field(min_length=1)
    door: str = Field(min_length=1)
    hidden_instrument: str = Field(min_length=1)
    xun_palace: int = Field(ge=1, le=9)
    hosted_xun_palace: int = Field(ge=1, le=9)
    destination_palace: int = Field(ge=1, le=9)


class QimenDirector(ContractModel):
    door: str = Field(min_length=1)
    xun_palace: int = Field(ge=1, le=9)
    destination_palace: int = Field(ge=1, le=9)
    hour_offset_in_xun: int = Field(ge=0, le=9)


class QimenXunkong(ContractModel):
    xun: str = Field(min_length=1)
    branches: tuple[str, ...] = Field(min_length=1)
    palaces: tuple[int, ...] = Field(min_length=1, max_length=9)


class QimenHorse(ContractModel):
    hour_branch: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    palace: int = Field(ge=1, le=9)


class QimenPatternSourceRef(ContractModel):
    pack: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    verification_status: Literal["verified"]
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class QimenPatternIdentityAdjudication(ContractModel):
    status: Literal["adjudicated_pattern_identity"]
    decision_scope: Literal["qimen_named_pattern_identity"]
    pattern_id: str = Field(min_length=1)
    pattern_name: str = Field(min_length=1)
    palace: int | None = Field(default=None, ge=1, le=9)
    hard_verdict: None = None
    event_verdict: None = None
    source_ref: QimenPatternSourceRef
    unresolved_checks: tuple[str, ...] = Field(min_length=1)


class QimenNamedPattern(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    palace: int | None = Field(default=None, ge=1, le=9)
    identity_adjudication: QimenPatternIdentityAdjudication


class QimenPlateStem(ContractModel):
    palace: int = Field(ge=1, le=9)
    stem: str = Field(min_length=1)
    kind: Literal["six_instrument", "three_wonder"]


class QimenHiddenJia(ContractModel):
    xun: str = Field(min_length=1)
    instrument: str = Field(min_length=1)


class QimenInstrumentsWonders(ContractModel):
    six_instruments: tuple[str, ...] = Field(min_length=1)
    three_wonders: tuple[str, ...] = Field(min_length=1)
    earth_plate: tuple[QimenPlateStem, ...]
    heaven_plate: tuple[QimenPlateStem, ...]
    hidden_jia: QimenHiddenJia


class QimenChartV1(ContractModel):
    schema_version: Literal["qimen-chart/v1"] = "qimen-chart/v1"
    subject_ref: str = Field(min_length=1)
    question: str = Field(min_length=1)
    dun_type: Literal["yin", "yang"]
    ju_number: int = Field(ge=1, le=9)
    palaces: tuple[QimenPalace, ...] = Field(min_length=9, max_length=9)
    chief: QimenChief
    director: QimenDirector
    instruments_wonders: QimenInstrumentsWonders
    xunkong: QimenXunkong
    horse: QimenHorse
    named_patterns: tuple[QimenNamedPattern, ...]


DaliurenLessonUpper = Literal[
    "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"
]
DALIUREN_LESSON_UPPERS: tuple[DaliurenLessonUpper, ...] = (
    "子",
    "丑",
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
)


class DaliurenLesson(ContractModel):
    lesson_id: str = Field(min_length=1)
    upper: DaliurenLessonUpper
    lower: str = Field(min_length=1)


class DaliurenTransmission(ContractModel):
    stage: Literal["initial", "middle", "final"]
    branch: str = Field(min_length=1)
    general: str = Field(min_length=1)


class DaliurenTimingCandidate(ContractModel):
    id: Literal["initial_group_upper_candidate"]
    role: Literal["event_response_candidate"]
    anchor_earth_branch: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    solar_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    day_ganzhi: str = Field(min_length=2)
    days_after_cast: int = Field(ge=1, le=12, strict=True)
    source_pack: str = Field(min_length=1)
    source_rule: Literal["LM-R21"]
    candidate_not_guarantee: Literal[True]


_DALIUREN_STRUCTURAL_INDEX_MAX = 3
_DALIUREN_STRUCTURAL_INDEX_BY_TOKEN = {"0": 0, "1": 1, "2": 2, "3": 3}
_DALIUREN_INCOMPLETE_FOUR_LESSONS_RULE_ID = "DLR-S01"
_DALIUREN_FOUR_LESSON_UPPER_PATHS = frozenset(
    f"fact:/chart_facts/output/four_lessons/{index}/upper" for index in range(4)
)
_DALIUREN_FOUR_LESSON_DISTINCT_AUDIT = (
    "/chart_facts/output/four_lessons/*/upper:distinct_count_eq:3"
)


def daliuren_in_range_structural_indices(
    structural_patterns: object,
    title: str,
) -> tuple[int, ...]:
    if not isinstance(structural_patterns, (list, tuple)):
        return ()
    return tuple(
        index
        for index, pattern in enumerate(structural_patterns)
        if pattern == title and 0 <= index <= _DALIUREN_STRUCTURAL_INDEX_MAX
    )


def _daliuren_canonical_structural_index(token: str) -> int:
    # Exact ASCII "0"-"3" only. str.isdigit()/int() would accept "00"/"０".
    try:
        return _DALIUREN_STRUCTURAL_INDEX_BY_TOKEN[token]
    except KeyError:
        raise ValueError("source pattern structural index must be 0-3") from None


def _daliuren_structural_index_from_fact_path(path: str) -> int | None:
    prefix = "fact:/chart_facts/output/structural_patterns/"
    if not path.startswith(prefix):
        return None
    return _daliuren_canonical_structural_index(path[len(prefix) :])


def _daliuren_structural_index_from_audit(audit: str, title: str) -> int | None:
    prefix = "/chart_facts/output/structural_patterns/"
    suffix = f":eq:{title}"
    if not audit.startswith(prefix) or not audit.endswith(suffix):
        return None
    return _daliuren_canonical_structural_index(audit[len(prefix) : -len(suffix)])


def validate_daliuren_source_pattern_provenance(
    *,
    rule_id: str,
    title: str,
    fact_paths: tuple[str, ...],
    predicate_audit: tuple[str, ...],
) -> int:
    """Return the unique in-range structural index or raise ValueError."""

    if len(set(fact_paths)) != len(fact_paths) or len(set(predicate_audit)) != len(
        predicate_audit
    ):
        raise ValueError("source pattern provenance must be unique")

    path_indices: list[int] = []
    extra_paths: list[str] = []
    for path in fact_paths:
        index = _daliuren_structural_index_from_fact_path(path)
        if index is None:
            extra_paths.append(path)
        else:
            path_indices.append(index)

    audit_indices: list[int] = []
    extra_audits: list[str] = []
    for audit in predicate_audit:
        index = _daliuren_structural_index_from_audit(audit, title)
        if index is None:
            extra_audits.append(audit)
        else:
            audit_indices.append(index)

    if path_indices != audit_indices or len(path_indices) != 1:
        raise ValueError("source pattern requires unique structural provenance")
    structural_index = path_indices[0]

    if rule_id == _DALIUREN_INCOMPLETE_FOUR_LESSONS_RULE_ID:
        if set(extra_paths) != _DALIUREN_FOUR_LESSON_UPPER_PATHS:
            raise ValueError("incomplete four lessons must publish four upper paths")
        if extra_audits != [_DALIUREN_FOUR_LESSON_DISTINCT_AUDIT]:
            raise ValueError(
                "incomplete four lessons must publish the distinct-count audit"
            )
        if len(fact_paths) != 5 or len(predicate_audit) != 2:
            raise ValueError("incomplete four lessons provenance cardinality is fixed")
    elif extra_paths or extra_audits or len(fact_paths) != 1 or len(predicate_audit) != 1:
        raise ValueError("source pattern provenance must stay on the structural path")
    return structural_index


def daliuren_source_pattern_structural_index(pattern: DaliurenSourcePattern) -> int:
    return validate_daliuren_source_pattern_provenance(
        rule_id=pattern.rule_id,
        title=pattern.title,
        fact_paths=pattern.fact_paths,
        predicate_audit=pattern.predicate_audit,
    )


_DALIUREN_SOURCE_PATTERN_IDENTITIES = frozenset(
    {
        (
            "DLR-S01",
            "liuren.structural.incomplete-four-lessons",
            "四课不备",
            "fulltext.md#L58",
        ),
        (
            "DLR-08",
            "liuren.structural.bazhuan-day",
            "八专日",
            "fulltext.md#L7556",
        ),
        (
            "DLR-09",
            "liuren.structural.fuyin",
            "伏吟",
            "fulltext.md#L7696",
        ),
        (
            "DLR-10",
            "liuren.structural.fanyin",
            "反吟",
            "fulltext.md#L7874",
        ),
    }
)


class DaliurenSourcePattern(ContractModel):
    """Audited structural-pattern match, never a divination verdict."""

    rule_id: Literal["DLR-S01", "DLR-08", "DLR-09", "DLR-10"]
    local_rule_id: Literal[
        "liuren.structural.incomplete-four-lessons",
        "liuren.structural.bazhuan-day",
        "liuren.structural.fuyin",
        "liuren.structural.fanyin",
    ]
    title: Literal["四课不备", "八专日", "伏吟", "反吟"]
    source_pack: Literal["san-shi/daliuren-daquan"]
    source_anchor: Literal[
        "fulltext.md#L58",
        "fulltext.md#L7556",
        "fulltext.md#L7696",
        "fulltext.md#L7874",
    ]
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)
    source_dependency_id: Literal[
        "liuren.source-conditioned-structural-patterns-v1"
    ]

    @model_validator(mode="after")
    def _uses_one_audited_rule_identity(self) -> DaliurenSourcePattern:
        identity = (
            self.rule_id,
            self.local_rule_id,
            self.title,
            self.source_anchor,
        )
        if identity not in _DALIUREN_SOURCE_PATTERN_IDENTITIES:
            raise ValueError("source pattern identity fields must match one audited rule")
        validate_daliuren_source_pattern_provenance(
            rule_id=self.rule_id,
            title=self.title,
            fact_paths=self.fact_paths,
            predicate_audit=self.predicate_audit,
        )
        return self


class DaliurenDayHour(ContractModel):
    day: str = Field(min_length=2)
    hour: str = Field(min_length=2)


class DaliurenMonthGeneral(ContractModel):
    branch: str = Field(min_length=1)
    name: str = Field(min_length=1)


class DaliurenNoblePerson(ContractModel):
    branch: str = Field(min_length=1)
    day_night_profile: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    earth_position: str = Field(min_length=1)
    period: Literal["day", "night"]
    profile: str = Field(min_length=1)
    source: str = Field(min_length=1)


class DaliurenXunkong(ContractModel):
    branches: tuple[
        Annotated[str, Field(min_length=1)],
        Annotated[str, Field(min_length=1)],
    ]
    xun: str = Field(min_length=2)


class DaliurenHeavenPlateCell(ContractModel):
    earth: str = Field(min_length=1)
    heaven: str = Field(min_length=1)


class DaliurenGeneralCell(ContractModel):
    earth: str = Field(min_length=1)
    general: str = Field(min_length=1)
    heaven: str = Field(min_length=1)


class DaliurenLessonMethod(ContractModel):
    """Stable nine-method fields from mingli-liuren-runtime-core-facts-v1."""

    calculated_transmissions: str = Field(min_length=3)
    calculation_source: str = Field(min_length=1)
    direct_direction: str | None
    primary: str = Field(min_length=1)
    selected_initial: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    use_method: str = Field(min_length=1)


class DaliurenRuleSourceRef(ContractModel):
    pack: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    quote_id: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    source_anchor: str = Field(min_length=1)


class DaliurenRuleEvidenceEntry(ContractModel):
    activation_id: str = Field(min_length=1)
    dependency_group: str = Field(min_length=1)
    fact_paths: tuple[Annotated[str, Field(min_length=1)], ...]
    observation: dict[str, object]
    polarity: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_key: str = Field(min_length=1)
    source_refs: tuple[DaliurenRuleSourceRef, ...] = Field(min_length=1)
    status: str = Field(min_length=1)
    weight_class: str = Field(min_length=1)
    confidence_ceiling: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    stop_conditions: tuple[Annotated[str, Field(min_length=1)], ...] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )


class DaliurenRuleNotEvaluatedEntry(ContractModel):
    activation_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_key: str = Field(min_length=1)
    source_refs: tuple[DaliurenRuleSourceRef, ...] = Field(min_length=1)
    status: str = Field(min_length=1)


class DaliurenRuleEvidence(ContractModel):
    catalog_schema: str = Field(min_length=1)
    hard_verdict: None
    matched: tuple[DaliurenRuleEvidenceEntry, ...]
    not_evaluated: tuple[DaliurenRuleNotEvaluatedEntry, ...]
    requires_school_adjudication: Literal[True]
    scope_boundaries: tuple[DaliurenRuleEvidenceEntry, ...]
    status: str = Field(min_length=1)


class DaliurenRelationFact(ContractModel):
    object: str = Field(min_length=1)
    object_element: str = Field(min_length=1)
    object_value: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    subject_element: str = Field(min_length=1)
    subject_value: str = Field(min_length=1)


class DaliurenStageFlowEntry(DaliurenRelationFact):
    from_stage: str = Field(min_length=1)
    to_stage: str = Field(min_length=1)


class DaliurenTransmissionToDayEntry(DaliurenRelationFact):
    stage: str = Field(min_length=1)


class DaliurenSixRelativeStage(ContractModel):
    branch: str = Field(min_length=1)
    six_relative: str = Field(min_length=1)
    stage: str = Field(min_length=1)


class DaliurenStageStatusEntry(ContractModel):
    branch: str = Field(min_length=1)
    heavenly_general: str = Field(min_length=1)
    is_xunkong: bool = Field(strict=True)
    season_strength: str | None = Field(min_length=1)
    six_relative: str = Field(min_length=1)
    stage: str = Field(min_length=1)


class DaliurenTargetStrengthEntry(ContractModel):
    branch: str = Field(min_length=1)
    is_xunkong: bool = Field(strict=True)
    season_strength: str | None = Field(min_length=1)
    six_relative: str = Field(min_length=1)
    stage: str = Field(min_length=1)


class DaliurenWealthStageStrengthEntry(ContractModel):
    branch: str = Field(min_length=1)
    season_strength: str | None = Field(min_length=1)
    six_relative: str = Field(min_length=1)
    stage: str = Field(min_length=1)


class DaliurenWealthVoidStatusEntry(ContractModel):
    branch: str = Field(min_length=1)
    is_xunkong: bool = Field(strict=True)
    six_relative: str = Field(min_length=1)
    stage: str = Field(min_length=1)


class DaliurenStageBranchDirection(ContractModel):
    branch: str = Field(min_length=1)
    declared_source_anchor: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    direction_chinese: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    source_binding_status: str = Field(min_length=1)
    stage: str = Field(min_length=1)


class DaliurenGeneralLanding(ContractModel):
    heavenly_general: str = Field(min_length=1)
    landing_branch: str = Field(min_length=1)
    role: str = Field(min_length=1)
    source_anchor: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    source_pack: str = Field(min_length=1)
    source_rule: str = Field(min_length=1)
    source_text: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    stage: str = Field(min_length=1)
    status: Literal[
        "source_correspondence_matched",
        "no_exact_source_correspondence",
    ]

    @model_validator(mode="before")
    @classmethod
    def _source_fields_match_status(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        source_fields = frozenset({"source_anchor", "source_text"})
        present_source_fields = source_fields.intersection(value)
        if (
            value.get("status") == "source_correspondence_matched"
            and present_source_fields != source_fields
        ):
            raise ValueError("matched source correspondences require source fields")
        if (
            value.get("status") == "no_exact_source_correspondence"
            and present_source_fields
        ):
            raise ValueError("missing source correspondences must omit source fields")
        return value


class DaliurenGeneralModifierEntry(DaliurenGeneralLanding):
    six_relative: str = Field(min_length=1)


class DaliurenCandidateBranch(ContractModel):
    anchor_earth_branch: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    source_rule: str = Field(min_length=1)


_DALIUREN_DIMENSION_ENVELOPE_FIELDS = frozenset(
    {
        "requested_dimension",
        "canonical_dimension",
        "status",
        "source_rule_ids",
        "rule_evidence",
    }
)
_DALIUREN_CANONICAL_DIMENSION_FIELDS = {
    "outcome": frozenset(
        {
            "subject_object_relation",
            "transmissions_to_day",
            "initial_final_relation",
            "stage_flow",
        }
    ),
    "timing": frozenset(
        {"relative_speed", "candidate_branch", "candidate_date"}
    ),
    "state": frozenset({"stage_status", "general_landing_correspondences"}),
    "location": frozenset({"stage_branch_directions"}),
    "relationship": frozenset(
        {"six_relative_stages", "subject_object_relation", "stage_flow"}
    ),
    "work": frozenset(
        {
            "six_relative_stages",
            "stage_status",
            "subject_object_relation",
            "target_relative",
            "target_contract_status",
            "target_presence",
            "target_strength",
            "target_general_modifier",
        }
    ),
    "money": frozenset(
        {
            "wealth_presence",
            "wealth_stage_strength",
            "wealth_void_status",
            "wealth_general_modifier",
        }
    ),
}
_DALIUREN_REQUESTED_TO_CANONICAL = {
    "outcome": "outcome",
    "timing": "timing",
    "state": "state",
    "current_state": "state",
    "location": "location",
    "location_direction": "location",
    "relationship": "relationship",
    "work": "work",
    "career": "work",
    "money": "money",
}
_DALIUREN_EARTH_PLATE_ORDER = DALIUREN_LESSON_UPPERS


class DaliurenDimensionFact(ContractModel):
    canonical_dimension: str = Field(min_length=1)
    requested_dimension: str = Field(min_length=1)
    rule_evidence: DaliurenRuleEvidence | None = None
    status: Literal["calculated_facts_not_verdict"]
    source_rule_ids: tuple[Annotated[str, Field(min_length=1)], ...]
    initial_final_relation: DaliurenRelationFact | None = Field(
        default=None,
    )
    subject_object_relation: DaliurenRelationFact | None = Field(
        default=None,
    )
    stage_flow: tuple[DaliurenStageFlowEntry, ...] | None = Field(
        default=None,
    )
    transmissions_to_day: tuple[DaliurenTransmissionToDayEntry, ...] | None = Field(
        default=None,
    )
    six_relative_stages: tuple[DaliurenSixRelativeStage, ...] | None = Field(
        default=None,
    )
    stage_status: tuple[DaliurenStageStatusEntry, ...] | None = Field(
        default=None,
    )
    stage_branch_directions: tuple[DaliurenStageBranchDirection, ...] | None = Field(
        default=None,
    )
    general_landing_correspondences: tuple[DaliurenGeneralLanding, ...] | None = Field(
        default=None,
    )
    candidate_branch: DaliurenCandidateBranch | None = Field(
        default=None,
    )
    candidate_date: DaliurenTimingCandidate | None = Field(
        default=None,
    )
    relative_speed: str | None = Field(
        default=None,
        min_length=1,
    )
    target_contract_status: str | None = Field(
        default=None,
        min_length=1,
    )
    target_presence: bool | None = Field(
        default=None,
        strict=True,
    )
    target_relative: str | None = Field(
        default=None,
        min_length=1,
    )
    target_general_modifier: tuple[DaliurenGeneralModifierEntry, ...] | None = Field(
        default=None,
    )
    target_strength: tuple[DaliurenTargetStrengthEntry, ...] | None = Field(
        default=None,
    )
    wealth_presence: bool | None = Field(
        default=None,
        strict=True,
    )
    wealth_general_modifier: tuple[DaliurenGeneralModifierEntry, ...] | None = Field(
        default=None,
    )
    wealth_stage_strength: tuple[DaliurenWealthStageStrengthEntry, ...] | None = Field(
        default=None,
    )
    wealth_void_status: tuple[DaliurenWealthVoidStatusEntry, ...] | None = Field(
        default=None,
    )

    @model_validator(mode="before")
    @classmethod
    def _uses_exact_runtime_canonical_field_set(cls, value: object) -> object:
        """Reject omitted or cross-dimension fields in Runtime v1 rows."""

        if not isinstance(value, Mapping):
            return value
        requested = value.get("requested_dimension")
        canonical = value.get("canonical_dimension")
        if not isinstance(requested, str) or not isinstance(canonical, str):
            return value
        expected_canonical = _DALIUREN_REQUESTED_TO_CANONICAL.get(requested)
        if expected_canonical != canonical:
            raise ValueError(
                "canonical_dimension must match requested_dimension in Runtime v1"
            )
        expected_fields = _DALIUREN_DIMENSION_ENVELOPE_FIELDS | (
            _DALIUREN_CANONICAL_DIMENSION_FIELDS[canonical]
        )
        present = set(value)
        if present != expected_fields and present != expected_fields - {"rule_evidence"}:
            raise ValueError(
                f"{canonical} dimensions must use the complete Runtime v1 field set"
            )
        nullable_fields = {"target_relative"} if canonical == "work" else set()
        if canonical in {"work", "money"}:
            null_fields = sorted(
                field
                for field in _DALIUREN_CANONICAL_DIMENSION_FIELDS[canonical]
                if field not in nullable_fields and value[field] is None
            )
            if null_fields:
                raise ValueError(
                    f"{canonical} dimensions require non-null Runtime v1 fields: "
                    + ", ".join(null_fields)
                )
        return value

    @model_serializer(mode="wrap")
    def _serialize_only_runtime_fields(
        self,
        handler: SerializerFunctionWrapHandler,
    ) -> dict[str, object]:
        """Keep explicit Runtime nulls while omitting fields absent for this dimension."""

        serialized = handler(self)
        return {
            key: value
            for key, value in serialized.items()
            if key in self.model_fields_set or value is not None
        }


_DALIUREN_REQUESTED_DIMENSIONS = frozenset(_DALIUREN_REQUESTED_TO_CANONICAL)


class DaliurenCoreFacts(ContractModel):
    """Runtime-owned six-ren plate and rule-trace facts; no event verdicts."""

    day_hour: DaliurenDayHour | None = None
    dimension_facts: dict[str, DaliurenDimensionFact] | None = None
    earth_plate: tuple[str, ...] | None = Field(
        default=None,
        min_length=12,
        max_length=12,
    )
    heaven_plate: tuple[DaliurenHeavenPlateCell, ...] | None = Field(
        default=None,
        min_length=12,
        max_length=12,
    )
    heavenly_generals: tuple[DaliurenGeneralCell, ...] | None = Field(
        default=None,
        min_length=12,
        max_length=12,
    )
    lesson_method: DaliurenLessonMethod | None = None
    month_general: DaliurenMonthGeneral | None = None
    noble_person: DaliurenNoblePerson | None = None
    plate_offset: int | None = Field(default=None, ge=0, le=11, strict=True)
    structural_patterns: tuple[Annotated[str, Field(min_length=1)], ...] | None = None
    source_conditioned_patterns: tuple[DaliurenSourcePattern, ...] = Field(
        default=(),
        max_length=4,
    )
    timing_candidates: tuple[DaliurenTimingCandidate, ...] | None = None
    xunkong: DaliurenXunkong | None = None

    @field_validator("structural_patterns")
    @classmethod
    def _structural_patterns_are_unique(
        cls,
        value: tuple[str, ...] | None,
    ) -> tuple[str, ...] | None:
        # Isomorphic to Schema uniqueItems, even without a source block.
        if value is not None and len(value) != len(set(value)):
            raise ValueError("structural_patterns must be unique")
        return value

    @field_validator("dimension_facts")
    @classmethod
    def _dimension_facts_use_runtime_requested_dimensions(
        cls,
        value: dict[str, DaliurenDimensionFact] | None,
    ) -> dict[str, DaliurenDimensionFact] | None:
        if value is None:
            return value
        unknown = sorted(set(value) - _DALIUREN_REQUESTED_DIMENSIONS)
        if unknown:
            raise ValueError(
                "dimension_facts contains unsupported requested dimensions: "
                + ", ".join(unknown)
            )
        mismatched = sorted(
            key
            for key, dimension in value.items()
            if dimension.requested_dimension != key
        )
        if mismatched:
            raise ValueError(
                "dimension_facts keys must match each row's requested_dimension: "
                + ", ".join(mismatched)
            )
        return value

    @field_validator("source_conditioned_patterns")
    @classmethod
    def _source_pattern_identities_are_unique(
        cls,
        value: tuple[DaliurenSourcePattern, ...],
    ) -> tuple[DaliurenSourcePattern, ...]:
        identities = tuple(pattern.rule_id for pattern in value)
        if len(identities) != len(set(identities)):
            raise ValueError("source pattern identities must be unique")
        return value

    @model_validator(mode="after")
    def _source_patterns_match_unique_structural_title(self) -> DaliurenCoreFacts:
        for source in self.source_conditioned_patterns:
            structural_index = daliuren_source_pattern_structural_index(source)
            matching = daliuren_in_range_structural_indices(
                self.structural_patterns,
                source.title,
            )
            if matching != (structural_index,):
                raise ValueError(
                    "source pattern requires a unique in-range structural match"
                )
        return self

    @model_validator(mode="after")
    def _uses_runtime_v1_plate_topology(self) -> DaliurenCoreFacts:
        """Keep the three published plate layers internally aligned."""

        if (
            self.earth_plate is None
            or self.heaven_plate is None
            or self.heavenly_generals is None
        ):
            return self
        if self.earth_plate != _DALIUREN_EARTH_PLATE_ORDER:
            raise ValueError("earth_plate must use fixed Zi-through-Hai order")
        heaven_values = tuple(cell.heaven for cell in self.heaven_plate)
        if tuple(cell.earth for cell in self.heaven_plate) != self.earth_plate:
            raise ValueError("heaven_plate earth values must align with earth_plate")
        if set(heaven_values) != set(_DALIUREN_EARTH_PLATE_ORDER):
            raise ValueError("heaven_plate must be a branch permutation")
        if any(
            general.earth != self.earth_plate[index]
            or general.heaven != heaven_values[index]
            for index, general in enumerate(self.heavenly_generals)
        ):
            raise ValueError("heavenly_generals must align with heaven_plate")
        return self


class DaliurenChartV1(ContractModel):
    schema_version: Literal["daliuren-chart/v1"] = "daliuren-chart/v1"
    subject_ref: str = Field(min_length=1)
    question: str = Field(min_length=1)
    lessons: tuple[DaliurenLesson, ...] = Field(min_length=4, max_length=4)
    transmissions: tuple[DaliurenTransmission, ...] = Field(min_length=3, max_length=3)
    core_facts: DaliurenCoreFacts | None = None
    public_labels: tuple[PublicKeyLabel, ...] = ()

    @model_validator(mode="after")
    def _incomplete_four_lessons_require_three_distinct_uppers(
        self,
    ) -> DaliurenChartV1:
        core_facts = self.core_facts
        if core_facts is None:
            return self
        if not any(
            pattern.rule_id == _DALIUREN_INCOMPLETE_FOUR_LESSONS_RULE_ID
            for pattern in core_facts.source_conditioned_patterns
        ):
            return self
        uppers = tuple(lesson.upper for lesson in self.lessons)
        if len(set(uppers)) != 3:
            raise ValueError(
                "incomplete four lessons require exactly three distinct uppers"
            )
        return self


class PhysiognomyObservation(ContractModel):
    observation_id: str = Field(min_length=1)
    region_id: str = Field(min_length=1)
    feature_id: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    display_text: str = Field(min_length=1)


class PhysiognomySourceComparison(ContractModel):
    """Public source lineage for visible observations, never a person verdict."""

    sources: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    disagreements_retained: bool = False
    disagreements: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    forced_resolution: bool = False


class PhysiognomySourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)


class PhysiognomyViewV1(ContractModel):
    schema_version: Literal["physiognomy-view/v1"] = "physiognomy-view/v1"
    subject_ref: str = Field(min_length=1)
    mode: Literal["face", "palm", "posture", "combined"]
    observations: tuple[PhysiognomyObservation, ...]
    missing_targets: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    uncertainties: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    conflicts: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    cross_capture_variations: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    source_comparison: PhysiognomySourceComparison = Field(
        default_factory=PhysiognomySourceComparison
    )
    active_source_rule_ids: tuple[str, ...] = Field(default_factory=tuple)
    source_conditioned_patterns: tuple[PhysiognomySourcePattern, ...] = ()


class RelationshipSubject(ContractModel):
    subject_ref: str = Field(min_length=1)
    profile_version_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class RelationshipSignal(ContractModel):
    dimension_id: str = Field(min_length=1)
    subject_refs: tuple[str, str]
    signal_id: str = Field(min_length=1)
    display_text: str = Field(min_length=1)
    fact_refs: tuple[str, ...]


class RelationshipBase(ContractModel):
    subjects: tuple[RelationshipSubject, RelationshipSubject]
    relationship_type: Literal["romantic", "married", "parent_child", "business", "work", "friend"]
    signals: tuple[RelationshipSignal, ...]

    @model_validator(mode="after")
    def _subjects_must_be_distinct(self) -> RelationshipBase:
        if self.subjects[0].profile_version_id == self.subjects[1].profile_version_id:
            raise ValueError("relationship subjects must use distinct profile versions")
        return self


class BaziRelationshipV1(RelationshipBase):
    schema_version: Literal["bazi-relationship/v1"] = "bazi-relationship/v1"


class ZiweiRelationshipV1(RelationshipBase):
    schema_version: Literal["ziwei-relationship/v1"] = "ziwei-relationship/v1"


class QizhengRelationshipV1(RelationshipBase):
    schema_version: Literal["qizheng-relationship/v1"] = "qizheng-relationship/v1"


class ArtSignal(ContractModel):
    art_id: Literal["bazi", "ziwei", "qizheng", "liuyao", "qimen", "daliuren"]
    subject_refs: tuple[str, ...]
    signal_id: str = Field(min_length=1)
    display_text: str = Field(min_length=1)
    fact_refs: tuple[str, ...]


class DimensionSynthesis(ContractModel):
    dimension_id: str = Field(min_length=1)
    signals: tuple[ArtSignal, ...]
    convergence: tuple[str, ...]
    disagreements: tuple[str, ...]
    missing_art_ids: tuple[str, ...]


class HecanViewV1(ContractModel):
    schema_version: Literal["hecan-view/v1"] = "hecan-view/v1"
    subject_ref: str = Field(min_length=1)
    selected_art_ids: tuple[Literal["bazi", "ziwei", "qizheng"], ...] = Field(
        min_length=2, max_length=3
    )
    dimensions: tuple[DimensionSynthesis, ...] = Field(min_length=1)

    @field_validator("selected_art_ids")
    @classmethod
    def _selected_arts_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("selected arts must be unique")
        return value


class WenshiViewV1(ContractModel):
    schema_version: Literal["wenshi-view/v1"] = "wenshi-view/v1"
    subject_ref: str = Field(min_length=1)
    question: str = Field(min_length=1)
    selected_art_ids: tuple[Literal["liuyao"], Literal["qimen"], Literal["daliuren"]]
    dimensions: tuple[DimensionSynthesis, ...] = Field(min_length=1)


class CanwenViewV1(ContractModel):
    schema_version: Literal["canwen-view/v1"] = "canwen-view/v1"
    subject_ref: str = Field(min_length=1)
    question: str = Field(min_length=1)
    selected_art_ids: tuple[Literal["bazi", "ziwei", "qizheng"], ...] = Field(
        min_length=2, max_length=3
    )
    dimensions: tuple[DimensionSynthesis, ...] = Field(min_length=1)

    @field_validator("selected_art_ids")
    @classmethod
    def _selected_arts_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("selected arts must be unique")
        return value


BaziCalendarNormalization.model_rebuild()
BaziCoreFacts.model_rebuild()
BaziChartV1.model_rebuild()


ViewModel = Annotated[
    BaziChartV1
    | ChartSimilarityViewV1
    | TimeCheckViewV1
    | FiveElementsFactsViewV1
    | LifeKlineSeriesV1
    | FortuneFactsViewV1
    | ZiweiChartV1
    | QizhengChartV1
    | LiuyaoChartV1
    | MeihuaChartV1
    | LumingNayinChartV1
    | RhythmFactsViewV1
    | TaiyiChartV1
    | SelectionChartV1
    | FengshuiViewV1
    | QimenChartV1
    | DaliurenChartV1
    | PhysiognomyViewV1
    | BaziRelationshipV1
    | ZiweiRelationshipV1
    | QizhengRelationshipV1
    | HecanViewV1
    | WenshiViewV1
    | CanwenViewV1,
    Field(discriminator="schema_version"),
]

VIEW_MODEL_TYPES: dict[str, type[ContractModel]] = {
    "bazi-chart/v1": BaziChartV1,
    "chart-similarity-view/v1": ChartSimilarityViewV1,
    "time-check-view/v1": TimeCheckViewV1,
    "five-elements-facts-view/v1": FiveElementsFactsViewV1,
    "life-kline-series/v1": LifeKlineSeriesV1,
    "fortune-facts-view/v1": FortuneFactsViewV1,
    "ziwei-chart/v1": ZiweiChartV1,
    "qizheng-chart/v1": QizhengChartV1,
    "liuyao-chart/v1": LiuyaoChartV1,
    "meihua-chart/v1": MeihuaChartV1,
    "luming-nayin-chart/v1": LumingNayinChartV1,
    "rhythm-facts-view/v1": RhythmFactsViewV1,
    "taiyi-chart/v1": TaiyiChartV1,
    "selection-chart/v1": SelectionChartV1,
    "fengshui-view/v1": FengshuiViewV1,
    "qimen-chart/v1": QimenChartV1,
    "daliuren-chart/v1": DaliurenChartV1,
    "physiognomy-view/v1": PhysiognomyViewV1,
    "bazi-relationship/v1": BaziRelationshipV1,
    "ziwei-relationship/v1": ZiweiRelationshipV1,
    "qizheng-relationship/v1": QizhengRelationshipV1,
    "hecan-view/v1": HecanViewV1,
    "wenshi-view/v1": WenshiViewV1,
    "canwen-view/v1": CanwenViewV1,
}


def parse_view_model(payload: object) -> ContractModel:
    if not isinstance(payload, dict):
        raise TypeError("view model payload must be an object")
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or schema_version not in VIEW_MODEL_TYPES:
        raise ValueError(f"unsupported view model schema_version: {schema_version!r}")
    return VIEW_MODEL_TYPES[schema_version].model_validate(payload)
