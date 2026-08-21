"use client";

import { useEffect, useMemo, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminCommerceKind,
  AdminCommerceResponse,
  AdminOrder,
  AdminPayment,
  AdminRefund,
} from "@/lib/admin-commerce";

import styles from "./admin-commerce-surface.module.css";

const COLUMNS: Record<AdminCommerceKind, TableColumn[]> = {
  orders: [
    { key: "id", header: "订单", sortable: true },
    { key: "target", header: "交付目标" },
    { key: "amount", header: "金额", sortable: true },
    { key: "fulfillment", header: "交付" },
    { key: "status", header: "状态", sortable: true },
    { key: "createdAt", header: "创建时间", sortable: true },
  ],
  payments: [
    { key: "id", header: "支付尝试", sortable: true },
    { key: "order", header: "订单" },
    { key: "channel", header: "渠道", sortable: true },
    { key: "settlement", header: "到账事实", sortable: true },
    { key: "transaction", header: "渠道交易号" },
    { key: "amount", header: "金额", sortable: true },
    { key: "status", header: "状态", sortable: true },
  ],
  refunds: [
    { key: "id", header: "退款", sortable: true },
    { key: "order", header: "订单" },
    { key: "channel", header: "渠道", sortable: true },
    { key: "amount", header: "金额", sortable: true },
    { key: "reason", header: "原因" },
    { key: "confirmation", header: "活动退款确认" },
    { key: "status", header: "状态", sortable: true },
  ],
};

const KIND_COPY: Record<AdminCommerceKind, { title: string; empty: string; description: string }> = {
  orders: {
    title: "订单事实",
    empty: "暂无订单事实",
    description: "显示本地订单与交付状态；不把订单列表当成渠道到账证明。",
  },
  payments: {
    title: "支付事实",
    empty: "暂无支付事实",
    description: "显示本地确认的支付交易号、渠道和金额；真实渠道验签仍由支付边界负责。",
  },
  refunds: {
    title: "退款事实",
    empty: "暂无退款事实",
    description: "显示本地退款流水和原因；当前页面不伪造审批或补偿命令。",
  },
};

const STATUS_FILTERS = {
  orders: {
    label: "按订单状态筛选",
    rowKey: "status",
    options: [
      { value: "", label: "全部" },
      { value: "已创建", label: "新建订单" },
      { value: "已支付", label: "已支付订单" },
      { value: "已退款", label: "退款订单" },
    ],
  },
  payments: {
    label: "按支付状态筛选",
    rowKey: "status",
    options: [
      { value: "", label: "全部" },
      { value: "待处理", label: "待处理支付" },
      { value: "已确认", label: "已确认支付" },
      { value: "失败", label: "失败支付" },
    ],
  },
  refunds: {
    label: "按退款状态筛选",
    rowKey: "status",
    options: [
      { value: "", label: "全部" },
      { value: "待处理", label: "待处理退款" },
      { value: "已确认", label: "已确认退款" },
      { value: "失败", label: "失败退款" },
    ],
  },
} as const;

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatAmount(amountMinor: number, currency: string): string {
  return `${(amountMinor / 100).toFixed(2)} ${currency}`;
}

function statusCopy(value: string): string {
  return {
    created: "已创建",
    paid: "已支付",
    refunded: "已退款",
    confirmed: "已确认",
    pending: "待处理",
    failed: "失败",
    reserved: "已占用",
    delivered: "已交付",
    released: "已释放",
  }[value] ?? value;
}

function orderRows(items: readonly AdminOrder[]): TableRow[] {
  return items.map((item) => ({
    id: item.id,
    target: item.purchase_target_ref,
    amount: formatAmount(item.amount_minor, item.currency),
    fulfillment: item.fulfillment_status ? statusCopy(item.fulfillment_status) : "未创建",
    status: statusCopy(item.status),
    createdAt: formatDate(item.created_at),
  }));
}

function paymentRows(items: readonly AdminPayment[]): TableRow[] {
  return items.map((item) => ({
    id: item.id,
    order: item.order_id,
    channel: item.channel,
    settlement: formatDate(item.confirmed_at),
    transaction: item.channel_transaction_id,
    amount: formatAmount(item.amount_minor, item.currency),
    status: statusCopy(item.status),
  }));
}

function refundRows(items: readonly AdminRefund[]): TableRow[] {
  return items.map((item) => ({
    id: item.id,
    order: item.order_id,
    channel: item.channel,
    amount: formatAmount(item.amount_minor, item.currency),
    reason: item.reason,
    confirmation: item.referral_confirmation_id
      ? `${item.referral_confirmation_id} · ${item.referral_confirmation_policy_version ?? "未标注政策"} · ${formatDate(item.referral_confirmation_at)}`
      : "—",
    status: statusCopy(item.status),
  }));
}

function rowsFor(kind: AdminCommerceKind, data: AdminCommerceResponse): TableRow[] {
  if (kind === "orders" && "orders" in data) return orderRows(data.orders);
  if (kind === "payments" && "payments" in data) return paymentRows(data.payments);
  if (kind === "refunds" && "refunds" in data) return refundRows(data.refunds);
  return [];
}

function countFor(kind: AdminCommerceKind, data: AdminCommerceResponse): number {
  if (kind === "orders" && "orders" in data) return data.orders.length;
  if (kind === "payments" && "payments" in data) return data.payments.length;
  if (kind === "refunds" && "refunds" in data) return data.refunds.length;
  return 0;
}

export function AdminCommerceSurface({
  kind,
  role,
}: {
  kind: AdminCommerceKind;
  role?: StaffRole;
}) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const copy = KIND_COPY[kind];
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable">("loading");
  const [data, setData] = useState<AdminCommerceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminCommerceResponse>(`/api/v1/admin/commerce/${kind}`);
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
      setData(response.data);
      setState(countFor(kind, response.data) > 0 ? "ready" : "empty");
    })();
    return () => {
      cancelled = true;
    };
  }, [kind]);

  const rows = useMemo(() => (data ? rowsFor(kind, data) : []), [data, kind]);
  const notice =
    state === "loading" ? (
      <Status state="loading" title={`正在读取${copy.title}…`} description="只显示服务端返回的本地商业事实。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="商业事实只允许财务、运营和超级管理员查看。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="商业平台暂不可用" description="页面不显示假订单、假支付或假退款。" />
    ) : state === "error" ? (
      <Status state="error" title={`${copy.title}读取失败`} description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title={copy.empty} description={copy.description} />
    ) : (
      <Status state="success" title={`${copy.title}已接入`} description={copy.description} />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" ? <section className={styles.panel} aria-labelledby={`${kind}-title`}>
        <div className={styles.heading}>
          <div>
            <h2 id={`${kind}-title`}>{copy.title}</h2>
            <p>{copy.description}</p>
          </div>
          <span className={styles.badge}>只读事实</span>
        </div>
        <Table
          caption={copy.title}
          columns={COLUMNS[kind]}
          rows={rows}
          filterLabel={`筛选${copy.title}`}
          filterPlaceholder="例如：编号、渠道、状态或金额…"
          filter={STATUS_FILTERS[kind]}
          pageSize={20}
          emptyState={`没有符合筛选条件的${copy.title}`}
        />
      </section> : null}
    </div>
  );
}
