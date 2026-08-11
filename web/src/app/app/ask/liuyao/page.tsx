"use client";

import { Clock3, LockKeyhole } from "lucide-react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { LiuyaoForm } from "@/components/liuyao-form";


export default function LiuyaoPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="一件事业或工作问题，一次起卦。"
        description="当前成稿范围是事业与工作。先把问题、时间范围和起卦方式确认清楚；换问题、换卦或重新起卦会形成新的解读根。"
        meta={
          <>
            <span><Clock3 aria-hidden="true" size={15} /> 起卦时刻需确认</span>
            <span><LockKeyhole aria-hidden="true" size={15} /> 问题正文不进入 URL</span>
          </>
        }
      />
      <LiuyaoForm />
    </div>
  );
}
