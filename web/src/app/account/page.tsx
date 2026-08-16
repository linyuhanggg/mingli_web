import { AccountCenter } from "@/components/account-center";
import { AppPageHeader } from "@/components/app-page-header";
import styles from "@/components/app-surface.module.css";


export default function AccountPage() {
  return (
    <div className={`${styles.page} ${styles.accountPage}`}>
      <AppPageHeader
        stacked
        title="我的"
        description="从这里查看当前账号、档案、推演历史、通知和账户设置。"
      />
      <AccountCenter />
    </div>
  );
}
