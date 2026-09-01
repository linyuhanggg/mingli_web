"use client";

import { AlertCircle, Ban, LockKeyhole } from "lucide-react";
import Link from "next/link";
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
  prioritizeBoard = false,
}: Readonly<{
  view: ChartWorkspaceView;
  renderBoard: (activeLayer: WorkspaceLayer) => ReactNode;
  detail: WorkspaceFocusDetail | null;
  detailId?: string;
  onCloseDetail: () => void;
  boardLabel?: string;
  prioritizeBoard?: boolean;
}>) {
  const layerIdPrefix = useId();
  const [activeLayerId, setActiveLayerId] = useState<WorkspaceLayerId>(
    view.activeLayerId,
  );
  const [transitionDirection, setTransitionDirection] = useState<
    "forward" | "backward"
  >("forward");

  const activeLayer =
    view.layers.find((layer) => layer.id === activeLayerId) ?? view.layers[0];

  function renderLayerState(layer: WorkspaceLayer) {
    if (layer.status === "ready") return renderBoard(layer);
    if (layer.status === "empty") {
      return (
        <div className={styles.statePanel} data-state="empty">
          <AlertCircle aria-hidden="true" />
          <h4>{layer.label}暂无结构</h4>
          <p>{layer.summary ?? "服务端尚未返回可展示的结构"}</p>
        </div>
      );
    }
    if (layer.status === "locked-unavailable") {
      return (
        <div className={styles.statePanel} data-state="unavailable">
          <Ban aria-hidden="true" />
          <h4>{layer.label}待接入</h4>
          <p>当前 Runtime 尚未返回这一时间层的可展示事实。</p>
        </div>
      );
    }

    const paywall = layer.status === "locked-paywall";
    return (
      <div className={styles.statePanel} data-state="locked">
        <LockKeyhole aria-hidden="true" />
        <h4>{layer.label}已锁定</h4>
        {paywall ? (
          <p>这是专业版时间层；当前盘面不会展示或预填任何锁定事实。</p>
        ) : (
          <p>
            <strong>权益状态未确认</strong>
            <span>为保护边界，当前盘面不会展示或预填任何付费事实。</span>
          </p>
        )}
        {layer.upgradeCta === "professional_info" ? (
          <Link className={styles.stateLink} href="/pricing">
            了解专业版
          </Link>
        ) : null}
      </div>
    );
  }

  function handleSelectLayer(layerId: WorkspaceLayerId) {
    if (layerId === activeLayerId) return;
    const currentIndex = view.layers.findIndex(
      (layer) => layer.id === activeLayerId,
    );
    const nextIndex = view.layers.findIndex((layer) => layer.id === layerId);
    setTransitionDirection(
      currentIndex >= 0 && nextIndex >= 0 && nextIndex < currentIndex
        ? "backward"
        : "forward",
    );
    setActiveLayerId(layerId);
    onCloseDetail();
  }

  return (
    <section
      className={styles.workspace}
      aria-label="排盘工作台"
      data-prioritize-board={prioritizeBoard}
    >
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>{view.title}</h3>
          <p className={styles.order}>定位与时间层 → 盘面 → 连续阅读面</p>
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

      <div className={styles.body} data-has-detail={Boolean(detail)}>
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
                data-direction={transitionDirection}
                className={styles.layerPanel}
                tabIndex={active ? 0 : -1}
              >
                <div
                  className={styles.board}
                  role="group"
                  aria-label={`${boardLabel} · ${layer.label}`}
                >
                  {renderLayerState(layer)}
                </div>
              </div>
            );
          })}
        </div>
        <div
          className={styles.readingPane}
          data-has-detail={Boolean(detail)}
          aria-label="连续阅读面"
        >
          <p className={styles.readingOrder}>盘面事实 / 方法解释 / 来源依据</p>
          <FocusDetailDrawer id={detailId} detail={detail} onClose={onCloseDetail} />
        </div>
      </div>
    </section>
  );
}
