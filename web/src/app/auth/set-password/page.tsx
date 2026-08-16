import Link from "next/link";

import { PasswordSetForm } from "@/components/password-set-form";
import { SecondaryStatus } from "@/components/surfaces/secondary-status";
import { SecondarySurfaceFrame } from "@/components/surfaces/secondary-surface-frame";
import styles from "@/components/surfaces/secondary-surfaces.module.css";

export default function AuthSetPasswordPage() {
  return (
    <SecondarySurfaceFrame
      eyebrow="设置密码"
      intro="正式流程只保存不可逆密码哈希；请先完成 OTP 或密码登录，确认当前设备身份。"
      title="设置密码前必须先确认身份。"
    >
      <div className={styles.authGrid}>
        <PasswordSetForm />
        <aside aria-label="密码状态与其他入口" className={styles.authAside}>
          <SecondaryStatus
            description="设置密码不会改变已保存的身份事实；如忘记旧密码，请使用 OTP 找回流程。"
            state="need-login"
            title="需要已验证会话"
          />
          <nav aria-label="其他认证入口">
            <ul className={styles.linkList}>
              <li><Link href="/auth/login">返回登录</Link></li>
              <li><Link href="/auth/recover">找回账号</Link></li>
            </ul>
          </nav>
        </aside>
      </div>
    </SecondarySurfaceFrame>
  );
}
