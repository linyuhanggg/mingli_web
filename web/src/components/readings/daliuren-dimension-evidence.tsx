"use client";

import type {
  DaliurenChartViewModel,
  DaliurenCompassDirection,
  DaliurenDimensionObservationMap,
  DaliurenGeneralLandingCorrespondence,
  DaliurenGeneralLandingUnavailableCorrespondence,
  DaliurenHeavenlyGeneral,
  DaliurenLocationObservation,
  DaliurenMiddleVoidObservation,
  DaliurenMoneyObservation,
  DaliurenOutcomeObservation,
  DaliurenOutcomeRelation,
  DaliurenRelationshipObservation,
  DaliurenSeasonStrength,
  DaliurenSixRelative,
  DaliurenSixRelativeStage,
  DaliurenStageStatusEntry,
  DaliurenStateObservation,
  DaliurenStageBranchDirection,
  DaliurenTimingCandidateObservation,
  DaliurenTimingObservation,
  DaliurenTransmissionStage,
  DaliurenWealthGeneralModifier,
  DaliurenWealthStageStrengthEntry,
  DaliurenWealthVoidStatusEntry,
  DaliurenWorkPresentObservation,
  DaliurenWorkObservation,
} from "@/view-models/registry";

import styles from "./daliuren-dimension-evidence.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;
type WealthStage = DaliurenWealthStageStrengthEntry;
type WealthVoidObservation = Extract<DaliurenMoneyObservation, { readonly wealth_void_rows: ReadonlyArray<unknown> }>;
type WealthVoidRow = WealthVoidObservation["wealth_void_rows"][number];
type WealthGeneralModifier = DaliurenWealthGeneralModifier;
type WealthVoidStatus = DaliurenWealthVoidStatusEntry;
type WorkStrength = DaliurenWorkPresentObservation["target_strength"][number];
type WorkGeneralModifier = DaliurenWorkPresentObservation["target_general_modifier"][number];
type LocationDirection = DaliurenLocationObservation["stage_branch_directions"][number];
type DaliurenDimensionId = keyof DaliurenDimensionObservationMap;
type GeneralLandingCorrespondence =
  | DaliurenGeneralLandingCorrespondence
  | DaliurenGeneralLandingUnavailableCorrespondence;

export type DaliurenDimensionEvidenceProps = {
  dimensionFacts?: CoreFacts["dimension_facts"];
};

const DIMENSION_LABELS = Object.freeze({
  location: "方位",
  money: "求财",
  outcome: "结果",
  relationship: "关系",
  state: "状态",
  timing: "时机",
  work: "事业",
}) satisfies Readonly<Record<DaliurenDimensionId, string>>;
const DIRECTION_LABELS = Object.freeze({
  east: "正东",
  north: "正北",
  northeast: "东北",
  northwest: "西北",
  south: "正南",
  southeast: "东南",
  southwest: "西南",
  west: "正西",
}) satisfies Readonly<Record<DaliurenCompassDirection, LocationDirection["direction_chinese"]>>;
const OUTCOME_RELATION_FACTS: Readonly<Record<DaliurenOutcomeRelation, string>> = {
  object_overcomes_subject: "客体克主体",
  subject_generates_object: "主体生客体",
  subject_overcomes_object: "主体克客体",
};
const RELATIONSHIP_FACTS: Readonly<Record<DaliurenRelationshipObservation["relation"], string>> = {
  object_overcomes_subject: OUTCOME_RELATION_FACTS.object_overcomes_subject,
  subject_overcomes_object: OUTCOME_RELATION_FACTS.subject_overcomes_object,
};
const TRANSMISSION_RELATION_FACTS = Object.freeze({
  subject_generates_object: "三传支均生日干",
  subject_overcomes_object: "三传支均克日干",
}) satisfies Readonly<Record<"subject_generates_object" | "subject_overcomes_object", string>>;
const RELATIVE_SPEED_FACTS: Readonly<
  Record<NonNullable<DaliurenTimingObservation["relative_speed"]>, string>
> = {
  relatively_faster: "较快",
  relatively_slower: "较慢",
};
const STAGE_FACTS: Readonly<Record<DaliurenTransmissionStage, string>> = {
  final: "末传",
  initial: "初传",
  middle: "中传",
};
const SEASON_STRENGTH_FACTS: Readonly<Record<DaliurenSeasonStrength, string>> = {
  unknown: "强弱未提供",
  休: "休",
  囚: "囚",
  旺: "旺",
  死: "死",
  相: "相",
};
const SIX_RELATIVES: ReadonlySet<DaliurenSixRelative> = new Set(["兄弟", "子孙", "妻财", "官鬼", "父母"]);
const FIVE_ELEMENTS = ["木", "火", "土", "金", "水"] as const;
type FiveElement = (typeof FIVE_ELEMENTS)[number];
const HEAVENLY_STEM_ELEMENTS = Object.freeze({
  甲: "木",
  乙: "木",
  丙: "火",
  丁: "火",
  戊: "土",
  己: "土",
  庚: "金",
  辛: "金",
  壬: "水",
  癸: "水",
}) satisfies Readonly<Record<string, FiveElement>>;
const EARTHLY_BRANCH_ELEMENTS = Object.freeze({
  子: "水",
  丑: "土",
  寅: "木",
  卯: "木",
  辰: "土",
  巳: "火",
  午: "火",
  未: "土",
  申: "金",
  酉: "金",
  戌: "土",
  亥: "水",
}) satisfies Readonly<Record<string, FiveElement>>;
const HEAVENLY_GENERALS: ReadonlySet<DaliurenHeavenlyGeneral> = new Set([
  "贵人",
  "腾蛇",
  "朱雀",
  "六合",
  "勾陈",
  "青龙",
  "天空",
  "白虎",
  "太常",
  "玄武",
  "太阴",
  "天后",
]);
const OUTCOME_RELATIONSHIP_KEYS = ["relation"] as const;
const OUTCOME_TRANSMISSION_KEYS = ["relations"] as const;
const MIDDLE_VOID_KEYS = ["stage", "branch", "is_xunkong"] as const;
const RELATIONSHIP_OBSERVATION_KEYS = ["relation"] as const;
const TIMING_OBSERVATION_KEYS = ["candidate_branch", "candidate_date", "relative_speed"] as const;
const TIMING_PACE_KEYS = ["relative_speed"] as const;
const CANDIDATE_BRANCH_KEYS = ["anchor_earth_branch", "branch", "source_rule"] as const;
const CANDIDATE_DATE_KEYS = [
  "id",
  "role",
  "anchor_earth_branch",
  "branch",
  "solar_date",
  "day_ganzhi",
  "days_after_cast",
  "source_pack",
  "source_rule",
  "candidate_not_guarantee",
] as const;
const WEALTH_PRESENT_KEYS = ["wealth_presence", "wealth_stages"] as const;
const WEALTH_ABSENT_KEYS = ["wealth_presence"] as const;
const WEALTH_STAGE_KEYS = ["stage", "branch", "six_relative", "season_strength"] as const;
const WEALTH_VOID_KEYS = ["wealth_void_rows"] as const;
const WEALTH_VOID_ROW_KEYS = ["stage", "branch", "six_relative", "is_xunkong"] as const;
const MONEY_DIMENSION_KEYS = [
  "canonical_dimension",
  "requested_dimension",
  "status",
  "source_rule_ids",
  "rule_evidence",
  "wealth_presence",
  "wealth_stage_strength",
  "wealth_void_status",
  "wealth_general_modifier",
] as const;
const STATE_OBSERVATION_KEYS = ["matched_count", "stages", "correspondences"] as const;
const STATE_DIMENSION_KEYS = [
  "canonical_dimension",
  "requested_dimension",
  "status",
  "source_rule_ids",
  "rule_evidence",
  "stage_status",
  "general_landing_correspondences",
] as const;
const OUTCOME_DIMENSION_KEYS = [
  "canonical_dimension",
  "requested_dimension",
  "status",
  "source_rule_ids",
  "rule_evidence",
  "subject_object_relation",
  "transmissions_to_day",
  "initial_final_relation",
  "stage_flow",
] as const;
const RELATIONSHIP_DIMENSION_KEYS = [
  "canonical_dimension",
  "requested_dimension",
  "status",
  "source_rule_ids",
  "rule_evidence",
  "subject_object_relation",
  "six_relative_stages",
  "stage_flow",
] as const;
const WORK_DIMENSION_KEYS = [
  "canonical_dimension",
  "requested_dimension",
  "status",
  "source_rule_ids",
  "rule_evidence",
  "six_relative_stages",
  "stage_status",
  "subject_object_relation",
  "target_relative",
  "target_contract_status",
  "target_presence",
  "target_strength",
  "target_general_modifier",
] as const;
const RULE_EVIDENCE_KEYS = [
  "catalog_schema",
  "hard_verdict",
  "matched",
  "not_evaluated",
  "requires_school_adjudication",
  "scope_boundaries",
  "status",
] as const;
const MATCHED_EVIDENCE_REQUIRED_KEYS = [
  "activation_id",
  "dependency_group",
  "fact_paths",
  "observation",
  "polarity",
  "rule_id",
  "rule_key",
  "source_refs",
  "status",
  "weight_class",
] as const;
const MATCHED_EVIDENCE_OPTIONAL_KEYS = ["confidence_ceiling", "stop_conditions"] as const;
const NOT_EVALUATED_KEYS = [
  "activation_id",
  "reason",
  "rule_id",
  "rule_key",
  "source_refs",
  "status",
] as const;
const SOURCE_REF_REQUIRED_KEYS = ["pack", "rule_id", "source_anchor"] as const;
const SOURCE_REF_OPTIONAL_KEYS = ["quote_id"] as const;
const WEALTH_PRESENT_SOURCE_REFS = [
  {
    pack: "san-shi/liuren-miben",
    rule_id: "LM-R20",
    quote_id: "LM-Q072",
    source_anchor: "fulltext.md#L4917",
  },
] as const;
const WEALTH_VOID_SOURCE_REFS = [
  ...WEALTH_PRESENT_SOURCE_REFS,
  {
    pack: "san-shi/liuren-miben",
    rule_id: "LM-R10",
    quote_id: "LM-Q051",
    source_anchor: "fulltext.md#L3568",
  },
] as const;
const MIDDLE_VOID_SOURCE_REFS = [WEALTH_VOID_SOURCE_REFS[1]] as const;
const WORK_TARGET_SOURCE_REFS = [
  {
    pack: "san-shi/liuren-zhiyin",
    rule_id: "LR-19",
    quote_id: "LZ-Q056",
    source_anchor: "fulltext.md#L777",
  },
] as const;
const WORK_TARGET_FACT_PATHS = [
  "dimension_facts.work.target_relative",
  "dimension_facts.work.target_presence",
] as const;
const WORK_TARGET_EVIDENCE_KEYS = [
  ...MATCHED_EVIDENCE_REQUIRED_KEYS,
  "confidence_ceiling",
] as const;
const SIX_RELATIVE_STAGE_KEYS = ["stage", "branch", "six_relative"] as const;
const STAGE_STATUS_KEYS = [
  "stage",
  "branch",
  "six_relative",
  "heavenly_general",
  "season_strength",
  "is_xunkong",
] as const;
const GENERAL_LANDING_KEYS = [
  "stage",
  "heavenly_general",
  "landing_branch",
  "source_pack",
  "source_rule",
  "role",
  "status",
  "source_text",
  "source_anchor",
] as const;
const GENERAL_LANDING_UNAVAILABLE_KEYS = [
  "stage",
  "heavenly_general",
  "landing_branch",
  "source_pack",
  "source_rule",
  "role",
  "status",
] as const;
const WEALTH_GENERAL_MODIFIER_KEYS = [...GENERAL_LANDING_KEYS, "six_relative"] as const;
const WEALTH_GENERAL_MODIFIER_UNAVAILABLE_KEYS = [
  ...GENERAL_LANDING_UNAVAILABLE_KEYS,
  "six_relative",
] as const;
const WORK_OBSERVATION_KEYS = ["target_relative", "target_strength", "target_general_modifier"] as const;
const WORK_ABSENT_KEYS = ["target_relative", "target_presence", "target_contract_status"] as const;
const TARGET_STRENGTH_KEYS = [
  "stage",
  "branch",
  "six_relative",
  "season_strength",
  "is_xunkong",
] as const;
const TARGET_GENERAL_MODIFIER_KEYS = [...GENERAL_LANDING_KEYS, "six_relative"] as const;
const TARGET_GENERAL_MODIFIER_UNAVAILABLE_KEYS = [...GENERAL_LANDING_UNAVAILABLE_KEYS, "six_relative"] as const;
const TIMING_DIMENSION_KEYS = [
  "canonical_dimension",
  "requested_dimension",
  "status",
  "source_rule_ids",
  "rule_evidence",
  "relative_speed",
  "candidate_branch",
  "candidate_date",
] as const;
const TIMING_PACE_RULE_IDS = ["DLR-16", "LR-16"] as const;
const TIMING_CANDIDATE_FACT_PATH = "dimension_facts.timing.candidate_branch";
const TIMING_CANDIDATE_SOURCE_REF = {
  pack: "san-shi/liuren-miben",
  rule_id: "LM-R21",
  source_anchor: "fulltext.md#L3070-L3076",
} as const;
const LOCATION_OBSERVATION_KEYS = ["stage_branch_directions"] as const;
const LOCATION_DIRECTION_KEYS = [
  "stage",
  "branch",
  "direction",
  "direction_chinese",
  "declared_source_anchor",
  "source_binding_status",
  "scope",
] as const;
const LOCATION_STAGES = ["initial", "middle", "final"] as const;
const RELATION_FACT_KEYS = [
  "object",
  "object_element",
  "object_value",
  "relation",
  "subject",
  "subject_element",
  "subject_value",
] as const;
const TRANSMISSION_RELATION_KEYS = [...RELATION_FACT_KEYS, "stage"] as const;
const STAGE_FLOW_KEYS = [...RELATION_FACT_KEYS, "from_stage", "to_stage"] as const;
const ELEMENT_GENERATES = Object.freeze({
  木: "火",
  火: "土",
  土: "金",
  金: "水",
  水: "木",
}) satisfies Readonly<Record<FiveElement, FiveElement>>;
const ELEMENT_OVERCOMES = Object.freeze({
  木: "土",
  火: "金",
  土: "水",
  金: "木",
  水: "火",
}) satisfies Readonly<Record<FiveElement, FiveElement>>;
const DETERMINISTIC_RELATION_FACTS = Object.freeze({
  object_generates_subject: "后者生前者",
  object_overcomes_subject: "后者克前者",
  same_element: "五行同类",
  subject_generates_object: "前者生后者",
  subject_overcomes_object: "前者克后者",
});

type DeterministicRelation = keyof typeof DETERMINISTIC_RELATION_FACTS;

type DeterministicRelationFact = {
  object: string;
  objectElement: FiveElement;
  objectValue: string;
  relation: DeterministicRelation;
  subject: string;
  subjectElement: FiveElement;
  subjectValue: string;
};

type TransmissionRelationFact = DeterministicRelationFact & {
  stage: DaliurenTransmissionStage;
};

type StageFlowFact = DeterministicRelationFact & {
  fromStage: DaliurenTransmissionStage;
  toStage: DaliurenTransmissionStage;
};

type EvidenceEntry = {
  marker: string;
  fact: string;
  sources: readonly EvidenceSource[];
};

type EvidenceSource = {
  key: string;
  label: string;
};

type EvidenceGroup = {
  dimension: DaliurenDimensionId;
  entries: readonly EvidenceEntry[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function readString(value: unknown, key: string): string | null {
  if (!isRecord(value)) return null;
  const field = value[key];
  return typeof field === "string" && field.trim() ? field.trim() : null;
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key));
}

function hasRequiredAndOptionalKeys(
  value: Record<string, unknown>,
  required: readonly string[],
  optional: readonly string[],
): boolean {
  const actual = Object.keys(value);
  const allowed = new Set([...required, ...optional]);
  return (
    required.every((key) => Object.prototype.hasOwnProperty.call(value, key)) &&
    actual.every((key) => allowed.has(key))
  );
}

function hasOwnKey<T extends object>(value: T, key: PropertyKey): key is keyof T {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function isTransmissionStage(value: unknown): value is DaliurenTransmissionStage {
  return typeof value === "string" && hasOwnKey(STAGE_FACTS, value);
}

function isSeasonStrength(value: unknown): value is DaliurenSeasonStrength {
  return typeof value === "string" && hasOwnKey(SEASON_STRENGTH_FACTS, value);
}

function isSixRelative(value: unknown): value is DaliurenSixRelative {
  return typeof value === "string" && SIX_RELATIVES.has(value as DaliurenSixRelative);
}

function isEarthlyBranch(value: unknown): value is string {
  return typeof value === "string" && hasOwnKey(EARTHLY_BRANCH_ELEMENTS, value);
}

function isHeavenlyGeneral(value: unknown): value is DaliurenHeavenlyGeneral {
  return typeof value === "string" && HEAVENLY_GENERALS.has(value as DaliurenHeavenlyGeneral);
}

function hasRuntimeStageOrder(rows: readonly { readonly stage: DaliurenTransmissionStage }[]): boolean {
  let previous = -1;
  for (const row of rows) {
    const current = LOCATION_STAGES.indexOf(row.stage);
    if (current <= previous) return false;
    previous = current;
  }
  return true;
}

function isFiveElement(value: unknown): value is FiveElement {
  return typeof value === "string" && FIVE_ELEMENTS.includes(value as FiveElement);
}

function directedRelation(subject: FiveElement, object: FiveElement): DeterministicRelation {
  if (subject === object) return "same_element";
  if (ELEMENT_GENERATES[subject] === object) return "subject_generates_object";
  if (ELEMENT_GENERATES[object] === subject) return "object_generates_subject";
  if (ELEMENT_OVERCOMES[subject] === object) return "subject_overcomes_object";
  return "object_overcomes_subject";
}

function fixedElement(role: string, value: string): FiveElement | null {
  if (role === "day_stem") {
    return hasOwnKey(HEAVENLY_STEM_ELEMENTS, value) ? HEAVENLY_STEM_ELEMENTS[value] : null;
  }
  if (
    role === "day_branch" ||
    role === "transmission_branch" ||
    role === "initial_branch" ||
    role === "final_branch" ||
    role === "from_branch" ||
    role === "to_branch"
  ) {
    return hasOwnKey(EARTHLY_BRANCH_ELEMENTS, value) ? EARTHLY_BRANCH_ELEMENTS[value] : null;
  }
  return null;
}

function parseRelationFact(
  value: unknown,
  subject: string,
  object: string,
  exactKeys: readonly string[] = RELATION_FACT_KEYS,
): DeterministicRelationFact | null {
  if (!isRecord(value) || !hasExactKeys(value, exactKeys)) return null;
  const subjectValue = readString(value, "subject_value");
  const objectValue = readString(value, "object_value");
  if (
    value.subject !== subject ||
    value.object !== object ||
    !subjectValue ||
    !objectValue ||
    !isFiveElement(value.subject_element) ||
    !isFiveElement(value.object_element) ||
    fixedElement(subject, subjectValue) !== value.subject_element ||
    fixedElement(object, objectValue) !== value.object_element
  ) {
    return null;
  }
  const relation = directedRelation(value.subject_element, value.object_element);
  if (value.relation !== relation) return null;
  return {
    object,
    objectElement: value.object_element,
    objectValue,
    relation,
    subject,
    subjectElement: value.subject_element,
    subjectValue,
  };
}

function parseTransmissionRelation(
  value: unknown,
  stage: DaliurenTransmissionStage,
): TransmissionRelationFact | null {
  const relation = parseRelationFact(value, "transmission_branch", "day_stem", TRANSMISSION_RELATION_KEYS);
  if (!relation || !isRecord(value) || value.stage !== stage) return null;
  return { ...relation, stage };
}

function parseStageFlowRelation(
  value: unknown,
  fromStage: DaliurenTransmissionStage,
  toStage: DaliurenTransmissionStage,
): StageFlowFact | null {
  const relation = parseRelationFact(value, "from_branch", "to_branch", STAGE_FLOW_KEYS);
  if (!relation || !isRecord(value) || value.from_stage !== fromStage || value.to_stage !== toStage) return null;
  return { ...relation, fromStage, toStage };
}

function parseSixRelativeStage(
  value: unknown,
  stage: DaliurenTransmissionStage,
): DaliurenSixRelativeStage | null {
  if (!isRecord(value) || !hasExactKeys(value, SIX_RELATIVE_STAGE_KEYS)) return null;
  const branch = readString(value, "branch");
  if (value.stage !== stage || !isEarthlyBranch(branch) || !isSixRelative(value.six_relative)) return null;
  return { branch, six_relative: value.six_relative, stage };
}

function parseStageStatus(
  value: unknown,
  stage: DaliurenTransmissionStage,
): DaliurenStageStatusEntry | null {
  if (!isRecord(value) || !hasExactKeys(value, STAGE_STATUS_KEYS)) return null;
  const branch = readString(value, "branch");
  const heavenlyGeneral = readString(value, "heavenly_general");
  if (
    value.stage !== stage ||
    !isEarthlyBranch(branch) ||
    !isHeavenlyGeneral(heavenlyGeneral) ||
    !isSixRelative(value.six_relative) ||
    !isSeasonStrength(value.season_strength) ||
    typeof value.is_xunkong !== "boolean"
  ) {
    return null;
  }
  return {
    branch,
    heavenly_general: heavenlyGeneral,
    is_xunkong: value.is_xunkong,
    season_strength: value.season_strength,
    six_relative: value.six_relative,
    stage,
  };
}

function isLocationDirection<Stage extends DaliurenTransmissionStage>(
  value: unknown,
  stage: Stage,
): value is DaliurenStageBranchDirection<Stage> {
  if (!isRecord(value) || !hasExactKeys(value, LOCATION_DIRECTION_KEYS)) return false;
  const direction = readString(value, "direction");
  return Boolean(
    value.stage === stage &&
      readString(value, "branch") &&
      direction &&
      hasOwnKey(DIRECTION_LABELS, direction) &&
      value.direction_chinese === DIRECTION_LABELS[direction] &&
      readString(value, "declared_source_anchor") &&
      value.source_binding_status === "unverified_source_excerpt_not_in_release" &&
      value.scope === "symbolic_direction_candidate_only",
  );
}

function isLocationObservation(value: unknown): value is DaliurenLocationObservation {
  if (!isRecord(value) || !hasExactKeys(value, LOCATION_OBSERVATION_KEYS)) return false;
  const rows = value.stage_branch_directions;
  return (
    Array.isArray(rows) &&
    rows.length === LOCATION_STAGES.length &&
    LOCATION_STAGES.every((stage, index) => isLocationDirection(rows[index], stage))
  );
}

function locationFact(value: unknown): string | null {
  if (!isLocationObservation(value)) return null;
  const rows = value.stage_branch_directions
    .map((row) => `${STAGE_FACTS[row.stage]} ${row.branch} · ${row.direction_chinese}`)
    .join("；");
  return `三传象意方位候选：${rows} · 边界：只表示地支对应的象意方向；来源摘录尚未纳入签名发行`;
}

function isMiddleVoidObservation(value: unknown): value is DaliurenMiddleVoidObservation {
  return (
    isRecord(value) &&
    hasExactKeys(value, MIDDLE_VOID_KEYS) &&
    value.stage === "middle" &&
    Boolean(readString(value, "branch")) &&
    value.is_xunkong === true
  );
}

function middleVoidFact(value: DaliurenMiddleVoidObservation): string {
  return `中传旬空：${value.branch}`;
}

function isOutcomeObservation(value: unknown): value is DaliurenOutcomeObservation {
  if (!isRecord(value)) return false;
  if (hasExactKeys(value, OUTCOME_RELATIONSHIP_KEYS)) {
    const relation = readString(value, "relation");
    return Boolean(
      relation &&
        (relation === "subject_overcomes_object" || relation === "object_overcomes_subject"),
    );
  }
  if (hasExactKeys(value, OUTCOME_TRANSMISSION_KEYS)) {
    const relations = value.relations;
    return (
      Array.isArray(relations) &&
      relations.length === 3 &&
      relations.every(
        (relation) => relation === "subject_generates_object" || relation === "subject_overcomes_object",
      ) &&
      relations.every((relation) => relation === relations[0])
    );
  }
  return isMiddleVoidObservation(value);
}

function outcomeFact(value: unknown): string | null {
  if (!isOutcomeObservation(value)) return null;
  if ("relation" in value) return `结构关系：${OUTCOME_RELATION_FACTS[value.relation]}`;
  if ("relations" in value) return `三传与日干关系：${TRANSMISSION_RELATION_FACTS[value.relations[0]]}`;
  return middleVoidFact(value);
}

function isRelationshipObservation(value: unknown): value is DaliurenRelationshipObservation {
  if (!isRecord(value) || !hasExactKeys(value, RELATIONSHIP_OBSERVATION_KEYS)) return false;
  const relation = readString(value, "relation");
  return Boolean(relation && hasOwnKey(RELATIONSHIP_FACTS, relation));
}

function isCandidateBranch(value: unknown): value is DaliurenTimingCandidateObservation["candidate_branch"] {
  return (
    isRecord(value) &&
    hasExactKeys(value, CANDIDATE_BRANCH_KEYS) &&
    Boolean(readString(value, "anchor_earth_branch")) &&
    Boolean(readString(value, "branch")) &&
    value.source_rule === "LM-R21"
  );
}

function isCandidateDate(value: unknown): value is NonNullable<DaliurenTimingCandidateObservation["candidate_date"]> {
  return (
    isRecord(value) &&
    hasExactKeys(value, CANDIDATE_DATE_KEYS) &&
    value.id === "initial_group_upper_candidate" &&
    value.role === "event_response_candidate" &&
    Boolean(readString(value, "anchor_earth_branch")) &&
    Boolean(readString(value, "branch")) &&
    Boolean(readString(value, "solar_date")) &&
    Boolean(readString(value, "day_ganzhi")) &&
    typeof value.days_after_cast === "number" &&
    Number.isInteger(value.days_after_cast) &&
    Boolean(readString(value, "source_pack")) &&
    value.source_rule === "LM-R21" &&
    value.candidate_not_guarantee === true
  );
}

function isTimingObservation(value: unknown): value is DaliurenTimingObservation {
  if (!isRecord(value)) return false;
  if (hasExactKeys(value, TIMING_PACE_KEYS)) {
    return typeof value.relative_speed === "string" && hasOwnKey(RELATIVE_SPEED_FACTS, value.relative_speed);
  }
  if (!hasExactKeys(value, TIMING_OBSERVATION_KEYS)) return false;
  const candidateBranch = value.candidate_branch;
  const candidateDate = value.candidate_date;
  const relativeSpeed = value.relative_speed;
  if (!isCandidateBranch(candidateBranch)) return false;
  if (candidateDate !== null && !isCandidateDate(candidateDate)) return false;
  if (
    relativeSpeed !== null &&
    (typeof relativeSpeed !== "string" || !hasOwnKey(RELATIVE_SPEED_FACTS, relativeSpeed))
  ) {
    return false;
  }
  return (
    candidateDate === null ||
    (candidateDate.branch === candidateBranch.branch &&
      candidateDate.anchor_earth_branch === candidateBranch.anchor_earth_branch &&
      candidateDate.source_rule === candidateBranch.source_rule)
  );
}

function isWealthStage(value: unknown): value is WealthStage {
  return (
    isRecord(value) &&
    hasExactKeys(value, WEALTH_STAGE_KEYS) &&
    isTransmissionStage(value.stage) &&
    isEarthlyBranch(value.branch) &&
    value.six_relative === "妻财" &&
    isSeasonStrength(value.season_strength)
  );
}

function isWealthVoidRow(value: unknown): value is WealthVoidRow {
  return (
    isRecord(value) &&
    hasExactKeys(value, WEALTH_VOID_ROW_KEYS) &&
    isTransmissionStage(value.stage) &&
    isEarthlyBranch(value.branch) &&
    value.six_relative === "妻财" &&
    value.is_xunkong === true
  );
}

function isMoneyObservation(value: unknown): value is DaliurenMoneyObservation {
  if (!isRecord(value)) return false;
  if (hasExactKeys(value, WEALTH_PRESENT_KEYS)) {
    return (
      value.wealth_presence === true &&
      Array.isArray(value.wealth_stages) &&
      value.wealth_stages.length > 0 &&
      value.wealth_stages.every(isWealthStage)
    );
  }
  if (hasExactKeys(value, WEALTH_ABSENT_KEYS)) return value.wealth_presence === false;
  if (hasExactKeys(value, WEALTH_VOID_KEYS)) {
    return (
      Array.isArray(value.wealth_void_rows) &&
      value.wealth_void_rows.length > 0 &&
      value.wealth_void_rows.every(isWealthVoidRow)
    );
  }
  return isMiddleVoidObservation(value);
}

function moneyFact(value: unknown): string | null {
  if (!isMoneyObservation(value)) return null;
  if ("wealth_presence" in value && value.wealth_presence === false) return "妻财未入三传";
  if ("wealth_stages" in value) {
    const stages = value.wealth_stages
      .map((row) => `${STAGE_FACTS[row.stage]} ${row.branch}（${SEASON_STRENGTH_FACTS[row.season_strength]}）`)
      .join("、");
    return `妻财入传：${stages}`;
  }
  if ("wealth_void_rows" in value) {
    const rows = value.wealth_void_rows.map((row) => `${STAGE_FACTS[row.stage]} ${row.branch}`).join("、");
    return `妻财旬空：${rows}`;
  }
  return middleVoidFact(value);
}

function hasGeneralLandingBaseFields(value: Record<string, unknown>): boolean {
  return (
    isTransmissionStage(value.stage) &&
    isHeavenlyGeneral(value.heavenly_general) &&
    isEarthlyBranch(value.landing_branch) &&
    value.source_pack === "san-shi/liuren-miben" &&
    value.source_rule === "LM-R01" &&
    value.role === "imagery_correspondence_not_observed_activity"
  );
}

function isGeneralLandingCorrespondence(value: unknown): value is DaliurenGeneralLandingCorrespondence {
  return (
    isRecord(value) &&
    hasExactKeys(value, GENERAL_LANDING_KEYS) &&
    hasGeneralLandingBaseFields(value) &&
    value.status === "source_correspondence_matched" &&
    Boolean(readString(value, "source_text")) &&
    Boolean(readString(value, "source_anchor"))
  );
}

function isGeneralLandingUnavailableCorrespondence(
  value: unknown,
): value is DaliurenGeneralLandingUnavailableCorrespondence {
  return (
    isRecord(value) &&
    hasExactKeys(value, GENERAL_LANDING_UNAVAILABLE_KEYS) &&
    hasGeneralLandingBaseFields(value) &&
    value.status === "no_exact_source_correspondence"
  );
}

function isGeneralLandingRow(value: unknown): value is GeneralLandingCorrespondence {
  return isGeneralLandingCorrespondence(value) || isGeneralLandingUnavailableCorrespondence(value);
}

function isWealthVoidStatus(value: unknown): value is WealthVoidStatus {
  return (
    isRecord(value) &&
    hasExactKeys(value, WEALTH_VOID_ROW_KEYS) &&
    isTransmissionStage(value.stage) &&
    isEarthlyBranch(value.branch) &&
    value.six_relative === "妻财" &&
    typeof value.is_xunkong === "boolean"
  );
}

function isWealthGeneralModifier(value: unknown): value is WealthGeneralModifier {
  if (
    !isRecord(value) ||
    !hasGeneralLandingBaseFields(value) ||
    !isEarthlyBranch(value.landing_branch) ||
    !isHeavenlyGeneral(value.heavenly_general) ||
    value.six_relative !== "妻财"
  ) {
    return false;
  }
  if (hasExactKeys(value, WEALTH_GENERAL_MODIFIER_KEYS)) {
    return (
      value.status === "source_correspondence_matched" &&
      Boolean(readString(value, "source_text")) &&
      Boolean(readString(value, "source_anchor"))
    );
  }
  return (
    hasExactKeys(value, WEALTH_GENERAL_MODIFIER_UNAVAILABLE_KEYS) &&
    value.status === "no_exact_source_correspondence"
  );
}

function sameWealthStage(left: WealthStage, right: WealthStage): boolean {
  return (
    left.stage === right.stage &&
    left.branch === right.branch &&
    left.six_relative === right.six_relative &&
    left.season_strength === right.season_strength
  );
}

function sameWealthVoidStatus(left: WealthVoidStatus, right: WealthVoidRow): boolean {
  return (
    left.stage === right.stage &&
    left.branch === right.branch &&
    left.six_relative === right.six_relative &&
    left.is_xunkong === right.is_xunkong
  );
}

function isStateObservation(value: unknown): value is DaliurenStateObservation {
  if (!isRecord(value) || !hasExactKeys(value, STATE_OBSERVATION_KEYS)) return false;
  const stages = value.stages;
  const correspondences = value.correspondences;
  if (
    typeof value.matched_count !== "number" ||
    !Number.isInteger(value.matched_count) ||
    value.matched_count <= 0 ||
    !Array.isArray(stages) ||
    !stages.every(isTransmissionStage) ||
    !Array.isArray(correspondences) ||
    !correspondences.every(isGeneralLandingCorrespondence) ||
    stages.length !== value.matched_count ||
    correspondences.length !== value.matched_count
  ) {
    return false;
  }
  return stages.every((stage, index) => correspondences[index]?.stage === stage);
}

function stateFact(value: unknown): string | null {
  if (!isStateObservation(value)) return null;
  const rows = value.correspondences
    .map((row) => `${STAGE_FACTS[row.stage]} ${row.heavenly_general}落${row.landing_branch}`)
    .join("、");
  return `天将落地类象：${rows} · 共 ${value.matched_count} 条`;
}

function sameGeneralLandingCorrespondence(
  left: DaliurenGeneralLandingCorrespondence,
  right: DaliurenGeneralLandingCorrespondence,
): boolean {
  return (
    left.stage === right.stage &&
    left.heavenly_general === right.heavenly_general &&
    left.landing_branch === right.landing_branch &&
    left.source_pack === right.source_pack &&
    left.source_rule === right.source_rule &&
    left.role === right.role &&
    left.status === right.status &&
    left.source_text === right.source_text &&
    left.source_anchor === right.source_anchor
  );
}

function parseTopLevelStateFacts(
  value: Record<string, unknown>,
  evidence: Record<string, unknown>,
): readonly EvidenceEntry[] | null {
  const rows = value.general_landing_correspondences;
  const statusRows = value.stage_status;
  if (
    !hasExactKeys(value, STATE_DIMENSION_KEYS) ||
    value.canonical_dimension !== "state" ||
    (value.requested_dimension !== "state" && value.requested_dimension !== "current_state") ||
    value.status !== "calculated_facts_not_verdict" ||
    !Array.isArray(value.source_rule_ids) ||
    !Array.isArray(statusRows) ||
    statusRows.length !== LOCATION_STAGES.length ||
    !Array.isArray(rows) ||
    rows.length !== LOCATION_STAGES.length ||
    !rows.every(isGeneralLandingRow) ||
    !LOCATION_STAGES.every((stage, index) => rows[index]?.stage === stage) ||
    !hasExactKeys(evidence, RULE_EVIDENCE_KEYS) ||
    evidence.catalog_schema !== "mingli-liuren-executable-rules-v1" ||
    evidence.hard_verdict !== null ||
    evidence.requires_school_adjudication !== true ||
    !Array.isArray(evidence.matched) ||
    !isEmptyArray(evidence.not_evaluated) ||
    !isEmptyArray(evidence.scope_boundaries)
  ) {
    return null;
  }

  const parsedStatusRows = LOCATION_STAGES.map((stage, index) => parseStageStatus(statusRows[index], stage));
  if (parsedStatusRows.some((row) => row === null)) return null;
  const typedStatusRows = parsedStatusRows as readonly DaliurenStageStatusEntry[];
  if (
    typedStatusRows.some(
      (row, index) =>
        row.branch !== rows[index]?.landing_branch ||
        row.heavenly_general !== rows[index]?.heavenly_general,
    )
  ) {
    return null;
  }

  const exactRows = rows.filter(isGeneralLandingCorrespondence);
  const expectedSourceRuleIds = exactRows.length ? ["LM-R01", "LR-09"] : ["LR-09"];
  if (
    value.source_rule_ids.length !== expectedSourceRuleIds.length ||
    value.source_rule_ids.some((ruleId, index) => ruleId !== expectedSourceRuleIds[index]) ||
    evidence.status !== (exactRows.length ? "matched_evidence" : "not_bound")
  ) {
    return null;
  }

  let sources: readonly EvidenceSource[] = [];
  if (exactRows.length) {
    if (evidence.matched.length !== 1) return null;
    const matchedEntry = parseEntry(evidence.matched[0], "state");
    const matchedObservation = isRecord(evidence.matched[0])
      ? evidence.matched[0].observation
      : null;
    if (
      !matchedEntry ||
      matchedEntry.marker !== "LM-R01" ||
      !isStateObservation(matchedObservation) ||
      matchedObservation.correspondences.length !== exactRows.length ||
      !matchedObservation.correspondences.every((row, index) =>
        sameGeneralLandingCorrespondence(row, exactRows[index]),
      )
    ) {
      return null;
    }
    sources = matchedEntry.sources;
  } else if (evidence.matched.length) {
    return null;
  }

  return [
    {
      marker: "LR-09",
      fact: `三传状态：${typedStatusRows
        .map(
          (row) =>
            `${STAGE_FACTS[row.stage]} ${row.branch} · 六亲${row.six_relative} · 天将${row.heavenly_general} · ${
              SEASON_STRENGTH_FACTS[row.season_strength]
            } · ${row.is_xunkong ? "旬空" : "非旬空"}`,
        )
        .join("；")}`,
      sources: [],
    },
    {
      marker: "LM-R01",
      fact: `天将落地类象：${rows
        .map(
          (row) =>
            `${STAGE_FACTS[row.stage]} ${row.heavenly_general}落${row.landing_branch}${
              row.status === "no_exact_source_correspondence" ? "（缺少精确类象来源）" : ""
            }`,
        )
        .join("、")} · 共 ${rows.length} 条`,
      sources,
    },
  ];
}

function isWorkStrength(value: unknown): value is WorkStrength {
  return (
    isRecord(value) &&
    hasExactKeys(value, TARGET_STRENGTH_KEYS) &&
    isTransmissionStage(value.stage) &&
    isEarthlyBranch(value.branch) &&
    isSixRelative(value.six_relative) &&
    isSeasonStrength(value.season_strength) &&
    typeof value.is_xunkong === "boolean"
  );
}

function isWorkGeneralModifier(value: unknown): value is WorkGeneralModifier {
  if (!isRecord(value) || !hasGeneralLandingBaseFields(value) || !isSixRelative(value.six_relative)) return false;
  if (hasExactKeys(value, TARGET_GENERAL_MODIFIER_KEYS)) {
    return (
      value.status === "source_correspondence_matched" &&
      Boolean(readString(value, "source_text")) &&
      Boolean(readString(value, "source_anchor"))
    );
  }
  return (
    hasExactKeys(value, TARGET_GENERAL_MODIFIER_UNAVAILABLE_KEYS) &&
    value.status === "no_exact_source_correspondence"
  );
}

function isWorkObservation(value: unknown): value is DaliurenWorkObservation {
  if (!isRecord(value)) return false;
  if (hasExactKeys(value, WORK_ABSENT_KEYS)) {
    return (
      isSixRelative(value.target_relative) &&
      value.target_presence === false &&
      value.target_contract_status === "bound"
    );
  }
  if (!hasExactKeys(value, WORK_OBSERVATION_KEYS)) return false;
  if (
    !isSixRelative(value.target_relative) ||
    !Array.isArray(value.target_strength) ||
    value.target_strength.length === 0 ||
    !value.target_strength.every(isWorkStrength) ||
    !Array.isArray(value.target_general_modifier) ||
    !value.target_general_modifier.every(isWorkGeneralModifier)
  ) {
    return false;
  }
  return (
    value.target_strength.every((row) => row.six_relative === value.target_relative) &&
    value.target_general_modifier.every((row) => row.six_relative === value.target_relative)
  );
}

function workFact(value: unknown): string | null {
  if (!isWorkObservation(value)) return null;
  if ("target_presence" in value) return `工作所取六亲：${value.target_relative} · 未入三传`;
  const strengths = value.target_strength
    .map(
      (row) =>
        `${STAGE_FACTS[row.stage]} ${row.branch}（${SEASON_STRENGTH_FACTS[row.season_strength]}，${row.is_xunkong ? "旬空" : "非旬空"}）`,
    )
    .join("、");
  return `工作所取六亲：${value.target_relative} · 入传状态：${strengths}`;
}

function workGeneralModifierEntries(rows: readonly WorkGeneralModifier[]): readonly EvidenceEntry[] {
  return rows.map((row) => ({
    marker: "LM-R01",
    fact: `${row.six_relative}天将落地类象：${STAGE_FACTS[row.stage]} ${row.heavenly_general}落${row.landing_branch}${
      row.status === "no_exact_source_correspondence" ? "（无精确类象对应）" : ""
    }`,
    sources:
      row.status === "source_correspondence_matched"
        ? [
            {
              key: `${row.stage}-${row.source_pack}-${row.source_rule}-${row.source_anchor}`,
              label: `${row.source_pack} · ${row.source_rule} · ${row.source_anchor}`,
            },
          ]
        : [],
  }));
}

function sameWorkStrength(left: WorkStrength, right: WorkStrength): boolean {
  return (
    left.stage === right.stage &&
    left.branch === right.branch &&
    left.six_relative === right.six_relative &&
    left.season_strength === right.season_strength &&
    left.is_xunkong === right.is_xunkong
  );
}

function sameWorkGeneralModifier(left: WorkGeneralModifier, right: WorkGeneralModifier): boolean {
  if (
    left.stage !== right.stage ||
    left.heavenly_general !== right.heavenly_general ||
    left.landing_branch !== right.landing_branch ||
    left.source_pack !== right.source_pack ||
    left.source_rule !== right.source_rule ||
    left.role !== right.role ||
    left.status !== right.status ||
    left.six_relative !== right.six_relative
  ) {
    return false;
  }
  if (left.status === "source_correspondence_matched") {
    return (
      right.status === "source_correspondence_matched" &&
      left.source_text === right.source_text &&
      left.source_anchor === right.source_anchor
    );
  }
  return right.status === "no_exact_source_correspondence";
}

function sameWorkObservation(left: DaliurenWorkObservation, right: DaliurenWorkObservation): boolean {
  if (left.target_relative !== right.target_relative) return false;
  if ("target_presence" in left || "target_presence" in right) {
    return (
      "target_presence" in left &&
      "target_presence" in right &&
      left.target_presence === right.target_presence &&
      left.target_contract_status === right.target_contract_status
    );
  }
  return (
    left.target_strength.length === right.target_strength.length &&
    left.target_strength.every((row, index) => {
      const other = right.target_strength[index];
      return other !== undefined && sameWorkStrength(row, other);
    }) &&
    left.target_general_modifier.length === right.target_general_modifier.length &&
    left.target_general_modifier.every((row, index) => {
      const other = right.target_general_modifier[index];
      return other !== undefined && sameWorkGeneralModifier(row, other);
    })
  );
}

function hasRuntimeWorkEvidenceMetadata(
  value: unknown,
  status: "matched" | "scope_boundary",
): boolean {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, WORK_TARGET_EVIDENCE_KEYS) ||
    value.activation_id !== "liuren.target.work.present" ||
    value.dependency_group !== "liuren.target.work.presence" ||
    value.polarity !== "support" ||
    value.rule_id !== "LR-19" ||
    value.rule_key !== "work_target_present" ||
    value.status !== status ||
    value.weight_class !== "primary" ||
    value.confidence_ceiling !== "medium" ||
    !Array.isArray(value.fact_paths) ||
    value.fact_paths.length !== WORK_TARGET_FACT_PATHS.length ||
    value.fact_paths.some((path, index) => path !== WORK_TARGET_FACT_PATHS[index]) ||
    !Array.isArray(value.source_refs) ||
    value.source_refs.length !== WORK_TARGET_SOURCE_REFS.length
  ) {
    return false;
  }
  return value.source_refs.every((source, index) => {
    const expected = WORK_TARGET_SOURCE_REFS[index];
    return (
      expected !== undefined &&
      isRecord(source) &&
      hasRequiredAndOptionalKeys(source, SOURCE_REF_REQUIRED_KEYS, SOURCE_REF_OPTIONAL_KEYS) &&
      Object.keys(source).length === SOURCE_REF_REQUIRED_KEYS.length + SOURCE_REF_OPTIONAL_KEYS.length &&
      source.pack === expected.pack &&
      source.rule_id === expected.rule_id &&
      source.quote_id === expected.quote_id &&
      source.source_anchor === expected.source_anchor
    );
  });
}

function relationshipFact(value: unknown): string | null {
  return isRelationshipObservation(value) ? `主客关系：${RELATIONSHIP_FACTS[value.relation]}` : null;
}

function timingFact(value: unknown): string | null {
  if (!isTimingObservation(value)) return null;
  if (!("candidate_branch" in value)) return `相对节奏：${RELATIVE_SPEED_FACTS[value.relative_speed]}`;
  const facts = [`规则候选支：${value.candidate_branch.branch}`];
  if (value.candidate_date) {
    facts.push(`候选日期：${value.candidate_date.solar_date}（${value.candidate_date.day_ganzhi}日）`);
  }
  return facts.join(" · ");
}

const RUNTIME_OBSERVATION_FACTS = Object.freeze({
  location: locationFact,
  money: moneyFact,
  outcome: outcomeFact,
  relationship: relationshipFact,
  state: stateFact,
  timing: timingFact,
  work: workFact,
}) satisfies Readonly<{
  [Dimension in keyof DaliurenDimensionObservationMap]: (value: unknown) => string | null;
}>;

function observationFact(dimension: DaliurenDimensionId, value: unknown): string | null {
  return RUNTIME_OBSERVATION_FACTS[dimension](value);
}

function evidenceObservation(value: unknown): unknown {
  return isRecord(value) ? value.observation : null;
}

function moneyPresence(value: unknown): boolean | null {
  if (!isMoneyObservation(value)) return null;
  if ("wealth_presence" in value) return value.wealth_presence;
  return "wealth_void_rows" in value ? true : null;
}

function workPresence(value: unknown): boolean | null {
  if (!isWorkObservation(value)) return null;
  return "target_presence" in value ? false : true;
}

function hasBooleanConflict(values: readonly (boolean | null)[]): boolean {
  return values.includes(true) && values.includes(false);
}

function hasConflictingPresenceObservations(
  value: Record<string, unknown>,
  dimension: DaliurenDimensionId,
  matched: readonly unknown[],
  scopeBoundaries: readonly unknown[],
): boolean {
  if (!matched.length || !scopeBoundaries.length) return false;
  const observations = [...matched, ...scopeBoundaries].map(evidenceObservation);
  if (dimension === "money") {
    const topLevelPresence =
      typeof value.wealth_presence === "boolean" ? value.wealth_presence : null;
    return hasBooleanConflict([topLevelPresence, ...observations.map(moneyPresence)]);
  }
  if (dimension === "work") {
    const topLevelPresence =
      typeof value.target_presence === "boolean" ? value.target_presence : null;
    const targetRelative = readString(value, "target_relative");
    const typedObservations = observations.filter(isWorkObservation);
    return (
      hasBooleanConflict([topLevelPresence, ...typedObservations.map(workPresence)]) ||
      Boolean(
        targetRelative &&
          typedObservations.some((observation) => observation.target_relative !== targetRelative),
      )
    );
  }
  return false;
}

function parseSource(value: unknown): EvidenceSource | null {
  if (!isRecord(value)) return null;
  const pack = readString(value, "pack");
  const ruleId = readString(value, "rule_id");
  if (!pack || !ruleId) return null;
  const quoteId = readString(value, "quote_id");
  const anchor = readString(value, "source_anchor");
  const label = [pack, ruleId, quoteId, anchor].filter(Boolean).join(" · ");
  return {
    key: label,
    label,
  };
}

function parseRuntimeSource(value: unknown): EvidenceSource | null {
  if (
    !isRecord(value) ||
    !hasRequiredAndOptionalKeys(value, SOURCE_REF_REQUIRED_KEYS, SOURCE_REF_OPTIONAL_KEYS) ||
    !readString(value, "pack") ||
    !readString(value, "rule_id") ||
    !readString(value, "source_anchor") ||
    (hasOwnKey(value, "quote_id") && !readString(value, "quote_id"))
  ) {
    return null;
  }
  return parseSource(value);
}

type RuntimeMoneyMatchExpectation = Readonly<{
  activationId: string;
  dependencyGroup: string;
  factPath: string;
  polarity: string;
  ruleId: string;
  ruleKey: string;
  sourceRefs: readonly Readonly<{
    pack: string;
    rule_id: string;
    quote_id: string;
    source_anchor: string;
  }>[];
  weightClass: string;
}>;

function hasRuntimeMoneyMatchMetadata(
  value: unknown,
  expected: RuntimeMoneyMatchExpectation,
): boolean {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, MATCHED_EVIDENCE_REQUIRED_KEYS) ||
    value.activation_id !== expected.activationId ||
    value.dependency_group !== expected.dependencyGroup ||
    value.polarity !== expected.polarity ||
    value.rule_id !== expected.ruleId ||
    value.rule_key !== expected.ruleKey ||
    value.status !== "matched" ||
    value.weight_class !== expected.weightClass ||
    !Array.isArray(value.fact_paths) ||
    value.fact_paths.length !== 1 ||
    value.fact_paths[0] !== expected.factPath ||
    !Array.isArray(value.source_refs) ||
    value.source_refs.length !== expected.sourceRefs.length
  ) {
    return false;
  }
  return value.source_refs.every((source, index) => {
    const expectedSource = expected.sourceRefs[index];
    return (
      expectedSource !== undefined &&
      isRecord(source) &&
      hasRequiredAndOptionalKeys(source, SOURCE_REF_REQUIRED_KEYS, SOURCE_REF_OPTIONAL_KEYS) &&
      Object.keys(source).length === SOURCE_REF_REQUIRED_KEYS.length + SOURCE_REF_OPTIONAL_KEYS.length &&
      source.pack === expectedSource.pack &&
      source.rule_id === expectedSource.rule_id &&
      source.quote_id === expectedSource.quote_id &&
      source.source_anchor === expectedSource.source_anchor
    );
  });
}

function hasRuntimeEvidenceEnvelope(value: Record<string, unknown>): boolean {
  return (
    hasExactKeys(value, RULE_EVIDENCE_KEYS) &&
    value.catalog_schema === "mingli-liuren-executable-rules-v1" &&
    value.hard_verdict === null &&
    value.requires_school_adjudication === true &&
    Array.isArray(value.matched) &&
    Array.isArray(value.not_evaluated) &&
    Array.isArray(value.scope_boundaries)
  );
}

function isRuntimeNotEvaluatedEntry(value: unknown): boolean {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, NOT_EVALUATED_KEYS) ||
    !readString(value, "activation_id") ||
    !readString(value, "reason") ||
    !readString(value, "rule_id") ||
    !readString(value, "rule_key") ||
    !readString(value, "status") ||
    !Array.isArray(value.source_refs) ||
    value.source_refs.length === 0
  ) {
    return false;
  }
  return value.source_refs.every((source) => parseRuntimeSource(source) !== null);
}

function parseRuntimeMatchedEntry(
  value: unknown,
  dimension: DaliurenDimensionId,
): { entry: EvidenceEntry; observation: unknown } | null {
  if (!isRecord(value)) return null;
  const ruleId = readString(value, "rule_id");
  if (
    !hasRequiredAndOptionalKeys(
      value,
      MATCHED_EVIDENCE_REQUIRED_KEYS,
      MATCHED_EVIDENCE_OPTIONAL_KEYS,
    ) ||
    !readString(value, "activation_id") ||
    !readString(value, "dependency_group") ||
    !readString(value, "polarity") ||
    !ruleId ||
    !readString(value, "rule_key") ||
    value.status !== "matched" ||
    !readString(value, "weight_class") ||
    !Array.isArray(value.fact_paths) ||
    value.fact_paths.length === 0 ||
    !value.fact_paths.every((path) => typeof path === "string" && Boolean(path.trim())) ||
    !Array.isArray(value.source_refs) ||
    value.source_refs.length === 0 ||
    (hasOwnKey(value, "confidence_ceiling") && !readString(value, "confidence_ceiling")) ||
    (hasOwnKey(value, "stop_conditions") &&
      (!Array.isArray(value.stop_conditions) ||
        !value.stop_conditions.every(
          (condition) => typeof condition === "string" && Boolean(condition.trim()),
        )))
  ) {
    return null;
  }
  const fact = observationFact(dimension, value.observation);
  const sources = value.source_refs.map(parseRuntimeSource);
  if (!fact || sources.some((source) => source === null)) return null;
  return {
    entry: {
      marker: ruleId,
      fact,
      sources: sources as readonly EvidenceSource[],
    },
    observation: value.observation,
  };
}

function parseEntry(value: unknown, dimension: DaliurenDimensionId): EvidenceEntry | null {
  if (!isRecord(value)) return null;
  const ruleId = readString(value, "rule_id");
  const fact = observationFact(dimension, value.observation);
  if (!ruleId || !fact) return null;
  const refs = value.source_refs;
  return {
    marker: ruleId,
    fact,
    sources: Array.isArray(refs)
      ? refs.map(parseSource).filter((source): source is EvidenceSource => source !== null)
      : [],
  };
}

function isEmptyArray(value: unknown): value is readonly [] {
  return Array.isArray(value) && value.length === 0;
}

function parseScopeBoundaryEntry(value: unknown, dimension: DaliurenDimensionId): EvidenceEntry | null {
  if (!isRecord(value) || value.status !== "scope_boundary") return null;
  return parseEntry(value, dimension);
}

function parseScopeBoundaryFacts(
  value: Record<string, unknown>,
  dimension: DaliurenDimensionId,
  scopeBoundaries: readonly unknown[],
): readonly EvidenceEntry[] {
  if (dimension === "money") {
    if (
      value.wealth_presence !== false ||
      !isEmptyArray(value.wealth_stage_strength) ||
      !isEmptyArray(value.wealth_void_status) ||
      !isEmptyArray(value.wealth_general_modifier)
    ) {
      return [];
    }
    const entries = scopeBoundaries
      .map((entry) => parseScopeBoundaryEntry(entry, dimension))
      .filter((entry): entry is EvidenceEntry => entry?.fact === "妻财未入三传");
    return entries.length === scopeBoundaries.length ? entries : [];
  }
  if (dimension === "work") {
    const targetRelative = readString(value, "target_relative");
    if (
      !targetRelative ||
      !isSixRelative(targetRelative) ||
      value.target_presence !== false ||
      value.target_contract_status !== "bound" ||
      !isEmptyArray(value.target_strength) ||
      !isEmptyArray(value.target_general_modifier)
    ) {
      return [];
    }
    const expectedFact = `工作所取六亲：${targetRelative} · 未入三传`;
    const entries = scopeBoundaries
      .map((entry) => parseScopeBoundaryEntry(entry, dimension))
      .filter((entry): entry is EvidenceEntry => entry?.fact === expectedFact);
    return entries.length === scopeBoundaries.length ? entries : [];
  }
  return [];
}

function parseTopLevelMoneyFacts(
  value: Record<string, unknown>,
  evidence: Record<string, unknown>,
): readonly EvidenceEntry[] | null {
  const strengthRows = value.wealth_stage_strength;
  const voidRows = value.wealth_void_status;
  const modifierRows = value.wealth_general_modifier;
  if (
    !hasExactKeys(value, MONEY_DIMENSION_KEYS) ||
    value.canonical_dimension !== "money" ||
    value.requested_dimension !== "money" ||
    value.status !== "calculated_facts_not_verdict" ||
    value.wealth_presence !== true ||
    !Array.isArray(value.source_rule_ids) ||
    value.source_rule_ids.length !== 1 ||
    value.source_rule_ids[0] !== "LM-R20" ||
    !Array.isArray(strengthRows) ||
    strengthRows.length === 0 ||
    !strengthRows.every(isWealthStage) ||
    !Array.isArray(voidRows) ||
    voidRows.length !== strengthRows.length ||
    !voidRows.every(isWealthVoidStatus) ||
    !Array.isArray(modifierRows) ||
    modifierRows.length !== strengthRows.length ||
    !modifierRows.every(isWealthGeneralModifier) ||
    !hasRuntimeEvidenceEnvelope(evidence) ||
    evidence.status !== "matched_evidence" ||
    !isEmptyArray(evidence.not_evaluated) ||
    !isEmptyArray(evidence.scope_boundaries) ||
    !Array.isArray(evidence.matched) ||
    evidence.matched.length === 0
  ) {
    return null;
  }

  const typedStrengthRows = strengthRows as readonly WealthStage[];
  const typedVoidRows = voidRows as readonly WealthVoidStatus[];
  const typedModifierRows = modifierRows as readonly WealthGeneralModifier[];
  if (
    !hasRuntimeStageOrder(typedStrengthRows) ||
    !hasRuntimeStageOrder(typedVoidRows) ||
    !hasRuntimeStageOrder(typedModifierRows) ||
    typedVoidRows.some(
      (row, index) =>
        row.stage !== typedStrengthRows[index]?.stage ||
        row.branch !== typedStrengthRows[index]?.branch,
    ) ||
    typedModifierRows.some(
      (row, index) =>
        row.stage !== typedStrengthRows[index]?.stage ||
        row.landing_branch !== typedStrengthRows[index]?.branch,
    )
  ) {
    return null;
  }

  const parsedMatches = evidence.matched.map((entry) => parseRuntimeMatchedEntry(entry, "money"));
  if (parsedMatches.some((entry) => entry === null)) return null;
  const typedMatches = parsedMatches as readonly { entry: EvidenceEntry; observation: unknown }[];

  let matchIndex = 0;
  const presenceMatch = typedMatches[matchIndex];
  const presenceRecord = evidence.matched[matchIndex];
  if (
    !presenceMatch ||
    presenceMatch.entry.marker !== "LM-R20" ||
    !isMoneyObservation(presenceMatch.observation) ||
    !("wealth_stages" in presenceMatch.observation) ||
    presenceMatch.observation.wealth_stages.length !== typedStrengthRows.length ||
    !presenceMatch.observation.wealth_stages.every((row, index) =>
      sameWealthStage(row, typedStrengthRows[index] as WealthStage),
    ) ||
    !hasRuntimeMoneyMatchMetadata(presenceRecord, {
      activationId: "liuren.wealth.present.miben",
      dependencyGroup: "wealth_receipt_availability",
      factPath: "dimension_facts.money.wealth_presence",
      polarity: "support",
      ruleId: "LM-R20",
      ruleKey: "wealth_present_miben",
      sourceRefs: WEALTH_PRESENT_SOURCE_REFS,
      weightClass: "primary",
    })
  ) {
    return null;
  }
  matchIndex += 1;

  const trueVoidRows = typedVoidRows.filter(
    (row): row is WealthVoidStatus & { readonly is_xunkong: true } => row.is_xunkong,
  );
  if (trueVoidRows.length) {
    const voidMatch = typedMatches[matchIndex];
    const voidRecord = evidence.matched[matchIndex];
    if (
      !voidMatch ||
      voidMatch.entry.marker !== "LM-R20" ||
      !isMoneyObservation(voidMatch.observation) ||
      !("wealth_void_rows" in voidMatch.observation) ||
      voidMatch.observation.wealth_void_rows.length !== trueVoidRows.length ||
      !voidMatch.observation.wealth_void_rows.every((row, index) =>
        sameWealthVoidStatus(trueVoidRows[index] as WealthVoidStatus, row),
      ) ||
      !hasRuntimeMoneyMatchMetadata(voidRecord, {
        activationId: "liuren.wealth.void",
        dependencyGroup: "wealth_receipt_availability",
        factPath: "dimension_facts.money.wealth_void_status",
        polarity: "oppose",
        ruleId: "LM-R20",
        ruleKey: "wealth_void_miben",
        sourceRefs: WEALTH_VOID_SOURCE_REFS,
        weightClass: "primary",
      })
    ) {
      return null;
    }
    matchIndex += 1;
  }

  if (matchIndex < typedMatches.length) {
    const middleMatch = typedMatches[matchIndex];
    const middleRecord = evidence.matched[matchIndex];
    if (
      !middleMatch ||
      middleMatch.entry.marker !== "LM-R10" ||
      !isMiddleVoidObservation(middleMatch.observation) ||
      !isEarthlyBranch(middleMatch.observation.branch) ||
      !hasRuntimeMoneyMatchMetadata(middleRecord, {
        activationId: "liuren.process.middle_void",
        dependencyGroup: "stage_void",
        factPath: "dimension_facts.money.stage_status",
        polarity: "uncertain",
        ruleId: "LM-R10",
        ruleKey: "middle_void_process",
        sourceRefs: MIDDLE_VOID_SOURCE_REFS,
        weightClass: "supporting",
      })
    ) {
      return null;
    }
    const middleStrengthIndex = typedStrengthRows.findIndex((row) => row.stage === "middle");
    if (
      middleStrengthIndex >= 0 &&
      (typedStrengthRows[middleStrengthIndex]?.branch !== middleMatch.observation.branch ||
        typedVoidRows[middleStrengthIndex]?.is_xunkong !== true)
    ) {
      return null;
    }
    matchIndex += 1;
  }
  if (matchIndex !== typedMatches.length) return null;

  return [
    ...typedMatches.map((match) => match.entry),
    ...typedModifierRows.map((row) => ({
      marker: "LM-R01",
      fact: `妻财天将落地类象：${STAGE_FACTS[row.stage]} ${row.heavenly_general}落${row.landing_branch}${
        row.status === "no_exact_source_correspondence" ? "（无精确类象对应）" : ""
      }`,
      sources:
        row.status === "source_correspondence_matched"
          ? [
              {
                key: `${row.stage}-${row.source_pack}-${row.source_rule}-${row.source_anchor}`,
                label: `${row.source_pack} · ${row.source_rule} · ${row.source_anchor}`,
              },
            ]
          : [],
    })),
  ];
}

function timingPaceRuleIds(sourceRuleIds: readonly unknown[]): readonly string[] | null {
  if (
    !Array.isArray(sourceRuleIds) ||
    !sourceRuleIds.every((ruleId) => typeof ruleId === "string" && Boolean(ruleId.trim()))
  ) {
    return null;
  }
  const paceIds = sourceRuleIds
    .map((ruleId) => (ruleId as string).trim())
    .filter((ruleId) => ruleId === "DLR-16" || ruleId === "LR-16");
  const expected = TIMING_PACE_RULE_IDS.filter((ruleId) => paceIds.includes(ruleId));
  if (paceIds.length !== expected.length || paceIds.some((ruleId, index) => ruleId !== expected[index])) {
    return null;
  }
  return paceIds;
}

function parseTimingPaceEntry(
  relativeSpeed: unknown,
  sourceRuleIds: readonly unknown[],
): EvidenceEntry | null {
  if (typeof relativeSpeed !== "string" || !hasOwnKey(RELATIVE_SPEED_FACTS, relativeSpeed)) return null;
  const paceIds = timingPaceRuleIds(sourceRuleIds);
  if (!paceIds || paceIds.length === 0) return null;
  return {
    marker: paceIds.join(" · "),
    fact: `相对节奏：${RELATIVE_SPEED_FACTS[relativeSpeed]}`,
    sources: [],
  };
}

function sameCandidateBranch(
  left: DaliurenTimingCandidateObservation["candidate_branch"],
  right: DaliurenTimingCandidateObservation["candidate_branch"],
): boolean {
  return (
    left.branch === right.branch &&
    left.anchor_earth_branch === right.anchor_earth_branch &&
    left.source_rule === right.source_rule
  );
}

function sameCandidateDate(
  left: NonNullable<DaliurenTimingCandidateObservation["candidate_date"]>,
  right: NonNullable<DaliurenTimingCandidateObservation["candidate_date"]>,
): boolean {
  return (
    left.id === right.id &&
    left.role === right.role &&
    left.anchor_earth_branch === right.anchor_earth_branch &&
    left.branch === right.branch &&
    left.solar_date === right.solar_date &&
    left.day_ganzhi === right.day_ganzhi &&
    left.days_after_cast === right.days_after_cast &&
    left.source_pack === right.source_pack &&
    left.source_rule === right.source_rule &&
    left.candidate_not_guarantee === right.candidate_not_guarantee
  );
}

function hasRuntimeTimingCandidateMetadata(value: unknown): boolean {
  if (
    !isRecord(value) ||
    !hasRequiredAndOptionalKeys(value, MATCHED_EVIDENCE_REQUIRED_KEYS, MATCHED_EVIDENCE_OPTIONAL_KEYS) ||
    value.activation_id !== "liuren.timing.candidate_branch" ||
    value.dependency_group !== "liuren.timing.initial-group-seasonal-upper" ||
    value.polarity !== "uncertain" ||
    value.rule_id !== "LM-R21" ||
    value.rule_key !== "timing_candidate_branch" ||
    value.status !== "matched" ||
    value.weight_class !== "primary" ||
    !Array.isArray(value.fact_paths) ||
    value.fact_paths.length !== 1 ||
    value.fact_paths[0] !== TIMING_CANDIDATE_FACT_PATH ||
    !Array.isArray(value.source_refs) ||
    value.source_refs.length !== 1
  ) {
    return false;
  }
  const source = value.source_refs[0];
  return (
    isRecord(source) &&
    hasRequiredAndOptionalKeys(source, SOURCE_REF_REQUIRED_KEYS, SOURCE_REF_OPTIONAL_KEYS) &&
    Object.keys(source).length === SOURCE_REF_REQUIRED_KEYS.length &&
    source.pack === TIMING_CANDIDATE_SOURCE_REF.pack &&
    source.rule_id === TIMING_CANDIDATE_SOURCE_REF.rule_id &&
    source.source_anchor === TIMING_CANDIDATE_SOURCE_REF.source_anchor
  );
}

function expectedTimingSourceRuleIds(
  hasValidPace: boolean,
  hasCandidate: boolean,
  sourceRuleIds: readonly string[],
): readonly string[] | null {
  if (sourceRuleIds.includes("LR-16") && !hasValidPace) return null;
  const expected = [
    ...(hasValidPace ? (["DLR-16"] as const) : []),
    ...(sourceRuleIds.includes("LR-16") ? (["LR-16"] as const) : []),
    ...(hasCandidate ? (["LM-R21"] as const) : []),
  ];
  if (
    sourceRuleIds.length !== expected.length ||
    sourceRuleIds.some((ruleId, index) => ruleId !== expected[index])
  ) {
    return null;
  }
  return expected;
}

function parseTopLevelTimingFact(value: Record<string, unknown>): EvidenceEntry | null {
  if (
    (value.candidate_branch !== null && value.candidate_branch !== undefined) ||
    (value.candidate_date !== null && value.candidate_date !== undefined)
  ) {
    return null;
  }
  return parseTimingPaceEntry(
    value.relative_speed,
    Array.isArray(value.source_rule_ids) ? value.source_rule_ids : [],
  );
}

function parseTimingFacts(
  value: Record<string, unknown>,
  evidence: Record<string, unknown>,
): readonly EvidenceEntry[] | null {
  const matched = evidence.matched;
  if (!Array.isArray(matched) || !Array.isArray(evidence.scope_boundaries)) return null;

  if (hasExactKeys(value, TIMING_DIMENSION_KEYS)) {
    if (
      value.canonical_dimension !== "timing" ||
      value.requested_dimension !== "timing" ||
      value.status !== "calculated_facts_not_verdict"
    ) {
      return null;
    }
    const sourceRuleIds = value.source_rule_ids;
    if (
      !Array.isArray(sourceRuleIds) ||
      !sourceRuleIds.every((ruleId) => typeof ruleId === "string" && Boolean(ruleId.trim()))
    ) {
      return null;
    }
    const normalizedSourceRuleIds = sourceRuleIds.map((ruleId) => (ruleId as string).trim());
    const relativeSpeed = value.relative_speed;
    const hasValidPace =
      typeof relativeSpeed === "string" && hasOwnKey(RELATIVE_SPEED_FACTS, relativeSpeed);
    const topLevelCandidate = value.candidate_branch;
    const topLevelDate = value.candidate_date;
    if (topLevelCandidate !== null && !isCandidateBranch(topLevelCandidate)) return null;
    if (topLevelDate !== null && !isCandidateDate(topLevelDate)) return null;
    const candidatePresent = isCandidateBranch(topLevelCandidate);
    if (
      candidatePresent &&
      isCandidateDate(topLevelDate) &&
      (topLevelDate.branch !== topLevelCandidate.branch ||
        topLevelDate.anchor_earth_branch !== topLevelCandidate.anchor_earth_branch ||
        topLevelDate.source_rule !== topLevelCandidate.source_rule)
    ) {
      return null;
    }
    if (!expectedTimingSourceRuleIds(hasValidPace, candidatePresent, normalizedSourceRuleIds)) {
      return null;
    }

    const entries: EvidenceEntry[] = [];
    if (isCandidateBranch(topLevelCandidate)) {
      if (
        !hasRuntimeEvidenceEnvelope(evidence) ||
        evidence.status !== "matched_evidence" ||
        matched.length !== 1 ||
        !isEmptyArray(evidence.scope_boundaries) ||
        !isEmptyArray(evidence.not_evaluated) ||
        !hasRuntimeTimingCandidateMetadata(matched[0])
      ) {
        return null;
      }
      const parsed = parseRuntimeMatchedEntry(matched[0], "timing");
      if (
        !parsed ||
        parsed.entry.marker !== "LM-R21" ||
        !isTimingObservation(parsed.observation) ||
        !("candidate_branch" in parsed.observation) ||
        !sameCandidateBranch(parsed.observation.candidate_branch, topLevelCandidate)
      ) {
        return null;
      }
      if (topLevelDate === null) {
        if (parsed.observation.candidate_date !== null) return null;
      } else if (
        !isCandidateDate(topLevelDate) ||
        parsed.observation.candidate_date === null ||
        !sameCandidateDate(parsed.observation.candidate_date, topLevelDate)
      ) {
        return null;
      }
      if (
        parsed.observation.relative_speed !== null &&
        parsed.observation.relative_speed !== relativeSpeed
      ) {
        return null;
      }
      entries.push(parsed.entry);
    } else if (matched.length !== 0 || !isEmptyArray(evidence.scope_boundaries)) {
      return null;
    }

    if (hasValidPace) {
      const pace = parseTimingPaceEntry(relativeSpeed, normalizedSourceRuleIds);
      if (!pace) return null;
      entries.push(pace);
    }

    return entries.length ? entries : null;
  }

  const entries: EvidenceEntry[] = [];
  for (const item of matched) {
    const entry = parseEntry(item, "timing");
    if (entry) entries.push(entry);
  }
  if (!entries.length && isEmptyArray(evidence.scope_boundaries)) {
    const timingEntry = parseTopLevelTimingFact(value);
    if (timingEntry) entries.push(timingEntry);
  }
  return entries.length ? entries : null;
}

function relationFactText(value: DeterministicRelationFact): string {
  return `${value.subjectValue}（${value.subjectElement}）与${value.objectValue}（${value.objectElement}）：${DETERMINISTIC_RELATION_FACTS[value.relation]}`;
}

function parseTopLevelOutcomeFacts(
  value: Record<string, unknown>,
  evidence: Record<string, unknown>,
): readonly EvidenceEntry[] | null {
  const matched = evidence.matched;
  const notEvaluated = evidence.not_evaluated;
  if (
    !hasExactKeys(value, OUTCOME_DIMENSION_KEYS) ||
    value.canonical_dimension !== "outcome" ||
    value.requested_dimension !== "outcome" ||
    value.status !== "calculated_facts_not_verdict" ||
    !hasRuntimeEvidenceEnvelope(evidence) ||
    !Array.isArray(matched) ||
    !Array.isArray(notEvaluated) ||
    !isEmptyArray(evidence.scope_boundaries) ||
    !notEvaluated.every(isRuntimeNotEvaluatedEntry)
  ) {
    return null;
  }
  const sourceRuleIds = value.source_rule_ids;
  if (
    !Array.isArray(sourceRuleIds) ||
    !sourceRuleIds.every((ruleId) => typeof ruleId === "string" && Boolean(ruleId.trim()))
  ) {
    return null;
  }

  const subjectObject = parseRelationFact(value.subject_object_relation, "day_stem", "day_branch");
  const transmissionRows = value.transmissions_to_day;
  const initialFinal = parseRelationFact(value.initial_final_relation, "initial_branch", "final_branch");
  const flowRows = value.stage_flow;
  if (
    !subjectObject ||
    !Array.isArray(transmissionRows) ||
    transmissionRows.length !== LOCATION_STAGES.length ||
    !initialFinal ||
    !Array.isArray(flowRows) ||
    flowRows.length !== 2
  ) {
    return null;
  }

  const transmissions = LOCATION_STAGES.map((stage, index) =>
    parseTransmissionRelation(transmissionRows[index], stage),
  );
  const flows = [
    parseStageFlowRelation(flowRows[0], "initial", "middle"),
    parseStageFlowRelation(flowRows[1], "middle", "final"),
  ] as const;
  if (transmissions.some((row) => row === null) || flows.some((row) => row === null)) return null;
  const typedTransmissions = transmissions as readonly TransmissionRelationFact[];
  const typedFlows = flows as readonly StageFlowFact[];
  if (
    typedTransmissions.some(
      (row) =>
        row.objectValue !== subjectObject.subjectValue ||
        row.objectElement !== subjectObject.subjectElement,
    ) ||
    initialFinal.subjectValue !== typedTransmissions[0]?.subjectValue ||
    initialFinal.subjectElement !== typedTransmissions[0]?.subjectElement ||
    initialFinal.objectValue !== typedTransmissions[2]?.subjectValue ||
    initialFinal.objectElement !== typedTransmissions[2]?.subjectElement ||
    typedFlows.some(
      (row, index) =>
        row.subjectValue !== typedTransmissions[index]?.subjectValue ||
        row.subjectElement !== typedTransmissions[index]?.subjectElement ||
        row.objectValue !== typedTransmissions[index + 1]?.subjectValue ||
        row.objectElement !== typedTransmissions[index + 1]?.subjectElement,
    )
  ) {
    return null;
  }

  const normalizedSourceRuleIds = sourceRuleIds.map((ruleId) => ruleId.trim());
  const subjectMatched =
    subjectObject.relation === "subject_overcomes_object" ||
    subjectObject.relation === "object_overcomes_subject";
  const transmissionMatched =
    typedTransmissions.every((row) => row.relation === "subject_generates_object") ||
    typedTransmissions.every((row) => row.relation === "subject_overcomes_object");
  const initialFinalMatched =
    initialFinal.relation === "subject_overcomes_object" ||
    initialFinal.relation === "object_overcomes_subject";
  const flowSourceMatched =
    typedFlows.every((row) => row.relation === "subject_generates_object") &&
    (typedTransmissions[2]?.relation === "subject_generates_object" ||
      typedTransmissions[2]?.relation === "subject_overcomes_object");
  const expectedSourceRuleIds = [
    ...(subjectMatched ? ["LR-17"] : []),
    ...(transmissionMatched || initialFinalMatched ? ["LR-18"] : []),
    ...(flowSourceMatched ? ["DLR-17"] : []),
  ];
  if (
    normalizedSourceRuleIds.length !== expectedSourceRuleIds.length ||
    normalizedSourceRuleIds.some((ruleId, index) => ruleId !== expectedSourceRuleIds[index])
  ) {
    return null;
  }

  const deterministicEntries: readonly EvidenceEntry[] = [
    {
      marker: "主客五行",
      fact: `日干与日支：${relationFactText(subjectObject)}`,
      sources: [],
    },
    {
      marker: "三传五行",
      fact: `三传与日干：${typedTransmissions
        .map((row) => `${STAGE_FACTS[row.stage]} ${relationFactText(row)}`)
        .join("；")}`,
      sources: [],
    },
    {
      marker: "初末五行",
      fact: `初末关系：${relationFactText(initialFinal)}`,
      sources: [],
    },
    {
      marker: "传间流转",
      fact: `三传流转：${typedFlows
        .map((row) => `${STAGE_FACTS[row.fromStage]}至${STAGE_FACTS[row.toStage]} ${relationFactText(row)}`)
        .join("；")}`,
      sources: [],
    },
  ];

  if (matched.length === 0) {
    return evidence.status === "not_calculated" && expectedSourceRuleIds.length === 0
      ? deterministicEntries
      : null;
  }
  if (evidence.status !== "matched_evidence") return null;

  const parsedMatches = matched.map((entry) => parseRuntimeMatchedEntry(entry, "outcome"));
  if (parsedMatches.some((entry) => entry === null)) return null;
  let subjectMatchCount = 0;
  let transmissionMatchCount = 0;
  let initialFinalMatchCount = 0;
  let middleVoidMatchCount = 0;
  for (const parsed of parsedMatches) {
    if (!parsed) return null;
    const observation = parsed.observation;
    if (!isOutcomeObservation(observation)) return null;
    if (
      parsed.entry.marker === "LR-17" &&
      "relation" in observation &&
      observation.relation === subjectObject.relation
    ) {
      subjectMatchCount += 1;
      continue;
    }
    if (parsed.entry.marker === "LR-18" && "relations" in observation) {
      if (
        observation.relations.length !== typedTransmissions.length ||
        observation.relations.some((relation, index) => relation !== typedTransmissions[index]?.relation)
      ) {
        return null;
      }
      transmissionMatchCount += 1;
      continue;
    }
    if (
      parsed.entry.marker === "LR-18" &&
      "relation" in observation &&
      observation.relation === initialFinal.relation
    ) {
      initialFinalMatchCount += 1;
      continue;
    }
    if (
      parsed.entry.marker === "LM-R10" &&
      "stage" in observation &&
      observation.branch === typedTransmissions[1]?.subjectValue
    ) {
      middleVoidMatchCount += 1;
      continue;
    }
    return null;
  }
  if (
    subjectMatchCount !== Number(subjectMatched) ||
    transmissionMatchCount !== Number(transmissionMatched) ||
    initialFinalMatchCount !== Number(initialFinalMatched) ||
    middleVoidMatchCount > 1
  ) {
    return null;
  }

  return [
    ...(parsedMatches as readonly { entry: EvidenceEntry; observation: unknown }[]).map(
      (entry) => entry.entry,
    ),
    ...deterministicEntries,
  ];
}

function parseTopLevelRelationshipFacts(
  value: Record<string, unknown>,
  evidence: Record<string, unknown>,
): readonly EvidenceEntry[] | null {
  const sourceRuleIds = value.source_rule_ids;
  const stageRows = value.six_relative_stages;
  const flowRows = value.stage_flow;
  if (
    !hasExactKeys(value, RELATIONSHIP_DIMENSION_KEYS) ||
    value.requested_dimension !== "relationship" ||
    value.status !== "calculated_facts_not_verdict" ||
    !Array.isArray(sourceRuleIds) ||
    !sourceRuleIds.every((ruleId) => typeof ruleId === "string" && Boolean(ruleId.trim())) ||
    !hasExactKeys(evidence, RULE_EVIDENCE_KEYS) ||
    !readString(evidence, "catalog_schema") ||
    evidence.requires_school_adjudication !== true ||
    !Array.isArray(evidence.matched) ||
    !Array.isArray(evidence.not_evaluated) ||
    !isEmptyArray(evidence.scope_boundaries) ||
    !Array.isArray(stageRows) ||
    stageRows.length !== LOCATION_STAGES.length ||
    !Array.isArray(flowRows) ||
    flowRows.length !== 2
  ) {
    return null;
  }

  const subjectObject = parseRelationFact(value.subject_object_relation, "day_stem", "day_branch");
  const stages = LOCATION_STAGES.map((stage, index) => parseSixRelativeStage(stageRows[index], stage));
  const flows = [
    parseStageFlowRelation(flowRows[0], "initial", "middle"),
    parseStageFlowRelation(flowRows[1], "middle", "final"),
  ] as const;
  if (!subjectObject || stages.some((row) => row === null) || flows.some((row) => row === null)) {
    return null;
  }

  const typedStages = stages as readonly DaliurenSixRelativeStage[];
  const typedFlows = flows as readonly StageFlowFact[];
  if (
    typedFlows.some(
      (row, index) =>
        row.subjectValue !== typedStages[index]?.branch ||
        row.objectValue !== typedStages[index + 1]?.branch,
    )
  ) {
    return null;
  }

  const normalizedSourceRuleIds = sourceRuleIds.map((ruleId) => ruleId.trim());
  const deterministicEntries: readonly EvidenceEntry[] = [
    {
      marker: "主客五行",
      fact: `日干与日支：${relationFactText(subjectObject)}`,
      sources: [],
    },
    {
      marker: "三传六亲",
      fact: `三传六亲：${typedStages
        .map((row) => `${STAGE_FACTS[row.stage]} ${row.branch} · ${row.six_relative}`)
        .join("；")}`,
      sources: [],
    },
    {
      marker: "传间流转",
      fact: `三传流转：${typedFlows
        .map((row) => `${STAGE_FACTS[row.fromStage]}至${STAGE_FACTS[row.toStage]} ${relationFactText(row)}`)
        .join("；")}`,
      sources: [],
    },
  ];
  if (evidence.matched.length) {
    const matched =
      evidence.matched.length === 1
        ? parseRuntimeMatchedEntry(evidence.matched[0], "relationship")
        : null;
    if (
      !hasRuntimeEvidenceEnvelope(evidence) ||
      evidence.status !== "matched_evidence" ||
      !isEmptyArray(evidence.not_evaluated) ||
      normalizedSourceRuleIds.length !== 1 ||
      normalizedSourceRuleIds[0] !== "LR-17" ||
      !matched ||
      matched.entry.marker !== "LR-17" ||
      !isRelationshipObservation(matched.observation) ||
      matched.observation.relation !== subjectObject.relation
    ) {
      return null;
    }
    return [matched.entry, ...deterministicEntries];
  }

  if (
    evidence.status !== "not_bound" ||
    normalizedSourceRuleIds.length !== 0 ||
    subjectObject.relation === "subject_overcomes_object" ||
    subjectObject.relation === "object_overcomes_subject"
  ) {
    return null;
  }

  return deterministicEntries;
}

function workDeterministicEntries(
  subjectObject: DeterministicRelationFact,
  stages: readonly DaliurenSixRelativeStage[],
  statuses: readonly DaliurenStageStatusEntry[],
): readonly EvidenceEntry[] {
  return [
    {
      marker: "主客五行",
      fact: `日干与日支：${relationFactText(subjectObject)}`,
      sources: [],
    },
    {
      marker: "三传六亲",
      fact: `三传六亲：${stages
        .map((row) => `${STAGE_FACTS[row.stage]} ${row.branch} · ${row.six_relative}`)
        .join("；")}`,
      sources: [],
    },
    {
      marker: "三传状态",
      fact: `三传状态：${statuses
        .map(
          (row) =>
            `${STAGE_FACTS[row.stage]} ${row.branch} · 六亲${row.six_relative} · 天将${row.heavenly_general} · ${
              SEASON_STRENGTH_FACTS[row.season_strength]
            } · ${row.is_xunkong ? "旬空" : "非旬空"}`,
        )
        .join("；")}`,
      sources: [],
    },
  ];
}

function parseTopLevelWorkFacts(
  value: Record<string, unknown>,
  evidence: Record<string, unknown>,
): readonly EvidenceEntry[] | null {
  const stageRows = value.six_relative_stages;
  const statusRows = value.stage_status;
  const sourceRuleIds = value.source_rule_ids;
  if (
    !hasExactKeys(value, WORK_DIMENSION_KEYS) ||
    value.canonical_dimension !== "work" ||
    (value.requested_dimension !== "work" && value.requested_dimension !== "career") ||
    value.status !== "calculated_facts_not_verdict" ||
    !Array.isArray(sourceRuleIds) ||
    !sourceRuleIds.every((ruleId) => typeof ruleId === "string" && Boolean(ruleId.trim())) ||
    !isSixRelative(value.target_relative) ||
    value.target_contract_status !== "bound" ||
    typeof value.target_presence !== "boolean" ||
    !Array.isArray(stageRows) ||
    stageRows.length !== LOCATION_STAGES.length ||
    !Array.isArray(statusRows) ||
    statusRows.length !== LOCATION_STAGES.length ||
    !hasRuntimeEvidenceEnvelope(evidence) ||
    !Array.isArray(evidence.matched) ||
    !Array.isArray(evidence.scope_boundaries) ||
    !isEmptyArray(evidence.not_evaluated)
  ) {
    return null;
  }

  const subjectObject = parseRelationFact(value.subject_object_relation, "day_stem", "day_branch");
  const stages = LOCATION_STAGES.map((stage, index) => parseSixRelativeStage(stageRows[index], stage));
  const statuses = LOCATION_STAGES.map((stage, index) => parseStageStatus(statusRows[index], stage));
  if (!subjectObject || stages.some((row) => row === null) || statuses.some((row) => row === null)) {
    return null;
  }
  const typedStages = stages as readonly DaliurenSixRelativeStage[];
  const typedStatuses = statuses as readonly DaliurenStageStatusEntry[];
  if (
    typedStatuses.some(
      (row, index) =>
        row.branch !== typedStages[index]?.branch ||
        row.six_relative !== typedStages[index]?.six_relative,
    )
  ) {
    return null;
  }

  const targetObservation =
    value.target_presence === false
      ? {
          target_relative: value.target_relative,
          target_presence: false,
          target_contract_status: value.target_contract_status,
        }
      : {
          target_relative: value.target_relative,
          target_strength: value.target_strength,
          target_general_modifier: value.target_general_modifier,
        };
  if (!isWorkObservation(targetObservation)) return null;

  const targetStatuses = typedStatuses.filter(
    (row) => row.six_relative === targetObservation.target_relative,
  );
  if ("target_presence" in targetObservation) {
    if (
      targetStatuses.length !== 0 ||
      !isEmptyArray(value.target_strength) ||
      !isEmptyArray(value.target_general_modifier)
    ) {
      return null;
    }
  } else {
    if (
      targetStatuses.length === 0 ||
      targetObservation.target_strength.length !== targetStatuses.length ||
      targetObservation.target_general_modifier.length !== targetStatuses.length ||
      !hasRuntimeStageOrder(targetObservation.target_strength) ||
      !hasRuntimeStageOrder(targetObservation.target_general_modifier) ||
      targetObservation.target_strength.some((row, index) => {
        const status = targetStatuses[index];
        return (
          status === undefined ||
          row.stage !== status.stage ||
          row.branch !== status.branch ||
          row.six_relative !== status.six_relative ||
          row.season_strength !== status.season_strength ||
          row.is_xunkong !== status.is_xunkong
        );
      }) ||
      targetObservation.target_general_modifier.some((row, index) => {
        const status = targetStatuses[index];
        return (
          status === undefined ||
          row.stage !== status.stage ||
          row.landing_branch !== status.branch ||
          row.heavenly_general !== status.heavenly_general ||
          row.six_relative !== status.six_relative
        );
      })
    ) {
      return null;
    }
  }

  const deterministicEntries = workDeterministicEntries(subjectObject, typedStages, typedStatuses);

  const normalizedSourceRuleIds = sourceRuleIds.map((ruleId) => ruleId.trim());
  if ("target_presence" in targetObservation) {
    const scope = evidence.scope_boundaries[0];
    const parsed = parseScopeBoundaryEntry(scope, "work");
    if (
      normalizedSourceRuleIds.length !== 0 ||
      evidence.status !== "scope_boundary" ||
      !isEmptyArray(evidence.matched) ||
      evidence.scope_boundaries.length !== 1 ||
      !hasRuntimeWorkEvidenceMetadata(scope, "scope_boundary") ||
      !isRecord(scope) ||
      !isWorkObservation(scope.observation) ||
      !sameWorkObservation(scope.observation, targetObservation) ||
      !parsed
    ) {
      return null;
    }
    return [parsed, ...deterministicEntries];
  }

  const matched = evidence.matched[0];
  const parsed = parseRuntimeMatchedEntry(matched, "work");
  if (
    normalizedSourceRuleIds.length !== 1 ||
    normalizedSourceRuleIds[0] !== "LR-19" ||
    evidence.status !== "matched_evidence" ||
    evidence.matched.length !== 1 ||
    !isEmptyArray(evidence.scope_boundaries) ||
    !hasRuntimeWorkEvidenceMetadata(matched, "matched") ||
    !isRecord(matched) ||
    !isWorkObservation(matched.observation) ||
    !sameWorkObservation(matched.observation, targetObservation) ||
    !parsed
  ) {
    return null;
  }
  return [
    parsed.entry,
    ...workGeneralModifierEntries(targetObservation.target_general_modifier),
    ...deterministicEntries,
  ];
}

function isMissingWorkTargetNotEvaluated(value: unknown): boolean {
  return (
    isRuntimeNotEvaluatedEntry(value) &&
    isRecord(value) &&
    value.rule_key === "work_target_present" &&
    value.activation_id === "liuren.target.work.present" &&
    value.rule_id === "LR-19" &&
    value.status === "required_fact_missing" &&
    value.reason === "work_target_relative_not_supplied"
  );
}

function parseMissingWorkTargetBoundary(
  value: Record<string, unknown>,
  evidence: Record<string, unknown>,
): readonly EvidenceEntry[] | null {
  const stageRows = value.six_relative_stages;
  const statusRows = value.stage_status;
  if (
    !hasExactKeys(value, WORK_DIMENSION_KEYS) ||
    value.canonical_dimension !== "work" ||
    (value.requested_dimension !== "work" && value.requested_dimension !== "career") ||
    value.status !== "calculated_facts_not_verdict" ||
    !isEmptyArray(value.source_rule_ids) ||
    value.target_relative !== null ||
    value.target_contract_status !== "missing_target_relative" ||
    value.target_presence !== false ||
    !isEmptyArray(value.target_strength) ||
    !isEmptyArray(value.target_general_modifier) ||
    !Array.isArray(stageRows) ||
    stageRows.length !== LOCATION_STAGES.length ||
    !Array.isArray(statusRows) ||
    statusRows.length !== LOCATION_STAGES.length ||
    !hasRuntimeEvidenceEnvelope(evidence) ||
    evidence.status !== "not_bound" ||
    !isEmptyArray(evidence.matched) ||
    !isEmptyArray(evidence.scope_boundaries) ||
    !Array.isArray(evidence.not_evaluated) ||
    evidence.not_evaluated.length !== 1 ||
    !isMissingWorkTargetNotEvaluated(evidence.not_evaluated[0])
  ) {
    return null;
  }

  const subjectObject = parseRelationFact(value.subject_object_relation, "day_stem", "day_branch");
  const stages = LOCATION_STAGES.map((stage, index) => parseSixRelativeStage(stageRows[index], stage));
  const statuses = LOCATION_STAGES.map((stage, index) => parseStageStatus(statusRows[index], stage));
  if (!subjectObject || stages.some((row) => row === null) || statuses.some((row) => row === null)) {
    return null;
  }
  const typedStages = stages as readonly DaliurenSixRelativeStage[];
  const typedStatuses = statuses as readonly DaliurenStageStatusEntry[];
  if (
    typedStatuses.some(
      (row, index) =>
        row.branch !== typedStages[index]?.branch ||
        row.six_relative !== typedStages[index]?.six_relative,
    )
  ) {
    return null;
  }

  return [
    {
      marker: "目标边界",
      fact: "未绑定目标六亲",
      sources: [],
    },
    ...workDeterministicEntries(subjectObject, typedStages, typedStatuses),
  ];
}

function parseDimension(value: unknown): EvidenceGroup | null {
  if (!isRecord(value)) return null;
  const dimension = readString(value, "canonical_dimension");
  const requested = readString(value, "requested_dimension");
  const evidence = value.rule_evidence;
  if (!dimension || !requested || !isRecord(evidence)) return null;
  if (!hasOwnKey(DIMENSION_LABELS, dimension)) return null;
  if (!Object.prototype.hasOwnProperty.call(evidence, "hard_verdict") || evidence.hard_verdict !== null) {
    return null;
  }
  if (!Array.isArray(evidence.matched) || !Array.isArray(evidence.scope_boundaries)) return null;
  if (
    hasConflictingPresenceObservations(
      value,
      dimension,
      evidence.matched,
      evidence.scope_boundaries,
    )
  ) {
    return null;
  }
  if (dimension === "location") {
    if (requested !== "location" && requested !== "location_direction") return null;
    const observation = { stage_branch_directions: value.stage_branch_directions };
    if (!isLocationObservation(observation)) return null;
    const fact = locationFact(observation);
    if (!fact) return null;
    return {
      dimension,
      entries: [
        {
          marker: "方位候选",
          fact,
          sources: observation.stage_branch_directions.map((row) => ({
            key: `${row.stage}-${row.declared_source_anchor}`,
            label: `来源标注 · ${row.declared_source_anchor}`,
          })),
        },
      ],
    };
  }
  if (
    dimension === "money" &&
    value.wealth_presence !== false &&
    (hasOwnKey(value, "wealth_presence") ||
      hasOwnKey(value, "wealth_stage_strength") ||
      hasOwnKey(value, "wealth_void_status") ||
      hasOwnKey(value, "wealth_general_modifier"))
  ) {
    const moneyEntries = parseTopLevelMoneyFacts(value, evidence);
    return moneyEntries ? { dimension, entries: moneyEntries } : null;
  }
  if (dimension === "state" && hasOwnKey(value, "general_landing_correspondences")) {
    const stateEntries = parseTopLevelStateFacts(value, evidence);
    return stateEntries ? { dimension, entries: stateEntries } : null;
  }
  if (
    dimension === "relationship" &&
    (hasOwnKey(value, "subject_object_relation") ||
      hasOwnKey(value, "six_relative_stages") ||
      hasOwnKey(value, "stage_flow"))
  ) {
    const relationshipEntries = parseTopLevelRelationshipFacts(value, evidence);
    return relationshipEntries ? { dimension, entries: relationshipEntries } : null;
  }
  if (dimension === "work" && value.target_contract_status === "missing_target_relative") {
    const entries = parseMissingWorkTargetBoundary(value, evidence);
    return entries ? { dimension, entries } : null;
  }
  if (dimension === "work" && value.target_contract_status === "bound") {
    const workEntries = parseTopLevelWorkFacts(value, evidence);
    return workEntries ? { dimension, entries: workEntries } : null;
  }
  if (dimension === "timing") {
    const timingEntries = parseTimingFacts(value, evidence);
    return timingEntries ? { dimension, entries: timingEntries } : null;
  }
  const entries: EvidenceEntry[] = [];
  for (const item of evidence.matched) {
    const entry = parseEntry(item, dimension);
    if (entry) entries.push(entry);
  }
  entries.push(...parseScopeBoundaryFacts(value, dimension, evidence.scope_boundaries));
  if (
    dimension === "outcome" &&
    (hasOwnKey(value, "subject_object_relation") ||
      hasOwnKey(value, "transmissions_to_day") ||
      hasOwnKey(value, "initial_final_relation") ||
      hasOwnKey(value, "stage_flow"))
  ) {
    const outcomeEntries = parseTopLevelOutcomeFacts(value, evidence);
    return outcomeEntries ? { dimension, entries: outcomeEntries } : null;
  }
  return entries.length ? { dimension, entries } : null;
}

function parseGroups(value: CoreFacts["dimension_facts"]): readonly EvidenceGroup[] {
  if (!isRecord(value)) return [];
  const grouped = new Map<DaliurenDimensionId, readonly EvidenceEntry[]>();
  for (const block of Object.values(value)) {
    const parsed = parseDimension(block);
    if (!parsed || grouped.has(parsed.dimension)) continue;
    grouped.set(parsed.dimension, parsed.entries);
  }
  return [...grouped.entries()].map(([dimension, entries]) => ({ dimension, entries }));
}

export function DaliurenDimensionEvidence({ dimensionFacts = null }: DaliurenDimensionEvidenceProps) {
  const groups = parseGroups(dimensionFacts);
  if (!groups.length) return null;

  return (
    <section className={styles.panel} aria-label="维度证据" data-slot="dimension-evidence">
      {groups.map((group) => (
        <section
          className={styles.group}
          aria-label={DIMENSION_LABELS[group.dimension]}
          key={group.dimension}
          role="group"
        >
          <h3 className={styles.heading}>{DIMENSION_LABELS[group.dimension]}</h3>
          <ul className={styles.list}>
            {group.entries.map((entry, entryIndex) => (
              <li className={styles.item} key={`${group.dimension}-${entry.marker}-${entry.fact}-${entryIndex}`}>
                {entry.sources.length ? (
                  <details className={styles.drawer}>
                    <summary className={styles.summary}>
                      <span className={styles.rule}>{entry.marker}</span>
                      <span className={styles.fact}>{entry.fact}</span>
                    </summary>
                    <ol className={styles.sources} aria-label="来源">
                      {entry.sources.map((source, sourceIndex) => (
                        <li
                          className={styles.source}
                          data-source-ref={sourceIndex}
                          key={`${source.key}-${sourceIndex}`}
                        >
                          {source.label}
                        </li>
                      ))}
                    </ol>
                  </details>
                ) : (
                  <div className={styles.plain}>
                    <span className={styles.rule}>{entry.marker}</span>
                    <span className={styles.fact}>{entry.fact}</span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </section>
  );
}
