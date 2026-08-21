"use client";

import { useEffect, useState } from "react";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
import {
  ApiError,
  listAccountReferrals,
  type AccountReferralCampaign,
  type AccountReferralsResponse,
} from "@/lib/api";

import surface from "../app-surface.module.css";
import { StatusPanel } from "../status-panel";
import styles from "./account-referrals-surface.module.css";
import { SecondaryStatus } from "./secondary-status";
import secondary from "./secondary-surfaces.module.css";

function stateLabel(state: string): string {
  return {
    active: "进行中",
    draft: "草稿",
    scheduled: "待开始",
    paused: "已暂停",
    ended: "已结束",
  }[state] ?? state;
}

function rewardLabel(status: string): string {
  return {
    reserved: "奖励已预留",
    committed: "奖励已确认",
    released: "奖励已释放",
  }[status] ?? `奖励状态：${status}`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(date);
}

function readableError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "邀请进度暂时无法读取，请稍后重试。";
}

function CampaignCard({ campaign }: { readonly campaign: AccountReferralCampaign }) {
  return (
    <li className={styles.campaign}>
      <div className={styles.campaignHeader}>
        <h3>{campaign.campaign_key}</h3>
        <span className={styles.stateTag}>{stateLabel(campaign.state)}</span>
      </div>
      <p className={styles.campaignMeta}>
        版本 {campaign.version} · 活动时间 {formatDate(campaign.starts_at)}
        {campaign.ends_at ? ` 至 ${formatDate(campaign.ends_at)}` : ""}
      </p>
      <p className={styles.progressLine}>
        已邀请 {campaign.invited_count} / {campaign.per_inviter_limit}
      </p>
      {campaign.my_attribution_stage ? (
        <p className={styles.campaignMeta}>我的参与状态：{campaign.my_attribution_stage}</p>
      ) : null}
      {campaign.codes.length ? (
        <div className={styles.codeBlock}>
          <div className={styles.codeHeader}>
            <h4>我的邀请码</h4>
            <span>只显示服务端确认的代码</span>
          </div>
          <ul className={styles.codeList}>
            {campaign.codes.map((code) => (
              <li key={code}>
                <code className={styles.code}>{code}</code>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {campaign.rewards.length ? (
        <div className={styles.rewardBlock}>
          <div className={styles.rewardHeader}>
            <h4>奖励记录</h4>
            <span>金额和数量以账户记录为准</span>
          </div>
          <ul className={styles.rewardList}>
            {campaign.rewards.map((reward) => (
              <li key={`${reward.status}-${reward.occurred_at}`}>
                <span>{rewardLabel(reward.status)}</span>
                <time dateTime={reward.occurred_at}>{formatDate(reward.occurred_at)}</time>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </li>
  );
}

function ReferralsContent() {
  const { state } = useAccountSession();
  const userId = state.status === "signedIn" ? state.account.user_id : null;
  const [progress, setProgress] = useState<AccountReferralsResponse | null>(null);
  const [loadedUserId, setLoadedUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!userId) return;

    let active = true;
    void listAccountReferrals()
      .then((next) => {
        if (!active) return;
        setProgress(next);
        setLoadedUserId(userId);
        setError(null);
        setSessionExpired(false);
      })
      .catch((nextError: unknown) => {
        if (!active) return;
        setLoadedUserId(userId);
        if (nextError instanceof ApiError && nextError.status === 401) {
          setSessionExpired(true);
        } else {
          setError(readableError(nextError));
        }
      });

    return () => {
      active = false;
    };
  }, [attempt, userId]);

  if (state.status === "checking") {
    return <StatusPanel state="loading" title="正在确认账户…" description="正在确认账户。" />;
  }

  if (state.status === "error") {
    return <StatusPanel state="error" title="无法确认账户" description={state.message} />;
  }

  if (state.status === "signedOut") {
    return (
      <SecondaryStatus
        action={{ href: "/auth/login", label: "前往登录" }}
        description="登录后才能查看邀请。"
        state="need-login"
        title="需要登录"
      />
    );
  }

  if (sessionExpired) {
    return (
      <StatusPanel
        actionHref="/auth/login"
        actionLabel="重新登录"
        state="error"
        title="登录已过期"
        description="登录已失效，请重新登录后再查看。"
      />
    );
  }

  const loading = userId !== loadedUserId || progress === null;
  return (
    <section aria-labelledby="account-referrals-title" className={surface.paper}>
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="account-referrals-title">邀请进度</h2>
          <p>只显示已确认的活动和邀请码。</p>
        </div>
      </div>
      {loading ? (
        <StatusPanel state="loading" title="正在读取邀请进度…" description="只会读取当前账户的邀请记录。" />
      ) : null}
      {!loading && error ? (
        <>
          <StatusPanel state="error" title="无法读取邀请进度" description={error} />
          <div className={secondary.actionRow}>
            <button
              className={surface.secondaryButton}
              onClick={() => {
                setError(null);
                setProgress(null);
                setLoadedUserId(null);
                setAttempt((value) => value + 1);
              }}
              type="button"
            >
              重试
            </button>
          </div>
        </>
      ) : null}
      {!loading && !error && progress?.campaigns.length === 0 ? (
        <StatusPanel
          state="empty"
          title="还没有邀请记录"
          description="服务端确认活动和邀请码后，进度会显示在这里。"
        />
      ) : null}
      {!loading && !error && progress?.campaigns.length ? (
        <ul className={styles.campaigns}>
          {progress.campaigns.map((campaign) => (
            <CampaignCard
              campaign={campaign}
              key={`${campaign.campaign_key}-${campaign.version}`}
            />
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function AccountReferralsSurface() {
  return (
    <AccountSessionBoundary>
      <AccountSectionShell intro="查看你的邀请活动。" title="邀请">
        <ReferralsContent />
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
