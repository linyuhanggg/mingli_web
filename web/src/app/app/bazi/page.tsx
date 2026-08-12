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
        title="八字命盘"
        description="从已确认档案出发，同步查看 Runtime 5.1 返回的结构化命盘。浏览器不排盘，事实盘也不会创建或核销深度解读。"
        meta={
          <>
            <span>
              <ScanLine aria-hidden="true" size={15} /> 同步事实盘
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
            title="八字命盘"
            description="正在准备同步看盘入口…"
          />
        </div>
      }
    >
      <BaziPageBody />
    </Suspense>
  );
}
