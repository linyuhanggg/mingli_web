"use client";

import { useEffect, useState } from "react";

import {
  ApiError,
  clearReferralAttribution,
  getReferralInvite,
  recordReferralAttribution,
  type ReferralPublicResponse,
} from "@/lib/api";

import { StatusPanel } from "../status-panel";
import surface from "../app-surface.module.css";
import { SecondarySurfaceFrame } from "./secondary-surface-frame";
import styles from "./secondary-surfaces.module.css";

const STATUS_COPY: Record<ReferralPublicResponse["status"], { label: string; description: string }> = {
  planned: { label: "活动计划中", description: "活动尚未开始，不能建立临时归因。" },
  active: { label: "活动进行中", description: "当前邀请活动可建立临时归因。" },
  paused: { label: "活动已暂停", description: "暂停期间不接收新的归因或合格支付。" },
  full: { label: "名额已满", description: "付款前已说明本单不参加活动。" },
  ended: { label: "活动已结束", description: "历史奖励仍可在账户中查看。" },
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(date);
}

function isMissing(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

type InviteLoadState = {
  readonly code: string;
  readonly invite?: ReferralPublicResponse;
  readonly error?: unknown;
};

export function InviteSurface({ code }: { readonly code: string }) {
  const [loadState, setLoadState] = useState<InviteLoadState | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void getReferralInvite(code)
      .then((next) => {
        if (!cancelled) setLoadState({ code, invite: next });
      })
      .catch((nextError: unknown) => {
        if (!cancelled) setLoadState({ code, error: nextError });
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  if (loadState?.code !== code) {
    return (
      <SecondarySurfaceFrame eyebrow="邀请活动" intro="正在读取服务端确认的活动状态。" title="邀请活动">
        <StatusPanel
          description="不会根据邀请码在浏览器里猜测活动或邀请人。"
          state="loading"
          title="正在验证邀请…"
        />
      </SecondarySurfaceFrame>
    );
  }

  if (loadState.error !== undefined) {
    return (
      <SecondarySurfaceFrame eyebrow="邀请活动" intro="页面只展示服务端确认的邀请状态。" title="邀请活动">
        <StatusPanel
          description={
            isMissing(loadState.error)
              ? "链接无效，不会写入邀请归因。"
              : "邀请状态暂时无法读取，请稍后重试。"
          }
          state="error"
          title={isMissing(loadState.error) ? "邀请无效" : "无法读取邀请状态"}
        />
      </SecondarySurfaceFrame>
    );
  }

  const invite = loadState.invite;
  if (invite === undefined) {
    return null;
  }

  const copy = STATUS_COPY[invite.status];
  const canCapture = invite.status === "active" && !invite.self_invite;

  async function capture() {
    setBusy(true);
    try {
      await recordReferralAttribution(code);
      setLoadState((current) => (
        current?.code === code && current.invite
          ? { ...current, invite: { ...current.invite, attribution_recorded: true } }
          : current
      ));
    } catch (nextError: unknown) {
      setLoadState((current) => (
        current?.code === code ? { ...current, error: nextError } : current
      ));
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    setBusy(true);
    try {
      await clearReferralAttribution(code);
      setLoadState((current) => (
        current?.code === code && current.invite
          ? { ...current, invite: { ...current.invite, attribution_recorded: false } }
          : current
      ));
    } catch (nextError: unknown) {
      setLoadState((current) => (
        current?.code === code ? { ...current, error: nextError } : current
      ));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SecondarySurfaceFrame
      eyebrow="邀请活动"
      intro="邀请状态、有效期和临时归因均来自服务端；页面不展示邀请人身份、收益榜或倒计时。"
      title="邀请活动"
    >
      <section aria-labelledby="invite-status-title" className={styles.boundaryPanel}>
        <div className={surface.sectionHeader}>
          <div>
            <h2 id="invite-status-title">{copy.label}</h2>
            <p>{copy.description}</p>
          </div>
        </div>
        <dl className={styles.inviteFacts}>
          <div>
            <dt>活动版本</dt>
            <dd>{invite.campaign_key} · {invite.version}</dd>
          </div>
          <div>
            <dt>活动时间</dt>
            <dd>
              {formatDate(invite.starts_at)}
              {invite.ends_at ? ` 至 ${formatDate(invite.ends_at)}` : ""}
            </dd>
          </div>
          <div>
            <dt>邀请规则</dt>
            <dd>每位邀请人最多 {invite.per_inviter_limit} 位新用户</dd>
          </div>
        </dl>
        {invite.self_invite ? <p>这是你的邀请码，不能自邀。</p> : null}
        {canCapture && invite.attribution_recorded ? (
          <div className={surface.actionRow}>
            <p role="status">临时归因已记录，注册确认前仍可清除。</p>
            <button className={surface.secondaryButton} disabled={busy} onClick={clear} type="button">
              清除本次邀请
            </button>
          </div>
        ) : null}
        {canCapture && !invite.attribution_recorded ? (
          <div className={surface.actionRow}>
            <button className={surface.button} disabled={busy} onClick={capture} type="button">
              记录本次邀请
            </button>
            <p>只有注册确认时才会永久锁定归因；此刻不会占用奖励名额。</p>
          </div>
        ) : null}
      </section>
    </SecondarySurfaceFrame>
  );
}
