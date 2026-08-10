"use client";

import { FilePlus2, History } from "lucide-react";
import { Suspense } from "react";

import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";
import { ProfileArchive } from "@/components/profile-archive";
import { StatusPanel } from "@/components/status-panel";


export default function ProfilesPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="档案保存人，也保存每次确认。"
        description="资料不会被“覆盖保存”。每次修改都会形成新的不可变档案版本，旧解读仍能回到当时使用的资料。建档后从这里继续看八字。"
        meta={
          <>
            <span>
              <History aria-hidden="true" size={15} /> 不可变版本
            </span>
            <span>
              <FilePlus2 aria-hidden="true" size={15} /> 每次确认生成新版本
            </span>
          </>
        }
      />
      <Suspense
        fallback={
          <StatusPanel
            state="loading"
            title="正在读取档案…"
            description="不可变档案版本正在抵达，请稍候。"
          />
        }
      >
        <ProfileArchive />
      </Suspense>
    </div>
  );
}
