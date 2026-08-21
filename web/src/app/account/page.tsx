import type { Metadata } from "next";

import { AccountCenter } from "@/components/account-center";
import { AccountSectionShell } from "@/components/account-section-shell";
import styles from "@/components/app-surface.module.css";

export const metadata: Metadata = { title: "我的", description: "查看账号、档案、历史和设置。" };

export default function AccountPage() {
  return (
    <div className={`${styles.page} ${styles.accountPage}`}>
      <AccountSectionShell intro="查看账号、档案、历史和设置。" title="我的">
        <AccountCenter />
      </AccountSectionShell>
    </div>
  );
}
