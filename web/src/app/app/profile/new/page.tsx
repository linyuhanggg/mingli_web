"use client";

import { LockKeyhole, ScanLine } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { ProfileForm } from "@/components/profile-form";
import { StatusPanel } from "@/components/status-panel";


function ProfileFormSurface() {
  const searchParams = useSearchParams();
  const editProfileId = searchParams.get("edit") ?? undefined;
  return (
    <div className={styles.page}>
      <AppPageHeader
        title={
          editProfileId
            ? "修改会留下轨迹，旧版本永远可以回看。"
            : "先确认出生事实，再进入可复现的推算。"
        }
        description="原始资料与时间口径由你最后确认，再由服务端规范化。修改资料会产生新版本，不覆盖已经用于解读的历史快照。"
        meta={
          <>
            <span><ScanLine aria-hidden="true" size={15} /> 游客可先核对输入</span>
            <span><LockKeyhole aria-hidden="true" size={15} /> 登录后才承诺保存</span>
          </>
        }
      />
      <ProfileForm editProfileId={editProfileId} />
    </div>
  );
}


export default function NewProfilePage() {
  return (
    <Suspense
      fallback={
        <div className={styles.page}>
          <StatusPanel
            state="loading"
            title="正在准备档案表单…"
            description="请稍候。"
          />
        </div>
      }
    >
      <ProfileFormSurface />
    </Suspense>
  );
}
