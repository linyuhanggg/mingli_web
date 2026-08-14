"use client";

import {
  ArrowRight,
  Bell,
  FolderLock,
  Gift,
  History,
  ReceiptText,
  Settings2,
  ShieldCheck,
  UserRoundCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import {
  AccountSessionBoundary,
  primaryLoginIdentity,
  type AccountSessionState,
  useAccountSession,
} from "./account-session-context";
import AccountSessionControl from "./account-session-control";
import surface from "./app-surface.module.css";
import styles from "./account-center.module.css";
import { OtpForm } from "./otp-form";
import { ReadingHistory } from "./reading-history";
import { StatusPanel } from "./status-panel";


type Shortcut = {
  href: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

const shortcuts: readonly Shortcut[] = [
  {
    href: "/account/profiles",
    label: "受测人档案",
    description: "管理服务端确认的档案版本。",
    icon: FolderLock,
  },
  {
    href: "/account/history",
    label: "推演历史",
    description: "回看任务、版本与报告交付状态。",
    icon: History,
  },
  {
    href: "/account/orders",
    label: "订单与权益",
    description: "查看真实订单和追加式权益账本。",
    icon: ReceiptText,
  },
  {
    href: "/account/notifications",
    label: "通知",
    description: "查看任务、账户和安全状态。",
    icon: Bell,
  },
  {
    href: "/account/settings",
    label: "账户设置",
    description: "管理设备、通知与数据权利。",
    icon: Settings2,
  },
  {
    href: "/account/invites",
    label: "邀请有礼",
    description: "查看服务端确认的邀请进度。",
    icon: Gift,
  },
];

function AccountIdentityCard({ state }: { readonly state: AccountSessionState }) {
  let title = "确认中";
  let eyebrow = "账户状态";
  let description = "正在向服务端确认当前设备，不会从浏览器存储猜测身份。";
  let status = "正在确认";
  let entitlement = "等待确认";
  let Icon = ShieldCheck;

  if (state.status === "signedOut") {
    title = "游客模式";
    description = "登录后才能读取你的档案、历史、通知和权益；当前不展示任何未授权资料。";
    status = "未登录";
    entitlement = "登录后查看";
    Icon = UserRoundCheck;
  } else if (state.status === "error") {
    title = "账户状态暂不可读";
    description = state.message;
    status = "暂不可用";
    entitlement = "暂不可读";
    Icon = ShieldCheck;
  } else if (state.status === "signedIn") {
    const identity = primaryLoginIdentity(state.account);
    title = identity?.masked_destination ?? "已验证账户";
    eyebrow = "当前账号";
    description = "这里只展示服务端返回的脱敏身份；档案、历史和权益都按当前账户权限读取。";
    status = "已登录";
    entitlement = "以订单与权益页为准";
  }

  return (
    <section className={styles.identityCard} aria-labelledby="account-identity-title">
      <div className={styles.identityMain}>
        <span className={styles.identityIcon} aria-hidden="true">
          <Icon size={25} strokeWidth={1.7} />
        </span>
        <div>
          <p className={styles.identityEyebrow}>{eyebrow}</p>
          <h2 id="account-identity-title">{title}</h2>
          <p className={styles.identityDescription}>{description}</p>
        </div>
      </div>
      <dl className={styles.identityFacts} aria-label="账户摘要">
        <div>
          <dt>账号状态</dt>
          <dd>{status}</dd>
        </div>
        <div>
          <dt>权益摘要</dt>
          <dd>{entitlement}</dd>
        </div>
      </dl>
    </section>
  );
}

function AccountShortcuts() {
  return (
    <section className={styles.shortcutSection} aria-labelledby="account-shortcuts-title">
      <div className={styles.sectionHeader}>
        <div>
          <h2 id="account-shortcuts-title">我的入口</h2>
          <p>只连接当前产品已经存在的账户页面，不在这里生成新的业务事实。</p>
        </div>
      </div>
      <nav aria-label="我的账户入口" className={styles.shortcutGrid}>
        {shortcuts.map(({ href, label, description, icon: Icon }) => (
          <Link className={styles.shortcut} href={href} key={href}>
            <span className={styles.shortcutIcon} aria-hidden="true">
              <Icon size={21} strokeWidth={1.7} />
            </span>
            <span className={styles.shortcutCopy}>
              <strong>{label}</strong>
              <span>{description}</span>
            </span>
            <ArrowRight aria-hidden="true" size={18} strokeWidth={1.7} />
          </Link>
        ))}
      </nav>
    </section>
  );
}

function AccountBoundaryNote() {
  return (
    <aside className={surface.rail} aria-labelledby="account-boundary-title">
      <h2 id="account-boundary-title">账户边界</h2>
      <p>登录成功只代表设备会话建立，不代表支付、模型或其他能力已经开通。</p>
      <p className={surface.railNote}>
        游客草稿认领要由服务端一次性、幂等完成；跨设备历史需要当前账号授权；换绑、导出和删除等高风险操作需要近期重新验证。
      </p>
    </aside>
  );
}

function GuestAccess() {
  return (
    <div className={surface.dashboard}>
      <section className={surface.paper} aria-labelledby="login-title">
        <div className={surface.sectionHeader}>
          <div>
            <h2 id="login-title">登录后开始使用</h2>
            <p>
              这里提供 OTP 快捷登录；密码是默认登录方式。OTP 用于注册验证、快捷登录和找回密码；注册需要在 OTP 核验后设置密码并同意当版政策。
            </p>
          </div>
        </div>
        <OtpForm />
      </section>
      <AccountBoundaryNote />
    </div>
  );
}

function AccountCenterContent() {
  const { state, refresh } = useAccountSession();

  if (state.status === "checking") {
    return (
      <>
        <AccountIdentityCard state={state} />
        <StatusPanel
          state="loading"
          title="正在确认账户状态"
          description="只读取服务端会话与脱敏登录身份，请稍候。"
        />
      </>
    );
  }

  if (state.status === "error") {
    return (
      <>
        <AccountIdentityCard state={state} />
        <div className={styles.statusStack}>
          <StatusPanel
            state="error"
            title="暂时无法确认账户"
            description={state.message}
          />
          <button
            className={surface.secondaryButton}
            type="button"
            onClick={() => void refresh()}
          >
            重新读取账户状态
          </button>
        </div>
      </>
    );
  }

  if (state.status === "signedOut") {
    return (
      <>
        <AccountIdentityCard state={state} />
        <AccountShortcuts />
        <GuestAccess />
      </>
    );
  }

  return (
    <>
      <AccountIdentityCard state={state} />
      <AccountShortcuts />
      <ReadingHistory
        accountScoped
        title="最近交付与待处理事项"
        description="每条记录的状态、版本和时间都来自服务端；处理中或等待输入的任务会保留在这里。"
      />
      <AccountSessionControl />
    </>
  );
}

export function AccountCenter() {
  return (
    <AccountSessionBoundary>
      <AccountCenterContent />
    </AccountSessionBoundary>
  );
}
