"use client";

import { useState, type ReactNode } from "react";

import type {
  ChartWorkspaceView,
  WorkspaceFocusDetail,
  WorkspaceLayer,
  WorkspaceLayerId,
} from "@/lib/chart-workspace";

import { FocusDetailDrawer } from "./focus-detail-drawer";
import { TimeLayerTabs } from "./time-layer-tabs";

import styles from "./chart-workspace-shell.module.css";

/**
 * Reusable chart workspace shell: layer tabs on top, a board slot in the
 * middle, and a focus detail drawer beside (desktop) or below (mobile) the
 * board. The shell never fetches data and never calculates; the board and the
 * focus detail come from parent-provided public facts.
 */
export function ChartWorkspaceShell({
  view,
  renderBoard,
  detail,
  onCloseDetail,
  boardLabel = "盘面",
}: Readonly<{
  view: ChartWorkspaceView;
  renderBoard: (activeLayer: WorkspaceLayer) => ReactNode;
  detail: WorkspaceFocusDetail | null;
  onCloseDetail: () => void;
  boardLabel?: string;
}>) {
  const [activeLayerId, setActiveLayerId] = useState<WorkspaceLayerId>(
    view.activeLayerId,
  );

  const activeLayer =
    view.layers.find((layer) => layer.id === activeLayerId) ?? view.layers[0];

  function handleSelectLayer(layerId: WorkspaceLayerId) {
    if (layerId === activeLayerId) return;
    setActiveLayerId(layerId);
    onCloseDetail();
  }

  return (
    <section className={styles.workspace} aria-label="排盘工作台">
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>确定性盘面</p>
          <h3 className={styles.title}>{view.title}</h3>
        </div>
        {view.subtitle ? (
          <p className={styles.subtitle}>{view.subtitle}</p>
        ) : null}
      </header>

      <TimeLayerTabs
        layers={view.layers}
        activeLayerId={activeLayer.id}
        onSelect={handleSelectLayer}
      />

      <div className={styles.body}>
        <div className={styles.board} role="group" aria-label={boardLabel}>
          {activeLayer.status === "empty" ? (
            <p className={styles.emptyState}>
              {activeLayer.summary ?? "服务端尚未返回可展示的结构"}
            </p>
          ) : (
            renderBoard(activeLayer)
          )}
        </div>
        <FocusDetailDrawer detail={detail} onClose={onCloseDetail} />
      </div>
    </section>
  );
}
