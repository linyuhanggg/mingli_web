export const VIEW_MODEL_VERSIONS = [
  "bazi-chart/v1",
  "bazi-relationship/v1",
  "canwen-view/v1",
  "chart-similarity-view/v1",
  "daliuren-chart/v1",
  "fengshui-view/v1",
  "five-elements-facts-view/v1",
  "fortune-facts-view/v1",
  "hecan-view/v1",
  "liuyao-chart/v1",
  "luming-nayin-chart/v1",
  "rhythm-facts-view/v1",
  "meihua-chart/v1",
  "physiognomy-view/v1",
  "qimen-chart/v1",
  "qizheng-chart/v1",
  "qizheng-relationship/v1",
  "selection-chart/v1",
  "taiyi-chart/v1",
  "time-check-view/v1",
  "wenshi-view/v1",
  "ziwei-chart/v1",
  "ziwei-relationship/v1",
] as const;

export type ViewModelVersion = (typeof VIEW_MODEL_VERSIONS)[number];

export type TimeLayer = {
  readonly layer_id: string;
  readonly label: string;
  readonly available: boolean;
  readonly unavailable_reason: string | null;
};

export type BaziInterpretiveCandidates = {
  readonly strength: {
    readonly status: "evidence_only";
    readonly hard_verdict: null;
    readonly day_element: "wood" | "fire" | "earth" | "metal" | "water";
    readonly month_command_element: "wood" | "fire" | "earth" | "metal" | "water";
    readonly seasonal_state: "旺" | "相" | "休" | "囚" | "死";
    readonly seasonal_state_source_rule_id: string;
    readonly same_element_occurrences: number;
    readonly resource_element: "wood" | "fire" | "earth" | "metal" | "water";
    readonly resource_occurrences: number;
    readonly all_element_occurrences: ReadonlyArray<{
      readonly element: "wood" | "fire" | "earth" | "metal" | "water";
      readonly value: number;
    }>;
    readonly month_order_adjudication: {
      readonly status: "adjudicated_month_order_state";
      readonly decision_scope: "bazi_month_order_seasonal_state";
      readonly day_master_element: "wood" | "fire" | "earth" | "metal" | "water";
      readonly month_command_element: "wood" | "fire" | "earth" | "metal" | "water";
      readonly seasonal_state: "旺" | "相" | "休" | "囚" | "死";
      readonly whole_chart_strength_verdict: null;
      readonly useful_god_verdict: null;
      readonly source_ref: {
        readonly pack: "bazi/sanming-tonghui";
        readonly rule_id: "R-02-04";
        readonly source_anchor: string;
        readonly verification_status: "verified";
        readonly binding_digest: string;
      };
      readonly unresolved_checks: ReadonlyArray<string>;
    };
    readonly boundary: string;
  };
  readonly structure: {
    readonly status: "candidate_only";
    readonly hard_verdict: null;
    readonly month_main_qi: string;
    readonly month_main_qi_ten_god: string;
    readonly main_qi_visible: boolean;
    readonly visible_positions: ReadonlyArray<string>;
    readonly boundary: string;
  };
  readonly following_and_transformation: {
    readonly status: "requires_classical_adjudication";
    readonly hard_verdict: null;
    readonly stem_combination_candidates: ReadonlyArray<{
      readonly with_position: string;
      readonly stems: ReadonlyArray<string>;
      readonly candidate_element: "wood" | "fire" | "earth" | "metal" | "water";
      readonly status: string;
    }>;
    readonly branch_formation_candidates: ReadonlyArray<{
      readonly relation_type: string;
      readonly positions: ReadonlyArray<string>;
      readonly branches: ReadonlyArray<string>;
    }>;
    readonly boundary: string;
  };
  readonly salience_signals: ReadonlyArray<{
    readonly signal_id: string;
    readonly status: "mechanical_candidate";
    readonly hard_verdict: null;
    readonly basis: Readonly<Record<string, unknown>>;
    readonly boundary: string;
  }>;
  readonly reasoning_tools?: Readonly<Record<string, {
    readonly schema_version?: string;
    readonly tool_id?: string;
    readonly tool_kind?: string;
    readonly confidence_bucket?: "low" | "medium" | "high";
    readonly confidence_ceiling?: "low" | "medium" | "high";
    readonly visibility_class?: "auto_injected" | "on_demand" | "translated" | "trigger_only";
    readonly fact_refs?: ReadonlyArray<Readonly<Record<string, unknown>>>;
    readonly source_refs?: ReadonlyArray<Readonly<Record<string, string>>>;
    readonly output: Readonly<Record<string, unknown>>;
    readonly caveats?: ReadonlyArray<string>;
    readonly tool_digest?: string;
  }>> | null;
};

export type BaziTemporalLayer = {
  readonly granularity: "month" | "day";
  readonly period: string;
  readonly year: number;
  readonly month: number | null;
  readonly date: string | null;
  readonly ganzhi_segments: ReadonlyArray<Readonly<Record<string, unknown>>>;
  readonly active_transits: Readonly<Record<string, unknown>> | null;
  readonly structural_changes: Readonly<Record<string, unknown>>;
  readonly seasonal_tiaohou_delta: Readonly<Record<string, unknown>>;
  readonly shensha_auxiliary: Readonly<Record<string, unknown>>;
  readonly active_luck_cycle: Readonly<Record<string, unknown>>;
  readonly calendar_normalization: Readonly<Record<string, unknown>>;
  readonly representative_instant: string | null;
  readonly rule_trace: ReadonlyArray<Readonly<Record<string, unknown>>>;
};

export type BaziCalendarNormalization = {
  readonly status: string;
  readonly algorithm_version: string;
  readonly effective_datetime?: string | null;
  readonly day_boundary?: {
    readonly correction_crossed_date: boolean;
    readonly zi_policy_advanced_day_pillar: boolean;
  } | null;
  readonly changed_pillars?: ReadonlyArray<"year" | "month" | "day" | "hour"> | null;
  readonly solar_terms?: {
    readonly previous: {
      readonly name: string;
      readonly index: number;
      readonly is_month_boundary_jie: boolean;
      readonly datetime: string;
      readonly instant_utc: string;
    } | null;
    readonly next: {
      readonly name: string;
      readonly index: number;
      readonly is_month_boundary_jie: boolean;
      readonly datetime: string;
      readonly instant_utc: string;
    } | null;
    readonly month_switch_policy: string;
  } | null;
  readonly time_basis: {
    readonly policy: string;
    readonly standard_meridian_degrees: number | null;
    readonly longitude_correction_seconds: number | null;
    readonly equation_of_time_seconds: number | null;
    readonly total_correction_seconds: number | null;
    readonly algorithm: {
      readonly id: string | null;
      readonly version: string | null;
      readonly source: string | null;
      readonly uncertainty_seconds: number | null;
    };
    readonly boundary: {
      readonly distance_seconds: number | null;
      readonly correction_changes_hour_branch: boolean | null;
      readonly within_uncertainty: boolean | null;
    };
  };
  readonly true_solar_time: {
    readonly status: string;
    readonly policy: string | null;
    readonly longitude_correction_seconds: number | null;
    readonly equation_of_time_seconds: number | null;
    readonly total_correction_seconds: number | null;
  };
  readonly calendar_convention: {
    readonly id: string | null;
    readonly version: string | null;
    readonly year_boundary: string | null;
    readonly month_boundary: string | null;
    readonly day_rollover: string | null;
    readonly hour_basis: string | null;
    readonly zi_hour_policy: string | null;
  };
};

export type BaziSourcePattern = {
  readonly rule_id: string;
  readonly local_rule_id: string;
  readonly title: string;
  readonly source_pack: string;
  readonly source_anchor: string;
  readonly status: "predicate_matched_not_verdict";
  readonly fact_paths: ReadonlyArray<string>;
  readonly predicate_audit: ReadonlyArray<string>;
  readonly evidence_ref?: string | null;
};

export type BaziCoreFacts = {
  readonly day_master: {
    readonly stem: string;
    readonly element: "wood" | "fire" | "earth" | "metal" | "water";
    readonly polarity: "阳" | "阴";
  } | null;
  readonly hidden_stems: ReadonlyArray<{
    readonly position: "year" | "month" | "day" | "hour";
    readonly branch: string;
    readonly stems: ReadonlyArray<string>;
  }> | null;
  readonly ten_gods: {
    readonly heavenly_stems: ReadonlyArray<{
      readonly position: "year" | "month" | "day" | "hour";
      readonly layer: "heavenly_stem" | "hidden_stem";
      readonly stem: string;
      readonly ten_god: string;
    }>;
    readonly hidden_stems: ReadonlyArray<{
      readonly position: "year" | "month" | "day" | "hour";
      readonly layer: "heavenly_stem" | "hidden_stem";
      readonly stem: string;
      readonly ten_god: string;
    }>;
  } | null;
  readonly nayin: ReadonlyArray<{
    readonly position: "year" | "month" | "day" | "hour";
    readonly name: string;
  }> | null;
  readonly twelve_growth_stages?: ReadonlyArray<{
    readonly position: "year" | "month" | "day" | "hour";
    readonly stem: string;
    readonly branch: string;
    readonly stage: string;
    readonly stage_index: number;
    readonly direction: "forward" | "reverse";
    readonly source_dependency_id: string;
    readonly boundary: string;
  }> | null;
  readonly xunkong?: {
    readonly day_pillar: string;
    readonly xun: string;
    readonly branches: readonly [string, string];
    readonly source_dependency_id: string;
    readonly boundary: string;
  } | null;
  readonly san_yuan?: {
    readonly tai_yuan: string;
    readonly ming_gong: string;
    readonly shen_gong: string;
    readonly source: string;
    readonly source_dependency_id: string;
    readonly boundary: string;
  } | null;
  readonly month_command: {
    readonly branch: string;
    readonly label: string;
    readonly main_qi: string;
    readonly main_qi_element: "wood" | "fire" | "earth" | "metal" | "water";
  } | null;
  readonly seasonal_profile: {
    readonly season: string;
    readonly month_qi: string;
    readonly temperature: string;
    readonly moisture: string;
  } | null;
  readonly tiaohou_markers: {
    readonly temperature: string;
    readonly moisture: string;
    readonly markers: ReadonlyArray<string>;
    readonly day_stem: string | null;
    readonly month_branch: string | null;
    readonly scope: string;
  } | null;
  readonly element_inventory: {
    readonly visible_stem_branch_counts: ReadonlyArray<{
      readonly element: "wood" | "fire" | "earth" | "metal" | "water";
      readonly value: number;
    }>;
    readonly hidden_stem_occurrence_counts: ReadonlyArray<{
      readonly element: "wood" | "fire" | "earth" | "metal" | "water";
      readonly value: number;
    }>;
    readonly scope: string;
  } | null;
  readonly interpretive_candidates: BaziInterpretiveCandidates | null;
  readonly source_conditioned_patterns: ReadonlyArray<BaziSourcePattern>;
  readonly branch_relations: ReadonlyArray<{
    readonly relation_type: string;
    readonly positions: ReadonlyArray<string>;
    readonly branches: ReadonlyArray<string>;
  }> | null;
  readonly shensha_auxiliary: {
    readonly status: string;
    readonly temporal_scope: string;
    readonly precedence: string;
    readonly evaluated_rules: ReadonlyArray<{
      readonly rule_id: string;
      readonly name: string;
      readonly anchor_position: string;
      readonly anchor_branch: string;
      readonly target_branch: string;
      readonly matched: boolean;
    }>;
    readonly calculated_items: ReadonlyArray<{
      readonly item_id: string;
      readonly name: string;
      readonly target_branch: string;
      readonly anchor_positions: ReadonlyArray<string>;
      readonly anchor_branches: ReadonlyArray<string>;
      readonly matched_positions: ReadonlyArray<string>;
      readonly status: string;
    }>;
    readonly cannot_override: ReadonlyArray<string>;
    readonly boundary: string;
  } | null;
  readonly luck_cycles: {
    readonly status: "calculated" | "sequence_only" | "not_calculated_missing_gender";
    readonly direction: "forward" | "reverse" | null;
    readonly direction_rule: string | null;
    readonly start_age_rule: string | null;
    readonly boundary_term: {
      readonly name: string;
      readonly index: number;
      readonly is_month_boundary_jie: boolean;
      readonly datetime: string;
      readonly instant_utc: string;
    } | null;
    readonly interval_days: number | null;
    readonly start_age_years: number | null;
    readonly approximate_start_datetime: string | null;
    readonly cycles: ReadonlyArray<{
      readonly sequence: number;
      readonly pillar: string;
      readonly start_age_years: number | null;
      readonly end_age_years: number | null;
    }>; 
    readonly unavailable: ReadonlyArray<string>;
  } | null;
  readonly calendar_normalization: BaziCalendarNormalization | null;
  readonly year_layers?: ReadonlyArray<{
    readonly year: number;
    readonly ganzhi: string;
    readonly stem_ten_god: string;
    readonly branch_hidden_ten_gods: ReadonlyArray<{
      readonly stem: string;
      readonly ten_god: string;
    }>;
    readonly branch_relations: ReadonlyArray<{
      readonly relation_type: string;
      readonly natal_position: string;
      readonly natal_branch: string;
      readonly transit_branch: string;
    }>;
    readonly structural_changes: {
      readonly status: "mechanical_candidates_only";
      readonly transit_pillar: string;
      readonly stem_ten_god: string;
      readonly branch_relations: ReadonlyArray<{
        readonly relation_type: string;
        readonly natal_position: string;
        readonly natal_branch: string;
        readonly transit_branch: string;
      }>;
      readonly hard_verdict: null;
    };
    readonly shensha_auxiliary: Readonly<Record<string, unknown>>;
    readonly active_luck_cycle: Readonly<Record<string, unknown>>;
    readonly seasonal_effect: Readonly<Record<string, unknown>>;
    readonly tiaohou_effect: Readonly<Record<string, unknown>>;
    readonly seasonal_tiaohou_delta: Readonly<Record<string, unknown>>;
    readonly calendar_normalization: Readonly<Record<string, unknown>>;
    readonly rule_trace: ReadonlyArray<{
      readonly rule_id: string;
      readonly source_dependency_id: string;
      readonly operation: string;
    }>;
    readonly ganzhi_segments: ReadonlyArray<{
      readonly start_inclusive: string;
      readonly end_exclusive: string;
      readonly ganzhi: string;
      readonly stem_ten_god: string;
      readonly branch_hidden_ten_gods: ReadonlyArray<{
        readonly stem: string;
        readonly ten_god: string;
      }>;
      readonly branch_relations: ReadonlyArray<{
        readonly relation_type: string;
        readonly natal_position: string;
        readonly natal_branch: string;
        readonly transit_branch: string;
      }>;
      readonly seasonal_effect: Readonly<Record<string, unknown>>;
      readonly tiaohou_effect: Readonly<Record<string, unknown>>;
      readonly structural_changes: {
        readonly status: "mechanical_candidates_only";
        readonly transit_pillar: string;
        readonly stem_ten_god: string;
        readonly branch_relations: ReadonlyArray<{
          readonly relation_type: string;
          readonly natal_position: string;
          readonly natal_branch: string;
          readonly transit_branch: string;
        }>;
        readonly hard_verdict: null;
      };
      readonly seasonal_tiaohou_delta: Readonly<Record<string, unknown>>;
      readonly shensha_auxiliary: Readonly<Record<string, unknown>>;
    }>;
  }> | null;
  readonly month_layers?: ReadonlyArray<BaziTemporalLayer> | null;
  readonly day_layers?: ReadonlyArray<BaziTemporalLayer> | null;
};

export type BaziChartViewModel = {
  readonly schema_version: "bazi-chart/v1";
  readonly subject_ref: string;
  readonly pillars: ReadonlyArray<{
    readonly position: "year" | "month" | "day" | "hour";
    readonly stem: string;
    readonly branch: string;
  }>;
  readonly element_balance: ReadonlyArray<{
    readonly element: "wood" | "fire" | "earth" | "metal" | "water";
    readonly value: number;
    readonly display_text: string;
  }>;
  readonly time_layers: ReadonlyArray<TimeLayer>;
  readonly core_facts?: BaziCoreFacts | null;
};

export type ChartSimilarityPillarPosition = "year" | "month" | "day" | "hour";

export type ChartSimilarityPillar = {
  readonly position: ChartSimilarityPillarPosition;
  readonly stem: string;
  readonly branch: string;
};

export type ChartSimilarityPillarComparison = {
  readonly position: ChartSimilarityPillarPosition;
  readonly left: ChartSimilarityPillar;
  readonly right: ChartSimilarityPillar;
  readonly exact_match: boolean;
};

export type ChartSimilarityViewModel = {
  readonly schema_version: "chart-similarity-view/v1";
  readonly left_subject_ref: string;
  readonly right_subject_ref: string;
  readonly basis: "bazi.four_pillars.exact";
  readonly left_fact_ref: string;
  readonly right_fact_ref: string;
  readonly comparisons: ReadonlyArray<ChartSimilarityPillarComparison>;
  readonly exact_match: boolean;
  readonly matched_positions: ReadonlyArray<ChartSimilarityPillarPosition>;
  readonly differing_positions: ReadonlyArray<ChartSimilarityPillarPosition>;
  readonly limitations: ReadonlyArray<string>;
};

export type TimeCheckViewModel = {
  readonly schema_version: "time-check-view/v1";
  readonly subject_ref: string;
  readonly candidate_count: 12;
  readonly candidates: ReadonlyArray<{
    readonly candidate_id: string;
    readonly hour_branch: string;
    readonly local_civil_datetime: string;
    readonly within_known_time_range: boolean;
    readonly bazi_chart_digest: string | null;
    readonly four_pillars: unknown;
    readonly day_master: unknown;
    readonly calendar_normalization: Readonly<Record<string, unknown>>;
  }>;
  readonly known_time_range: Readonly<Record<string, unknown>>;
  readonly time_basis_policy: string;
  readonly known_event_count: number;
  readonly event_input_status: "not_supplied" | "invalid_structured_events" | "structured_valid";
  readonly candidate_rankings: ReadonlyArray<{
    readonly candidate_id: string;
    readonly hour_branch: string;
    readonly eligible: boolean;
    readonly evidence_score: number;
    readonly matched_event_ids: ReadonlyArray<string>;
    readonly elimination_reasons: ReadonlyArray<string>;
    readonly event_evidence: ReadonlyArray<{
      readonly event_id: string;
      readonly matched: boolean;
      readonly evidence_score: number;
      readonly relations: ReadonlyArray<{
        readonly natal_position: "year" | "month" | "day" | "hour";
        readonly natal_branch: string;
        readonly event_branch: string;
        readonly relation_type: string;
      }>;
      readonly event_year_ten_god: string | null;
      readonly reasons: ReadonlyArray<string>;
    }>;
    readonly rank: number;
  }>;
  readonly event_matches: ReadonlyArray<{
    readonly event_id: string;
    readonly domain: string;
    readonly occurred_at: string;
    readonly year_pillar: string;
    readonly matched_candidate_ids: ReadonlyArray<string>;
  }>;
  readonly ranking_status: "not_ranked" | "candidate_evidence_ranked";
  readonly event_matching_status: "not_calculated" | "structured_evidence";
  readonly rectification_status?:
    | "hour_determined"
    | "no_valid_candidate"
    | "not_attempted"
    | "remaining_ambiguous"
    | null;
  readonly rectification_conclusion?: {
    readonly status:
      | "hour_determined"
      | "no_valid_candidate"
      | "not_attempted"
      | "remaining_ambiguous";
    readonly selected_candidate_id: string | null;
    readonly remaining_candidate_ids: ReadonlyArray<string>;
    readonly basis: string;
    readonly rule_ids?: ReadonlyArray<string>;
  } | null;
  readonly limitations: ReadonlyArray<string>;
};

export type FiveElementsFactsViewModel = {
  readonly schema_version: "five-elements-facts-view/v1";
  readonly subject_ref: string;
  readonly day_master: BaziCoreFacts["day_master"];
  readonly month_command: BaziCoreFacts["month_command"];
  readonly seasonal_profile: BaziCoreFacts["seasonal_profile"];
  readonly tiaohou_markers: BaziCoreFacts["tiaohou_markers"];
  readonly element_inventory: BaziCoreFacts["element_inventory"];
  readonly interpretive_candidates: BaziInterpretiveCandidates | null;
  readonly source_identity: {
    readonly day_stem: string | null;
    readonly month_branch: string | null;
    readonly source_dependency_id: string | null;
    readonly source_section_id: string | null;
    readonly source_rule_id: string | null;
  } | null;
  readonly active_source_rule_ids: ReadonlyArray<string>;
  readonly source_dependency_ids: ReadonlyArray<string>;
  readonly source_status: "exact_rule_bound" | "identity_only" | "unavailable";
  readonly source_gaps: ReadonlyArray<string>;
  readonly limitations: ReadonlyArray<string>;
};

export type ZiweiMajorLimitSegment = {
  readonly start_inclusive: string;
  readonly end_exclusive: string;
  readonly major_limit: Readonly<Record<string, unknown>>;
};

export type ZiweiCoreFacts = {
  readonly chart_convention?: Readonly<Record<string, unknown>> | null;
  readonly chinese_date?: string | null;
  readonly active_major_limit?: Readonly<Record<string, unknown>> | null;
  readonly active_major_limit_segments?: ReadonlyArray<ZiweiMajorLimitSegment>;
  readonly five_elements_class: string | null;
  readonly interpretive_candidates?: Readonly<Record<string, unknown>> | null;
  readonly source_conditioned_patterns: ReadonlyArray<SourceConditionedPattern>;
  readonly ming_shen: {
    readonly body_star: string;
    readonly ming_branch: string;
    readonly shen_branch: string;
    readonly soul_star: string;
  } | null;
  readonly major_limit_direction: {
    readonly direction: string;
    readonly gender: string;
    readonly year_polarity: string;
    readonly year_stem: string;
  } | null;
  readonly major_limit_starting_age: number | null;
  readonly major_limit_sequence: ReadonlyArray<{
    readonly palace: string;
    readonly palace_index: number;
    readonly palace_branch: string;
    readonly age_start: number;
    readonly age_end: number;
    readonly sequence: number;
    readonly heavenly_stem: string;
    readonly earthly_branch: string;
    readonly direction: string | null;
  }> | null;
  readonly major_limits: ReadonlyArray<{
    readonly palace: string;
    readonly palace_index: number;
    readonly palace_branch: string;
    readonly age_start: number;
    readonly age_end: number;
    readonly sequence: number;
    readonly heavenly_stem: string;
    readonly earthly_branch: string;
    readonly direction: string | null;
  }> | null;
  readonly transformations: ReadonlyArray<{
    readonly star: string;
    readonly transformation: string;
    readonly palace: string;
    readonly palace_branch: string;
    readonly scope: string;
  }> | null;
  readonly star_facts: ReadonlyArray<{
    readonly name: string;
    readonly star_type: string | null;
    readonly scope: string | null;
    readonly brightness: string | null;
    readonly palace: string;
    readonly palace_branch: string;
    readonly palace_index: number;
  }> | null;
  readonly annual_layers?: ReadonlyArray<{
    readonly year: number;
    readonly coverage_start: string;
    readonly coverage_end_exclusive: string;
    readonly liu_nian: Readonly<Record<string, unknown>>;
    readonly segments: ReadonlyArray<Readonly<Record<string, unknown>>>;
    readonly representative_scope: string;
  }> | null;
  readonly monthly_layers?: ReadonlyArray<{
    readonly year: number;
    readonly month: number;
    readonly liu_yue: Readonly<Record<string, unknown>>;
    readonly segments: ReadonlyArray<Readonly<Record<string, unknown>>>;
    readonly representative_scope: string;
  }> | null;
};

export type QizhengCoreFacts = {
  readonly ephemeris?: {
    readonly schema_version: string;
    readonly engine: {
      readonly name: string;
      readonly version: string;
      readonly license: string;
    };
    readonly coordinate_convention: {
      readonly frame: string;
      readonly zodiac: string;
      readonly aberration: boolean;
      readonly precession: string;
    };
  } | null;
  readonly conventions?: Readonly<Record<string, unknown>> | null;
  readonly classical_bodies: ReadonlyArray<{
    readonly body_id: string;
    readonly classical_name: string;
    readonly longitude: number;
    readonly latitude_degrees: number | null;
    readonly degree_in_zodiac_sign: number | null;
    readonly house_id: string | null;
    readonly house_degree: number | null;
    readonly motion_state: string | null;
    readonly fact_status: string;
    readonly point_kind?: string | null;
    readonly observed_body?: boolean | null;
    readonly source_dependency_id?: string | null;
    readonly trace?: Readonly<Record<string, unknown>> | null;
  }> | null;
  readonly ming_shen: {
    readonly ming_degree: number;
    readonly shen_degree: number;
    readonly separation_degrees: number;
    readonly local_apparent_sidereal_degrees: number | null;
    readonly profile: string;
    readonly fact_status: string;
  } | null;
  readonly major_limits: ReadonlyArray<{
    readonly sequence: number;
    readonly house: string;
    readonly age_start_years: number;
    readonly age_end_years: number;
    readonly start_degree: number;
    readonly end_degree: number;
    readonly status: string;
  }> | null;
  readonly source_conditioned_patterns: ReadonlyArray<SourceConditionedPattern>;
  readonly transformations: ReadonlyArray<{
    readonly sequence: number;
    readonly transformation: string;
    readonly label: string;
    readonly classical_body: string;
    readonly body: string;
    readonly year_stem: string;
    readonly status: string;
  }> | null;
  readonly annual_transformations?: ReadonlyArray<{
    readonly year: number;
    readonly year_ganzhi: string;
    readonly transformations: ReadonlyArray<{
      readonly sequence: number;
      readonly transformation: string;
      readonly label: string;
      readonly classical_body: string;
      readonly body: string;
      readonly year_stem: string;
      readonly status: string;
    }>;
    readonly calendar_digest: string;
    readonly fact_status: string;
  }> | null;
  readonly requested_limit_layers?: ReadonlyArray<{
    readonly date: string;
    readonly age_years: number;
    readonly house: string;
    readonly segment_index: number;
    readonly segment: Readonly<Record<string, unknown>>;
    readonly status: string;
  }> | null;
};

export type RelationshipSubject = {
  readonly subject_ref: string;
  readonly profile_version_id: string;
  readonly label: string;
};

export type RelationshipSignal = {
  readonly dimension_id: string;
  readonly subject_refs: ReadonlyArray<string>;
  readonly signal_id: string;
  readonly display_text: string;
  readonly fact_refs: ReadonlyArray<string>;
};

export type BaziRelationshipViewModel = {
  readonly schema_version: "bazi-relationship/v1";
  readonly subjects: readonly [RelationshipSubject, RelationshipSubject];
  readonly relationship_type:
    | "romantic"
    | "married"
    | "parent_child"
    | "business"
    | "work"
    | "friend";
  readonly signals: ReadonlyArray<RelationshipSignal>;
};

export type CrossArtSignal = {
  readonly art_id:
    | "bazi"
    | "ziwei"
    | "qizheng"
    | "liuyao"
    | "qimen"
    | "daliuren";
  readonly subject_refs: ReadonlyArray<string>;
  readonly signal_id: string;
  readonly display_text: string;
  readonly fact_refs: ReadonlyArray<string>;
};

export type NatalArtId = "bazi" | "ziwei" | "qizheng";

export type CrossArtDimension = {
  readonly dimension_id: string;
  readonly signals: ReadonlyArray<CrossArtSignal>;
  readonly convergence: ReadonlyArray<string>;
  readonly disagreements: ReadonlyArray<string>;
  readonly missing_art_ids: ReadonlyArray<string>;
};

export type CanwenViewModel = {
  readonly schema_version: "canwen-view/v1";
  readonly subject_ref: string;
  readonly question: string;
  readonly selected_art_ids: ReadonlyArray<"bazi" | "ziwei" | "qizheng">;
  readonly dimensions: ReadonlyArray<CrossArtDimension>;
};

export type DaliurenDayHour = {
  readonly day: string;
  readonly hour: string;
};

export type DaliurenMonthGeneral = {
  readonly branch: string;
  readonly name: string;
};

export type DaliurenNoblePerson = {
  readonly branch: string;
  readonly day_night_profile: string;
  readonly direction: "forward" | "reverse";
  readonly earth_position: string;
  readonly period: "day" | "night";
  readonly profile: string;
  readonly source: string;
};

export type DaliurenXunkong = {
  readonly branches: readonly [string, string];
  readonly xun: string;
};

export type DaliurenHeavenPlateCell = {
  readonly earth: string;
  readonly heaven: string;
};

export type DaliurenGeneralCell = {
  readonly earth: string;
  readonly general: string;
  readonly heaven: string;
};

export type DaliurenLessonMethod = Readonly<{
  readonly calculated_transmissions: string;
  readonly calculation_source: string;
  readonly direct_direction: string | null;
  readonly primary: string;
  readonly selected_initial: string;
  readonly source_anchor: string;
  readonly use_method: string;
}>;

export type DaliurenRuleSourceRef = {
  readonly pack: string;
  readonly rule_id: string;
  readonly quote_id?: string;
  readonly source_anchor?: string;
};

export type DaliurenRuleEvidenceEntry = Readonly<{
  readonly activation_id: string;
  readonly confidence_ceiling?: string;
  readonly dependency_group: string;
  readonly fact_paths: ReadonlyArray<string>;
  readonly observation: Readonly<Record<string, unknown>>;
  readonly polarity: string;
  readonly rule_id: string;
  readonly rule_key: string;
  readonly source_refs: ReadonlyArray<DaliurenRuleSourceRef>;
  readonly status: string;
  readonly stop_conditions?: ReadonlyArray<string>;
  readonly weight_class: string;
}> & Readonly<Record<string, unknown>>;

export type DaliurenRuleEvidence = {
  readonly catalog_schema: string;
  readonly hard_verdict: null;
  readonly matched: ReadonlyArray<DaliurenRuleEvidenceEntry>;
  readonly not_evaluated: ReadonlyArray<Readonly<Record<string, unknown>>>;
  readonly requires_school_adjudication: boolean;
  readonly scope_boundaries: ReadonlyArray<DaliurenRuleEvidenceEntry>;
  readonly status: string;
};

export type DaliurenTimingCandidate = {
  readonly id: "initial_group_upper_candidate";
  readonly role: "event_response_candidate";
  readonly anchor_earth_branch: string;
  readonly branch: string;
  readonly solar_date: string;
  readonly day_ganzhi: string;
  readonly days_after_cast: number;
  readonly source_pack: string;
  readonly source_rule: "LM-R21";
  readonly candidate_not_guarantee: true;
};

export type DaliurenTransmissionStage = "initial" | "middle" | "final";

export type DaliurenCompassDirection =
  | "north"
  | "northeast"
  | "east"
  | "southeast"
  | "south"
  | "southwest"
  | "west"
  | "northwest";

export type DaliurenCompassDirectionChinese = "正北" | "东北" | "正东" | "东南" | "正南" | "西南" | "正西" | "西北";

export type DaliurenStageBranchDirection<
  Stage extends DaliurenTransmissionStage = DaliurenTransmissionStage,
> = Readonly<{
  readonly stage: Stage;
  readonly branch: string;
  readonly direction: DaliurenCompassDirection;
  readonly direction_chinese: DaliurenCompassDirectionChinese;
  readonly declared_source_anchor: string;
  readonly source_binding_status: "unverified_source_excerpt_not_in_release";
  readonly scope: "symbolic_direction_candidate_only";
}>;

export type DaliurenLocationObservation = Readonly<{
  readonly stage_branch_directions: readonly [
    DaliurenStageBranchDirection<"initial">,
    DaliurenStageBranchDirection<"middle">,
    DaliurenStageBranchDirection<"final">,
  ];
}>;

export type DaliurenSixRelative = "兄弟" | "子孙" | "妻财" | "官鬼" | "父母";

export type DaliurenSeasonStrength = "旺" | "相" | "休" | "囚" | "死" | "unknown";

export type DaliurenHeavenlyGeneral =
  | "贵人"
  | "腾蛇"
  | "朱雀"
  | "六合"
  | "勾陈"
  | "青龙"
  | "天空"
  | "白虎"
  | "太常"
  | "玄武"
  | "太阴"
  | "天后";

export type DaliurenOutcomeRelation =
  | "subject_generates_object"
  | "subject_overcomes_object"
  | "object_overcomes_subject";

export type DaliurenDeterministicRelation =
  | DaliurenOutcomeRelation
  | "same_element"
  | "object_generates_subject";

export type DaliurenRelationFact = Readonly<{
  readonly object: string;
  readonly object_element: string;
  readonly object_value: string;
  readonly relation: DaliurenDeterministicRelation;
  readonly subject: string;
  readonly subject_element: string;
  readonly subject_value: string;
}>;

export type DaliurenStageFlowEntry = DaliurenRelationFact &
  Readonly<{
    readonly from_stage: DaliurenTransmissionStage;
    readonly to_stage: DaliurenTransmissionStage;
  }>;

export type DaliurenTransmissionToDayEntry = DaliurenRelationFact &
  Readonly<{
    readonly stage: DaliurenTransmissionStage;
  }>;

export type DaliurenSixRelativeStage = Readonly<{
  readonly branch: string;
  readonly six_relative: DaliurenSixRelative;
  readonly stage: DaliurenTransmissionStage;
}>;

export type DaliurenStageStatusEntry = Readonly<{
  readonly branch: string;
  readonly heavenly_general: string;
  readonly is_xunkong: boolean;
  readonly season_strength: DaliurenSeasonStrength;
  readonly six_relative: DaliurenSixRelative;
  readonly stage: DaliurenTransmissionStage;
}>;

export type DaliurenMiddleVoidObservation = Readonly<{
  readonly stage: "middle";
  readonly branch: string;
  readonly is_xunkong: true;
}>;

export type DaliurenOutcomeObservation =
  | Readonly<{
      readonly relation: "subject_overcomes_object" | "object_overcomes_subject";
    }>
  | Readonly<{
      readonly relations: readonly [
        "subject_generates_object" | "subject_overcomes_object",
        "subject_generates_object" | "subject_overcomes_object",
        "subject_generates_object" | "subject_overcomes_object",
      ];
    }>
  | DaliurenMiddleVoidObservation;

export type DaliurenRelationshipObservation = Readonly<{
  readonly relation: "subject_overcomes_object" | "object_overcomes_subject";
}>;

export type DaliurenRelativeSpeed = "relatively_faster" | "relatively_slower";

export type DaliurenCandidateBranch = Readonly<{
  readonly anchor_earth_branch: string;
  readonly branch: string;
  readonly source_rule: "LM-R21";
}>;

export type DaliurenTimingCandidateObservation = Readonly<{
  readonly candidate_branch: DaliurenCandidateBranch;
  readonly candidate_date: DaliurenTimingCandidate | null;
  readonly relative_speed: DaliurenRelativeSpeed | null;
}>;

export type DaliurenTimingPaceObservation = Readonly<{
  readonly relative_speed: DaliurenRelativeSpeed;
}>;

export type DaliurenTimingObservation = DaliurenTimingCandidateObservation | DaliurenTimingPaceObservation;

export type DaliurenMoneyObservation =
  | Readonly<{
      readonly wealth_presence: true;
      readonly wealth_stages: ReadonlyArray<DaliurenWealthStageStrengthEntry>;
    }>
  | Readonly<{
      readonly wealth_void_rows: ReadonlyArray<
        Readonly<{
          readonly stage: DaliurenTransmissionStage;
          readonly branch: string;
          readonly six_relative: "妻财";
          readonly is_xunkong: true;
        }>
      >;
    }>
  | Readonly<{
      readonly wealth_presence: false;
    }>
  | DaliurenMiddleVoidObservation;

export type DaliurenGeneralLandingCorrespondence = Readonly<{
  readonly stage: DaliurenTransmissionStage;
  readonly heavenly_general: string;
  readonly landing_branch: string;
  readonly source_pack: "san-shi/liuren-miben";
  readonly source_rule: "LM-R01";
  readonly role: "imagery_correspondence_not_observed_activity";
  readonly status: "source_correspondence_matched";
  readonly source_text: string;
  readonly source_anchor: string;
}>;

export type DaliurenGeneralLandingUnavailableCorrespondence = Readonly<{
  readonly stage: DaliurenTransmissionStage;
  readonly heavenly_general: string;
  readonly landing_branch: string;
  readonly source_pack: "san-shi/liuren-miben";
  readonly source_rule: "LM-R01";
  readonly role: "imagery_correspondence_not_observed_activity";
  readonly status: "no_exact_source_correspondence";
}>;

export type DaliurenWealthStageStrengthEntry = Readonly<{
  readonly stage: DaliurenTransmissionStage;
  readonly branch: string;
  readonly six_relative: "妻财";
  readonly season_strength: DaliurenSeasonStrength;
}>;

export type DaliurenWealthVoidStatusEntry = Readonly<{
  readonly stage: DaliurenTransmissionStage;
  readonly branch: string;
  readonly six_relative: "妻财";
  readonly is_xunkong: boolean;
}>;

export type DaliurenWealthGeneralModifier =
  | (DaliurenGeneralLandingCorrespondence &
      Readonly<{
        readonly heavenly_general: DaliurenHeavenlyGeneral;
        readonly six_relative: "妻财";
      }>)
  | (DaliurenGeneralLandingUnavailableCorrespondence &
      Readonly<{
        readonly heavenly_general: DaliurenHeavenlyGeneral;
        readonly six_relative: "妻财";
      }>);

export type DaliurenStateObservation = Readonly<{
  readonly matched_count: number;
  readonly stages: ReadonlyArray<DaliurenTransmissionStage>;
  readonly correspondences: ReadonlyArray<DaliurenGeneralLandingCorrespondence>;
}>;

export type DaliurenWorkPresentObservation = Readonly<{
  readonly target_relative: DaliurenSixRelative;
  readonly target_strength: ReadonlyArray<
    Readonly<{
      readonly stage: DaliurenTransmissionStage;
      readonly branch: string;
      readonly six_relative: DaliurenSixRelative;
      readonly season_strength: DaliurenSeasonStrength;
      readonly is_xunkong: boolean;
    }>
  >;
  readonly target_general_modifier: ReadonlyArray<
    (DaliurenGeneralLandingCorrespondence | DaliurenGeneralLandingUnavailableCorrespondence) &
      Readonly<{
        readonly six_relative: DaliurenSixRelative;
      }>
  >;
}>;

export type DaliurenWorkAbsentObservation = Readonly<{
  readonly target_relative: DaliurenSixRelative;
  readonly target_presence: false;
  readonly target_contract_status: "bound";
}>;

export type DaliurenWorkObservation = DaliurenWorkPresentObservation | DaliurenWorkAbsentObservation;

export type DaliurenDimensionObservationMap = Readonly<{
  readonly outcome: DaliurenOutcomeObservation;
  readonly location: DaliurenLocationObservation;
  readonly money: DaliurenMoneyObservation;
  readonly relationship: DaliurenRelationshipObservation;
  readonly state: DaliurenStateObservation;
  readonly timing: DaliurenTimingObservation;
  readonly work: DaliurenWorkObservation;
}>;

export type DaliurenDimensionFact = Readonly<{
  readonly canonical_dimension: string;
  readonly requested_dimension: string;
  readonly rule_evidence: DaliurenRuleEvidence;
  readonly status: "calculated_facts_not_verdict";
  readonly source_rule_ids: ReadonlyArray<string>;
  readonly general_landing_correspondences?: ReadonlyArray<
    DaliurenGeneralLandingCorrespondence | DaliurenGeneralLandingUnavailableCorrespondence
  >;
  readonly six_relative_stages?: ReadonlyArray<DaliurenSixRelativeStage>;
  readonly stage_branch_directions?: DaliurenLocationObservation["stage_branch_directions"];
  readonly stage_flow?: ReadonlyArray<DaliurenStageFlowEntry>;
  readonly stage_status?: ReadonlyArray<DaliurenStageStatusEntry>;
  readonly subject_object_relation?: DaliurenRelationFact;
  readonly transmissions_to_day?: ReadonlyArray<DaliurenTransmissionToDayEntry>;
  readonly initial_final_relation?: DaliurenRelationFact;
  readonly relative_speed?: DaliurenRelativeSpeed | null;
  readonly candidate_branch?: DaliurenCandidateBranch | null;
  readonly candidate_date?: DaliurenTimingCandidate | null;
  readonly target_relative?: DaliurenSixRelative | null;
  readonly target_contract_status?: "bound" | "missing_target_relative";
  readonly target_presence?: boolean;
  readonly target_strength?: ReadonlyArray<Readonly<Record<string, unknown>>>;
  readonly target_general_modifier?: ReadonlyArray<Readonly<Record<string, unknown>>>;
  readonly wealth_presence?: boolean;
  readonly wealth_stage_strength?: ReadonlyArray<DaliurenWealthStageStrengthEntry>;
  readonly wealth_void_status?: ReadonlyArray<DaliurenWealthVoidStatusEntry>;
  readonly wealth_general_modifier?: ReadonlyArray<DaliurenWealthGeneralModifier>;
}> & Readonly<Record<string, unknown>>;

export type DaliurenChartViewModel = {
  readonly schema_version: "daliuren-chart/v1";
  readonly subject_ref: string;
  readonly question: string;
  readonly lessons: readonly [
    { readonly lesson_id: string; readonly upper: string; readonly lower: string },
    { readonly lesson_id: string; readonly upper: string; readonly lower: string },
    { readonly lesson_id: string; readonly upper: string; readonly lower: string },
    { readonly lesson_id: string; readonly upper: string; readonly lower: string },
  ];
  readonly transmissions: readonly [
    { readonly stage: "initial"; readonly branch: string; readonly general: string },
    { readonly stage: "middle"; readonly branch: string; readonly general: string },
    { readonly stage: "final"; readonly branch: string; readonly general: string },
  ];
  readonly core_facts: {
    readonly day_hour: DaliurenDayHour | null;
    readonly dimension_facts: Readonly<Record<string, DaliurenDimensionFact>> | null;
    readonly earth_plate: ReadonlyArray<string> | null;
    readonly heaven_plate: ReadonlyArray<DaliurenHeavenPlateCell> | null;
    readonly heavenly_generals: ReadonlyArray<DaliurenGeneralCell> | null;
    readonly lesson_method: DaliurenLessonMethod | null;
    readonly month_general: DaliurenMonthGeneral | null;
    readonly noble_person: DaliurenNoblePerson | null;
    readonly plate_offset: number | null;
    readonly structural_patterns: ReadonlyArray<string> | null;
    readonly timing_candidates: ReadonlyArray<DaliurenTimingCandidate> | null;
    readonly xunkong: DaliurenXunkong | null;
  } | null;
  readonly public_labels?: ReadonlyArray<{ readonly key: string; readonly label: string }>;
};

export type HecanViewModel = {
  readonly schema_version: "hecan-view/v1";
  readonly subject_ref: string;
  readonly selected_art_ids:
    | readonly [NatalArtId, NatalArtId]
    | readonly [NatalArtId, NatalArtId, NatalArtId];
  readonly dimensions: ReadonlyArray<CrossArtDimension>;
};

export type LiuyaoSourceRef = {
  readonly pack: "divination/huangjin-ce";
  readonly rule_id: "HJC-R009";
  readonly source_anchor: string;
  readonly verification_status: "verified";
  readonly binding_digest: string;
};

export type LiuyaoSpecificLineSourceRef = {
  readonly pack: "divination/zengshan-buyi";
  readonly rule_id: "ZR-04-04";
  readonly source_anchor: string;
  readonly verification_status: "verified";
  readonly binding_digest: string;
};

export type LiuyaoSpecificLineAdjudication = {
  readonly status:
    | "adjudicated_unique_visible_line"
    | "adjudicated_single_moving_visible_line"
    | "unresolved_multiple_visible_lines"
    | "unresolved_no_visible_line";
  readonly decision_scope: "finance_primary_relative_line_identity";
  readonly primary_relative: "妻财";
  readonly visible_candidate_count: number;
  readonly visible_candidate_lines: ReadonlyArray<1 | 2 | 3 | 4 | 5 | 6>;
  readonly moving_visible_candidate_count: number;
  readonly moving_visible_candidate_lines: ReadonlyArray<1 | 2 | 3 | 4 | 5 | 6>;
  readonly specific_line_selection: 1 | 2 | 3 | 4 | 5 | 6 | null;
  readonly derivation_basis:
    | "verified_role_plus_runtime_unique_visible_candidate"
    | "verified_two_present_rule_plus_runtime_single_moving_candidate"
    | "verified_role_plus_runtime_multiple_visible_candidates"
    | "verified_role_plus_runtime_no_visible_candidate";
  readonly selection_source_ref:
    | LiuyaoSourceRef
    | LiuyaoSpecificLineSourceRef
    | null;
  readonly hard_verdict: null;
};

export type LiuyaoRoleAdjudication = {
  readonly status: "adjudicated_question_role_set";
  readonly decision_scope: "finance_useful_spirit_role_set";
  readonly question_class: "finance";
  readonly primary_relative: "妻财";
  readonly supporting_relatives: readonly ["子孙"];
  readonly obstacle_attention_relatives: readonly ["兄弟", "官鬼", "父母"];
  readonly specific_line_selection: 1 | 2 | 3 | 4 | 5 | 6 | null;
  readonly specific_line_adjudication: LiuyaoSpecificLineAdjudication;
  readonly hard_verdict: null;
  readonly source_ref: LiuyaoSourceRef;
  readonly unresolved_checks: ReadonlyArray<string>;
};

export type LiuyaoNotRequestedRoleAdjudication = {
  readonly status: "not_requested";
  readonly decision_scope: null;
  readonly question_class: null;
  readonly primary_relative: null;
  readonly supporting_relatives: readonly [];
  readonly obstacle_attention_relatives: readonly [];
  readonly specific_line_selection: null;
  readonly hard_verdict: null;
  readonly source_ref: null;
  readonly unresolved_checks: ReadonlyArray<string>;
};

export type LiuyaoSeasonalStrengthSourceRef = {
  readonly pack: "divination/zengshan-buyi";
  readonly rule_id: "ZR-05-05";
  readonly source_anchor: string;
  readonly verification_status: "verified";
  readonly binding_digest: string;
};

export type LiuyaoSeasonalStrengthAdjudication = {
  readonly status: "adjudicated_seasonal_strength_band";
  readonly decision_scope: "liuyao_candidate_month_order_strength_band";
  readonly candidate_source: "visible_line" | "changed_line" | "hidden_line";
  readonly line: 1 | 2 | 3 | 4 | 5 | 6;
  readonly line_element: "木" | "火" | "土" | "金" | "水";
  readonly month_element: "木" | "火" | "土" | "金" | "水";
  readonly seasonal_state: "旺" | "相" | "休" | "囚" | "死";
  readonly strength_band: "旺相" | "休囚";
  readonly whole_candidate_strength_verdict: null;
  readonly outcome_verdict: null;
  readonly source_ref: LiuyaoSeasonalStrengthSourceRef;
  readonly unresolved_checks: ReadonlyArray<string>;
};

export type LiuyaoStrengthSignal = {
  readonly signal:
    | "seasonal_support"
    | "seasonal_weakening"
    | "month_break"
    | "day_clash"
    | "xunkong"
    | "moving_line";
  readonly value: string | boolean;
  readonly status: "candidate_signal";
};

export type LiuyaoStrengthCandidate = {
  readonly source: "visible_line" | "changed_line" | "hidden_line";
  readonly line: 1 | 2 | 3 | 4 | 5 | 6;
  readonly moving: boolean;
  readonly xunkong: boolean;
  readonly najia: StructuredFactObject;
  readonly month_day_strength: StructuredFactObject;
  readonly seasonal_adjudication: LiuyaoSeasonalStrengthAdjudication;
  readonly signals: ReadonlyArray<LiuyaoStrengthSignal>;
  readonly status: "candidate_only";
  readonly hard_verdict: null;
};

export type LiuyaoRelativeStrengthEvidence = {
  readonly status: "candidate_only" | "not_available";
  readonly candidates: ReadonlyArray<LiuyaoStrengthCandidate>;
  readonly hard_verdict: null;
};

export type LiuyaoStrengthRuleRef = LiuyaoSeasonalStrengthSourceRef & {
  readonly role: "useful_spirit_month_order_strength_band";
};

export type LiuyaoStrengthEvidence = {
  readonly status: "candidate_only" | "not_requested";
  readonly by_relative: Readonly<Record<string, LiuyaoRelativeStrengthEvidence>>;
  readonly source_rules: ReadonlyArray<LiuyaoStrengthRuleRef>;
  readonly fact_status: "calculated_relation_not_verdict";
  readonly hard_verdict: null;
  readonly requires_school_adjudication: true;
  readonly source_dependency_id:
    "liuyao.interpretation.useful-spirit-strength-evidence";
};

export type LiuyaoUsefulSpiritSelection = {
  readonly status: "evidence_bound";
  readonly reason: string;
  readonly query_word_matching: false;
  readonly source_dependency_id: string;
  readonly chain_candidates: StructuredFactObject;
  readonly strength_evidence: LiuyaoStrengthEvidence;
  readonly role_adjudication:
    | LiuyaoRoleAdjudication
    | LiuyaoNotRequestedRoleAdjudication;
  readonly question_context: {
    readonly question_class: "finance";
    readonly classification_source: "explicit_structured_input";
  } | null;
};

export type LiuyaoChartViewModel = {
  readonly schema_version: "liuyao-chart/v1";
  readonly subject_ref: string;
  readonly question: string;
  readonly primary_hexagram: {
    readonly name: string;
    readonly upper_trigram: string;
    readonly lower_trigram: string;
  };
  readonly changed_hexagram: {
    readonly name: string;
    readonly upper_trigram: string;
    readonly lower_trigram: string;
  } | null;
  readonly lines: readonly [
    { readonly position: 1 | 2 | 3 | 4 | 5 | 6; readonly value: 6 | 7 | 8 | 9; readonly moving: boolean },
    { readonly position: 1 | 2 | 3 | 4 | 5 | 6; readonly value: 6 | 7 | 8 | 9; readonly moving: boolean },
    { readonly position: 1 | 2 | 3 | 4 | 5 | 6; readonly value: 6 | 7 | 8 | 9; readonly moving: boolean },
    { readonly position: 1 | 2 | 3 | 4 | 5 | 6; readonly value: 6 | 7 | 8 | 9; readonly moving: boolean },
    { readonly position: 1 | 2 | 3 | 4 | 5 | 6; readonly value: 6 | 7 | 8 | 9; readonly moving: boolean },
    { readonly position: 1 | 2 | 3 | 4 | 5 | 6; readonly value: 6 | 7 | 8 | 9; readonly moving: boolean },
  ];
  readonly core_facts: {
    readonly calendar: StructuredFactObject | null;
    readonly casting: StructuredFactObject | null;
    readonly casting_method: string | null;
    readonly changed_najia: ReadonlyArray<StructuredFactObject> | null;
    readonly changed_plate_lines: ReadonlyArray<StructuredFactObject> | null;
    readonly changed_six_relatives: ReadonlyArray<string> | null;
    readonly hidden_lines: ReadonlyArray<StructuredFactObject> | null;
    readonly interpretation_status: string | null;
    readonly line_facts: ReadonlyArray<StructuredFactObject> | null;
    readonly lines: ReadonlyArray<StructuredFactObject> | null;
    readonly month_day_strength: ReadonlyArray<StructuredFactObject> | null;
    readonly moving_lines: ReadonlyArray<number> | null;
    readonly najia: ReadonlyArray<StructuredFactObject> | null;
    readonly relation_facts: ReadonlyArray<StructuredFactObject> | null;
    readonly returning_relations: ReadonlyArray<StructuredFactObject> | null;
    readonly requested_useful_spirit_candidates: StructuredFactObject | null;
    readonly shi_ying: StructuredFactObject | null;
    readonly shi_ying_moving_relations: StructuredFactObject | null;
    readonly six_relatives: ReadonlyArray<string> | null;
    readonly six_spirit_profile: StructuredFactObject | null;
    readonly six_spirits: ReadonlyArray<string> | null;
    readonly useful_spirit_candidates: StructuredFactObject | null;
    readonly useful_spirit_selection: LiuyaoUsefulSpiritSelection | null;
    readonly xunkong: StructuredFactObject | null;
  } | null;
};

export type MeihuaRelationSourceRef = {
  readonly pack: string;
  readonly rule_id: string;
  readonly source_anchor: string;
  readonly verification_status: "verified";
  readonly binding_digest: string;
};

export type MeihuaRelationAdjudication = {
  readonly status: "adjudicated_relation_polarity";
  readonly decision_scope: "meihua_body_use_relation";
  readonly relation_key: string;
  readonly source_polarity: "supportive" | "depleting" | "adverse" | "favorable" | "harmonious";
  readonly hard_verdict: null;
  readonly event_verdict: null;
  readonly source_refs: ReadonlyArray<MeihuaRelationSourceRef>;
  readonly unresolved_checks: ReadonlyArray<string>;
};

export type MeihuaInterpretiveCandidates = {
  readonly schema_version: "mingli-meihua-interpretive-candidates-v1";
  readonly status: "source_adjudicated_relations";
  readonly hard_verdict: null;
  readonly verification_status: "verified";
  readonly relation_candidates: ReadonlyArray<{
    readonly candidate_id: string;
    readonly source_plate: string;
    readonly position: "upper" | "lower";
    readonly relation: string;
    readonly relation_key: string;
    readonly actor: { readonly position: "upper" | "lower"; readonly trigram: string; readonly element: string };
    readonly body: { readonly position: "upper" | "lower"; readonly trigram: string; readonly element: string };
    readonly seasonal_state: string | null;
    readonly rule_id: string;
    readonly status: "relation_adjudicated_not_event_verdict";
    readonly hard_verdict: null;
    readonly verification_status: "verified";
    readonly source_pack: string;
    readonly source_anchor: string;
    readonly source_dependency_id: string;
    readonly relation_adjudication: MeihuaRelationAdjudication;
  }>;
  readonly requires_classical_adjudication: false;
  readonly requires_synthesis_adjudication: true;
  readonly boundary: string;
};

export type MeihuaChartViewModel = {
  readonly schema_version: "meihua-chart/v1";
  readonly subject_ref: string;
  readonly question: string;
  readonly casting_method:
    | "time"
    | "supplied_number"
    | "sound_count"
    | "observation"
    | "supplied_hexagram";
  readonly primary_hexagram: {
    readonly name: string;
    readonly upper_trigram: string;
    readonly lower_trigram: string;
  };
  readonly mutual_hexagram: {
    readonly name: string;
    readonly upper_trigram: string;
    readonly lower_trigram: string;
  } | null;
  readonly changed_hexagram: {
    readonly name: string;
    readonly upper_trigram: string;
    readonly lower_trigram: string;
  } | null;
  readonly moving_lines: ReadonlyArray<number>;
  readonly body_use: {
    readonly body: { readonly position: "upper" | "lower"; readonly trigram: string; readonly element: string };
    readonly use: { readonly position: "upper" | "lower"; readonly trigram: string; readonly element: string };
    readonly relation: string;
    readonly status: string;
  };
  readonly core_facts: {
    readonly body_relation_facts: ReadonlyArray<StructuredFactObject> | null;
    readonly seasonal_strength: StructuredFactObject | null;
    readonly interpretive_candidates: MeihuaInterpretiveCandidates | null;
    readonly interpretation_status: string | null;
  } | null;
  readonly public_labels?: ReadonlyArray<{ readonly key: string; readonly label: string }>;
};

export type StructuredFactValue =
  | string
  | number
  | boolean
  | null
  | ReadonlyArray<StructuredFactValue>
  | { readonly [key: string]: StructuredFactValue };

export type StructuredFactObject = {
  readonly [key: string]: StructuredFactValue;
};

export type SourceConditionedPattern = {
  readonly rule_id: string;
  readonly local_rule_id: string;
  readonly title: string;
  readonly source_pack: string;
  readonly source_anchor: string;
  readonly status: "predicate_matched_not_verdict";
  readonly fact_paths: ReadonlyArray<string>;
  readonly predicate_audit: ReadonlyArray<string>;
};

export type LumingNayinChartViewModel = {
  readonly schema_version: "luming-nayin-chart/v1";
  readonly subject_ref: string;
  readonly pillars: ReadonlyArray<{
    readonly position: "year" | "month" | "day" | "hour";
    readonly stem: string;
    readonly branch: string;
    readonly nayin: string;
  }>;
  readonly three_yuan_profiles: StructuredFactObject;
  readonly taiyuan: StructuredFactObject | null;
  readonly relations: ReadonlyArray<{
    readonly category: "lu" | "ma" | "gui";
    readonly relation: string;
    readonly anchor: string;
    readonly anchor_pillar: string;
    readonly status: string;
    readonly target_branch: string | null;
    readonly candidates: ReadonlyArray<string>;
    readonly matched_positions: ReadonlyArray<string>;
    readonly recension: string | null;
  }>;
  readonly source_conditioned_patterns: ReadonlyArray<{
    readonly rule_id: string;
    readonly local_rule_id: string;
    readonly title: string;
    readonly source_pack: string;
    readonly source_anchor: string;
    readonly status: "predicate_matched_not_verdict";
    readonly fact_paths: ReadonlyArray<string>;
    readonly predicate_audit: ReadonlyArray<string>;
    readonly applicability_adjudication: {
      readonly status: "adjudicated_rule_applicability";
      readonly decision_scope: "luming_nayin_source_rule_applicability";
      readonly rule_id: string;
      readonly local_rule_id: string;
      readonly rule_title: string;
      readonly evidence_role:
        | "issue_specific_judgment_rule"
        | "methodology_rule";
      readonly hard_verdict: null;
      readonly life_verdict: null;
      readonly source_ref: {
        readonly pack: string;
        readonly rule_id: string;
        readonly source_anchor: string;
        readonly verification_status: "verified";
        readonly binding_digest: string;
      };
      readonly unresolved_checks: ReadonlyArray<string>;
    };
  }>;
};

export type RhythmFactsViewModel = {
  readonly schema_version: "rhythm-facts-view/v1";
  readonly subject_ref: string;
  readonly pillars: ReadonlyArray<{
    readonly position: "year" | "month" | "day" | "hour";
    readonly stem: string;
    readonly branch: string;
    readonly nayin: string;
  }>;
  readonly independent_lineage: string;
  readonly fact_scope: string;
  readonly interpretation_status: "facts_only";
  readonly source_boundary: string;
};

export type FortuneFactsViewModel = {
  readonly schema_version: "fortune-facts-view/v1";
  readonly subject_ref: string;
  readonly natal_pillars: Readonly<Record<"year" | "month" | "day" | "hour", string>>;
  readonly day_master: {
    readonly stem: string;
    readonly element: "wood" | "fire" | "earth" | "metal" | "water";
    readonly polarity: "阳" | "阴";
  };
  readonly month_command: {
    readonly branch: string;
    readonly label: string;
    readonly main_qi: string;
    readonly main_qi_element: "wood" | "fire" | "earth" | "metal" | "water";
  };
  readonly active_luck_cycle: string;
  readonly target_day: string;
  readonly target_period: {
    readonly kind: string;
    readonly start: string;
    readonly end: string;
  };
  readonly available_periods: ReadonlyArray<string>;
  readonly period_markers: ReadonlyArray<{
    readonly date: string;
    readonly day_pillar: string;
    readonly day_role: string;
    readonly active_luck_cycle: string;
    readonly primary_mechanism_ids: ReadonlyArray<string>;
    readonly decisive_mechanism_ids: ReadonlyArray<string>;
    readonly relations: ReadonlyArray<StructuredFactObject>;
    readonly specific_event_policy: string;
    readonly unresolved_boundaries: ReadonlyArray<string>;
  }>;
  readonly calendar_normalization: {
    readonly status: string;
    readonly algorithm_version: string;
    readonly time_basis: {
      readonly policy: string;
      readonly standard_meridian_degrees: number | null;
      readonly longitude_correction_seconds: number | null;
      readonly equation_of_time_seconds: number | null;
      readonly total_correction_seconds: number | null;
      readonly algorithm: {
        readonly id: string | null;
        readonly version: string | null;
        readonly source: string | null;
        readonly uncertainty_seconds: number | null;
      };
      readonly boundary: {
        readonly distance_seconds: number | null;
        readonly correction_changes_hour_branch: boolean | null;
        readonly within_uncertainty: boolean | null;
      };
    };
    readonly true_solar_time: {
      readonly status: string;
      readonly policy: string | null;
      readonly longitude_correction_seconds: number | null;
      readonly equation_of_time_seconds: number | null;
      readonly total_correction_seconds: number | null;
    };
    readonly calendar_convention: {
      readonly id: string | null;
      readonly version: string | null;
      readonly year_boundary: string | null;
      readonly month_boundary: string | null;
      readonly day_rollover: string | null;
      readonly hour_basis: string | null;
      readonly zi_hour_policy: string | null;
    };
  };
};

export type TaiyiChartViewModel = {
  readonly schema_version: "taiyi-chart/v1";
  readonly subject_ref: string;
  readonly calendar: {
    readonly annual_boundary: string;
    readonly lunar_year: number;
    readonly year_ganzhi: string;
  };
  readonly epoch: {
    readonly accumulated_year: number;
    readonly anchor_accumulated_year: number;
    readonly anchor_lunar_year_ce: number;
    readonly derived_ce_offset: number;
    readonly one_based: boolean;
    readonly profile_id: string;
    readonly source_anchor: string;
  };
  readonly cycle: {
    readonly bureau: number;
    readonly governance: string;
    readonly ji: number;
    readonly position_360: number;
    readonly year_in_ji: number;
    readonly year_in_zi_yuan: number;
    readonly zi_yuan: number;
    readonly zi_yuan_head: string;
  };
  readonly board: {
    readonly heshen: string;
    readonly jishen: string;
    readonly shiji: string;
    readonly taisui: string;
    readonly taiyi_position: string;
    readonly tianmu_wenchang: { readonly name: string; readonly position: string };
  };
  readonly host_guest: StructuredFactObject;
  readonly four_generals: {
    readonly guest_assistant: number;
    readonly guest_major: number;
    readonly host_assistant: number;
    readonly host_major: number;
  };
  readonly long_cycle_deities: ReadonlyArray<{
    readonly deity_id: string;
    readonly accumulated_year: number;
    readonly cycle_position: number;
    readonly epoch_profile: string;
    readonly name: string;
    readonly position: string;
    readonly source_anchor: string;
    readonly status: string;
  }>;
  readonly board_predicates: ReadonlyArray<{
    readonly predicate_id: string;
    readonly name: string;
    readonly predicate: string;
    readonly fact_paths: ReadonlyArray<string>;
    readonly source_anchor: string;
    readonly source_dependency_id: string;
    readonly status: "predicate_matched_not_verdict";
    readonly identity_adjudication: {
      readonly status: "adjudicated_pattern_identity";
      readonly decision_scope: "taiyi_board_pattern_identity";
      readonly pattern_id: string;
      readonly pattern_name: string;
      readonly hard_verdict: null;
      readonly event_verdict: null;
      readonly source_ref: {
        readonly pack: string;
        readonly rule_id: string;
        readonly source_anchor: string;
        readonly verification_status: "verified";
        readonly binding_digest: string;
      };
      readonly unresolved_checks: ReadonlyArray<string>;
    };
  }>;
  readonly scope_contract: {
    readonly declared_scope: string;
    readonly interpretation_policy: string;
    readonly supported_horizons: ReadonlyArray<string>;
    readonly supported_objects: ReadonlyArray<string>;
    readonly unsupported_scopes: ReadonlyArray<string>;
  };
};

export type SelectionChartViewModel = {
  readonly schema_version: "selection-chart/v1";
  readonly subject_ref: string;
  readonly event_profile: string;
  readonly eligible_candidates: ReadonlyArray<{
    readonly candidate_id: string;
    readonly civil_date: string;
    readonly best_candidate_time_id: string;
    readonly eligibility: StructuredFactObject;
    readonly rejection_reasons: ReadonlyArray<StructuredFactObject>;
    readonly ranking_components: StructuredFactObject;
  }>;
  readonly eligible_date_time_candidates: ReadonlyArray<string>;
  readonly eliminations: ReadonlyArray<StructuredFactObject>;
  readonly ranking: {
    readonly component_order: ReadonlyArray<string>;
    readonly eligible_candidate_ids: ReadonlyArray<string>;
    readonly eligible_date_time_candidate_ids: ReadonlyArray<string>;
    readonly folk_affects_rank: boolean;
    readonly method: string;
    readonly opaque_numeric_score: boolean;
    readonly ordered_candidate_ids: ReadonlyArray<string>;
    readonly ordered_date_time_candidate_ids: ReadonlyArray<string>;
  };
  readonly lineage_policy: {
    readonly folk: string;
    readonly folk_priority: string;
    readonly merge_verdicts: boolean;
    readonly official: string;
    readonly official_priority: string;
    readonly preserve_disagreement: boolean;
  };
  readonly no_valid_candidate: boolean;
  readonly basis_projection: StructuredFactObject;
  readonly source_conditioned_patterns: ReadonlyArray<SourceConditionedPattern>;
};

export type FengshuiViewModel = {
  readonly schema_version: "fengshui-view/v1";
  readonly subject_ref: string;
  readonly active_subprofiles: ReadonlyArray<"form" | "liqi">;
  readonly observation_provenance: StructuredFactObject;
  readonly compass: StructuredFactObject;
  readonly building_chronology: StructuredFactObject;
  readonly layout_graph: StructuredFactObject;
  readonly form: StructuredFactObject;
  readonly liqi: StructuredFactObject;
  readonly active_source_rule_ids: ReadonlyArray<string>;
  readonly conflicts: ReadonlyArray<StructuredFactObject>;
  readonly uncertainties: ReadonlyArray<StructuredFactObject>;
  readonly critical_missing: ReadonlyArray<string>;
};

export type PhysiognomySourceComparison = {
  readonly sources: ReadonlyArray<StructuredFactObject>;
  readonly disagreements_retained: boolean;
  readonly disagreements: ReadonlyArray<StructuredFactObject>;
  readonly forced_resolution: boolean;
};

export type PhysiognomyViewModel = {
  readonly schema_version: "physiognomy-view/v1";
  readonly subject_ref: string;
  readonly mode: "face" | "palm" | "posture" | "combined";
  readonly observations: ReadonlyArray<{
    readonly observation_id: string;
    readonly region_id: string;
    readonly feature_id: string;
    readonly confidence: number;
    readonly display_text: string;
  }>;
  readonly missing_targets: ReadonlyArray<StructuredFactObject>;
  readonly uncertainties: ReadonlyArray<StructuredFactObject>;
  readonly conflicts: ReadonlyArray<StructuredFactObject>;
  readonly cross_capture_variations: ReadonlyArray<StructuredFactObject>;
  readonly source_comparison: PhysiognomySourceComparison;
  readonly active_source_rule_ids: ReadonlyArray<string>;
};

export type QimenChartViewModel = {
  readonly schema_version: "qimen-chart/v1";
  readonly subject_ref: string;
  readonly question: string;
  readonly dun_type: "yin" | "yang";
  readonly ju_number: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;
  readonly palaces: ReadonlyArray<{
    readonly palace_id: string;
    readonly stem: string;
    readonly heaven_stems: ReadonlyArray<string>;
    readonly stars: ReadonlyArray<string>;
    readonly star: string | null;
    readonly door: string | null;
    readonly deity: string | null;
  }>;
  readonly chief: {
    readonly star: string;
    readonly door: string;
    readonly hidden_instrument: string;
    readonly xun_palace: number;
    readonly hosted_xun_palace: number;
    readonly destination_palace: number;
  };
  readonly director: {
    readonly door: string;
    readonly xun_palace: number;
    readonly destination_palace: number;
    readonly hour_offset_in_xun: number;
  };
  readonly instruments_wonders: {
    readonly six_instruments: ReadonlyArray<string>;
    readonly three_wonders: ReadonlyArray<string>;
    readonly earth_plate: ReadonlyArray<{ readonly palace: number; readonly stem: string; readonly kind: "six_instrument" | "three_wonder" }>;
    readonly heaven_plate: ReadonlyArray<{ readonly palace: number; readonly stem: string; readonly kind: "six_instrument" | "three_wonder" }>;
    readonly hidden_jia: { readonly xun: string; readonly instrument: string };
  };
  readonly xunkong: {
    readonly xun: string;
    readonly branches: ReadonlyArray<string>;
    readonly palaces: ReadonlyArray<number>;
  };
  readonly horse: {
    readonly hour_branch: string;
    readonly branch: string;
    readonly palace: number;
  };
  readonly named_patterns: ReadonlyArray<{
    readonly id: string;
    readonly name: string;
    readonly status: "predicate_matched_not_verdict";
    readonly palace: number | null;
    readonly identity_adjudication: {
      readonly status: "adjudicated_pattern_identity";
      readonly decision_scope: "qimen_named_pattern_identity";
      readonly pattern_id: string;
      readonly pattern_name: string;
      readonly palace: number | null;
      readonly hard_verdict: null;
      readonly event_verdict: null;
      readonly source_ref: {
        readonly pack: string;
        readonly rule_id: string;
        readonly source_anchor: string;
        readonly verification_status: "verified";
        readonly binding_digest: string;
      };
      readonly unresolved_checks: ReadonlyArray<string>;
    };
  }>;
};

export type QizhengChartViewModel = {
  readonly schema_version: "qizheng-chart/v1";
  readonly subject_ref: string;
  readonly planets: ReadonlyArray<{
    readonly planet_id: string;
    readonly sign_id: string;
    readonly house_id: string;
    readonly longitude: number;
  }>;
  readonly houses: ReadonlyArray<{
    readonly house_id: string;
    readonly sign_id: string;
    readonly cusp_longitude: number;
  }>;
  readonly aspects: ReadonlyArray<{
    readonly aspect_id: string;
    readonly from_planet_id: string;
    readonly to_planet_id: string;
    readonly orb: number;
  }>;
  readonly time_layers: ReadonlyArray<TimeLayer>;
  readonly core_facts?: QizhengCoreFacts | null;
};

export type QizhengRelationshipViewModel = {
  readonly schema_version: "qizheng-relationship/v1";
  readonly subjects: readonly [RelationshipSubject, RelationshipSubject];
  readonly relationship_type: BaziRelationshipViewModel["relationship_type"];
  readonly signals: ReadonlyArray<RelationshipSignal>;
};

export type WenshiViewModel = {
  readonly schema_version: "wenshi-view/v1";
  readonly subject_ref: string;
  readonly question: string;
  readonly selected_art_ids: readonly ["liuyao", "qimen", "daliuren"];
  readonly dimensions: ReadonlyArray<CrossArtDimension>;
};

export type ZiweiChartViewModel = {
  readonly schema_version: "ziwei-chart/v1";
  readonly subject_ref: string;
  readonly life_palace_id: string;
  readonly body_palace_id: string;
  readonly palaces: ReadonlyArray<{
    readonly palace_id: string;
    readonly label: string;
    readonly heavenly_stem: string;
    readonly earthly_branch: string;
    readonly major_stars: ReadonlyArray<string>;
    readonly minor_stars?: ReadonlyArray<{
      readonly name: string;
      readonly star_type: string | null;
      readonly scope: string | null;
      readonly brightness: string | null;
    }>;
    readonly adjective_stars?: ReadonlyArray<{
      readonly name: string;
      readonly star_type: string | null;
      readonly scope: string | null;
      readonly brightness: string | null;
    }>;
    readonly changsheng12?: string | null;
    readonly boshi12?: string | null;
    readonly jiangqian12?: string | null;
    readonly suiqian12?: string | null;
    readonly decadal?: {
      readonly age_start: number;
      readonly age_end: number;
      readonly heavenly_stem: string;
      readonly earthly_branch: string;
    } | null;
    readonly ages?: ReadonlyArray<number>;
  }>;
  readonly time_layers: ReadonlyArray<TimeLayer>;
  readonly core_facts?: ZiweiCoreFacts | null;
};

export type ZiweiRelationshipViewModel = {
  readonly schema_version: "ziwei-relationship/v1";
  readonly subjects: readonly [RelationshipSubject, RelationshipSubject];
  readonly relationship_type: BaziRelationshipViewModel["relationship_type"];
  readonly signals: ReadonlyArray<RelationshipSignal>;
};

export type ViewModelByVersion = {
  "bazi-chart/v1": BaziChartViewModel;
  "bazi-relationship/v1": BaziRelationshipViewModel;
  "canwen-view/v1": CanwenViewModel;
  "chart-similarity-view/v1": ChartSimilarityViewModel;
  "daliuren-chart/v1": DaliurenChartViewModel;
  "fengshui-view/v1": FengshuiViewModel;
  "five-elements-facts-view/v1": FiveElementsFactsViewModel;
  "fortune-facts-view/v1": FortuneFactsViewModel;
  "hecan-view/v1": HecanViewModel;
  "liuyao-chart/v1": LiuyaoChartViewModel;
  "luming-nayin-chart/v1": LumingNayinChartViewModel;
  "rhythm-facts-view/v1": RhythmFactsViewModel;
  "meihua-chart/v1": MeihuaChartViewModel;
  "physiognomy-view/v1": PhysiognomyViewModel;
  "qimen-chart/v1": QimenChartViewModel;
  "qizheng-chart/v1": QizhengChartViewModel;
  "qizheng-relationship/v1": QizhengRelationshipViewModel;
  "selection-chart/v1": SelectionChartViewModel;
  "taiyi-chart/v1": TaiyiChartViewModel;
  "time-check-view/v1": TimeCheckViewModel;
  "wenshi-view/v1": WenshiViewModel;
  "ziwei-chart/v1": ZiweiChartViewModel;
  "ziwei-relationship/v1": ZiweiRelationshipViewModel;
};

export type ViewModel = ViewModelByVersion[ViewModelVersion];

type UnavailableFixture<V extends ViewModelVersion> = {
  readonly version: V;
  readonly state: "unavailable";
  readonly title: string;
  readonly description: string;
};

export type ReadyFixture<V extends ViewModelVersion> = {
  readonly version: V;
  readonly state: "ready";
  readonly title: string;
  readonly description: string;
  readonly value: ViewModelByVersion[V];
};

export type ViewModelFixture<V extends ViewModelVersion = ViewModelVersion> =
  | UnavailableFixture<V>
  | ReadyFixture<V>;

const unavailableFixture = <V extends ViewModelVersion>(
  version: V,
  title: string,
  description = "真实 ViewModel 尚未接入；当前页面只展示诚实的能力状态。",
): UnavailableFixture<V> => ({
  version,
  state: "unavailable",
  title,
  description,
});

export const VIEW_MODEL_FIXTURES: {
  readonly [V in ViewModelVersion]: ViewModelFixture<V>;
} = {
  "bazi-chart/v1": unavailableFixture("bazi-chart/v1", "八字盘面待接入"),
  "bazi-relationship/v1": unavailableFixture("bazi-relationship/v1", "八字合盘待接入"),
  "canwen-view/v1": unavailableFixture("canwen-view/v1", "多盘问答待接入"),
  "chart-similarity-view/v1": unavailableFixture(
    "chart-similarity-view/v1",
    "八字同盘四柱事实比较已接入",
    "只比较两份已确认命盘的 Runtime 四柱原值；不生成百分比、合婚或缘分结论。",
  ),
  "time-check-view/v1": unavailableFixture(
    "time-check-view/v1",
    "寻时定盘十二候选事实已接入",
    "测试 Runtime 已支持结构化事件证据、候选排序和事件匹配；完整古法校时、淘汰规则与最可能时辰结论仍未接入。",
  ),
  "daliuren-chart/v1": unavailableFixture("daliuren-chart/v1", "大六壬盘面待接入"),
  "fengshui-view/v1": unavailableFixture(
    "fengshui-view/v1",
    "风水基础观察已接入",
    "基础 ViewModel 和产品输入已接入；完整深读、追问和导出仍待接入。",
  ),
  "five-elements-facts-view/v1": unavailableFixture(
    "five-elements-facts-view/v1",
    "五行事实与调候依据已接入",
    "事实切片使用真实 Runtime 结果；当前不输出旺衰、喜忌或用神结论。",
  ),
  "fortune-facts-view/v1": unavailableFixture(
    "fortune-facts-view/v1",
    "日运事实已接入",
    "只展示 Runtime 日运与周期事实；当前不追加具体事件、吉凶或人生判断。",
  ),
  "hecan-view/v1": unavailableFixture("hecan-view/v1", "命盘合参待接入"),
  "liuyao-chart/v1": unavailableFixture("liuyao-chart/v1", "六爻盘面待接入"),
  "luming-nayin-chart/v1": unavailableFixture(
    "luming-nayin-chart/v1",
    "禄命纳音基础盘面已接入",
    "基础 ViewModel 和产品输入已接入；完整深读、追问和导出仍待接入。",
  ),
  "rhythm-facts-view/v1": unavailableFixture(
    "rhythm-facts-view/v1",
    "本命音律纳音事实已接入",
    "只展示 Runtime 四柱纳音事实；不生成音色、频率、姓名学、性格或吉凶结论。",
  ),
  "meihua-chart/v1": unavailableFixture("meihua-chart/v1", "梅花易数盘面待接入"),
  "physiognomy-view/v1": unavailableFixture("physiognomy-view/v1", "见相观察待接入"),
  "qimen-chart/v1": unavailableFixture("qimen-chart/v1", "奇门盘面待接入"),
  "qizheng-chart/v1": unavailableFixture("qizheng-chart/v1", "七政盘面待接入"),
  "qizheng-relationship/v1": unavailableFixture("qizheng-relationship/v1", "七政合盘待接入"),
  "selection-chart/v1": unavailableFixture(
    "selection-chart/v1",
    "择日基础盘面已接入",
    "基础 ViewModel 和产品输入已接入；完整深读、追问和导出仍待接入。",
  ),
  "taiyi-chart/v1": unavailableFixture(
    "taiyi-chart/v1",
    "太乙基础盘面已接入",
    "基础 ViewModel 和产品输入已接入；完整深读、追问和导出仍待接入。",
  ),
  "wenshi-view/v1": unavailableFixture("wenshi-view/v1", "问事合参待接入"),
  "ziwei-chart/v1": unavailableFixture("ziwei-chart/v1", "紫微盘面待接入"),
  "ziwei-relationship/v1": unavailableFixture("ziwei-relationship/v1", "紫微合盘待接入"),
};

export function getViewModelFixture<V extends ViewModelVersion>(
  version: V,
): ViewModelFixture<V>;
export function getViewModelFixture(version: string): ViewModelFixture | undefined;
export function getViewModelFixture(version: string): ViewModelFixture | undefined {
  return VIEW_MODEL_VERSIONS.includes(version as ViewModelVersion)
    ? VIEW_MODEL_FIXTURES[version as ViewModelVersion]
    : undefined;
}
