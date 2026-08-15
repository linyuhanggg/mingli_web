import type { Metadata } from "next";
import Link from "next/link";

import { PasswordRecoveryForm } from "@/components/password-recovery-form";
import { SecondaryStatus } from "@/components/surfaces/secondary-status";
import { SecondarySurfaceFrame } from "@/components/surfaces/secondary-surface-frame";
import styles from "@/components/surfaces/secondary-surfaces.module.css";

export const metadata: Metadata = { title: "找回账号", description: "找回命理工具账号。" };

export default function RecoverPage() {
  return (
    <SecondarySurfaceFrame
      eyebrow="找回账号"
      intro="通过已验证的手机或邮箱重设密码；找回成功会撤销其他设备会话。"
      title="恢复访问，不覆盖历史事实。"
    >
      <div className={styles.authGrid}>
        <PasswordRecoveryForm />
        <aside aria-label="找回说明与其他入口" className={styles.authAside}>
          <SecondaryStatus
            description="验证码只用于确认已有身份，不会因找回请求自动创建新账号。"
            state="need-login"
            title="先确认身份"
          />
          <nav aria-label="其他认证入口">
            <ul className={styles.linkList}>
              <li><Link href="/auth/login">返回密码登录</Link></li>
              <li><Link href="/auth/register">创建账号</Link></li>
            </ul>
          </nav>
        </aside>
      </div>
    </SecondarySurfaceFrame>
  );
}
