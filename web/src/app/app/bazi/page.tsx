"use client";

import { ScanLine, LockKeyhole } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { BaziFlow } from "@/components/bazi-flow";

function BaziPageBody() {
  const searchParams = useSearchParams();
  const profileVersionId = searchParams.get("profile") ?? "";

  return (
    <div className={styles.page}>
      <AppPageHeader
        title="八字 · 事业概览"
        description="从已确认档案出发，发起确定性八字排盘，白话解读限定在事业与工作主题。这里不本地推算，结果由服务端计算并按解读版本保存。"
        meta={
          <>
            <span>
              <ScanLine aria-hidden="true" size={15} /> 先建档，再看盘
            </span>
            <span>
              <LockKeyhole aria-hidden="true" size={15} /> 绑定档案版本
            </span>
          </>
        }
      />
      <BaziFlow initialProfileVersionId={profileVersionId} />
    </div>
  );
}

export default function BaziPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.page}>
          <AppPageHeader
            title="八字 · 事业概览"
            description="正在准备事业概览入口…"
          />
        </div>
      }
    >
      <BaziPageBody />
    </Suspense>
  );
}
