"use client";

import {
  AlertCircle,
  Ban,
  CheckCircle2,
  LockKeyhole,
  type LucideIcon,
} from "lucide-react";
import { useRef, type KeyboardEvent } from "react";

import type {
  WorkspaceLayer,
  WorkspaceLayerId,
} from "@/lib/chart-workspace";

import styles from "./time-layer-tabs.module.css";

/**
 * Time layer switcher built strictly from the workspace view model.
 * Every layer remains inspectable. Its icon, label, and status copy distinguish
 * readable facts from unavailable capability and fail-closed entitlement.
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
    const currentIndex = layers.findIndex(
      (layer) => layer.id === currentLayerId,
    );
    if (currentIndex < 0 || layers.length === 0) return;

    let targetIndex: number | null = null;
    if (event.key === "ArrowRight") {
      targetIndex = (currentIndex + 1) % layers.length;
    } else if (event.key === "ArrowLeft") {
      targetIndex =
        (currentIndex - 1 + layers.length) % layers.length;
    } else if (event.key === "Home") {
      targetIndex = 0;
    } else if (event.key === "End") {
      targetIndex = layers.length - 1;
    }

    if (targetIndex === null) return;
    event.preventDefault();
    const targetLayer = layers[targetIndex];
    tabRefs.current[targetLayer.id]?.focus();
    onSelect(targetLayer.id);
  }

  return (
    <div className={styles.tabs} role="tablist" aria-label="时间层">
      {layers.map((layer) => {
        const active = activeLayerId === layer.id;
        const statusDefinition: Record<
          WorkspaceLayer["status"],
          { label: string; icon: LucideIcon }
        > = {
          ready: { label: layer.summary ?? "可查看", icon: CheckCircle2 },
          empty: { label: "暂无结构", icon: AlertCircle },
          "locked-paywall": { label: "PRO · 已锁定", icon: LockKeyhole },
          "locked-unavailable": { label: layer.summary ?? "待接入", icon: Ban },
          "fail-closed-unknown": { label: "权益未确认", icon: AlertCircle },
        };
        const status = statusDefinition[layer.status];
        const StatusIcon = status.icon;
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
            tabIndex={active ? 0 : -1}
            className={styles.tab}
            data-active={active}
            data-status={layer.status}
            onClick={() => onSelect(layer.id)}
            onKeyDown={(event) => handleKeyDown(event, layer.id)}
          >
            <span className={styles.tabLabel}>{layer.label}</span>
            <span className={styles.tabStatus}>
              <StatusIcon aria-hidden="true" size={13} strokeWidth={2} />
              <span>{status.label}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
