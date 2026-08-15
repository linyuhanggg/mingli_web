import { AppPageHeader } from "@/components/app-page-header";
import NotificationPreferencesForm from "@/components/notification-preferences-form";
import styles from "@/components/surfaces/secondary-surfaces.module.css";

export default function AccountPreferencesPage() {
  return (
    <div className={styles.accountPage}>
      <AppPageHeader
        description="站内通知默认开启；邮件和短信由你分别控制。"
        title="通知偏好"
      />
      <NotificationPreferencesForm />
    </div>
  );
}
