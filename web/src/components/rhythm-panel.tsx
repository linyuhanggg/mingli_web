"use client";

import { useState } from "react";

import styles from "./app-surface.module.css";
import { StatusPanel } from "./status-panel";


type Period = "today" | "week";

export function RhythmPanel() {
  const [period, setPeriod] = useState<Period>("today");

  return (
    <section className={styles.paper} aria-labelledby="rhythm-title">
      <div className={styles.sectionHeader}>
        <div>
          <h2 id="rhythm-title">{period === "today" ? "今日" : "近七日"}</h2>
          <p>阶段摘要只会基于已确认的档案版本生成。</p>
        </div>
        <div className={styles.periodSwitch} role="group" aria-label="时间范围">
          <button type="button" aria-pressed={period === "today"} onClick={() => setPeriod("today")}>今日</button>
          <button type="button" aria-pressed={period === "week"} onClick={() => setPeriod("week")}>近七日</button>
        </div>
      </div>
      <StatusPanel
        state="empty"
        title={period === "today" ? "今天还没有可读摘要" : "近七日还没有可读摘要"}
        description="先建立并确认受测档案。确定性 Runtime 接通前，页面不会用示例运势占据真实结果的位置。"
        actionHref="/app/profile/new"
        actionLabel="建立受测档案"
      />
    </section>
  );
}
