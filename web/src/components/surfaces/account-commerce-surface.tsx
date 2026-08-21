"use client";

import { useEffect, useState } from "react";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
import {
  ApiError,
  listAccountEntitlements,
  listAccountOrders,
  type AccountEntitlement,
  type AccountOrder,
} from "@/lib/api";

import surface from "../app-surface.module.css";
import { StatusPanel } from "../status-panel";
import styles from "./account-commerce-surface.module.css";
import { SecondaryStatus } from "./secondary-status";
import secondary from "./secondary-surfaces.module.css";

type CommerceKind = "orders" | "entitlements";

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function formatAmount(amountMinor: number, currency: string): string {
  return `${(amountMinor / 100).toFixed(2)} ${currency}`;
}

function orderStatusLabel(status: string): string {
  return {
    created: "待支付",
    payment_pending: "支付处理中",
    paid: "已支付",
    cancelled: "已取消",
    refunded: "已退款",
  }[status] ?? status;
}

function fulfillmentStatusLabel(status: string | null): string {
  return {
    reserved: "已占用",
    processing: "处理中",
    delivered: "已交付",
    released: "已释放",
    failed: "交付失败",
  }[status ?? ""] ?? (status ?? "未开始");
}

function eventLabel(kind: AccountEntitlement["events"][number]["kind"]): string {
  return {
    GRANT: "已发放",
    RESERVE: "已预留",
    CONSUME: "已消费",
    RELEASE: "已释放",
    REVERSE: "已冲正",
    EXPIRE: "已过期",
  }[kind];
}

function readableError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "暂时无法读取，请稍后重试。";
}

function OrderCard({ order }: { readonly order: AccountOrder }) {
  return (
    <li className={styles.item}>
      <div className={styles.itemHeader}>
        <h3>{order.product_label}</h3>
        <span className={styles.statusTag}>{orderStatusLabel(order.status)}</span>
      </div>
      <p className={styles.amountLine}>{formatAmount(order.amount_minor, order.currency)}</p>
      <p className={styles.metaLine}>履约：{fulfillmentStatusLabel(order.fulfillment_status)}</p>
      <time className={styles.metaLine} dateTime={order.created_at}>
        创建于 {formatDate(order.created_at)}
      </time>
    </li>
  );
}

function EntitlementCard({ entitlement }: { readonly entitlement: AccountEntitlement }) {
  return (
    <li className={styles.item}>
      <div className={styles.itemHeader}>
        <h3>{entitlement.label}</h3>
        <span className={styles.statusTag}>权益</span>
      </div>
      <dl className={styles.stats}>
        <div><dt>可用</dt><dd>{entitlement.available}</dd></div>
        <div><dt>已发放</dt><dd>{entitlement.granted}</dd></div>
        <div><dt>已预留</dt><dd>{entitlement.reserved}</dd></div>
        <div><dt>已消耗</dt><dd>{entitlement.consumed}</dd></div>
      </dl>
      {entitlement.events.length ? (
        <div className={styles.eventBlock}>
          <div className={styles.eventHeader}><h4>变更记录</h4><span>只读</span></div>
          <ul className={styles.eventList}>
            {entitlement.events.map((event) => (
              <li key={`${event.kind}-${event.occurred_at}`}>
                <span>{eventLabel(event.kind)} {event.quantity}</span>
                <time dateTime={event.occurred_at}>{formatDate(event.occurred_at)}</time>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </li>
  );
}

function CommerceContent({ kind }: { readonly kind: CommerceKind }) {
  const { state } = useAccountSession();
  const userId = state.status === "signedIn" ? state.account.user_id : null;
  const [orders, setOrders] = useState<AccountOrder[] | null>(null);
  const [entitlements, setEntitlements] = useState<AccountEntitlement[] | null>(null);
  const [loadedUserId, setLoadedUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!userId) return;

    let active = true;
    const handleError = (nextError: unknown) => {
      if (!active) return;
      setLoadedUserId(userId);
      if (nextError instanceof ApiError && nextError.status === 401) {
        setSessionExpired(true);
      } else {
        setError(readableError(nextError));
      }
    };
    if (kind === "orders") {
      void listAccountOrders()
        .then((next) => {
          if (!active) return;
          setOrders(next.orders);
          setLoadedUserId(userId);
          setError(null);
          setSessionExpired(false);
        })
        .catch(handleError);
    } else {
      void listAccountEntitlements()
        .then((next) => {
          if (!active) return;
          setEntitlements(next.entitlements);
          setLoadedUserId(userId);
          setError(null);
          setSessionExpired(false);
        })
        .catch(handleError);
    }

    return () => {
      active = false;
    };
  }, [attempt, kind, userId]);

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
        description={kind === "orders" ? "登录后才能查看订单。" : "登录后才能查看权益。"}
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

  const data = kind === "orders" ? orders : entitlements;
  const loading = userId !== loadedUserId || data === null;
  const retry = () => {
    setError(null);
    if (kind === "orders") setOrders(null);
    else setEntitlements(null);
    setLoadedUserId(null);
    setAttempt((value) => value + 1);
  };

  return (
    <section aria-labelledby={`account-${kind}-title`} className={surface.paper}>
      <div className={surface.sectionHeader}>
        <div>
          <h2 id={`account-${kind}-title`}>{kind === "orders" ? "订单" : "权益"}</h2>
          <p>
            {kind === "orders"
              ? "只显示当前账户的订单。"
              : "只显示当前账户的权益。"}
          </p>
        </div>
      </div>
      {loading ? <StatusPanel state="loading" title="正在读取…" description="只会读取当前账户的服务端事实。" /> : null}
      {!loading && error ? (
        <>
          <StatusPanel state="error" title="无法读取" description={error} />
          <div className={secondary.actionRow}>
            <button className={surface.secondaryButton} onClick={retry} type="button">重试</button>
          </div>
        </>
      ) : null}
      {!loading && !error && data?.length === 0 ? (
        <StatusPanel
          state="empty"
          title={kind === "orders" ? "还没有订单" : "还没有权益记录"}
          description="服务端确认记录后，会显示在这里。"
        />
      ) : null}
      {!loading && !error && data?.length ? (
        <ul className={styles.list}>
          {kind === "orders"
            ? orders?.map((order) => <OrderCard key={order.order_id} order={order} />)
            : entitlements?.map((entitlement) => (
                <EntitlementCard key={entitlement.label} entitlement={entitlement} />
              ))}
        </ul>
      ) : null}
    </section>
  );
}

export function AccountCommerceSurface({ kind }: { readonly kind: CommerceKind }) {
  return (
    <AccountSessionBoundary>
      <AccountSectionShell
        intro={kind === "orders" ? "查看你的订单。" : "查看你的权益。"}
        title={kind === "orders" ? "订单" : "权益"}
      >
        <CommerceContent kind={kind} />
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
