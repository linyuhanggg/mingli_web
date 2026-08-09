"use client";

import { FileClock, ShieldCheck } from "lucide-react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { ReadingHistory } from "@/components/reading-history";


export default function ReadingsPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="历史里保存的是版本，不是一串聊天消息。"
        description="每个解读根可以包含初次解读、核对后的新版本与同盘追问。旧正文保持可回看，不会被新答案覆盖。"
        meta={
          <>
            <span>
              <FileClock aria-hidden="true" size={15} /> 解读版本可回看
            </span>
            <span>
              <ShieldCheck aria-hidden="true" size={15} /> 状态与正文分开交付
            </span>
          </>
        }
      />
      <ReadingHistory />
    </div>
  );
}
