"use client";

import { useMemo, useRef, useState, type KeyboardEvent } from "react";

import type { BaziChartView } from "@/lib/reading-display";
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
  onSelect,
}: Readonly<{
  cells: WorkspaceCell[];
  selectedId: string | null;
  onSelect: (cellId: string) => void;
}>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  function focusAt(index: number) {
    if (index >= 0 && index < refs.current.length) {
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
            tabIndex={index === 0 ? 0 : -1}
            onClick={() => onSelect(cell.id)}
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
        服务端尚未返回该时间层的逐柱结构，此层暂无可聚焦内容。
      </p>
    </div>
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
          <p className={styles.brand}>FateRadar</p>
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
      </div>
    );
  }

  return (
    <ChartWorkspaceShell
      view={workspaceView}
      renderBoard={renderBoard}
      detail={detail}
      onCloseDetail={() => setSelectedCellId(null)}
      boardLabel="八字盘面"
    />
  );
}
