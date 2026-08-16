import Link from "next/link";

import { OtpForm } from "@/components/otp-form";
import { SecondaryStatus } from "@/components/surfaces/secondary-status";
import { SecondarySurfaceFrame } from "@/components/surfaces/secondary-surface-frame";
import styles from "@/components/surfaces/secondary-surfaces.module.css";

export default function AuthVerifyPage() {
  return (
    <SecondarySurfaceFrame
      eyebrow="验证身份"
      intro="验证码只用于确认手机或邮箱；验证成功会建立可撤销的当前设备会话，并接管游客任务。"
      title="验证完成后才建立会话。"
    >
      <div className={styles.authGrid}>
        <OtpForm />
        <aside aria-label="验证状态与其他入口" className={styles.authAside}>
          <SecondaryStatus
            description="未验证前不会创建用户身份；注册、快捷登录和找回密码都会先经过同一 OTP 事实。"
            state="need-login"
            title="需要一次性验证码"
          />
          <nav aria-label="其他认证入口">
            <ul className={styles.linkList}>
              <li><Link href="/auth/login">返回密码登录</Link></li>
              <li><Link href="/auth/register">创建账号</Link></li>
              <li><Link href="/auth/recover">找回账号</Link></li>
            </ul>
          </nav>
        </aside>
      </div>
    </SecondarySurfaceFrame>
  );
}
