"use client";

import { LockKeyhole, ScanLine } from "lucide-react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { ProfileForm } from "@/components/profile-form";


export default function NewProfilePage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="建立一份可复现的受测档案。"
        description="先确认原始资料和时间口径，再由服务端规范化。修改资料会产生新版本，不覆盖已经用于解读的历史快照。"
        meta={
          <>
            <span><ScanLine aria-hidden="true" size={15} /> 游客可先核对输入</span>
            <span><LockKeyhole aria-hidden="true" size={15} /> 登录后才承诺保存</span>
          </>
        }
      />
      <ProfileForm />
    </div>
  );
}
