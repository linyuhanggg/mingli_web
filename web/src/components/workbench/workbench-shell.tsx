"use client";

import { ArrowLeft, Download, History, MoreHorizontal, Save, Settings2, Share2, Ticket, UserRound } from "lucide-react";
import Link from "next/link";
import { DropdownMenu as DropdownMenuPrimitive } from "radix-ui";

import { ReadingShell } from "@/components/reading/reading-shell";
import { Status, type StatusState } from "@/components/ui/status";
import type { ProductDefinition } from "@/products/catalog";
import { ProductBoardPlaceholder } from "@/products/product-board-placeholder";

import styles from "./workbench-shell.module.css";

const SIX_STATES = ["loading", "empty", "error", "processing", "unavailable", "unauthorized"] as const;

export type WorkbenchSurfaceState = (typeof SIX_STATES)[number];

const taskActions = [
  { label: "规则", Icon: Settings2 },
  { label: "保存", Icon: Save },
  { label: "导出", Icon: Download },
  { label: "分享", Icon: Share2 },
  { label: "历史", Icon: History },
  { label: "权益", Icon: Ticket },
  { label: "账户", Icon: UserRound },
] as const;

const SURFACE_COPY: Record<WorkbenchSurfaceState, { title: string; description: string }> = {
  loading: {
    title: "正在载入工作台",
    description: "正在读取已有任务，不会伪造盘面或深读。",
  },
  empty: {
    title: "还没有可展示的盘面",
    description: "当前任务没有可展示的公开事实；不会用演示数据填满盘面。",
  },
  error: {
    title: "读取失败，请重试",
    description: "这次没有读到任务状态。可以返回录入或稍后重试。",
  },
  processing: {
    title: "盘面处理中",
    description: "服务端仍在处理确定性盘面，离开后任务会继续。",
  },
  unavailable: {
    title: "结果服务暂时不可用，不会展示未确认内容",
    description: "导出、分享、追问等仍待接入；当前不会伪造结果或权益。",
  },
  unauthorized: {
    title: "需要登录才能看这份结果",
    description: "登录后才能恢复当前任务；不会重复提交出生资料。",
  },
};

function isWorkbenchSurfaceState(value: StatusState | undefined): value is WorkbenchSurfaceState {
  return Boolean(value && (SIX_STATES as readonly string[]).includes(value));
}

function SurfaceActions({
  state,
  onBack,
}: {
  state: WorkbenchSurfaceState;
  onBack: () => void;
}) {
  if (state === "unauthorized") {
    return <Link href="/auth/login">登录后继续</Link>;
  }
  if (state === "empty" || state === "error") {
    return (
      <button onClick={onBack} type="button">
        返回录入
      </button>
    );
  }
  if (state === "unavailable") {
    return (
      <Link data-variant="secondary" href="/arts">
        查看术数总览
      </Link>
    );
  }
  return null;
}

export function WorkbenchShell({
  product,
  onBack,
  surfaceState,
}: {
  product: ProductDefinition;
  onBack: () => void;
  surfaceState?: WorkbenchSurfaceState;
}) {
  const unavailableId = `${product.id}-workbench-unavailable`;
  const state: WorkbenchSurfaceState = isWorkbenchSurfaceState(surfaceState)
    ? surfaceState
    : "unavailable";
  const copy = SURFACE_COPY[state];
  const showBoard = surfaceState == null;

  return (
    <section
      className={styles.shell}
      aria-labelledby={`${product.id}-workbench-title`}
      data-page-state={state}
    >
      <div className={styles.toolbar}>
        <button className={styles.backButton} onClick={onBack} type="button">
          <ArrowLeft aria-hidden="true" size={17} /> 返回确认
        </button>
        <div className={styles.taskIdentity}>
          <h2 id={`${product.id}-workbench-title`}>{product.name}工作台</h2>
          <span>{showBoard ? "资料已确认 · 尚未计算" : copy.title}</span>
        </div>
        <div className={styles.toolbarActions} aria-label="任务操作">
          {taskActions.map(({ Icon, label }) => (
            <button aria-describedby={unavailableId} disabled key={label} type="button">
              <Icon aria-hidden="true" size={16} /> {label}
              <span className={styles.pendingMark}>待接入</span>
            </button>
          ))}
          <DropdownMenuPrimitive.Root>
            <DropdownMenuPrimitive.Trigger asChild>
              <button aria-label="更多" className={styles.moreButton} type="button">
                <MoreHorizontal aria-hidden="true" size={18} /><span>更多</span>
              </button>
            </DropdownMenuPrimitive.Trigger>
            <DropdownMenuPrimitive.Portal>
              <DropdownMenuPrimitive.Content
                align="end"
                aria-label="更多任务操作"
                className={styles.moreMenu}
                sideOffset={8}
              >
                {taskActions.map(({ Icon, label }, index) => {
                  const reasonId = `${product.id}-more-action-${index}-reason`;
                  return (
                    <DropdownMenuPrimitive.Item
                      aria-describedby={reasonId}
                      aria-disabled="true"
                      className={styles.moreMenuItem}
                      key={label}
                      onSelect={(event) => event.preventDefault()}
                    >
                      <Icon aria-hidden="true" size={17} />
                      <span className={styles.moreMenuCopy}>
                        <strong>{label}</strong>
                        <small id={reasonId}>待接入 · {product.unavailableReason}</small>
                      </span>
                    </DropdownMenuPrimitive.Item>
                  );
                })}
              </DropdownMenuPrimitive.Content>
            </DropdownMenuPrimitive.Portal>
          </DropdownMenuPrimitive.Root>
        </div>
      </div>

      <div className={styles.layers} aria-label="时间层">
        <button aria-pressed="true" type="button">基础盘面</button>
        <button aria-describedby={unavailableId} disabled type="button">时间层待接入</button>
      </div>

      <p className={styles.disabledReason} id={unavailableId}>
        待接入 · {product.unavailableReason}
      </p>

      {showBoard ? (
        <div className={styles.workspace} data-layout="workbench-workspace">
          <section className={styles.board} aria-labelledby={`${product.id}-board-title`}>
            <div className={styles.panelHeading}>
              <div>
                <h2 id={`${product.id}-board-title`}>{product.moduleTitle}</h2>
                <p>专属盘面结构槽位 · 无结果数据</p>
              </div>
              <span>待接入</span>
            </div>
            <ProductBoardPlaceholder productId={product.id} />
            <Status
              actions={<SurfaceActions onBack={onBack} state="unavailable" />}
              description={SURFACE_COPY.unavailable.description}
              state="unavailable"
              title="盘面尚未生成"
            />
          </section>
          <ReadingShell product={product} />
        </div>
      ) : (
        <Status
          actions={<SurfaceActions onBack={onBack} state={state} />}
          description={copy.description}
          state={state}
          title={copy.title}
        />
      )}
    </section>
  );
}
