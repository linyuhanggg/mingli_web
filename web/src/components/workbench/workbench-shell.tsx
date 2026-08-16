"use client";

import { ArrowLeft, Download, History, MoreHorizontal, Save, Settings2, Share2, Ticket, UserRound } from "lucide-react";
import { DropdownMenu as DropdownMenuPrimitive } from "radix-ui";

import { ReadingShell } from "@/components/reading/reading-shell";
import { Status } from "@/components/ui/status";
import type { ProductDefinition } from "@/products/catalog";
import { ProductBoardPlaceholder } from "@/products/product-board-placeholder";

import styles from "./workbench-shell.module.css";

const taskActions = [
  { label: "规则", Icon: Settings2 },
  { label: "保存", Icon: Save },
  { label: "导出", Icon: Download },
  { label: "分享", Icon: Share2 },
  { label: "历史", Icon: History },
  { label: "权益", Icon: Ticket },
  { label: "账户", Icon: UserRound },
] as const;

export function WorkbenchShell({ product, onBack }: { product: ProductDefinition; onBack: () => void }) {
  const unavailableId = `${product.id}-workbench-unavailable`;
  return (
    <section className={styles.shell} aria-labelledby={`${product.id}-workbench-title`}>
      <div className={styles.toolbar}>
        <button className={styles.backButton} onClick={onBack} type="button"><ArrowLeft aria-hidden="true" size={17} /> 返回确认</button>
        <div className={styles.taskIdentity}>
          <h2 id={`${product.id}-workbench-title`}>{product.name}工作台</h2>
          <span>资料已确认 · 尚未计算</span>
        </div>
        <div className={styles.toolbarActions} aria-label="任务操作">
          {taskActions.map(({ Icon, label }) => (
            <button aria-describedby={unavailableId} disabled key={label} type="button">
              <Icon aria-hidden="true" size={16} /> {label}
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
                        <small id={reasonId}>{product.unavailableReason}</small>
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
        <button aria-describedby={unavailableId} disabled type="button">时间层待能力声明</button>
      </div>

      <p className={styles.disabledReason} id={unavailableId}>{product.unavailableReason}</p>
      <div className={styles.workspace} data-layout="workbench-workspace">
        <section className={styles.board} aria-labelledby={`${product.id}-board-title`}>
          <div className={styles.panelHeading}>
            <div><h2 id={`${product.id}-board-title`}>{product.moduleTitle}</h2><p>专属盘面结构槽位 · 无结果数据</p></div>
            <span>等待 ViewModel</span>
          </div>
          <ProductBoardPlaceholder productId={product.id} />
          <Status state="unavailable" title="盘面尚未生成" description={product.unavailableReason} />
        </section>
        <ReadingShell product={product} />
      </div>
    </section>
  );
}
