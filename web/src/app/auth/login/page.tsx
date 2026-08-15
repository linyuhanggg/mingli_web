import type { Metadata } from "next";
import Link from "next/link";

import { PasswordLoginForm } from "@/components/password-login-form";
import { SecondaryStatus } from "@/components/surfaces/secondary-status";
import { SecondarySurfaceFrame } from "@/components/surfaces/secondary-surface-frame";
import styles from "@/components/surfaces/secondary-surfaces.module.css";

export const metadata: Metadata = { title: "登录", description: "登录命理工具。" };

export default function LoginPage() {
  return (
    <SecondarySurfaceFrame
      eyebrow="登录"
      intro="密码是主登录方式；OTP 用于快捷登录、注册验证和找回密码。登录后会接管当前游客任务。"
      title="登录后继续原来的任务。"
    >
      <div className={styles.authGrid}>
        <PasswordLoginForm />
        <aside aria-label="认证状态与其他入口" className={styles.authAside}>
          <SecondaryStatus
            description="如果还没有密码，可以先使用 OTP 快捷登录；找回流程会在验证身份后重设密码并撤销旧设备。"
            state="need-login"
            title="支持密码主登录"
          />
          <nav aria-label="其他认证入口">
            <ul className={styles.linkList}>
              <li><Link href="/auth/verify">OTP 快捷登录</Link></li>
              <li><Link href="/auth/register">创建账号</Link></li>
              <li><Link href="/auth/recover">找回账号</Link></li>
              <li><Link href="/privacy">查看隐私政策</Link></li>
              <li><Link href="/terms">查看服务条款</Link></li>
            </ul>
          </nav>
        </aside>
      </div>
    </SecondarySurfaceFrame>
  );
}
