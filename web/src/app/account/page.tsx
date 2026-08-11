import { KeyRound, Mail } from "lucide-react";

import { AccountCenter } from "@/components/account-center";
import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";


export default function AccountPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="个人中心"
        description="登录后在这里确认当前身份、进入个人首页、管理设备并找到自己的档案与解读；未登录时只显示邮箱验证入口。"
        meta={
          <>
            <span><Mail aria-hidden="true" size={15} /> 邮箱验证为主</span>
            <span><KeyRound aria-hidden="true" size={15} /> 设备会话可撤销</span>
          </>
        }
      />
      <AccountCenter />
    </div>
  );
}
