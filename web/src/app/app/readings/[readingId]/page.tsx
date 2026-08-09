"use client";

import { FileClock, ShieldCheck } from "lucide-react";
import { useParams } from "next/navigation";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { ReadingResult } from "@/components/readings/reading-result";

export default function ReadingPage() {
  const params = useParams<{ readingId?: string | string[] }>();
  const readingId = typeof params?.readingId === "string" ? params.readingId : null;

  return (
    <div className={styles.page}>
      <AppPageHeader
        title="解读详情：事实、判断、依据与复核按顺序读。"
        description="每一份解读都交付为一页式阅读稿：正文、来源与边界来自服务端公开摘要，现实反馈独立保存，不会回写盘面。"
        meta={
          <>
            <span>
              <ShieldCheck aria-hidden="true" size={15} /> 状态与正文分开交付
            </span>
            <span>
              <FileClock aria-hidden="true" size={15} /> 解读版本可回看
            </span>
          </>
        }
      />
      {readingId ? (
        <ReadingResult readingId={readingId} />
      ) : (
        <p role="alert">未找到解读编号，请返回重新发起解读。</p>
      )}
    </div>
  );
}
