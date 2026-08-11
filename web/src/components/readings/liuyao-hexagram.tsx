import { useId } from "react";

import type { ReadingEvidence, ReadingFact } from "@/lib/api";

import styles from "./liuyao-hexagram.module.css";

type LineKind = "yin" | "yang" | "unknown";

type HexagramLine = {
  position: number;
  kind: LineKind;
  state: string | null;
  moving: boolean;
  roles: ("世" | "应")[];
  details: string[];
  changedKind: LineKind;
  changedDetails: string[];
};

type HexagramView = {
  primaryName: string | null;
  changedName: string | null;
  lines: HexagramLine[];
  lineCount: number;
  parseable: boolean;
  sourceRefs: Set<string>;
};

const lineLabels: Record<number, string> = {
  1: "初爻",
  2: "二爻",
  3: "三爻",
  4: "四爻",
  5: "五爻",
  6: "上爻",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function factKey(fact: ReadingFact): string {
  const refKey = fact.ref.split("/").at(-1)?.trim();
  if (refKey) return refKey;
  const displayKey = fact.display_text.match(/^([^:：]{1,40})\s*[:：]/)?.[1];
  return displayKey?.trim() ?? "";
}

function findFact(facts: ReadingFact[], keys: string[]): ReadingFact | undefined {
  return facts.find((fact) => {
    const key = factKey(fact);
    if (keys.includes(key)) return true;
    const displayKey = fact.display_text.match(/^([^:：]{1,40})\s*[:：]/)?.[1];
    return displayKey ? keys.includes(displayKey.trim()) : false;
  });
}

function nameFromFact(fact: ReadingFact | undefined): string | null {
  if (!fact) return null;
  if (isRecord(fact.value)) {
    return (
      safeText(fact.value.name) ??
      safeText(fact.value.label) ??
      safeText(fact.value.title)
    );
  }
  const direct = safeText(fact.value);
  if (direct) return direct;
  const displayValue = fact.display_text.match(/^[^:：]{1,40}\s*[:：]\s*(.+)$/s)?.[1];
  if (!displayValue || /^[{[]/.test(displayValue.trim())) return null;
  return displayValue.trim();
}

function integerLine(value: unknown): number | null {
  if (typeof value === "number" && Number.isInteger(value) && value >= 1 && value <= 6) {
    return value;
  }
  if (typeof value === "string" && /^[1-6]$/.test(value.trim())) {
    return Number(value.trim());
  }
  return null;
}

function lineKind(value: unknown): LineKind {
  const normalized = safeText(value)?.toLowerCase() ?? "";
  if (normalized === "阳" || normalized === "yang" || normalized.includes("阳")) {
    return "yang";
  }
  if (normalized === "阴" || normalized === "yin" || normalized.includes("阴")) {
    return "yin";
  }
  return "unknown";
}

function najiaText(value: unknown): string | null {
  if (!isRecord(value)) return null;
  const combined = [safeText(value.stem), safeText(value.branch)]
    .filter(Boolean)
    .join("");
  return safeText(value.ganzhi) ?? (combined || null);
}

function lineRoles(value: unknown): ("世" | "应")[] {
  const candidates = Array.isArray(value) ? value : [value];
  const roles: ("世" | "应")[] = [];
  for (const candidate of candidates) {
    const text = safeText(candidate)?.toLowerCase();
    if (!text) continue;
    if ((text === "世" || text === "shi" || text === "self") && !roles.includes("世")) {
      roles.push("世");
    }
    if (
      (text === "应" || text === "ying" || text === "response") &&
      !roles.includes("应")
    ) {
      roles.push("应");
    }
  }
  return roles;
}

function lineDetails(value: Record<string, unknown>): string[] {
  return [
    safeText(value.six_spirit),
    safeText(value.six_relative),
    najiaText(value.najia),
  ].filter((item): item is string => Boolean(item));
}

function parsedLines(value: unknown): Map<number, HexagramLine> {
  const parsed = new Map<number, HexagramLine>();
  if (!Array.isArray(value)) return parsed;

  for (const item of value) {
    if (!isRecord(item)) continue;
    const position =
      integerLine(item.line) ?? integerLine(item.position) ?? integerLine(item.index);
    if (!position) continue;
    const changed = isRecord(item.changed_line) ? item.changed_line : null;
    parsed.set(position, {
      position,
      kind: lineKind(item.yin_yang ?? item.line_type ?? item.state),
      state: safeText(item.state),
      moving: item.moving === true || item.is_moving === true,
      roles: lineRoles(item.roles ?? item.role),
      details: lineDetails(item),
      changedKind: changed
        ? lineKind(changed.yin_yang ?? changed.line_type ?? changed.state)
        : "unknown",
      changedDetails: changed ? lineDetails(changed) : [],
    });
  }
  return parsed;
}

function lineNumbers(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => integerLine(item))
    .filter((item): item is number => item !== null);
}

function buildHexagramView(facts: ReadingFact[]): HexagramView {
  const primaryFact = findFact(facts, ["primary_hexagram", "本卦"]);
  const changedFact = findFact(facts, ["changed_hexagram", "变卦"]);
  const movingFact = findFact(facts, ["moving_lines", "动爻"]);
  const shiYingFact = findFact(facts, ["shi_ying", "世应"]);
  const linesFact = findFact(facts, ["lines", "六爻", "爻"]);
  const recognized = [primaryFact, changedFact, movingFact, shiYingFact, linesFact].filter(
    (fact): fact is ReadingFact => Boolean(fact),
  );
  const sourceRefs = new Set(recognized.map((fact) => fact.ref));
  const lineMap = parsedLines(linesFact?.value);
  const movingLines = new Set(lineNumbers(movingFact?.value));

  const primaryValue = isRecord(primaryFact?.value) ? primaryFact.value : null;
  const shiYingValue = isRecord(shiYingFact?.value) ? shiYingFact.value : null;
  const shiLine =
    integerLine(shiYingValue?.shi) ?? integerLine(primaryValue?.shi_line);
  const yingLine =
    integerLine(shiYingValue?.ying) ?? integerLine(primaryValue?.ying_line);

  const lines = Array.from({ length: 6 }, (_, offset) => {
    const position = offset + 1;
    const parsed = lineMap.get(position) ?? {
      position,
      kind: "unknown" as const,
      state: null,
      moving: false,
      roles: [],
      details: [],
      changedKind: "unknown" as const,
      changedDetails: [],
    };
    const roles = [...parsed.roles];
    if (shiLine === position && !roles.includes("世")) roles.push("世");
    if (yingLine === position && !roles.includes("应")) roles.push("应");
    return {
      ...parsed,
      moving: parsed.moving || movingLines.has(position),
      roles,
    };
  }).sort((left, right) => right.position - left.position);

  return {
    primaryName: nameFromFact(primaryFact),
    changedName: nameFromFact(changedFact),
    lines,
    lineCount: lineMap.size,
    parseable:
      Boolean(primaryFact || changedFact || shiYingFact) ||
      lineMap.size > 0 ||
      movingLines.size > 0,
    sourceRefs,
  };
}

function LineMark({ kind }: Readonly<{ kind: LineKind }>) {
  const label = kind === "yang" ? "阳爻" : kind === "yin" ? "阴爻" : "阴阳未公开";
  return (
    <span className={styles.lineMark} data-kind={kind} aria-label={label}>
      {kind === "yin" ? (
        <>
          <span aria-hidden="true" />
          <span aria-hidden="true" />
        </>
      ) : (
        <span aria-hidden="true" />
      )}
    </span>
  );
}

export function LiuyaoHexagram({
  facts,
  evidence,
}: Readonly<{
  facts: ReadingFact[];
  evidence: ReadingEvidence[];
}>) {
  const titleId = useId();
  const view = buildHexagramView(facts);
  const linkedEvidence = evidence.filter((item) =>
    item.supports_fact_refs.some((ref) => view.sourceRefs.has(ref)),
  );

  return (
    <section className={styles.plate} aria-labelledby={titleId}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>服务端公开盘面</p>
          <h3 id={titleId}>六爻卦象</h3>
        </div>
        <p className={styles.order}>爻位按上爻至初爻排列</p>
      </header>

      <dl className={styles.names}>
        <div>
          <dt>本卦</dt>
          <dd>{view.primaryName ?? "未公开"}</dd>
        </div>
        <div>
          <dt>变卦</dt>
          <dd>{view.changedName ?? "未公开"}</dd>
        </div>
      </dl>

      {!view.parseable ? (
        <p className={styles.fallback} role="note">
          服务端未返回可解析的公开卦象结构；这里只保留六个爻位，页面不会自行补算。
        </p>
      ) : view.lineCount < 6 ? (
        <p className={styles.fallback} role="note">
          服务端仅返回 {view.lineCount}/6 个可解析爻位；其余爻位保持未公开，页面不会自行补算。
        </p>
      ) : null}

      <ol className={styles.lines} aria-label="六爻排布（自上而下）">
        {view.lines.map((line) => {
          const stateLabel =
            line.state ??
            (line.kind === "yang" ? "阳爻" : line.kind === "yin" ? "阴爻" : "结构未公开");
          return (
            <li className={styles.line} data-moving={line.moving} key={line.position}>
              <span className={styles.position}>{lineLabels[line.position]}</span>
              <div className={styles.lineBody}>
                <div className={styles.lineVisual}>
                  <LineMark kind={line.kind} />
                  <span className={styles.state}>{stateLabel}</span>
                </div>
                {line.details.length > 0 ? (
                  <span className={styles.details}>{line.details.join(" · ")}</span>
                ) : null}
              </div>
              <div className={styles.annotations}>
                <span className={line.moving ? styles.moving : styles.static}>
                  {line.moving ? "动爻" : "静爻"}
                </span>
                {line.roles.map((role) => (
                  <strong className={styles.role} key={role}>
                    {role}
                  </strong>
                ))}
              </div>
              {line.moving &&
              (line.changedKind !== "unknown" || line.changedDetails.length > 0) ? (
                <div className={styles.changed}>
                  <span>变为</span>
                  <LineMark kind={line.changedKind} />
                  {line.changedDetails.length > 0 ? (
                    <span>{line.changedDetails.join(" · ")}</span>
                  ) : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>

      {linkedEvidence.length > 0 ? (
        <p className={styles.evidenceLink}>
          {linkedEvidence.length} 条依据与卦象事实相连 ·{" "}
          <a href="#reading-evidence-title">查看依据</a>
        </p>
      ) : (
        <p className={styles.boundary}>
          卦象仅复述公开事实；没有关联依据时，不在此处补写解释。
        </p>
      )}
    </section>
  );
}
