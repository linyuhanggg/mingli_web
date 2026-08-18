"use client";

import { useId, useState, type ReactNode } from "react";

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
 * middle, and an inline focus detail below it. The shell never fetches data or
 * calculates; the board and detail come from parent-provided public facts.
 */
export function ChartWorkspaceShell({
  view,
  renderBoard,
  detail,
  detailId,
  onCloseDetail,
  boardLabel = "盘面",
}: Readonly<{
  view: ChartWorkspaceView;
  renderBoard: (activeLayer: WorkspaceLayer) => ReactNode;
  detail: WorkspaceFocusDetail | null;
  detailId?: string;
  onCloseDetail: () => void;
  boardLabel?: string;
}>) {
  const layerIdPrefix = useId();
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
        idPrefix={layerIdPrefix}
      />

      <div className={styles.body}>
        <div className={styles.layerPanels}>
          {view.layers.map((layer) => {
            const active = layer.id === activeLayer.id;
            return (
              <div
                key={layer.id}
                id={`${layerIdPrefix}-panel-${layer.id}`}
                role="tabpanel"
                aria-labelledby={`${layerIdPrefix}-tab-${layer.id}`}
                aria-hidden={!active}
                data-active={active}
                className={styles.layerPanel}
                tabIndex={active ? 0 : -1}
              >
                <div
                  className={styles.board}
                  role="group"
                  aria-label={`${boardLabel} · ${layer.label}`}
                >
                  {layer.status === "empty" ? (
                    <p className={styles.emptyState}>
                      {layer.summary ?? "服务端尚未返回可展示的结构"}
                    </p>
                  ) : (
                    renderBoard(layer)
                  )}
                </div>
              </div>
            );
          })}
        </div>
        <FocusDetailDrawer id={detailId} detail={detail} onClose={onCloseDetail} />
      </div>
    </section>
  );
}
