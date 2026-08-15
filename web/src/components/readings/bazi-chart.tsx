"use client";

import {
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import {
  formatBaziInterpretiveCandidateRows,
  type BaziChartView,
} from "@/lib/reading-display";
import type { BaziCoreFacts } from "@/view-models/registry";
import {
  baziWorkspaceFactsFromChart,
  buildBaziWorkspaceView,
  resolveBaziFocusDetail,
  type WorkspaceCell,
  type WorkspaceLayer,
} from "@/lib/chart-workspace";

import { ChartWorkspaceShell } from "./chart-workspace-shell";

import styles from "./bazi-chart.module.css";

/**
 * Focusable pillar board: roving tabindex with arrow-key movement and
 * Enter/Space activation via native button clicks.
 */
function PillarGrid({
  cells,
  selectedId,
  detailId,
  onSelect,
}: Readonly<{
  cells: WorkspaceCell[];
  selectedId: string | null;
  detailId: string;
  onSelect: (cellId: string) => void;
}>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const [tabStopId, setTabStopId] = useState<string | null>(
    cells[0]?.id ?? null,
  );
  const activeTabStopId = cells.some((cell) => cell.id === tabStopId)
    ? tabStopId
    : (cells[0]?.id ?? null);

  function focusAt(index: number) {
    if (index >= 0 && index < refs.current.length) {
      setTabStopId(cells[index].id);
      refs.current[index]?.focus();
    }
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      focusAt((index + 1) % cells.length);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      focusAt((index - 1 + cells.length) % cells.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusAt(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusAt(cells.length - 1);
    }
  }

  return (
    <div className={styles.pillarGrid} role="group" aria-label="四柱">
      {cells.map((cell, index) => {
        const stem = cell.value?.slice(0, 1) ?? "—";
        const branch = cell.value?.slice(1, 2) ?? "";
        return (
          <button
            key={cell.id}
            type="button"
            ref={(element) => {
              refs.current[index] = element;
            }}
            className={styles.pillarCard}
            data-selected={cell.id === selectedId}
            aria-pressed={cell.id === selectedId}
            aria-controls={detailId}
            aria-expanded={cell.id === selectedId}
            tabIndex={cell.id === activeTabStopId ? 0 : -1}
            onClick={() => onSelect(cell.id)}
            onFocus={() => setTabStopId(cell.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            <span className={styles.pillarLabel}>{cell.label}</span>
            <span className={styles.pillarStem}>{stem}</span>
            <span className={styles.pillarBranch}>{branch || "—"}</span>
            <span className={styles.pillarFull}>{cell.value ?? "—"}</span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * Honest note for layers whose per-pillar structure the server did not return.
 * The layer may still carry a summary fact, but there is nothing to focus.
 */
function LayerNote({ layer }: Readonly<{ layer: WorkspaceLayer }>) {
  return (
    <div className={styles.layerNote}>
      <p className={styles.layerNoteTitle}>{layer.label}</p>
      {layer.summary ? (
        <p className={styles.layerNoteText}>{layer.summary}</p>
      ) : null}
      <p className={styles.layerNoteText}>
        {layer.status === "ready"
          ? "Runtime 已返回该时间层事实；当前页面先展示年度汇总，未在浏览器重新排盘。"
          : "服务端尚未返回该时间层的逐柱结构，此层暂无可聚焦内容。"}
      </p>
    </div>
  );
}

const ELEMENT_LABELS: Record<string, string> = {
  wood: "木",
  fire: "火",
  earth: "土",
  metal: "金",
  water: "水",
};

function BaziCoreFactSummary({
  facts,
}: Readonly<{ facts: BaziCoreFacts | null | undefined }>) {
  if (!facts) return null;
  const rows: Array<{ label: string; text: string }> = [];
  if (facts.day_master) {
    rows.push({
      label: "日主",
      text: `${facts.day_master.stem} · ${ELEMENT_LABELS[facts.day_master.element] ?? facts.day_master.element} · ${facts.day_master.polarity}`,
    });
  }
  if (facts.hidden_stems) {
    rows.push({
      label: "藏干",
      text: facts.hidden_stems
        .map((item) => `${item.position} ${item.branch}：${item.stems.join("、")}`)
        .join("；"),
    });
  }
  if (facts.ten_gods) {
    rows.push({
      label: "十神",
      text: facts.ten_gods.heavenly_stems
        .map((item) => `${item.position} ${item.stem}·${item.ten_god}`)
        .join("；"),
    });
  }
  if (facts.nayin) {
    rows.push({
      label: "纳音",
      text: facts.nayin.map((item) => `${item.position} ${item.name}`).join("；"),
    });
  }
  if (facts.month_command) {
    rows.push({
      label: "月令",
      text: `${facts.month_command.label} · 主气 ${facts.month_command.main_qi}（${ELEMENT_LABELS[facts.month_command.main_qi_element] ?? facts.month_command.main_qi_element}）`,
    });
  }
  if (facts.seasonal_profile) {
    rows.push({
      label: "季节",
      text: `${facts.seasonal_profile.season} · ${facts.seasonal_profile.month_qi} · ${facts.seasonal_profile.temperature} · ${facts.seasonal_profile.moisture}`,
    });
  }
  if (facts.tiaohou_markers) {
    rows.push({
      label: "调候标记",
      text: `${facts.tiaohou_markers.markers.join("、")} · ${facts.tiaohou_markers.scope}`,
    });
  }
  if (facts.element_inventory) {
    rows.push({
      label: "五行计数",
      text: facts.element_inventory.visible_stem_branch_counts
        .map((item) => `${ELEMENT_LABELS[item.element] ?? item.element}${item.value}`)
        .join("、"),
    });
  }
  if (facts.branch_relations?.length) {
    rows.push({
      label: "地支关系",
      text: facts.branch_relations
        .map((item) => `${item.relation_type}（${item.branches.join("、")}）`)
        .join("；"),
    });
  }
  if (facts.shensha_auxiliary) {
    rows.push({
      label: "神煞辅助",
      text: facts.shensha_auxiliary.calculated_items.length
        ? facts.shensha_auxiliary.calculated_items
            .map((item) => `${item.name}（${item.matched_positions.join("、")}）`)
            .join("；")
        : "本命未命中已声明的辅助项",
    });
  }
  if (facts.luck_cycles) {
    const cycles = facts.luck_cycles.cycles.slice(0, 3).map((item) => item.pillar).join("、");
    rows.push({
      label: "大运",
      text: `${facts.luck_cycles.status}${facts.luck_cycles.direction ? ` · ${facts.luck_cycles.direction}` : ""}${cycles ? ` · 序列 ${cycles}` : ""}`,
    });
  }
  if (facts.year_layers?.length) {
    rows.push({
      label: "流年",
      text: facts.year_layers
        .map(
          (item) =>
            `${item.year} ${item.ganzhi} · ${item.stem_ten_god} · 立春分段 ${item.ganzhi_segments.length} 段 · 大运 ${String(item.active_luck_cycle.status ?? "已返回")}`,
        )
        .join("；"),
    });
  }
  if (facts.month_layers?.length) {
    rows.push({
      label: "流月",
      text: facts.month_layers
        .map((item) => {
          const ganzhi = item.ganzhi_segments
            .map((segment) => (typeof segment.ganzhi === "string" ? segment.ganzhi : null))
            .filter((value): value is string => Boolean(value))
            .join("、");
          return `${item.period} · ${ganzhi || "分段事实"} · ${item.ganzhi_segments.length} 段`;
        })
        .join("；"),
    });
  }
  if (facts.day_layers?.length) {
    rows.push({
      label: "流日",
      text: facts.day_layers
        .map((item) => {
          const ganzhi = item.ganzhi_segments
            .map((segment) => (typeof segment.ganzhi === "string" ? segment.ganzhi : null))
            .filter((value): value is string => Boolean(value))
            .join("、");
          return `${item.period} · ${ganzhi || "分段事实"} · ${item.ganzhi_segments.length} 段`;
        })
        .join("；"),
    });
  }
  if (facts.interpretive_candidates) {
    for (const [label, text] of formatBaziInterpretiveCandidateRows(
      facts.interpretive_candidates,
    )) {
      rows.push({ label, text });
    }
  }
  if (!rows.length) return null;
  return (
    <details className={styles.coreFacts} open>
      <summary>Runtime 已计算事实</summary>
      <dl className={styles.coreFactsList}>
        {rows.map((row) => (
          <div key={row.label}>
            <dt>{row.label}</dt>
            <dd>{row.text}</dd>
          </div>
        ))}
      </dl>
      <p className={styles.coreFactsNote}>
        这里只展示 Runtime 已返回的计算事实、证据与候选；页面不在浏览器重新排盘，也不把候选或辅助标记升级成吉凶结论。
      </p>
    </details>
  );
}

/**
 * Bazi board rendered inside the shared chart workspace shell. The board maps
 * only server-provided public facts; it never calculates pillars, stars, or
 * patterns, and missing structures render as unavailable.
 */
export function BaziChart({
  chart,
  title = "八字命盘",
}: Readonly<{ chart: BaziChartView; title?: string }>) {
  const detailId = `bazi-focus-${useId()}`;
  const view = useMemo(
    () => buildBaziWorkspaceView(baziWorkspaceFactsFromChart(chart)),
    [chart],
  );
  const workspaceView = useMemo(
    () => ({ ...view, title }),
    [view, title],
  );
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);

  const detail = useMemo(
    () =>
      selectedCellId
        ? resolveBaziFocusDetail(workspaceView, selectedCellId)
        : null,
    [workspaceView, selectedCellId],
  );

  function renderBoard(layer: WorkspaceLayer) {
    if (layer.id !== "natal") {
      return <LayerNote layer={layer} />;
    }
    return (
      <div className={styles.board}>
        <div className={styles.brandBlock}>
          <p className={styles.brand}>命理工具</p>
          <p className={styles.brandSub}>
            {chart.dayMaster ? `日主 ${chart.dayMaster}` : "八字本命"}
          </p>
          {chart.monthCommand ? (
            <p className={styles.brandMeta}>月令 {chart.monthCommand}</p>
          ) : null}
        </div>

        <PillarGrid
          cells={workspaceView.cells}
          selectedId={selectedCellId}
          detailId={detailId}
          onSelect={setSelectedCellId}
        />

        {workspaceView.highlights.length > 0 ? (
          <div className={styles.highlights}>
            <h4>盘面要点</h4>
            <ul>
              {workspaceView.highlights.map((highlight) => (
                <li key={highlight.id} data-tone={highlight.tone}>
                  <strong>{highlight.title}</strong>
                  <span>{highlight.body}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <BaziCoreFactSummary facts={chart.coreFacts} />
      </div>
    );
  }

  return (
    <ChartWorkspaceShell
      view={workspaceView}
      renderBoard={renderBoard}
      detail={detail}
      detailId={detailId}
      onCloseDetail={() => setSelectedCellId(null)}
      boardLabel="八字盘面"
    />
  );
}
