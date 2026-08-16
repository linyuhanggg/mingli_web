from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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


class BaziStrengthEvidence(ContractModel):
    """Runtime evidence for strength, without a categorical strong/weak verdict."""

    status: Literal["evidence_only"]
    hard_verdict: None = None
    day_element: Literal["wood", "fire", "earth", "metal", "water"]
    month_command_element: Literal["wood", "fire", "earth", "metal", "water"]
    same_element_occurrences: int = Field(ge=0)
    resource_element: Literal["wood", "fire", "earth", "metal", "water"]
    resource_occurrences: int = Field(ge=0)
    all_element_occurrences: tuple[BaziElementCount, ...] = Field(min_length=1)
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
    calendar_normalization: dict[str, object] | None = None
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


class TimeCheckCandidateEvidenceV1(ContractModel):
    """Bounded Runtime evidence attached to one time-check candidate."""

    candidate_id: str = Field(min_length=1)
    hour_branch: str = Field(min_length=1)
    eligible: bool
    evidence_score: int
    matched_event_ids: tuple[str, ...]
    elimination_reasons: tuple[str, ...]
    event_evidence: tuple[dict[str, object], ...]
    rank: int = Field(ge=1, le=12)


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
    limitations: tuple[str, ...] = Field(min_length=1)


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


class QizhengMingShen(ContractModel):
    ming_degree: float = Field(ge=0, lt=360)
    shen_degree: float = Field(ge=0, lt=360)
    longitude_degrees: float = Field(ge=0, lt=360)
    latitude_degrees: float | None = None
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
    ephemeris: dict[str, object] | None = None
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
    useful_spirit_selection: dict[str, object] | None = None
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


class MeihuaRelationCandidate(ContractModel):
    """Source-directed Meihua relation candidate, never a final verdict."""

    candidate_id: str = Field(min_length=1)
    source_plate: str = Field(min_length=1)
    position: Literal["upper", "lower"]
    relation: str = Field(min_length=1)
    relation_key: str = Field(min_length=1)
    actor: MeihuaTrigram
    body: MeihuaTrigram
    seasonal_state: str | None = Field(default=None, min_length=1)
    rule_id: str = Field(min_length=1)
    status: Literal["candidate_only"]
    hard_verdict: None = None
    verification_status: Literal["pending_verification"]
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    source_dependency_id: str = Field(min_length=1)


class MeihuaInterpretiveCandidates(ContractModel):
    """Bounded classical relation candidates for later question adjudication."""

    schema_version: Literal["mingli-meihua-interpretive-candidates-v1"]
    status: Literal["candidate_only"]
    hard_verdict: None = None
    verification_status: Literal["pending_verification"]
    relation_candidates: tuple[MeihuaRelationCandidate, ...] = Field(min_length=1)
    requires_classical_adjudication: bool
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


class LumingNayinSourcePattern(ContractModel):
    rule_id: str = Field(min_length=1)
    local_rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_pack: str = Field(min_length=1)
    source_anchor: str = Field(min_length=1)
    status: Literal["predicate_matched_not_verdict"]
    fact_paths: tuple[str, ...] = Field(min_length=1)
    predicate_audit: tuple[str, ...] = Field(min_length=1)


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


class TaiyiBoardPredicate(ContractModel):
    predicate_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    fact_paths: tuple[str, ...]
    source_anchor: str = Field(min_length=1)
    source_dependency_id: str = Field(min_length=1)
    status: str = Field(min_length=1)


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


class QimenNamedPattern(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: str = Field(min_length=1)
    palace: int = Field(ge=1, le=9)


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


class DaliurenLesson(ContractModel):
    lesson_id: str = Field(min_length=1)
    upper: str = Field(min_length=1)
    lower: str = Field(min_length=1)


class DaliurenTransmission(ContractModel):
    stage: Literal["initial", "middle", "final"]
    branch: str = Field(min_length=1)
    general: str = Field(min_length=1)


class DaliurenCoreFacts(ContractModel):
    """Runtime-owned six-ren plate and rule-trace facts; no event verdicts."""

    day_hour: dict[str, object] | None = None
    dimension_facts: dict[str, object] | None = None
    earth_plate: tuple[str, ...] | None = None
    heaven_plate: tuple[dict[str, object], ...] | None = None
    heavenly_generals: tuple[dict[str, object], ...] | None = None
    lesson_method: dict[str, object] | None = None
    month_general: dict[str, object] | None = None
    noble_person: dict[str, object] | None = None
    plate_offset: int | None = None
    structural_patterns: tuple[str, ...] | None = None
    transmission_method: dict[str, object] | None = None
    timing_candidates: tuple[dict[str, object], ...] | None = None
    xunkong: dict[str, object] | None = None


class DaliurenChartV1(ContractModel):
    schema_version: Literal["daliuren-chart/v1"] = "daliuren-chart/v1"
    subject_ref: str = Field(min_length=1)
    question: str = Field(min_length=1)
    lessons: tuple[DaliurenLesson, ...] = Field(min_length=4, max_length=4)
    transmissions: tuple[DaliurenTransmission, ...] = Field(min_length=3, max_length=3)
    core_facts: DaliurenCoreFacts | None = None


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


ViewModel = Annotated[
    BaziChartV1
    | ChartSimilarityViewV1
    | TimeCheckViewV1
    | FiveElementsFactsViewV1
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
