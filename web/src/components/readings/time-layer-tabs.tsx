"use client";

import type {
  WorkspaceLayer,
  WorkspaceLayerId,
} from "@/lib/chart-workspace";

import styles from "./time-layer-tabs.module.css";

/**
 * Time layer switcher built strictly from the workspace view model.
 * Layers the server did not generate are visible but disabled: the UI never
 * pretends a layer is ready when no public facts back it.
 */
export function TimeLayerTabs({
  layers,
  activeLayerId,
  onSelect,
}: Readonly<{
  layers: WorkspaceLayer[];
  activeLayerId: WorkspaceLayerId;
  onSelect: (layerId: WorkspaceLayerId) => void;
}>) {
  return (
    <div className={styles.tabs} role="tablist" aria-label="时间层">
      {layers.map((layer) => {
        const unavailable = layer.status === "unavailable";
        const active = !unavailable && activeLayerId === layer.id;
        return (
          <button
            key={layer.id}
            type="button"
            role="tab"
            id={`time-layer-tab-${layer.id}`}
            aria-selected={active}
            aria-disabled={unavailable}
            disabled={unavailable}
            className={styles.tab}
            data-active={active}
            data-status={layer.status}
            onClick={() => onSelect(layer.id)}
          >
            <span className={styles.tabLabel}>{layer.label}</span>
            {layer.status === "ready" && layer.summary ? (
              <span className={styles.tabSummary}>{layer.summary}</span>
            ) : null}
            {layer.status === "empty" ? (
              <span className={styles.tabStatus}>暂无结构</span>
            ) : null}
            {unavailable ? (
              <span className={styles.tabStatus}>未生成</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
