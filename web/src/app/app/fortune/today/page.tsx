"use client";

import { CalendarDays, LockKeyhole } from "lucide-react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { FortuneFlow } from "@/components/fortune-flow";

export default function FortuneTodayPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="今日解读"
        description="从已确认档案出发，查看服务端确定日期范围内的轻量提示；这一天不会在这里凭空生成。"
        meta={
          <>
            <span><CalendarDays aria-hidden="true" size={15} /> 日期范围由服务端确认</span>
            <span><LockKeyhole aria-hidden="true" size={15} /> 从已确认档案出发</span>
          </>
        }
      />
      <FortuneFlow mode="today" />
    </div>
  );
}
