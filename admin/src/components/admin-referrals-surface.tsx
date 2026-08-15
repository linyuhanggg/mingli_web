"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Button, Drawer, Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { useAdminStaff } from "@/components/admin-shell";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminReferralResponse,
  AdminReferralsResponse,
} from "@/lib/admin-referrals";

import styles from "./admin-referrals-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "id", header: "活动", sortable: true },
  { key: "campaign", header: "活动键", sortable: true },
  { key: "version", header: "版本" },
  { key: "state", header: "状态", sortable: true },
  { key: "funnel", header: "漏斗" },
  { key: "limits", header: "名额" },
  { key: "action", header: "操作" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function stateCopy(value: string): string {
  return { draft: "草稿", active: "活动中", paused: "已暂停", ended: "已结束" }[value] ?? value;
}

export function AdminReferralsSurface({ role, campaignId }: { role?: StaffRole; campaignId?: string }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable">("loading");
  const [data, setData] = useState<AdminReferralsResponse>({ campaigns: [] });
  const [selected, setSelected] = useState<AdminReferralResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = campaignId
        ? await adminFetch<AdminReferralResponse>(`/api/v1/admin/referrals/${campaignId}`)
        : await adminFetch<AdminReferralsResponse>("/api/v1/admin/referrals");
      if (cancelled) return;
      if (!response.ok) {
        setState(
          response.status === 403
            ? "forbidden"
            : response.status === 0 || response.status >= 500
              ? "unavailable"
              : "error",
        );
        setError(response.title);
        return;
      }
      if (campaignId) {
        setSelected(response.data as AdminReferralResponse);
        setState("ready");
      } else {
        const list = response.data as AdminReferralsResponse;
        setData(list);
        setState(list.campaigns.length > 0 ? "ready" : "empty");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [campaignId]);

  const rows = useMemo<TableRow[]>(
    () =>
      data.campaigns.map((item) => ({
        id: item.id,
        campaign: item.campaign_key,
        version: item.version,
        state: stateCopy(item.state),
        funnel: `${item.code_count} 个码 · ${item.temporary_attribution_count} 次临时归因 · ${item.attribution_count} 次归因 · ${item.reservation_count} 个奖励`,
        limits: `${item.total_limit ?? "不设总额"} · 每邀请人 ${item.per_inviter_limit}`,
        action: (
          <Button
            variant="secondary"
            type="button"
            aria-label={`查看活动详情 ${item.id}`}
            onClick={async () => {
              if (document.activeElement instanceof HTMLElement) {
                restoreFocusRef.current = document.activeElement;
              }
              const response = await adminFetch<AdminReferralResponse>(`/api/v1/admin/referrals/${item.id}`);
              if (response.ok) setSelected(response.data);
            }}
          >
            查看详情
          </Button>
        ),
      })),
    [data.campaigns],
  );

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取邀请活动…" description="只显示活动、归因和奖励事实，不展示访客识别哈希。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="邀请活动事实只允许运营和超级管理员查看。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="邀请平台暂不可用" description="页面不显示假活动、假归因或假奖励。" />
    ) : state === "error" ? (
      <Status state="error" title="邀请活动读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无邀请活动" description="创建正式活动版本后，这里会显示活动漏斗事实。" />
    ) : (
      <Status state="success" title="邀请活动已接入" description="展示 Campaign/Code/Attribution/RewardReservation 事实；visitor_key_hash 不进入响应。" />
    );

  if (campaignId) {
    return (
      <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
        {notice}
        {selected ? <ReferralDetail data={selected} /> : null}
      </div>
    );
  }

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="referrals-title">
          <div className={styles.heading}>
            <div>
              <h2 id="referrals-title">邀请活动漏斗</h2>
              <p>页面只读展示活动和奖励事实；活动配置通过受控 Admin 命令 API 执行，不在这里伪造前台购买或审批流程。</p>
            </div>
            <span className={styles.badge}>运营只读</span>
          </div>
          <Table
            caption="邀请活动"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选邀请活动"
            filterPlaceholder="例如：活动键、版本或状态…"
            pageSize={20}
            emptyState="当前没有邀请活动"
          />
        </section>
      ) : null}
      <Drawer
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
        title={selected ? `邀请活动 ${selected.campaign.campaign_key}` : "邀请活动详情"}
        description="只显示服务端脱敏漏斗事实；访客识别哈希不展示。"
        side="right"
        restoreFocusRef={restoreFocusRef}
      >
        {selected ? (
          <div className={styles.detail}>
            <dl className={styles.facts}>
              <div><dt>状态</dt><dd>{stateCopy(selected.campaign.state)}</dd></div>
              <div><dt>开始</dt><dd>{formatDate(selected.campaign.starts_at)}</dd></div>
              <div><dt>奖励额度</dt><dd>{selected.campaign.reward_quantity}</dd></div>
              <div><dt>活动码</dt><dd>{selected.codes.length}</dd></div>
              <div><dt>临时归因</dt><dd>{selected.campaign.temporary_attribution_count}</dd></div>
              <div><dt>已归因</dt><dd>{selected.attributions.length}</dd></div>
              <div><dt>商品槽数</dt><dd>{selected.slots.length}</dd></div>
              <div><dt>奖励预留</dt><dd>{selected.rewards.length}</dd></div>
            </dl>
            <h3>活动码</h3>
            <p>{selected.codes.map((item) => `${item.code} · ${stateCopy(item.status)}`).join("；") || "暂无活动码"}</p>
            <h3>归因</h3>
            <p>{selected.attributions.map((item) => `${item.referred_user_id} · ${stateCopy(item.status)}`).join("；") || "暂无归因"}</p>
            <h3>商品名额</h3>
            <p>{selected.slots.map((item) => `${item.product_version_id} · ${item.slot_key} · ${item.total_limit} 个名额`).join("；") || "暂无商品名额"}</p>
            <h3>奖励</h3>
            <p>{selected.rewards.map((item) => `${item.product_version_id ?? "商品未绑定"} · ${item.payment_attempt_id ? `已绑定支付 ${item.payment_attempt_id}` : "未绑定支付"}`).join("；") || "暂无奖励"}</p>
            <p>{selected.rewards.map((item) => `${item.quantity} 个 · ${stateCopy(item.status)}`).join("；") || "暂无奖励"}</p>
            <p>visitor_key_hash 不展示</p>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}

function ReferralDetail({ data }: { data: AdminReferralResponse }) {
  return (
    <section className={styles.panel} aria-labelledby="referral-detail-title">
      <div className={styles.heading}>
        <div>
          <h2 id="referral-detail-title">邀请活动 {data.campaign.campaign_key}</h2>
          <p>只显示活动码、归因和奖励事实；访客识别哈希不展示。</p>
        </div>
        <span className={styles.badge}>运营只读</span>
      </div>
      <dl className={styles.facts}>
        <div><dt>状态</dt><dd>{stateCopy(data.campaign.state)}</dd></div>
        <div><dt>版本</dt><dd>{data.campaign.version}</dd></div>
        <div><dt>开始</dt><dd>{formatDate(data.campaign.starts_at)}</dd></div>
        <div><dt>活动码</dt><dd>{data.codes.length}</dd></div>
        <div><dt>临时归因</dt><dd>{data.campaign.temporary_attribution_count}</dd></div>
        <div><dt>已归因</dt><dd>{data.attributions.length}</dd></div>
        <div><dt>商品槽数</dt><dd>{data.slots.length}</dd></div>
        <div><dt>奖励预留</dt><dd>{data.rewards.length}</dd></div>
      </dl>
      <div className={styles.detail}>
        <h3>活动码</h3>
        <p>{data.codes.map((item) => `${item.code} · ${stateCopy(item.status)}`).join("；") || "暂无活动码"}</p>
        <h3>归因</h3>
        <p>{data.attributions.map((item) => `${item.referred_user_id} · ${stateCopy(item.status)}`).join("；") || "暂无归因"}</p>
        <h3>商品名额</h3>
        <p>{data.slots.map((item) => `${item.product_version_id} · ${item.slot_key} · ${item.total_limit} 个名额`).join("；") || "暂无商品名额"}</p>
        <h3>奖励</h3>
        <p>{data.rewards.map((item) => `${item.product_version_id ?? "商品未绑定"} · ${item.payment_attempt_id ? `已绑定支付 ${item.payment_attempt_id}` : "未绑定支付"}`).join("；") || "暂无奖励"}</p>
        <p>{data.rewards.map((item) => `${item.quantity} 个 · ${stateCopy(item.status)}`).join("；") || "暂无奖励"}</p>
        <p>visitor_key_hash 不展示</p>
      </div>
    </section>
  );
}
