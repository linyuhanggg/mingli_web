import type {
  CanwenViewModel,
  ChartSimilarityViewModel,
  DaliurenChartViewModel,
  FengshuiViewModel,
  FiveElementsFactsViewModel,
  HecanViewModel,
  LumingNayinChartViewModel,
  RhythmFactsViewModel,
  LiuyaoChartViewModel,
  MeihuaChartViewModel,
  PhysiognomyViewModel,
  QimenChartViewModel,
  QizhengChartViewModel,
  QizhengRelationshipViewModel,
  SelectionChartViewModel,
  StructuredFactObject,
  StructuredFactValue,
  TaiyiChartViewModel,
  TimeCheckViewModel,
  BaziRelationshipViewModel,
  ViewModel,
  WenshiViewModel,
  ZiweiChartViewModel,
  ZiweiRelationshipViewModel,
} from "@/view-models/registry";
import { formatBaziInterpretiveCandidateRows } from "@/lib/reading-display";

import styles from "./runtime-chart.module.css";

function Table({
  caption,
  headers,
  rows,
}: Readonly<{
  caption: string;
  headers: string[];
  rows: string[][];
}>) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <caption>{caption}</caption>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${caption}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${caption}-${rowIndex}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function isStructuredObject(value: StructuredFactValue | undefined): value is StructuredFactObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return "—";
  }
}

const FACT_STATUS_LABELS: Record<string, string> = {
  calculated: "已计算",
  calculated_assignment_not_verdict: "已计算赋值",
  calculated_facts_and_predicates_only_no_event_verdicts: "只展示计算事实与结构命题",
  calculated_limit_span_not_verdict: "已计算区间",
  calculated_not_interpreted: "已计算，仅展示事实",
  calculated_position_not_verdict: "已计算位置",
  calculated_relation_not_verdict: "已计算关系",
  calculated_selected_school_facts_not_verdict: "已计算选定流派资料",
  not_calculated_missing_gender: "缺少性别，未计算",
  not_requested: "未请求",
  predicate_matched_not_verdict: "结构命题已匹配",
  resolved: "已解析",
  sequence_only: "仅展示顺序",
};

function factStatusLabel(value: string): string {
  return FACT_STATUS_LABELS[value] ?? value;
}

function structuredValueSummary(value: StructuredFactValue | undefined): string {
  if (value == null) {
    return "—";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return typeof value === "string" ? factStatusLabel(value) : String(value);
  }
  if (Array.isArray(value)) {
    return value.length === 0 ? "无" : `${value.length} 项结构化事实`;
  }
  if (!isStructuredObject(value)) {
    return "—";
  }
  if (typeof value.status === "string") {
    return factStatusLabel(value.status);
  }
  if (typeof value.name === "string") {
    return value.name;
  }
  const fieldCount = Object.keys(value).length;
  return fieldCount === 0 ? "空" : `${fieldCount} 个结构化字段`;
}

function structuredPrimitive(value: StructuredFactValue | undefined): string {
  if (value == null) {
    return "—";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return typeof value === "string" ? factStatusLabel(value) : String(value);
  }
  return structuredValueSummary(value);
}

function structuredText(value: StructuredFactObject, keys: ReadonlyArray<string>): string | null {
  for (const key of keys) {
    const candidate = value[key];
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate;
    }
  }
  return null;
}

function structuredEntries(value: StructuredFactObject): string[][] {
  return Object.values(value).map((item, index) => [
    `第${index + 1}项`,
    structuredValueSummary(item),
  ]);
}

function coreFactRows(value: StructuredFactObject | null): string[][] {
  if (!value) return [];
  return Object.entries(value)
    .filter(([, item]) => item !== null)
    .map(([key, item]) => [key, structuredValueSummary(item)]);
}

const POSITION_LABELS: Record<"year" | "month" | "day" | "hour", string> = {
  year: "年柱",
  month: "月柱",
  day: "日柱",
  hour: "时柱",
};

const LUMING_CATEGORY_LABELS: Record<"lu" | "ma" | "gui", string> = {
  lu: "禄",
  ma: "马",
  gui: "贵",
};

function internalScopeLabel(value: string): string {
  const labels: Record<string, string> = {
    annual_macro_historical_board_facts: "年度宏观历史盘面事实",
    calculated_facts_and_predicates_only_no_event_verdicts: "只展示计算事实与结构命题",
    macro_historical: "宏观历史对象",
    lunar_new_year_from_shared_calendar: "共享历法农历新年",
    not_required_for_bazhai: "八宅模式不要求建筑年代",
    year: "年",
    personal_event: "个人事件范围",
    personal_life: "个人生活范围",
    medical: "医疗范围",
    legal: "法律范围",
    military_action: "军事行动范围",
  };
  return labels[value] ?? "已声明范围";
}

function eventProfileLabel(value: string): string {
  const labels: Record<string, string> = {
    business_opening_transaction: "营业或交易开启",
  };
  return labels[value] ?? "事件约束已声明";
}

function candidateTimeLabel(value: string): string {
  const [date, branch] = value.split(":");
  return date && branch ? `${date} · ${branch}` : "候选时刻已记录";
}

function selectionComponentLabel(value: string): string {
  return value === "hard_eligible_first" ? "先排除不合格候选" : "排序组件已声明";
}

function fengshuiSubprofileLabel(value: "form" | "liqi"): string {
  return value === "form" ? "形势" : "理气";
}

function fengshuiMissingLabel(value: string): string {
  const labels: Record<string, string> = {
    compass: "罗盘测量",
    building_chronology: "建筑年代",
    layout_graph: "布局关系",
    form: "形势观察",
    liqi: "理气资料",
  };
  return labels[value] ?? "其他关键资料";
}

function ZiweiChart({ view }: Readonly<{ view: ZiweiChartViewModel }>) {
  const coreFacts = view.core_facts;
  const transformations = coreFacts?.transformations ?? [];
  const annualLayers = coreFacts?.annual_layers ?? [];
  const monthlyLayers = coreFacts?.monthly_layers ?? [];
  const interpretiveCandidates = coreFacts?.interpretive_candidates;
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>命宫</dt>
          <dd>{view.life_palace_id}</dd>
        </div>
        <div>
          <dt>身宫</dt>
          <dd>{view.body_palace_id}</dd>
        </div>
        {coreFacts?.five_elements_class ? (
          <div>
            <dt>五行局</dt>
            <dd>{coreFacts.five_elements_class}</dd>
          </div>
        ) : null}
        {coreFacts?.ming_shen ? (
          <div>
            <dt>命身</dt>
            <dd>
              命 {coreFacts.ming_shen.ming_branch} · 身 {coreFacts.ming_shen.shen_branch}
            </dd>
          </div>
        ) : null}
        {coreFacts?.major_limit_direction ? (
          <div>
            <dt>大限方向</dt>
            <dd>
              {coreFacts.major_limit_direction.direction} · 起运 {coreFacts.major_limit_starting_age ?? "—"} 岁
            </dd>
          </div>
        ) : null}
        {coreFacts?.active_major_limit ? (
          <div>
            <dt>当前大限事实</dt>
            <dd>{Object.keys(coreFacts.active_major_limit).length} 个 Runtime 字段</dd>
          </div>
        ) : null}
        {coreFacts?.chinese_date ? (
          <div>
            <dt>农历四柱</dt>
            <dd>{coreFacts.chinese_date}</dd>
          </div>
        ) : null}
      </dl>
      {interpretiveCandidates ? (
        <Table
          caption="命宫三方四正与古籍候选（非最终结论）"
          headers={["项目", "Runtime 输出"]}
          rows={[
            ["状态", String(interpretiveCandidates.status ?? "candidate_only")],
            ["命中候选", String(Array.isArray(interpretiveCandidates.matched_rules) ? interpretiveCandidates.matched_rules.length : 0)],
            ["四化在三方四正", String(Array.isArray(interpretiveCandidates.transformation_facts) ? interpretiveCandidates.transformation_facts.length : 0)],
            ["边界", String(interpretiveCandidates.boundary ?? "仅展示盘面候选")],
          ]}
        />
      ) : null}
      {coreFacts?.source_conditioned_patterns.length ? (
        <Table
          caption="古籍来源条件候选"
          headers={["规则", "来源", "命中条件", "状态"]}
          rows={coreFacts.source_conditioned_patterns.map((pattern) => [
            `${pattern.local_rule_id} · ${pattern.title}`,
            pattern.source_pack,
            pattern.predicate_audit.join("；"),
            "谓词命中，未下断语",
          ])}
        />
      ) : null}
      <Table
        caption="十二宫与主星"
        headers={["宫位", "天干", "地支", "主星", "辅曜"]}
        rows={view.palaces.map((palace) => [
          palace.label,
          palace.heavenly_stem,
          palace.earthly_branch,
          palace.major_stars.join("、") || "—",
          [...(palace.minor_stars ?? []), ...(palace.adjective_stars ?? [])]
            .map((star) => star.name)
            .join("、") || "—",
        ])}
      />
      {transformations.length ? (
        <Table
          caption="本命四化事实"
          headers={["星曜", "四化", "落宫", "范围"]}
          rows={transformations.map((item) => [item.star, item.transformation, `${item.palace} · ${item.palace_branch}`, item.scope])}
        />
      ) : null}
      {annualLayers.length ? (
        <Table
          caption="流年盘面事实"
          headers={["年份", "覆盖区间", "流年结构", "分段"]}
          rows={annualLayers.map((item) => [
            String(item.year),
            `${item.coverage_start}—${item.coverage_end_exclusive}`,
            item.representative_scope,
            String(item.segments.length),
          ])}
        />
      ) : null}
      {monthlyLayers.length ? (
        <Table
          caption="流月盘面事实"
          headers={["年份", "月份", "流月结构", "分段"]}
          rows={monthlyLayers.map((item) => [
            String(item.year),
            String(item.month),
            item.representative_scope,
            String(item.segments.length),
          ])}
        />
      ) : null}
      <p className={styles.note}>只展示 Runtime 返回的宫位、星曜、大限与四化事实，不在浏览器追加判断。</p>
    </div>
  );
}

function QizhengChart({ view }: Readonly<{ view: QizhengChartViewModel }>) {
  const coreFacts = view.core_facts;
  const annualTransformations = coreFacts?.annual_transformations ?? [];
  const requestedLimitLayers = coreFacts?.requested_limit_layers ?? [];
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      {coreFacts?.ming_shen ? (
        <dl className={styles.meta}>
          <div>
            <dt>命度 / 身度</dt>
            <dd>{coreFacts.ming_shen.ming_degree.toFixed(2)}° / {coreFacts.ming_shen.shen_degree.toFixed(2)}°</dd>
          </div>
          <div>
            <dt>命身距</dt>
            <dd>{coreFacts.ming_shen.separation_degrees.toFixed(2)}°</dd>
          </div>
        </dl>
      ) : null}
      {coreFacts?.ephemeris || coreFacts?.conventions ? (
        <dl className={styles.meta}>
          {coreFacts.ephemeris ? (
            <div>
              <dt>星历事实</dt>
              <dd>{Object.keys(coreFacts.ephemeris).length} 个 Runtime 字段</dd>
            </div>
          ) : null}
          {coreFacts.conventions ? (
            <div>
              <dt>计算口径</dt>
              <dd>{Object.keys(coreFacts.conventions).length} 个 Runtime 字段</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      <Table
        caption="七政四余星体位置"
        headers={["星体", "星座", "宫位", "黄经"]}
        rows={view.planets.map((planet) => [
          planet.planet_id,
          planet.sign_id,
          planet.house_id,
          `${planet.longitude.toFixed(2)}°`,
        ])}
      />
      <Table
        caption="十二宫宫头"
        headers={["宫位", "星座", "宫头"]}
        rows={view.houses.map((house) => [
          house.house_id,
          house.sign_id,
          `${house.cusp_longitude.toFixed(2)}°`,
        ])}
      />
      {coreFacts?.classical_bodies?.length ? (
        <Table
          caption="星体计算事实"
          headers={["星体", "点类型", "来源依赖", "黄纬", "入宫度", "运动"]}
          rows={coreFacts.classical_bodies.map((body) => [
            body.classical_name,
            body.point_kind ?? "—",
            body.source_dependency_id ?? "—",
            body.latitude_degrees == null ? "—" : `${body.latitude_degrees.toFixed(2)}°`,
            body.house_degree == null ? "—" : `${body.house_degree.toFixed(2)}°`,
            body.motion_state ?? "—",
          ])}
        />
      ) : null}
      {coreFacts?.classical_bodies?.some((body) => body.observed_body === false && body.trace) ? (
        <Table
          caption="四余算法来源事实"
          headers={["点", "计算类型", "公式/校准档案", "来源依赖"]}
          rows={coreFacts.classical_bodies
            .filter((body) => body.observed_body === false && body.trace)
            .map((body) => [
              body.classical_name,
              body.point_kind ?? "计算虚点",
              displayValue(body.trace?.profile ?? body.trace?.id ?? body.trace?.calibration_path),
              body.source_dependency_id ?? "—",
            ])}
        />
      ) : null}
      {coreFacts?.major_limits?.length ? (
        <Table
          caption="限段事实"
          headers={["序", "宫位", "年龄", "起度—止度"]}
          rows={coreFacts.major_limits.map((limit) => [
            String(limit.sequence),
            limit.house,
            `${limit.age_start_years}—${limit.age_end_years} 岁`,
            `${limit.start_degree.toFixed(2)}°—${limit.end_degree.toFixed(2)}°`,
          ])}
        />
      ) : null}
      {coreFacts?.transformations?.length ? (
        <Table
          caption="十干变换事实"
          headers={["序", "变换", "星体", "年干"]}
          rows={coreFacts.transformations.map((item) => [String(item.sequence), item.label, item.classical_body, item.year_stem])}
        />
      ) : null}
      {coreFacts?.source_conditioned_patterns.length ? (
        <Table
          caption="古籍来源条件候选"
          headers={["规则", "来源", "命中条件", "状态"]}
          rows={coreFacts.source_conditioned_patterns.map((pattern) => [
            `${pattern.local_rule_id} · ${pattern.title}`,
            pattern.source_pack,
            pattern.predicate_audit.join("；"),
            "谓词命中，未下断语",
          ])}
        />
      ) : null}
      {annualTransformations.length ? (
        <Table
          caption="流年变换事实"
          headers={["年份", "年干支", "变换数量", "事实状态"]}
          rows={annualTransformations.map((item) => [
            String(item.year),
            item.year_ganzhi,
            String(item.transformations.length),
            item.fact_status,
          ])}
        />
      ) : null}
      {requestedLimitLayers.length ? (
        <Table
          caption="指定时限事实"
          headers={["日期", "年龄", "宫位", "状态"]}
          rows={requestedLimitLayers.map((item) => [
            item.date,
            `${item.age_years} 岁`,
            item.house,
            item.status,
          ])}
        />
      ) : null}
      <p className={styles.note}>盘面只保留计算位置；Runtime 未返回相位时，页面不自行补算。</p>
    </div>
  );
}

function LiuyaoChart({ view }: Readonly<{ view: LiuyaoChartViewModel }>) {
  const coreRows = view.core_facts
    ? coreFactRows(view.core_facts as unknown as StructuredFactObject)
    : [];
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>本卦</dt>
          <dd>{view.primary_hexagram.name}</dd>
        </div>
        <div>
          <dt>变卦</dt>
          <dd>{view.changed_hexagram?.name ?? "无"}</dd>
        </div>
      </dl>
      <Table
        caption="六爻"
        headers={["爻位", "数值", "状态"]}
        rows={[...view.lines]
          .reverse()
          .map((line) => [
            `第${line.position}爻`,
            String(line.value),
            line.moving ? "动爻" : "静爻",
          ])}
      />
      {coreRows.length ? (
        <Table caption="六爻结构事实" headers={["事实项", "状态"]} rows={coreRows} />
      ) : null}
      <p className={styles.note}>卦象与爻位由 Runtime 固定；页面不重新起卦，也不把盘面事实当成判断。</p>
    </div>
  );
}

function MeihuaChart({ view }: Readonly<{ view: MeihuaChartViewModel }>) {
  const hexagramRows = [
    ["本卦", view.primary_hexagram.name, view.primary_hexagram.upper_trigram, view.primary_hexagram.lower_trigram],
    view.mutual_hexagram
      ? ["互卦", view.mutual_hexagram.name, view.mutual_hexagram.upper_trigram, view.mutual_hexagram.lower_trigram]
      : ["互卦", "无", "—", "—"],
    view.changed_hexagram
      ? ["变卦", view.changed_hexagram.name, view.changed_hexagram.upper_trigram, view.changed_hexagram.lower_trigram]
      : ["变卦", "无", "—", "—"],
  ];
  const bodyRelationRows = (view.core_facts?.body_relation_facts ?? []).map((item) => [
    structuredText(item, ["position"]) ?? "—",
    structuredText(item, ["trigram"]) ?? "—",
    structuredText(item, ["element"]) ?? "—",
    structuredText(item, ["relation"]) ?? "—",
    structuredPrimitive(item.status),
  ]);
  const seasonalRows = view.core_facts?.seasonal_strength
    ? Object.entries(view.core_facts.seasonal_strength).flatMap(([name, value]) => {
        if (!isStructuredObject(value)) return [];
        return [[
          name,
          structuredText(value, ["trigram"]) ?? "—",
          structuredText(value, ["month_branch"]) ?? "—",
          structuredText(value, ["season"]) ?? "—",
          structuredPrimitive(value.state),
          structuredPrimitive(value.status),
        ]];
      })
    : [];
  const interpretiveCandidates = view.core_facts?.interpretive_candidates;
  const relationCandidateRows = interpretiveCandidates && Array.isArray(interpretiveCandidates.relation_candidates)
    ? interpretiveCandidates.relation_candidates.flatMap((value) => {
        if (!isStructuredObject(value)) return [];
        return [[
          structuredText(value, ["source_plate"]) ?? "—",
          structuredText(value, ["position"]) ?? "—",
          structuredText(value, ["relation"]) ?? "—",
          structuredText(value, ["relation_key"]) ?? "—",
          structuredPrimitive(value.seasonal_state),
          structuredPrimitive(value.status),
        ]];
      })
    : [];
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>起卦方式</dt>
          <dd>{view.casting_method === "time" ? "按时间起卦" : view.casting_method}</dd>
        </div>
        <div>
          <dt>动爻</dt>
          <dd>{view.moving_lines.length ? view.moving_lines.map((line) => `第${line}爻`).join("、") : "无"}</dd>
        </div>
      </dl>
      <Table caption="卦象结构" headers={["层次", "卦名", "上卦", "下卦"]} rows={hexagramRows} />
      <Table
        caption="体用关系"
        headers={["位置", "卦", "五行", "关系", "状态"]}
        rows={[
          ["体", view.body_use.body.trigram, view.body_use.body.element, view.body_use.relation, view.body_use.status],
          ["用", view.body_use.use.trigram, view.body_use.use.element, view.body_use.relation, view.body_use.status],
        ]}
      />
      {bodyRelationRows.length ? (
        <Table
          caption="体用关系明细"
          headers={["位置", "卦", "五行", "关系", "状态"]}
          rows={bodyRelationRows}
        />
      ) : null}
      {seasonalRows.length ? (
        <Table
          caption="月令状态事实"
          headers={["对象", "卦", "月支", "季节", "状态", "事实状态"]}
          rows={seasonalRows}
        />
      ) : null}
      {relationCandidateRows.length ? (
        <Table
          caption="体用关系候选（非最终结论）"
          headers={["盘层", "位置", "关系", "关系类型", "月令状态", "候选状态"]}
          rows={relationCandidateRows}
        />
      ) : null}
      <p className={styles.note}>只展示 Runtime 返回的本卦、互卦、变卦与体用结构；页面不根据生克关系追加吉凶判断。</p>
    </div>
  );
}

function LumingNayinChart({ view }: Readonly<{ view: LumingNayinChartViewModel }>) {
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <Table
        caption="禄命纳音四柱"
        headers={["柱位", "天干", "地支", "纳音"]}
        rows={view.pillars.map((pillar) => [
          POSITION_LABELS[pillar.position],
          pillar.stem,
          pillar.branch,
          pillar.nayin,
        ])}
      />
      <Table
        caption="三元资料"
        headers={["资料组", "状态"]}
        rows={structuredEntries(view.three_yuan_profiles)}
      />
      {view.taiyuan ? (
        <Table
          caption="胎元事实"
          headers={["资料项", "状态"]}
          rows={structuredEntries(view.taiyuan)}
        />
      ) : null}
      {view.relations.length ? (
        <Table
          caption="禄马贵结构事实"
          headers={["类别", "锚点", "关系", "目标", "状态"]}
          rows={view.relations.map((relation) => [
            LUMING_CATEGORY_LABELS[relation.category],
            `${POSITION_LABELS[relation.anchor as keyof typeof POSITION_LABELS] ?? "已声明锚点"} · ${relation.anchor_pillar}`,
            relation.relation,
            relation.target_branch ?? "—",
            factStatusLabel(relation.status),
          ])}
        />
      ) : null}
      {view.source_conditioned_patterns.length ? (
        <Table
          caption="古籍来源条件候选"
          headers={["规则", "来源", "命中条件", "状态"]}
          rows={view.source_conditioned_patterns.map((pattern) => [
            `${pattern.local_rule_id} · ${pattern.title}`,
            pattern.source_pack,
            pattern.predicate_audit.join("；"),
            "谓词命中，未下断语",
          ])}
        />
      ) : null}
      <p className={styles.note}>这里只展示禄命纳音的四柱、纳音、已计算关系和来源条件候选；页面不追加吉凶或人生判断。</p>
    </div>
  );
}

function RhythmFactsChart({ view }: Readonly<{ view: RhythmFactsViewModel }>) {
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <Table
        caption="本命音律四柱纳音事实"
        headers={["柱位", "天干", "地支", "纳音"]}
        rows={view.pillars.map((pillar) => [
          POSITION_LABELS[pillar.position],
          pillar.stem,
          pillar.branch,
          pillar.nayin,
        ])}
      />
      <dl className={styles.meta}>
        <div>
          <dt>算法谱系</dt>
          <dd>{view.independent_lineage}</dd>
        </div>
        <div>
          <dt>事实范围</dt>
          <dd>{view.fact_scope}</dd>
        </div>
        <div>
          <dt>解释状态</dt>
          <dd>仅事实</dd>
        </div>
      </dl>
      <p className={styles.note}>{view.source_boundary}</p>
    </div>
  );
}

function TaiyiChart({ view }: Readonly<{ view: TaiyiChartViewModel }>) {
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>年干支</dt>
          <dd>{view.calendar.year_ganzhi}</dd>
        </div>
        <div>
          <dt>岁首口径</dt>
          <dd>{internalScopeLabel(view.calendar.annual_boundary)}</dd>
        </div>
        <div>
          <dt>局 / 理</dt>
          <dd>{view.cycle.bureau} · {view.cycle.governance}</dd>
        </div>
        <div>
          <dt>太乙所在</dt>
          <dd>{view.board.taiyi_position}</dd>
        </div>
      </dl>
      <Table
        caption="太乙周期事实"
        headers={["项目", "数值"]}
        rows={[
          ["积年", String(view.epoch.accumulated_year)],
          ["纪", String(view.cycle.ji)],
          ["周天位置", String(view.cycle.position_360)],
          ["纪内年份", String(view.cycle.year_in_ji)],
          ["子元内年份", String(view.cycle.year_in_zi_yuan)],
          ["子元", String(view.cycle.zi_yuan)],
          ["子元首", view.cycle.zi_yuan_head],
        ]}
      />
      <Table
        caption="太乙盘面事实"
        headers={["项目", "位置 / 状态"]}
        rows={[
          ["合神", view.board.heshen],
          ["计神", view.board.jishen],
          ["始击", view.board.shiji],
          ["太岁", view.board.taisui],
          ["天目 / 文昌", `${view.board.tianmu_wenchang.name} · ${view.board.tianmu_wenchang.position}`],
          ["主客结构", structuredValueSummary(view.host_guest)],
        ]}
      />
      <Table
        caption="四将位置"
        headers={["类别", "辅将", "大将"]}
        rows={[
          ["客", String(view.four_generals.guest_assistant), String(view.four_generals.guest_major)],
          ["主", String(view.four_generals.host_assistant), String(view.four_generals.host_major)],
        ]}
      />
      {view.long_cycle_deities.length ? (
        <Table
          caption="长周期神位置"
          headers={["神名", "位置", "周期位置", "状态"]}
          rows={view.long_cycle_deities.map((deity) => [
            deity.name,
            String(deity.position),
            String(deity.cycle_position),
            factStatusLabel(deity.status),
          ])}
        />
      ) : null}
      {view.board_predicates.length ? (
        <Table
          caption="盘面结构命题"
          headers={["命题", "事实路径数", "状态"]}
          rows={view.board_predicates.map((predicate) => [
            predicate.name,
            String(predicate.fact_paths.length),
            factStatusLabel(predicate.status),
          ])}
        />
      ) : null}
      <Table
        caption="范围合同"
        headers={["项目", "声明"]}
        rows={[
          ["支持时间层", view.scope_contract.supported_horizons.map(internalScopeLabel).join("、") || "—"],
          ["支持对象", view.scope_contract.supported_objects.map(internalScopeLabel).join("、") || "—"],
          ["不支持范围", view.scope_contract.unsupported_scopes.map(internalScopeLabel).join("、") || "无"],
          ["解释边界", internalScopeLabel(view.scope_contract.interpretation_policy)],
        ]}
      />
      <p className={styles.note}>太乙当前只展示年度宏观盘面事实和结构命题，不把它扩展成个人事件或现实决策结论。</p>
    </div>
  );
}

function SelectionChart({ view }: Readonly<{ view: SelectionChartViewModel }>) {
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>事件类型</dt>
          <dd>{eventProfileLabel(view.event_profile)}</dd>
        </div>
        <div>
          <dt>候选状态</dt>
          <dd>{view.no_valid_candidate ? "当前没有合格候选" : `${view.eligible_candidates.length} 个合格日期`}</dd>
        </div>
      </dl>
      {view.eligible_candidates.length ? (
        <Table
          caption="合格日期候选"
          headers={["日期", "推荐时刻", "资格", "排除原因", "排序依据"]}
          rows={view.eligible_candidates.map((candidate) => [
            candidate.civil_date,
            candidateTimeLabel(candidate.best_candidate_time_id),
            candidate.eligibility.eligible === true ? "符合" : structuredValueSummary(candidate.eligibility),
            candidate.rejection_reasons.length ? `${candidate.rejection_reasons.length} 项` : "无",
            structuredValueSummary(candidate.ranking_components),
          ])}
        />
      ) : null}
      <Table
        caption="排序机制"
        headers={["项目", "声明"]}
        rows={[
          ["排序方法", "可解释的分层排序"],
          ["排序组件", view.ranking.component_order.map(selectionComponentLabel).join("、") || "—"],
          ["候选时刻", `${view.eligible_date_time_candidates.length} 个候选`],
          ["民俗资料影响排序", view.ranking.folk_affects_rank ? "是" : "否"],
          ["使用不透明数值分数", view.ranking.opaque_numeric_score ? "是" : "否"],
        ]}
      />
      {view.eliminations.length ? (
        <Table
          caption="淘汰记录"
          headers={["记录", "原因"]}
          rows={view.eliminations.map((elimination, index) => [
            `第${index + 1}项`,
            structuredText(elimination, ["reason", "message", "display_text"]) ?? structuredValueSummary(elimination),
          ])}
        />
      ) : null}
      <Table
        caption="资料谱系"
        headers={["项目", "声明"]}
        rows={[
          ["官方资料优先级", "主要依据"],
          ["民俗资料优先级", "只作比较"],
          ["合并成单一判断", view.lineage_policy.merge_verdicts ? "是" : "否"],
          ["保留分歧", view.lineage_policy.preserve_disagreement ? "是" : "否"],
          ["候选范围", structuredValueSummary(view.basis_projection)],
        ]}
      />
      {view.source_conditioned_patterns.length ? (
        <Table
          caption="古籍来源条件候选"
          headers={["规则", "来源", "命中条件", "状态"]}
          rows={view.source_conditioned_patterns.map((pattern) => [
            `${pattern.local_rule_id} · ${pattern.title}`,
            `${pattern.source_pack} · ${pattern.source_anchor}`,
            pattern.predicate_audit.join("；"),
            "谓词命中，未下断语",
          ])}
        />
      ) : null}
      <p className={styles.note}>择日只展示候选、淘汰和可解释排序；页面不把排序结果包装成绝对吉日或保证。</p>
    </div>
  );
}

function FengshuiChart({ view }: Readonly<{ view: FengshuiViewModel }>) {
  const facing = isStructuredObject(view.compass.facing) ? view.compass.facing : null;
  const layoutNodes = view.layout_graph.nodes;
  const layoutEdges = view.layout_graph.edges;
  const buildingPeriod = view.building_chronology.period_use;
  const buildingChronology =
    buildingPeriod === "not_required_for_bazhai"
      ? "八宅模式不要求建筑年代"
      : structuredPrimitive(buildingPeriod ?? view.building_chronology.status);
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>启用分支</dt>
          <dd>{view.active_subprofiles.map(fengshuiSubprofileLabel).join("、") || "—"}</dd>
        </div>
        <div>
          <dt>罗盘状态</dt>
          <dd>{structuredPrimitive(view.compass.status)}</dd>
        </div>
        <div>
          <dt>图像观察</dt>
          <dd>{view.observation_provenance.provider_performed_vision === true ? "已执行" : "未执行"}</dd>
        </div>
      </dl>
      <Table
        caption="空间观测事实"
        headers={["项目", "记录"]}
        rows={[
          ["罗盘朝向", facing ? `${structuredPrimitive(facing.mountain)} · ${structuredPrimitive(facing.trigram)}` : "—"],
          ["朝向度数", facing ? structuredPrimitive(facing.degrees) : "—"],
          ["建筑年代", buildingChronology],
          ["布局节点", Array.isArray(layoutNodes) ? `${layoutNodes.length} 个` : structuredValueSummary(layoutNodes)],
          ["布局连接", Array.isArray(layoutEdges) ? `${layoutEdges.length} 条` : structuredValueSummary(layoutEdges)],
          ["形势状态", structuredValueSummary(view.form)],
          ["理气状态", structuredValueSummary(view.liqi)],
          ["来源规则", `${view.active_source_rule_ids.length} 条已绑定`],
        ]}
      />
      {view.conflicts.length ? (
        <Table
          caption="冲突记录"
          headers={["记录", "状态"]}
          rows={view.conflicts.map((conflict, index) => [
            `第${index + 1}项`,
            structuredText(conflict, ["message", "display_text"]) ?? structuredValueSummary(conflict),
          ])}
        />
      ) : null}
      {view.uncertainties.length ? (
        <Table
          caption="不确定性记录"
          headers={["记录", "状态"]}
          rows={view.uncertainties.map((uncertainty, index) => [
            `第${index + 1}项`,
            structuredText(uncertainty, ["message", "display_text"]) ?? structuredValueSummary(uncertainty),
          ])}
        />
      ) : null}
      {view.critical_missing.length ? (
        <Table
          caption="关键资料缺失"
          headers={["资料", "状态"]}
          rows={view.critical_missing.map((missing) => [fengshuiMissingLabel(missing), "需要补充"])}
        />
      ) : null}
      <p className={styles.note}>风水页面只复述测量、布局、形势/理气状态和边界；没有图像识别或居住吉凶判断时，不会补造结论。</p>
    </div>
  );
}

function QimenChart({ view }: Readonly<{ view: QimenChartViewModel }>) {
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>遁局</dt>
          <dd>{view.dun_type === "yin" ? "阴遁" : "阳遁"}</dd>
        </div>
        <div>
          <dt>局数</dt>
          <dd>{view.ju_number}</dd>
        </div>
        <div>
          <dt>值符 / 值使</dt>
          <dd>{view.chief.star} / {view.director.door}</dd>
        </div>
        <div>
          <dt>旬空</dt>
          <dd>{view.xunkong.xun} · {view.xunkong.branches.join("、")}</dd>
        </div>
        <div>
          <dt>驿马</dt>
          <dd>{view.horse.branch} · 第{view.horse.palace}宫</dd>
        </div>
      </dl>
      <Table
        caption="九宫盘面"
        headers={["宫", "地盘干", "天盘干", "星", "门", "神"]}
        rows={view.palaces.map((palace) => [
          palace.palace_id,
          palace.stem,
          palace.heaven_stems.join("、") || "—",
          palace.stars.join("、") || "—",
          palace.door ?? "—",
          palace.deity ?? "—",
        ])}
      />
      <Table
        caption="结构格局"
        headers={["编号", "名称", "状态", "宫位"]}
        rows={view.named_patterns.map((pattern) => [
          pattern.id,
          pattern.name,
          pattern.status,
          `第${pattern.palace}宫`,
        ])}
      />
      <p className={styles.note}>中宫缺少星、门、神时按 Runtime 的空值显示，不用占位事实填充。</p>
    </div>
  );
}

function DaliurenChart({ view }: Readonly<{ view: DaliurenChartViewModel }>) {
  const coreRows = view.core_facts
    ? coreFactRows(view.core_facts as unknown as StructuredFactObject)
    : [];
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <Table
        caption="四课"
        headers={["课次", "上", "下"]}
        rows={view.lessons.map((lesson) => [lesson.lesson_id, lesson.upper, lesson.lower])}
      />
      <Table
        caption="三传"
        headers={["阶段", "地支", "天将"]}
        rows={view.transmissions.map((item) => [item.stage, item.branch, item.general])}
      />
      {coreRows.length ? (
        <Table caption="大六壬结构事实" headers={["事实项", "状态"]} rows={coreRows} />
      ) : null}
      <p className={styles.note}>只复述四课三传结构，吉凶判断仍受服务端证据与边界约束。</p>
    </div>
  );
}

function PhysiognomyChart({ view }: Readonly<{ view: PhysiognomyViewModel }>) {
  const sourceRows = view.source_comparison.sources.map((source) => [
    displayValue(source.title),
    displayValue(source.edition_caveat),
  ]);
  const disagreementRows = view.source_comparison.disagreements.map((item) => [
    displayValue(item.sources),
    displayValue(item.summary),
  ]);
  const missingRows = view.missing_targets.map((item) => [
    displayValue(item.region),
    displayValue(item.feature_kind),
    displayValue(item.reason),
  ]);
  const uncertaintyRows = view.uncertainties.map((item) => [
    displayValue(item.region),
    displayValue(item.feature_kind),
    displayValue(item.reason_codes),
  ]);
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <Table
        caption="结构化可见观察"
        headers={["区域", "特征", "置信度", "记录"]}
        rows={view.observations.map((observation) => [
          observation.region_id,
          observation.feature_id,
          observation.confidence.toFixed(2),
          observation.display_text,
        ])}
      />
      <p className={styles.note}>
        只展示 Runtime 接纳的结构化可见观察；页面不做身份识别，也不追加健康、性格或财富推断。
      </p>
      {sourceRows.length ? (
        <Table caption="相法来源层" headers={["来源", "版本说明"]} rows={sourceRows} />
      ) : null}
      {disagreementRows.length ? (
        <Table caption="来源分歧（保留）" headers={["来源", "说明"]} rows={disagreementRows} />
      ) : null}
      {missingRows.length ? (
        <Table caption="尚缺观察" headers={["区域", "特征", "原因"]} rows={missingRows} />
      ) : null}
      {uncertaintyRows.length ? (
        <Table caption="观察不确定性" headers={["区域", "特征", "原因"]} rows={uncertaintyRows} />
      ) : null}
      <p className={styles.note}>
        已保留 {view.active_source_rule_ids.length} 条来源规则标记；本页只呈现可见观察、来源层、分歧和资料缺口，不作身份、健康、财富、寿命或性格断语。
      </p>
    </div>
  );
}

const FIVE_ELEMENT_LABELS: Record<string, string> = {
  wood: "木",
  fire: "火",
  earth: "土",
  metal: "金",
  water: "水",
};

function FiveElementsFactsChart({
  view,
}: Readonly<{ view: FiveElementsFactsViewModel }>) {
  const inventory = view.element_inventory;
  const sourceStatus = {
    exact_rule_bound: "精确来源规则已绑定",
    identity_only: "只有日主×月令适用性身份",
    unavailable: "来源身份暂不可用",
  }[view.source_status];
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>日主</dt>
          <dd>
            {view.day_master
              ? `${view.day_master.stem} · ${FIVE_ELEMENT_LABELS[view.day_master.element] ?? view.day_master.element}`
              : "—"}
          </dd>
        </div>
        <div>
          <dt>月令</dt>
          <dd>{view.month_command?.label ?? "—"}</dd>
        </div>
        <div>
          <dt>来源状态</dt>
          <dd>{sourceStatus}</dd>
        </div>
      </dl>
      <Table
        caption="五行库存事实"
        headers={["元素", "可见干支", "藏干出现"]}
        rows={Object.keys(FIVE_ELEMENT_LABELS).map((element) => [
          FIVE_ELEMENT_LABELS[element],
          String(inventory?.visible_stem_branch_counts.find((item) => item.element === element)?.value ?? "—"),
          String(inventory?.hidden_stem_occurrence_counts.find((item) => item.element === element)?.value ?? "—"),
        ])}
      />
      <Table
        caption="季节与调候事实"
        headers={["项目", "Runtime 事实"]}
        rows={[
          ["季节画像", view.seasonal_profile ? `${view.seasonal_profile.season} · ${view.seasonal_profile.month_qi}` : "—"],
          ["温湿度", view.seasonal_profile ? `${view.seasonal_profile.temperature} · ${view.seasonal_profile.moisture}` : "—"],
          ["调候标记", view.tiaohou_markers?.markers.join("、") ?? "—"],
          ["适用性范围", view.tiaohou_markers?.scope ?? "—"],
          ["来源依赖", view.source_dependency_ids.join("、") || "—"],
          ["来源规则", view.active_source_rule_ids.join("、") || "—"],
        ]}
      />
      {view.interpretive_candidates ? (
        <Table
          caption="强弱与结构候选（非最终结论）"
          headers={["层", "Runtime 输出"]}
          rows={formatBaziInterpretiveCandidateRows(view.interpretive_candidates)}
        />
      ) : null}
      {view.source_gaps.length ? (
        <div className={styles.note}>
          <strong>来源缺口</strong>
          <ul>
            {view.source_gaps.map((gap) => <li key={gap}>{gap}</li>)}
          </ul>
        </div>
      ) : null}
      <p className={styles.note}>
        {view.limitations.join(" ")}
      </p>
    </div>
  );
}

const CHART_SIMILARITY_POSITION_LABELS: Record<ChartSimilarityViewModel["comparisons"][number]["position"], string> = {
  year: "年柱",
  month: "月柱",
  day: "日柱",
  hour: "时柱",
};

function ChartSimilarityChart({
  view,
}: Readonly<{ view: ChartSimilarityViewModel }>) {
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>比较依据</dt>
          <dd>八字四柱原值</dd>
        </div>
        <div>
          <dt>四柱完全相同</dt>
          <dd>{view.exact_match ? "是" : "否"}</dd>
        </div>
        <div>
          <dt>相同柱位</dt>
          <dd>
            {view.matched_positions.length
              ? view.matched_positions.map((position) => CHART_SIMILARITY_POSITION_LABELS[position]).join("、")
              : "无"}
          </dd>
        </div>
      </dl>
      <Table
        caption="八字四柱逐柱比较"
        headers={["柱位", "左侧盘面", "右侧盘面", "原值结果"]}
        rows={view.comparisons.map((comparison) => [
          CHART_SIMILARITY_POSITION_LABELS[comparison.position],
          `${comparison.left.stem}${comparison.left.branch}`,
          `${comparison.right.stem}${comparison.right.branch}`,
          comparison.exact_match ? "相同" : "不同",
        ])}
      />
      <p className={styles.note}>
        {view.limitations.join(" ")}
      </p>
    </div>
  );
}

const TIME_CHECK_EVIDENCE_REASON_LABELS: Record<string, string> = {
  candidate_chart_facts_missing: "候选盘面事实缺失",
  positive_branch_relation: "存在合、会或三合支关系",
  negative_branch_relation: "存在冲、害、破或刑支关系",
  domain_ten_god_role: "事件领域对应十神角色",
  no_supporting_or_opposing_signal: "没有支持或反对信号",
};

function timeCheckEvidenceReasons(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return "无支持或反对信号";
  const labels = value
    .filter((item): item is string => typeof item === "string")
    .map((item) => TIME_CHECK_EVIDENCE_REASON_LABELS[item] ?? item);
  return labels.length ? labels.join("；") : "无支持或反对信号";
}

function timeCheckEvidenceRelations(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return "无";
  const relations = value.flatMap((item) => {
    if (item === null || typeof item !== "object" || Array.isArray(item)) return [];
    const row = item as Record<string, unknown>;
    const relation = typeof row.relation_type === "string" ? row.relation_type : "";
    const position = typeof row.natal_position === "string" ? row.natal_position : "";
    return relation ? [`${position || "柱位"}${relation}`] : [];
  });
  return relations.length ? relations.join("、") : "无";
}

function timeCheckEvidenceRows(view: TimeCheckViewModel): string[][] {
  return view.candidate_rankings.flatMap((candidate) =>
    candidate.event_evidence.map((evidence) => {
      const score = typeof evidence.evidence_score === "number"
        ? String(evidence.evidence_score)
        : "—";
      const eventId = typeof evidence.event_id === "string" ? evidence.event_id : "—";
      const tenGod = typeof evidence.event_year_ten_god === "string"
        ? evidence.event_year_ten_god
        : "无";
      return [
        candidate.hour_branch,
        eventId,
        score,
        evidence.matched === true ? "命中候选证据" : "未命中候选证据",
        timeCheckEvidenceRelations(evidence.relations),
        tenGod,
        timeCheckEvidenceReasons(evidence.reasons),
      ];
    }),
  );
}

function TimeCheckChart({ view }: Readonly<{ view: TimeCheckViewModel }>) {
  const evidenceRows = timeCheckEvidenceRows(view);
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>候选盘数</dt>
          <dd>{view.candidate_count} 个时辰代表候选</dd>
        </div>
        <div>
          <dt>时间口径</dt>
          <dd>{view.time_basis_policy}</dd>
        </div>
        <div>
          <dt>已知事件</dt>
          <dd>
            {view.known_event_count} 条 · {view.ranking_status === "candidate_evidence_ranked" ? "已生成候选证据排序" : "未生成候选排序"}
          </dd>
        </div>
      </dl>
      <Table
        caption="十二时辰候选四柱事实"
        headers={["时辰", "候选民用时间", "已知范围", "四柱", "归一化时间"]}
        rows={view.candidates.map((candidate) => [
          candidate.hour_branch,
          candidate.local_civil_datetime,
          candidate.within_known_time_range ? "范围内" : "范围外",
          displayValue(candidate.four_pillars),
          displayValue(candidate.calendar_normalization.normalized_datetime),
        ])}
      />
      {view.candidate_rankings.length > 0 ? (
        <Table
          caption="结构化事件候选证据排序"
          headers={["排名", "时辰", "证据分", "匹配事件", "范围"]}
          rows={view.candidate_rankings.map((candidate) => [
            String(candidate.rank),
            candidate.hour_branch,
            String(candidate.evidence_score),
            candidate.matched_event_ids.length ? candidate.matched_event_ids.join("、") : "无",
            candidate.eligible ? "范围内" : "范围外",
          ])}
        />
      ) : null}
      {evidenceRows.length > 0 ? (
        <Table
          caption="结构化事件证据明细"
          headers={["候选时辰", "事件", "分数", "结果", "支关系", "事件年柱十神", "证据说明"]}
          rows={evidenceRows}
        />
      ) : null}
      <p className={styles.note}>{view.limitations.join(" ")}</p>
    </div>
  );
}

function CanwenChart({ view }: Readonly<{ view: CanwenViewModel }>) {
  const artLabels: Record<"bazi" | "ziwei" | "qizheng", string> = {
    bazi: "八字",
    ziwei: "紫微",
    qizheng: "七政",
  };
  const labelFor = (art: string) =>
    art in artLabels ? artLabels[art as "bazi" | "ziwei" | "qizheng"] : art;
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>选用术数</dt>
          <dd>{view.selected_art_ids.map((art) => artLabels[art]).join("、")}</dd>
        </div>
      </dl>
      {view.dimensions.map((dimension) => (
        <div className={styles.tableWrap} key={dimension.dimension_id}>
          <Table
            caption={`维度：${dimension.dimension_id}`}
            headers={["术数", "事实范围", "状态"]}
            rows={dimension.signals.map((signal) => [
              artLabels[signal.art_id as "bazi" | "ziwei" | "qizheng"] ?? signal.art_id,
              signal.display_text,
              "已提供",
            ])}
          />
          {dimension.missing_art_ids.length > 0 ? (
            <p className={styles.note}>缺少跨术事实范围：{dimension.missing_art_ids.map(labelFor).join("、")}</p>
          ) : null}
          {dimension.convergence.map((item) => <p className={styles.note} key={item}>{item}</p>)}
          {dimension.disagreements.map((item) => <p className={styles.note} key={item}>{item}</p>)}
        </div>
      ))}
      <p className={styles.note}>这里只展示 Runtime 已声明的共同事实范围；没有把不同术数的原始字段拼成吉凶或实质性互证结论。</p>
    </div>
  );
}

function HecanChart({ view }: Readonly<{ view: HecanViewModel }>) {
  const artLabels: Record<"bazi" | "ziwei" | "qizheng", string> = {
    bazi: "八字",
    ziwei: "紫微",
    qizheng: "七政",
  };
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>选用术数</dt>
          <dd>{view.selected_art_ids.map((art) => artLabels[art]).join("、")}</dd>
        </div>
      </dl>
      {view.dimensions.map((dimension) => (
        <div className={styles.tableWrap} key={dimension.dimension_id}>
          <Table
            caption={`维度：${dimension.dimension_id}`}
            headers={["术数", "事实范围", "状态"]}
            rows={dimension.signals.map((signal) => [
              artLabels[signal.art_id as "bazi" | "ziwei" | "qizheng"] ?? signal.art_id,
              signal.display_text,
              "已提供",
            ])}
          />
          {dimension.missing_art_ids.length > 0 ? (
            <p className={styles.note}>缺少跨术事实范围：{dimension.missing_art_ids.map((art) => artLabels[art as "bazi" | "ziwei" | "qizheng"] ?? art).join("、")}</p>
          ) : null}
          {dimension.convergence.map((item) => <p className={styles.note} key={item}>{item}</p>)}
          {dimension.disagreements.map((item) => <p className={styles.note} key={item}>{item}</p>)}
        </div>
      ))}
      <p className={styles.note}>这里只展示 Runtime 已声明的共同事实范围；实质互证、分歧判断和整合深读仍需后续证据合同。</p>
    </div>
  );
}

function WenshiChart({ view }: Readonly<{ view: WenshiViewModel }>) {
  const artLabels: Record<"liuyao" | "qimen" | "daliuren", string> = {
    liuyao: "六爻",
    qimen: "奇门",
    daliuren: "大六壬",
  };
  const labelFor = (art: string) =>
    art in artLabels ? artLabels[art as "liuyao" | "qimen" | "daliuren"] : art;
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>选用术数</dt>
          <dd>{view.selected_art_ids.map((art) => artLabels[art]).join("、")}</dd>
        </div>
      </dl>
      {view.dimensions.map((dimension) => (
        <div className={styles.tableWrap} key={dimension.dimension_id}>
          <Table
            caption={`维度：${dimension.dimension_id}`}
            headers={["术数", "结构事实", "状态"]}
            rows={dimension.signals.map((signal) => [
              labelFor(signal.art_id),
              signal.display_text,
              "已提供",
            ])}
          />
          {dimension.missing_art_ids.length > 0 ? (
            <p className={styles.note}>缺少三术结构事实：{dimension.missing_art_ids.map(labelFor).join("、")}</p>
          ) : null}
          {dimension.convergence.map((item) => <p className={styles.note} key={item}>{item}</p>)}
          {dimension.disagreements.map((item) => <p className={styles.note} key={item}>{item}</p>)}
        </div>
      ))}
      <p className={styles.note}>这里只展示同一问题、同一时空下 Runtime 已计算的三术结构事实，不把不同术数拼成实质性结论。</p>
    </div>
  );
}

type RelationshipViewModel =
  | BaziRelationshipViewModel
  | ZiweiRelationshipViewModel
  | QizhengRelationshipViewModel;

const RELATIONSHIP_TYPE_LABELS: Record<RelationshipViewModel["relationship_type"], string> = {
  romantic: "情侣",
  married: "夫妻",
  parent_child: "亲子",
  business: "合伙",
  work: "职场",
  friend: "朋友",
};

function RelationshipChart({ view }: Readonly<{ view: RelationshipViewModel }>) {
  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <dl className={styles.meta}>
        <div>
          <dt>甲方</dt>
          <dd>{view.subjects[0].label}</dd>
        </div>
        <div>
          <dt>乙方</dt>
          <dd>{view.subjects[1].label}</dd>
        </div>
        <div>
          <dt>关系类型</dt>
          <dd>{RELATIONSHIP_TYPE_LABELS[view.relationship_type]}</dd>
        </div>
      </dl>
      <Table
        caption="跨盘结构事实"
        headers={["维度", "结构", "依据"]}
        rows={view.signals.map((signal) => [
          signal.dimension_id,
          signal.display_text,
          `双方${signal.fact_refs.length > 1 ? "命盘" : "盘面"}计算事实`,
        ])}
      />
      <p className={styles.note}>
        这里只展示双方命盘之间可追溯的机械结构事实；没有把结构事实转换成匹配分数、吉凶或现实决定。
      </p>
    </div>
  );
}

export function RuntimeChart({ viewModel }: Readonly<{ viewModel: ViewModel }>) {
  switch (viewModel.schema_version) {
    case "bazi-relationship/v1":
    case "ziwei-relationship/v1":
    case "qizheng-relationship/v1":
      return <RelationshipChart view={viewModel} />;
    case "hecan-view/v1":
      return <HecanChart view={viewModel} />;
    case "canwen-view/v1":
      return <CanwenChart view={viewModel} />;
    case "wenshi-view/v1":
      return <WenshiChart view={viewModel} />;
    case "ziwei-chart/v1":
      return <ZiweiChart view={viewModel} />;
    case "qizheng-chart/v1":
      return <QizhengChart view={viewModel} />;
    case "liuyao-chart/v1":
      return <LiuyaoChart view={viewModel} />;
    case "meihua-chart/v1":
      return <MeihuaChart view={viewModel} />;
    case "luming-nayin-chart/v1":
      return <LumingNayinChart view={viewModel} />;
    case "rhythm-facts-view/v1":
      return <RhythmFactsChart view={viewModel} />;
    case "taiyi-chart/v1":
      return <TaiyiChart view={viewModel} />;
    case "selection-chart/v1":
      return <SelectionChart view={viewModel} />;
    case "fengshui-view/v1":
      return <FengshuiChart view={viewModel} />;
    case "qimen-chart/v1":
      return <QimenChart view={viewModel} />;
    case "daliuren-chart/v1":
      return <DaliurenChart view={viewModel} />;
    case "physiognomy-view/v1":
      return <PhysiognomyChart view={viewModel} />;
    case "five-elements-facts-view/v1":
      return <FiveElementsFactsChart view={viewModel} />;
    case "chart-similarity-view/v1":
      return <ChartSimilarityChart view={viewModel} />;
    case "time-check-view/v1":
      return <TimeCheckChart view={viewModel} />;
    default:
      return null;
  }
}
