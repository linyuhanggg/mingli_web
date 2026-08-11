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
        title="八字概览"
        description="从已确认档案出发，发起确定性八字排盘与覆盖整体格局、状态主线的白话概览。这里不本地推算，结果由服务端计算并按解读版本保存。"
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
            title="八字概览"
            description="正在准备八字概览入口…"
          />
        </div>
      }
    >
      <BaziPageBody />
    </Suspense>
  );
}
