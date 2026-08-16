"use client";

import Link from "next/link";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "@/components/account-session-context";
import { AppPageHeader } from "@/components/app-page-header";

import surface from "../app-surface.module.css";
import { StatusPanel } from "../status-panel";
import { SecondaryStatus } from "./secondary-status";
import secondary from "./secondary-surfaces.module.css";

const links = [
  {
    href: "/account/settings/security",
    label: "设备安全",
    description: "查看已验证身份并撤销所有设备会话。",
  },
  {
    href: "/account/settings/preferences",
    label: "通知偏好",
    description: "管理站内通知、邮件和短信开关。",
  },
  {
    href: "/account/settings/privacy-data",
    label: "隐私与数据",
    description: "导出资料或管理 7 天可撤销的注销申请。",
  },
  {
    href: "/account/notifications",
    label: "站内通知",
    description: "查看账户、任务、退款和安全状态。",
  },
] as const;

function SettingsContent() {
  const { state } = useAccountSession();

  if (state.status === "checking") {
    return <StatusPanel state="loading" title="正在确认账户…" description="正在确认设置访问权限。" />;
  }

  if (state.status === "error") {
    return <StatusPanel state="error" title="无法确认账户" description={state.message} />;
  }

  if (state.status === "signedOut") {
    return (
      <SecondaryStatus
        action={{ href: "/auth/login", label: "前往登录" }}
        description="登录后才能进入设备、通知和数据权利设置。"
        state="need-login"
        title="需要登录"
      />
    );
  }

  return (
    <section aria-labelledby="account-settings-title" className={surface.paper}>
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="account-settings-title">账号设置</h2>
          <p>只列出已经接通的账户管理入口，不在这里猜测或生成支付、算法和身份事实。</p>
        </div>
      </div>
      <nav aria-label="账号设置分类">
        <ul className={secondary.linkList}>
          {links.map((link) => (
            <li key={link.href}>
              <Link href={link.href}>
                <strong>{link.label}</strong>
                <span>{link.description}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </section>
  );
}

export function AccountSettingsSurface() {
  return (
    <AccountSessionBoundary>
      <div className={secondary.accountPage}>
        <AppPageHeader
          description="账户设置只连接服务端已经存在的会话、通知和数据权利合同。"
          title="设置"
        />
        <SettingsContent />
      </div>
    </AccountSessionBoundary>
  );
}
