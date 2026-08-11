"use client";

import {
  ArrowRight,
  Database,
  FolderLock,
  History,
  KeyRound,
  ReceiptText,
  UserRoundCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import {
  AccountSessionBoundary,
  primaryLoginIdentity,
  useAccountSession,
} from "./account-session-context";
import AccountSessionControl from "./account-session-control";
import surface from "./app-surface.module.css";
import styles from "./account-center.module.css";
import { OtpForm } from "./otp-form";
import { StatusPanel } from "./status-panel";


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

function AccountLinks() {
  return (
    <section className={surface.paper} aria-labelledby="personal-data-title">
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="personal-data-title">我的档案与记录</h2>
          <p>这里的入口只通向服务端已经保存的真实档案、解读和设备状态。</p>
        </div>
      </div>
      <nav className={styles.personalLinks} aria-label="个人资料入口">
        <Link href="/app">
          <UserRoundCheck aria-hidden="true" size={20} strokeWidth={1.7} />
          <span>
            <strong>进入我的首页</strong>
            <small>查看下一步、处理状态和最近交付</small>
          </span>
          <ArrowRight aria-hidden="true" size={18} strokeWidth={1.7} />
        </Link>
        <Link href="/app/profiles">
          <FolderLock aria-hidden="true" size={20} strokeWidth={1.7} />
          <span>
            <strong>查看命理档案</strong>
            <small>回看每次确认形成的不可变版本</small>
          </span>
          <ArrowRight aria-hidden="true" size={18} strokeWidth={1.7} />
        </Link>
        <Link href="/app/readings">
          <History aria-hidden="true" size={20} strokeWidth={1.7} />
          <span>
            <strong>查看解读历史</strong>
            <small>按真实状态回看已交付与处理中记录</small>
          </span>
          <ArrowRight aria-hidden="true" size={18} strokeWidth={1.7} />
        </Link>
      </nav>
    </section>
  );
}

function AccountCenterContent() {
  const { state, refresh } = useAccountSession();

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (state.status === "checking") {
    return (
      <StatusPanel
        state="loading"
        title="正在确认当前设备身份"
        description="只读取服务端会话与脱敏登录身份，不从浏览器存储猜测登录状态。"
      />
    );
  }

  if (state.status === "error") {
    return (
      <div className={styles.statusStack}>
        <StatusPanel
          state="error"
          title="暂时无法确认登录状态"
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
    );
  }

  if (state.status === "signedOut") {
    return (
      <>
        <div className={styles.sessionBanner} data-state="signed-out" role="status">
          <KeyRound aria-hidden="true" size={20} strokeWidth={1.7} />
          <div>
            <strong>当前设备尚未登录</strong>
            <span>验证邮箱后，本页会切换为你的个人中心。</span>
          </div>
        </div>

        <div className={surface.dashboard}>
          <section className={surface.paper} aria-labelledby="login-title">
            <div className={surface.sectionHeader}>
              <div>
                <h2 id="login-title">验证码登录</h2>
                <p>首次邮箱验证自动注册，已有邮箱直接登录；验证成功后进入个人首页。</p>
              </div>
            </div>
            <OtpForm />
          </section>
          <AccountBoundaryNote />
        </div>

        <AccountSessionControl />
      </>
    );
  }

  const identity = primaryLoginIdentity(state.account);

  return (
    <>
      <section className={styles.identityHero} aria-labelledby="identity-title">
        <span className={styles.identityIcon} aria-hidden="true">
          <UserRoundCheck size={27} strokeWidth={1.65} />
        </span>
        <div>
          <p className={styles.sessionState}>账户已验证</p>
          <h2 id="identity-title">{identity?.masked_destination ?? "已验证账户"}</h2>
          <p>这是你在 FateRadar 的个人中心。这里只展示服务端返回的脱敏身份与真实记录。</p>
        </div>
      </section>

      <AccountLinks />

      <div className={surface.dashboard}>
        <AccountSessionControl />
        <AccountBoundaryNote />
      </div>

      <section className={surface.paper} aria-labelledby="account-tools-title">
        <div className={surface.sectionHeader}>
          <div>
            <h2 id="account-tools-title">设备、订单与数据权利</h2>
            <p>只有后端返回真实状态后，相关操作才会开放。</p>
          </div>
        </div>
        <div className={styles.rightsGrid}>
          <p>
            <ReceiptText aria-hidden="true" size={18} />
            真实支付尚未开放，不展示虚构订单、渠道或已付款状态。
          </p>
          <p>
            <Database aria-hidden="true" size={18} />
            导出、删除与撤回需要服务端授权和审计流程，正式资料不进 localStorage。
          </p>
        </div>
      </section>
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
