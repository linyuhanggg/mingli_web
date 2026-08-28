"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import {
  CORE_STATUS_STATES,
  Status,
  type CoreStatusState,
} from "@/components/ui/status";

import styles from "./bazi-result-six-states.module.css";

export function BaziResultSixStates({ children }: { readonly children: ReactNode }) {
  const [state, setState] = useState<CoreStatusState>("ready");

  return (
    <div className={styles.wrap}>
      <nav aria-label="结果页六态" className={styles.nav}>
        {CORE_STATUS_STATES.map((item) => (
          <button
            aria-pressed={state === item}
            className={styles.tab}
            key={item}
            onClick={() => setState(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </nav>

      {state === "ready" ? children : null}

      {state === "loading" ? (
        <div className={styles.loadingStack}>
          <div className={styles.chartSkeleton} aria-hidden="true">
            <span className={styles.skeletonTabs} />
            <span className={styles.skeletonPillars} />
            <span className={styles.skeletonReading} />
          </div>
          <Status
            description="正在准备定位、时间层与四柱事实；完成后直接进入盘面。"
            state="loading"
            title="正在同步出盘"
          />
        </div>
      ) : null}

      {state === "empty" ? (
        <Status
          actions={<Link href="/bazi">开始录入</Link>}
          description="服务端尚未返回盘面事实，不会用演示值补齐。"
          state="empty"
          title="还没有盘面"
        />
      ) : null}

      {state === "locked" ? (
        <div className={styles.lockedStack}>
          {children}
          <Status
            actions={<Link href="/pricing">了解专业版</Link>}
            description="本命、大运与流年事实仍可查看；锁定只作用于专业时间层和深读。"
            state="locked"
            title="专业时间层与深读已锁定"
          />
        </div>
      ) : null}

      {state === "need-input" ? (
        <Status
          actions={(
            <>
              <button type="button">返回补充资料</button>
              <button data-variant="secondary" type="button">沿用当前口径</button>
            </>
          )}
          description="出生时刻处在口径边界，请确认资料后再同步出盘。"
          state="need-input"
          title="需要确认边界口径"
        />
      ) : null}

      {state === "error" ? (
        <Status
          actions={<button type="button">重试</button>}
          description="这次同步没有成功；不会展示猜测盘面。"
          state="error"
          title="同步出盘失败"
        />
      ) : null}
    </div>
  );
}
