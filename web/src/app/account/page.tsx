import { KeyRound, Mail, ShieldCheck } from "lucide-react";

import { AccountCenter } from "@/components/account-center";
import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";


export default function AccountPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="我的"
        description="从这里查看当前账号、进入档案与推演历史、处理通知和设备设置；未登录时只显示安全登录入口。"
        meta={
          <>
            <span><KeyRound aria-hidden="true" size={15} /> 账户状态</span>
            <span><Mail aria-hidden="true" size={15} /> 真实通知</span>
            <span><ShieldCheck aria-hidden="true" size={15} /> 设备会话可撤销</span>
          </>
        }
      />
      <AccountCenter />
    </div>
  );
}
