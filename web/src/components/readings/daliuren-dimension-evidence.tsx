"use client";

import type {
  DaliurenChartViewModel,
  DaliurenCompassDirection,
  DaliurenDimensionObservationMap,
  DaliurenGeneralLandingCorrespondence,
  DaliurenLocationObservation,
  DaliurenMiddleVoidObservation,
  DaliurenMoneyObservation,
  DaliurenOutcomeObservation,
  DaliurenOutcomeRelation,
  DaliurenRelationshipObservation,
  DaliurenSeasonStrength,
  DaliurenSixRelative,
  DaliurenStateObservation,
  DaliurenStageBranchDirection,
  DaliurenTimingCandidateObservation,
  DaliurenTimingObservation,
  DaliurenTransmissionStage,
  DaliurenWorkPresentObservation,
  DaliurenWorkObservation,
} from "@/view-models/registry";

import styles from "./daliuren-dimension-evidence.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;
type WealthPresentObservation = Extract<DaliurenMoneyObservation, { readonly wealth_presence: true }>;
type WealthStage = WealthPresentObservation["wealth_stages"][number];
type WealthVoidObservation = Extract<DaliurenMoneyObservation, { readonly wealth_void_rows: ReadonlyArray<unknown> }>;
type WealthVoidRow = WealthVoidObservation["wealth_void_rows"][number];
type WorkStrength = DaliurenWorkPresentObservation["target_strength"][number];
type WorkGeneralModifier = DaliurenWorkPresentObservation["target_general_modifier"][number];
type LocationDirection = DaliurenLocationObservation["stage_branch_directions"][number];
type DaliurenDimensionId = keyof DaliurenDimensionObservationMap;

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
const STATE_OBSERVATION_KEYS = ["matched_count", "stages", "correspondences"] as const;
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
    Boolean(readString(value, "branch")) &&
    value.six_relative === "妻财" &&
    isSeasonStrength(value.season_strength)
  );
}

function isWealthVoidRow(value: unknown): value is WealthVoidRow {
  return (
    isRecord(value) &&
    hasExactKeys(value, WEALTH_VOID_ROW_KEYS) &&
    isTransmissionStage(value.stage) &&
    Boolean(readString(value, "branch")) &&
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
    Boolean(readString(value, "heavenly_general")) &&
    Boolean(readString(value, "landing_branch")) &&
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

function isWorkStrength(value: unknown): value is WorkStrength {
  return (
    isRecord(value) &&
    hasExactKeys(value, TARGET_STRENGTH_KEYS) &&
    isTransmissionStage(value.stage) &&
    Boolean(readString(value, "branch")) &&
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
  const facts = [`工作所取六亲：${value.target_relative}`, `入传状态：${strengths}`];
  if (value.target_general_modifier.length) {
    facts.push(
      `天将落地类象：${value.target_general_modifier
        .map(
          (row) =>
            `${STAGE_FACTS[row.stage]} ${row.heavenly_general}落${row.landing_branch}${
              row.status === "no_exact_source_correspondence" ? "（无精确类象对应）" : ""
            }`,
        )
        .join("、")}`,
    );
  }
  return facts.join(" · ");
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
  if (value.relative_speed) {
    facts.push(`相对节奏：${RELATIVE_SPEED_FACTS[value.relative_speed]}`);
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

function parseTopLevelTimingFact(value: Record<string, unknown>): EvidenceEntry | null {
  if (
    (value.candidate_branch !== null && value.candidate_branch !== undefined) ||
    (value.candidate_date !== null && value.candidate_date !== undefined)
  ) {
    return null;
  }
  const relativeSpeed = readString(value, "relative_speed");
  if (!relativeSpeed || !hasOwnKey(RELATIVE_SPEED_FACTS, relativeSpeed)) return null;
  const sourceRuleIds = value.source_rule_ids;
  if (
    !Array.isArray(sourceRuleIds) ||
    sourceRuleIds.length === 0 ||
    !sourceRuleIds.every((ruleId) => typeof ruleId === "string" && Boolean(ruleId.trim()))
  ) {
    return null;
  }
  return {
    marker: sourceRuleIds.map((ruleId) => ruleId.trim()).join(" · "),
    fact: `相对节奏：${RELATIVE_SPEED_FACTS[relativeSpeed]}`,
    sources: [],
  };
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
  const entries: EvidenceEntry[] = [];
  for (const item of evidence.matched) {
    const entry = parseEntry(item, dimension);
    if (entry) entries.push(entry);
  }
  entries.push(...parseScopeBoundaryFacts(value, dimension, evidence.scope_boundaries));
  if (dimension === "timing" && evidence.matched.length === 0 && evidence.scope_boundaries.length === 0) {
    const timingEntry = parseTopLevelTimingFact(value);
    if (timingEntry) entries.push(timingEntry);
  }
  return entries.length ? { dimension, entries } : null;
}

function parseGroups(value: CoreFacts["dimension_facts"]): readonly EvidenceGroup[] {
  if (!isRecord(value)) return [];
  const grouped = new Map<DaliurenDimensionId, EvidenceEntry[]>();
  for (const block of Object.values(value)) {
    const parsed = parseDimension(block);
    if (!parsed) continue;
    const current = grouped.get(parsed.dimension) ?? [];
    current.push(...parsed.entries);
    grouped.set(parsed.dimension, current);
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
