"use client";

import { useRef, type KeyboardEvent } from "react";

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
  idPrefix,
}: Readonly<{
  layers: WorkspaceLayer[];
  activeLayerId: WorkspaceLayerId;
  onSelect: (layerId: WorkspaceLayerId) => void;
  idPrefix: string;
}>) {
  const tabRefs = useRef<
    Partial<Record<WorkspaceLayerId, HTMLButtonElement | null>>
  >({});

  function handleKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    currentLayerId: WorkspaceLayerId,
  ) {
    const availableLayers = layers.filter(
      (layer) => layer.status !== "unavailable",
    );
    const currentIndex = availableLayers.findIndex(
      (layer) => layer.id === currentLayerId,
    );
    if (currentIndex < 0 || availableLayers.length === 0) return;

    let targetIndex: number | null = null;
    if (event.key === "ArrowRight") {
      targetIndex = (currentIndex + 1) % availableLayers.length;
    } else if (event.key === "ArrowLeft") {
      targetIndex =
        (currentIndex - 1 + availableLayers.length) % availableLayers.length;
    } else if (event.key === "Home") {
      targetIndex = 0;
    } else if (event.key === "End") {
      targetIndex = availableLayers.length - 1;
    }

    if (targetIndex === null) return;
    event.preventDefault();
    const targetLayer = availableLayers[targetIndex];
    tabRefs.current[targetLayer.id]?.focus();
    onSelect(targetLayer.id);
  }

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
            ref={(element) => {
              tabRefs.current[layer.id] = element;
            }}
            id={`${idPrefix}-tab-${layer.id}`}
            aria-controls={`${idPrefix}-panel-${layer.id}`}
            aria-selected={active}
            aria-disabled={unavailable}
            disabled={unavailable}
            tabIndex={active ? 0 : -1}
            className={styles.tab}
            data-active={active}
            data-status={layer.status}
            onClick={() => onSelect(layer.id)}
            onKeyDown={(event) => handleKeyDown(event, layer.id)}
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
