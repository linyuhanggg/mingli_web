"use client";

import { CalendarDays, LockKeyhole } from "lucide-react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { FortuneFlow } from "@/components/fortune-flow";

export default function FortuneWeekPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="近七日阶段解读"
        description="从已确认档案出发，发起近七日的阶段解读；日期范围由服务端确认，不在浏览器里推算。"
        meta={
          <>
            <span><CalendarDays aria-hidden="true" size={15} /> 日期范围由服务端确认</span>
            <span><LockKeyhole aria-hidden="true" size={15} /> 从已确认档案出发</span>
          </>
        }
      />
      <FortuneFlow mode="week" />
    </div>
  );
}
