"use client";

import { useEffect, useState, type FormEvent } from "react";

import {
  ApiError,
  clearReferralAttribution,
  getReferralInvite,
  recordReferralAttribution,
  type ReferralPublicResponse,
} from "@/lib/api";

import surface from "../app-surface.module.css";
import styles from "./secondary-surfaces.module.css";

const STATUS_COPY: Record<ReferralPublicResponse["status"], { label: string; description: string }> = {
  planned: { label: "计划中", description: "活动尚未开始。" },
  active: { label: "进行中", description: "现在可以记录这次邀请。" },
  paused: { label: "已暂停", description: "暂停期间不接收新的邀请。" },
  full: { label: "名额已满", description: "付款前已说明本单不参加活动。" },
  ended: { label: "已结束", description: "活动已结束。" },
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
    return <p role="status">正在读取邀请状态。</p>;
  }

  if (loadState.error !== undefined) {
    return (
      <div role="status">
        <p>{isMissing(loadState.error) ? "邀请无效" : "无法读取邀请状态"}</p>
        <p>
          {isMissing(loadState.error)
            ? "链接无效，不会写入邀请归因。"
            : "邀请状态暂时无法读取，请稍后重试。"}
        </p>
      </div>
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

  function submitCapture(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void capture();
  }

  return (
    <section aria-labelledby="invite-status-title">
      <h2 id="invite-status-title">{copy.label}</h2>
      <p>{copy.description}</p>
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
          <form onSubmit={submitCapture}>
            <button disabled={busy} type="submit">
              记录本次邀请
            </button>
          </form>
          <p>只有注册确认时才会永久锁定归因；此刻不会占用奖励名额。</p>
        </div>
      ) : null}
    </section>
  );
}
