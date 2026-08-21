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
import { ReadingHistory } from "./reading-history";
import { StatusPanel } from "./status-panel";


type Shortcut = {
  href: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

type ShortcutVariant = "primary" | "secondary";

const shortcuts: readonly Shortcut[] = [
  {
    href: "/account/profiles",
    label: "受测人档案",
    description: "查看已保存的出生档案。",
    icon: FolderLock,
  },
  {
    href: "/account/history",
    label: "推演历史",
    description: "查看你的任务和报告。",
    icon: History,
  },
  {
    href: "/account/orders",
    label: "订单与权益",
    description: "查看你的订单和权益。",
    icon: ReceiptText,
  },
  {
    href: "/account/notifications",
    label: "通知",
    description: "查看任务、账号和订单通知。",
    icon: Bell,
  },
  {
    href: "/account/settings",
    label: "账户设置",
    description: "管理登录设备、通知和数据权利。",
    icon: Settings2,
  },
  {
    href: "/account/invites",
    label: "邀请有礼",
    description: "查看你的邀请活动。",
    icon: Gift,
  },
];

const primaryShortcuts = shortcuts.slice(0, 3);
const secondaryShortcuts = shortcuts.slice(3);

function AccountIdentityCard({ state }: { readonly state: AccountSessionState }) {
  let title = "确认中";
  let eyebrow = "账户状态";
  let description = "正在确认当前登录状态。";
  let status = "正在确认";
  let entitlement = "等待确认";
  let Icon = ShieldCheck;

  if (state.status === "signedOut") {
    title = "未登录";
    description = "登录后才能看档案和历史";
    status = "未登录";
    entitlement = "登录后查看";
  } else if (state.status === "error") {
    title = "读取失败，请重试";
    description = "暂时无法确认账户状态。";
    status = "暂不可用";
    entitlement = "暂不可读";
    Icon = ShieldCheck;
  } else if (state.status === "signedIn") {
    const identity = primaryLoginIdentity(state.account);
    title = identity?.masked_destination ?? "已验证账户";
    eyebrow = "当前账号";
    description = "这里只展示脱敏身份；档案、历史和权益都按当前账户权限读取。";
    status = "已登录";
    entitlement = "以订单与权益页为准";
  }

  if (state.status === "signedOut") {
    return (
      <section className={`${styles.identityCard} ${styles.identityCardGuest}`} aria-labelledby="account-identity-title">
        <div className={styles.identityGuestRow}>
          <h2 id="account-identity-title">{status}</h2>
          <Link className={styles.guestLogin} href="/auth/login">
            登录
          </Link>
        </div>
        <p className={styles.identityDescription}>{description}</p>
        <p className={styles.guestSecondary}>
          <Link href="/auth/verify">用验证码登录</Link>
        </p>
      </section>
    );
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

function ShortcutLink({
  shortcut,
  variant,
}: {
  shortcut: Shortcut;
  variant: ShortcutVariant;
}) {
  const { href, label, description, icon: Icon } = shortcut;

  return (
    <Link
      className={variant === "primary" ? styles.primaryShortcut : styles.secondaryShortcut}
      href={href}
    >
      <span className={styles.shortcutIcon} aria-hidden="true">
        <Icon size={variant === "primary" ? 21 : 19} strokeWidth={1.7} />
      </span>
      <span className={styles.shortcutCopy}>
        <strong>{label}</strong>
        <span>{description}</span>
      </span>
      <ArrowRight aria-hidden="true" size={18} strokeWidth={1.7} />
    </Link>
  );
}

function AccountShortcuts() {
  return (
    <section className={styles.shortcutSection} aria-labelledby="account-shortcuts-title">
      <div className={styles.sectionHeader}>
        <div>
          <h2 id="account-shortcuts-title">继续使用</h2>
          <p>从这里进入已有的档案、历史、订单和账户服务。</p>
        </div>
      </div>
      <nav aria-label="我的账户入口" className={styles.shortcutGroups}>
        <div className={styles.shortcutGroup}>
          <h3 className={styles.shortcutGroupTitle}>主要入口</h3>
          <div className={styles.primaryShortcutGrid}>
            {primaryShortcuts.map((shortcut) => (
              <ShortcutLink key={shortcut.href} shortcut={shortcut} variant="primary" />
            ))}
          </div>
        </div>
        <div className={styles.shortcutGroup}>
          <h3 className={styles.shortcutGroupTitle}>账户工具</h3>
          <div className={styles.secondaryShortcutGrid}>
            {secondaryShortcuts.map((shortcut) => (
              <ShortcutLink key={shortcut.href} shortcut={shortcut} variant="secondary" />
            ))}
          </div>
        </div>
      </nav>
    </section>
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
          description="请稍候。"
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
            title="读取失败，请重试"
            description="暂时无法确认账户状态。"
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
    return <AccountIdentityCard state={state} />;
  }

  return (
    <>
      <AccountIdentityCard state={state} />
      <ReadingHistory
        accountScoped
        title="最近交付与待处理事项"
        description="每条记录的状态、版本和时间都来自服务端；处理中或等待输入的任务会保留在这里。"
      />
      <AccountShortcuts />
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
