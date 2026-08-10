"use client";

import { CalendarDays, LockKeyhole } from "lucide-react";
import { Suspense } from "react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { FortuneFlow } from "@/components/fortune-flow";

export default function FortunePage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="今日阶段解读"
        description="从已确认档案出发，发起今日的阶段解读；本页是阶段解读页，不是私人首页的当日总览，日期范围由服务端确认，结果不会凭空生成。"
        meta={
          <>
            <span><CalendarDays aria-hidden="true" size={15} /> 日期范围由服务端确认</span>
            <span><LockKeyhole aria-hidden="true" size={15} /> 从已确认档案出发</span>
          </>
        }
      />
      <Suspense fallback={<p role="status">正在准备解读入口…</p>}>
        <FortuneFlow mode="today" />
      </Suspense>
    </div>
  );
}
