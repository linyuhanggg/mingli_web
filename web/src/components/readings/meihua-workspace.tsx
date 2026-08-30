"use client";

import { useRef, useState, type KeyboardEvent } from "react";

import { displayPublicText } from "@/lib/public-labels";
import type {
  MeihuaChartViewModel,
  StructuredFactObject,
} from "@/view-models/registry";

import styles from "./meihua-workspace.module.css";

type Hexagram = MeihuaChartViewModel["primary_hexagram"];
type ElementName = "木" | "火" | "土" | "金" | "水";
type ElementId = "wood" | "fire" | "earth" | "metal" | "water";

const CASTING_METHOD_LABELS: Readonly<Record<MeihuaChartViewModel["casting_method"], string>> = {
  time: "按时间起卦",
  supplied_number: "按数字起卦",
  sound_count: "按声数起卦",
  observation: "观物起卦",
  supplied_hexagram: "已知卦象起卦",
};

const ELEMENT_IDS: Readonly<Record<ElementName, ElementId>> = {
  木: "wood",
  火: "fire",
  土: "earth",
  金: "metal",
  水: "water",
};

const ELEMENT_SHAPES: Readonly<Record<ElementName, string>> = {
  木: "▯",
  火: "△",
  土: "■",
  金: "●",
  水: "〜",
};

const FACT_STATUS_LABELS: Readonly<Record<string, string>> = {
  calculated: "已计算",
  calculated_relation_not_verdict: "已计算关系",
  calculated_strength_not_verdict: "旺衰已计算，尚非断语",
  relation_adjudicated_not_event_verdict: "关系极性已裁定",
  source_adjudicated_relations: "关系来源已核验",
  upper: "上卦",
  lower: "下卦",
};

const SOURCE_PLATE_LABELS: Readonly<Record<string, string>> = {
  primary_body: "本卦·体",
  primary_use: "本卦·用",
  mutual_body: "互卦·体",
  mutual_use: "互卦·用",
  changed_body: "变卦·体",
  changed_use: "变卦·用",
};

const RELATION_POLARITY_LABELS = {
  supportive: "用生体（支持体）",
  depleting: "体生用（体有耗）",
  adverse: "用克体（克体）",
  favorable: "体克用（体制用）",
  harmonious: "体用比和",
} as const;

function isRecord(value: unknown): value is StructuredFactObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function readText(value: StructuredFactObject, keys: readonly string[]): string | null {
  for (const key of keys) {
    const candidate = value[key];
    if (typeof candidate === "string" && candidate.trim()) return candidate.trim();
  }
  return null;
}

function publicLabel(view: MeihuaChartViewModel, value: string | null | undefined): string {
  if (!value) return "服务端未返回";
  return (
    displayPublicText(view.public_labels, value, FACT_STATUS_LABELS) ||
    "服务端未返回公开名称"
  );
}

function ElementFact({ element }: Readonly<{ element: string }>) {
  if (!(element in ELEMENT_IDS)) {
    return <span className={styles.elementFact}>{element}</span>;
  }
  const name = element as ElementName;
  return (
    <span className={styles.elementFact} data-element={ELEMENT_IDS[name]}>
      <span aria-hidden="true" className={styles.elementShape}>{ELEMENT_SHAPES[name]}</span>
      <span>{name}</span>
    </span>
  );
}

function HexagramPlate({
  label,
  hexagram,
  itemRef,
  onFocus,
  onKeyDown,
  tabIndex,
}: Readonly<{
  label: "本卦" | "互卦" | "变卦";
  hexagram: Hexagram | null;
  itemRef: (element: HTMLLIElement | null) => void;
  onFocus: () => void;
  onKeyDown: (event: KeyboardEvent<HTMLLIElement>) => void;
  tabIndex: number;
}>) {
  return (
    <li
      ref={itemRef}
      aria-label={hexagram
        ? `${label}，${hexagram.name}，上卦 ${hexagram.upper_trigram}，下卦 ${hexagram.lower_trigram}`
        : `${label}，服务端未返回这一卦层`}
      className={styles.plate}
      data-present={hexagram ? "true" : "false"}
      tabIndex={tabIndex}
      onFocus={onFocus}
      onKeyDown={onKeyDown}
    >
      <p className={styles.plateLabel}>{label}</p>
      {hexagram ? (
        <>
          <h3>{hexagram.name}</h3>
          <dl className={styles.trigrams}>
            <div>
              <dt>上卦</dt>
              <dd>{hexagram.upper_trigram}</dd>
            </div>
            <div>
              <dt>下卦</dt>
              <dd>{hexagram.lower_trigram}</dd>
            </div>
          </dl>
        </>
      ) : (
        <p className={styles.plateEmpty}>服务端未返回这一卦层，不补造卦象。</p>
      )}
    </li>
  );
}

function BodyUseSide({
  label,
  value,
}: Readonly<{
  label: "体" | "用";
  value: MeihuaChartViewModel["body_use"]["body"];
}>) {
  return (
    <div className={styles.bodyUseSide}>
      <dt>{label}</dt>
      <dd>
        <strong>{value.trigram}</strong>
        <span>{value.position === "upper" ? "上卦" : "下卦"}</span>
        <ElementFact element={value.element} />
      </dd>
    </div>
  );
}

function BodyRelationTable({
  view,
}: Readonly<{ view: MeihuaChartViewModel }>) {
  const rows = (view.core_facts?.body_relation_facts ?? []).flatMap((item, index) => {
    if (!isRecord(item)) return [];
    return [{
      key: `${readText(item, ["position"]) ?? "relation"}-${index}`,
      position: publicLabel(view, readText(item, ["position"])),
      trigram: readText(item, ["trigram"]) ?? "服务端未返回",
      element: readText(item, ["element"]),
      relation: readText(item, ["relation"]) ?? "服务端未返回",
      status: publicLabel(
        view,
        typeof item.status === "string" ? item.status : null,
      ),
    }];
  });
  if (!rows.length) return null;

  return (
    <div className={styles.tableScroll}>
      <table className={styles.factTable}>
        <caption>体用关系明细</caption>
        <thead>
          <tr>
            <th scope="col">位置</th>
            <th scope="col">卦</th>
            <th scope="col">五行</th>
            <th scope="col">关系</th>
            <th scope="col">事实状态</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <td>{row.position}</td>
              <td>{row.trigram}</td>
              <td>{row.element ? <ElementFact element={row.element} /> : "服务端未返回"}</td>
              <td>{row.relation}</td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SeasonalTable({
  view,
}: Readonly<{ view: MeihuaChartViewModel }>) {
  const rows = view.core_facts?.seasonal_strength
    ? Object.entries(view.core_facts.seasonal_strength).flatMap(([name, value]) => {
        if (!isRecord(value)) return [];
        return [{
          key: name,
          label: publicLabel(view, name),
          trigram: readText(value, ["trigram"]) ?? "服务端未返回",
          month: readText(value, ["month_branch"]) ?? "服务端未返回",
          season: publicLabel(view, readText(value, ["season"])),
          state: publicLabel(
            view,
            typeof value.state === "string" ? value.state : null,
          ),
          status: publicLabel(
            view,
            typeof value.status === "string" ? value.status : null,
          ),
        }];
      })
    : [];
  if (!rows.length) return null;

  return (
    <div className={styles.tableScroll}>
      <table className={styles.factTable}>
        <caption>月令状态事实</caption>
        <thead>
          <tr>
            <th scope="col">对象</th>
            <th scope="col">卦</th>
            <th scope="col">月支</th>
            <th scope="col">季节</th>
            <th scope="col">状态</th>
            <th scope="col">事实状态</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <td>{row.label}</td>
              <td>{row.trigram}</td>
              <td>{row.month}</td>
              <td>{row.season}</td>
              <td>{row.state}</td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RelationCandidateTable({
  view,
}: Readonly<{ view: MeihuaChartViewModel }>) {
  const candidates = view.core_facts?.interpretive_candidates?.relation_candidates ?? [];
  if (!candidates.length) return null;

  return (
    <div className={styles.tableScroll}>
      <table className={styles.factTable}>
        <caption>体用关系来源裁定（未形成事件结论）</caption>
        <thead>
          <tr>
            <th scope="col">盘层</th>
            <th scope="col">位置</th>
            <th scope="col">关系</th>
            <th scope="col">月令状态</th>
            <th scope="col">来源极性</th>
            <th scope="col">裁定状态</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => (
            <tr key={candidate.candidate_id}>
              <td>{SOURCE_PLATE_LABELS[candidate.source_plate] ?? "服务端未返回公开盘层名"}</td>
              <td>{candidate.position === "upper" ? "上卦" : "下卦"}</td>
              <td>{candidate.relation}</td>
              <td>{candidate.seasonal_state ?? "服务端未返回"}</td>
              <td>{RELATION_POLARITY_LABELS[candidate.relation_adjudication.source_polarity]}</td>
              <td>关系极性已裁定</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MeihuaWorkspace({
  view,
  showInterpretiveSections = true,
}: Readonly<{
  view: MeihuaChartViewModel;
  showInterpretiveSections?: boolean;
}>) {
  const plates = [
    { label: "本卦" as const, hexagram: view.primary_hexagram },
    { label: "互卦" as const, hexagram: view.mutual_hexagram },
    { label: "变卦" as const, hexagram: view.changed_hexagram },
  ];
  const plateRefs = useRef<Array<HTMLLIElement | null>>([]);
  const [tabStopIndex, setTabStopIndex] = useState(0);
  const movingLineText = view.moving_lines.length
    ? view.moving_lines.map((line) => `第${line}爻`).join("、")
    : "无动爻";

  function focusPlate(index: number) {
    const nextIndex = (index + plates.length) % plates.length;
    setTabStopIndex(nextIndex);
    plateRefs.current[nextIndex]?.focus();
  }

  function handlePlateKeyDown(
    event: KeyboardEvent<HTMLLIElement>,
    index: number,
  ) {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      focusPlate(index + 1);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      focusPlate(index - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusPlate(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusPlate(plates.length - 1);
    }
  }

  return (
    <section
      aria-label="梅花易数排盘工作台"
      className={styles.workspace}
      data-schema={view.schema_version}
    >
      <header className={styles.header}>
        <div>
          <h2>本互变卦与体用</h2>
          <p>先核对卦序，再读体用关系与来源依据。</p>
        </div>
        <dl className={styles.methodMeta}>
          <div>
            <dt>起卦方式</dt>
            <dd>{CASTING_METHOD_LABELS[view.casting_method]}</dd>
          </div>
          <div>
            <dt>动爻</dt>
            <dd>{movingLineText}</dd>
          </div>
        </dl>
      </header>

      <ol className={styles.plateSequence} aria-label="本卦、互卦、变卦">
        {plates.map((plate, index) => (
          <HexagramPlate
            key={plate.label}
            label={plate.label}
            hexagram={plate.hexagram}
            itemRef={(element) => {
              plateRefs.current[index] = element;
            }}
            tabIndex={index === tabStopIndex ? 0 : -1}
            onFocus={() => setTabStopIndex(index)}
            onKeyDown={(event) => handlePlateKeyDown(event, index)}
          />
        ))}
      </ol>

      <section className={styles.bodyUse} aria-labelledby="meihua-body-use-title">
        <div className={styles.sectionHeading}>
          <h3 id="meihua-body-use-title">体用关系</h3>
          <p>{publicLabel(view, view.body_use.status)}</p>
        </div>
        <dl className={styles.bodyUseFlow}>
          <BodyUseSide label="体" value={view.body_use.body} />
          <div className={styles.relation}>
            <dt>已返回关系</dt>
            <dd>{view.body_use.relation}</dd>
          </div>
          <BodyUseSide label="用" value={view.body_use.use} />
        </dl>
      </section>

      <section className={styles.readingPane} aria-label="梅花关系事实">
        <div className={styles.sectionHeading}>
          <h3>关系事实与方法边界</h3>
          <p>盘面事实 / 方法解释 / 来源依据</p>
        </div>
        <BodyRelationTable view={view} />
        <SeasonalTable view={view} />
        {showInterpretiveSections ? <RelationCandidateTable view={view} /> : null}
        <p className={styles.boundary}>
          只展示服务端返回的体用、生克与月令事实；关系极性可以被核验，综合成败与应期仍待正式合成裁决。
        </p>
      </section>
    </section>
  );
}
