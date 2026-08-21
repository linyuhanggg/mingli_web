"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
import {
  ApiError,
  deleteAccountNotification,
  listAccountNotifications,
  markAccountNotificationRead,
  markAllAccountNotificationsRead,
  type AccountNotification,
} from "@/lib/api";

import surface from "../app-surface.module.css";
import { StatusPanel } from "../status-panel";
import styles from "./account-notifications-surface.module.css";
import { SecondaryStatus } from "./secondary-status";
import secondary from "./secondary-surfaces.module.css";

type NotificationFilter = "all" | "unread";

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function readableError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "通知暂时无法读取，请稍后重试。";
}

function NotificationsContent() {
  const { state } = useAccountSession();
  const userId = state.status === "signedIn" ? state.account.user_id : null;
  const [filter, setFilter] = useState<NotificationFilter>("all");
  const [notifications, setNotifications] = useState<AccountNotification[] | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadedUserId, setLoadedUserId] = useState<string | null>(null);
  const [loadedFilter, setLoadedFilter] = useState<NotificationFilter | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;

    let active = true;
    void listAccountNotifications({ unreadOnly: filter === "unread" })
      .then((next) => {
        if (!active) return;
        setNotifications(next.notifications);
        setUnreadCount(next.unread_count);
        setLoadedUserId(userId);
        setLoadedFilter(filter);
        setError(null);
        setSessionExpired(false);
      })
      .catch((nextError: unknown) => {
        if (!active) return;
        setLoadedUserId(userId);
        setLoadedFilter(filter);
        if (nextError instanceof ApiError && nextError.status === 401) {
          setSessionExpired(true);
        } else {
          setError(readableError(nextError));
        }
      });

    return () => {
      active = false;
    };
  }, [attempt, filter, userId]);

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
        description="登录后才能查看通知。"
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

  const loading = userId !== loadedUserId || loadedFilter !== filter || notifications === null;

  function retry() {
    setError(null);
    setNotifications(null);
    setLoadedUserId(null);
    setLoadedFilter(null);
    setAttempt((value) => value + 1);
  }

  async function markRead(item: AccountNotification) {
    if (item.read_at) return;
    setBusyId(item.id);
    setError(null);
    try {
      const updated = await markAccountNotificationRead(item.id);
      setNotifications((current) =>
        current?.map((entry) => (entry.id === updated.id ? updated : entry)) ?? current,
      );
      setUnreadCount((current) => Math.max(0, current - 1));
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusyId(null);
    }
  }

  async function markAllRead() {
    if (unreadCount === 0) return;
    setBusyId("all");
    setError(null);
    try {
      await markAllAccountNotificationsRead();
      const now = new Date().toISOString();
      setNotifications((current) =>
        current?.map((entry) => ({ ...entry, read_at: entry.read_at ?? now })) ?? current,
      );
      setUnreadCount(0);
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(item: AccountNotification) {
    setBusyId(item.id);
    setError(null);
    try {
      await deleteAccountNotification(item.id);
      setNotifications((current) => current?.filter((entry) => entry.id !== item.id) ?? current);
      if (!item.read_at) setUnreadCount((current) => Math.max(0, current - 1));
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section aria-labelledby="account-notifications-title" className={surface.paper}>
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="account-notifications-title">通知列表</h2>
          <p>只显示站内通知。</p>
        </div>
        <span aria-live="polite" className={surface.metaLine}>未读 {unreadCount}</span>
      </div>

      <div aria-label="通知筛选" className={styles.filters} role="group">
        <button
          aria-pressed={filter === "all"}
          className={filter === "all" ? surface.button : surface.secondaryButton}
          onClick={() => setFilter("all")}
          type="button"
        >
          全部
        </button>
        <button
          aria-pressed={filter === "unread"}
          className={filter === "unread" ? surface.button : surface.secondaryButton}
          onClick={() => setFilter("unread")}
          type="button"
        >
          只看未读
        </button>
        <button
          className={surface.secondaryButton}
          disabled={busyId !== null || unreadCount === 0}
          onClick={() => void markAllRead()}
          type="button"
        >
          {busyId === "all" ? "正在处理…" : "全部标为已读"}
        </button>
      </div>

      {loading ? <StatusPanel state="loading" title="正在读取通知…" description="只会读取当前账户的站内记录。" /> : null}
      {!loading && error ? (
        <>
          <StatusPanel state="error" title="无法读取通知" description={error} />
          <div className={styles.retryRow}>
            <button className={surface.secondaryButton} onClick={retry} type="button">重试</button>
          </div>
        </>
      ) : null}
      {!loading && !error && notifications?.length === 0 ? (
        <StatusPanel
          state="empty"
          title={filter === "unread" ? "没有未读通知" : "还没有站内通知"}
          description="任务、退款、导出和账户安全状态确认后，会出现在这里。"
        />
      ) : null}
      {!loading && !error && notifications?.length ? (
        <ul className={styles.list}>
          {notifications.map((item) => (
            <li className={styles.item} data-unread={!item.read_at} key={item.id}>
              <div className={styles.itemHeader}>
                {item.target_href ? (
                  <Link
                    className={styles.title}
                    href={item.target_href}
                    onClick={() => void markRead(item)}
                  >
                    {item.title}
                  </Link>
                ) : (
                  <strong className={styles.title}>{item.title}</strong>
                )}
                {!item.read_at ? <span className={surface.stateTag} data-state="processing">未读</span> : null}
              </div>
              <p className={styles.summary}>{item.summary}</p>
              <div className={styles.itemFooter}>
                <time dateTime={item.available_at}>{formatDateTime(item.available_at)}</time>
                <div className={styles.actions}>
                  {!item.read_at ? (
                    <button
                      className={surface.quietButton}
                      disabled={busyId !== null}
                      onClick={() => void markRead(item)}
                      type="button"
                    >
                      {busyId === item.id ? "处理中…" : "标为已读"}
                    </button>
                  ) : null}
                  <button
                    aria-label={`删除${item.title}`}
                    className={surface.quietButton}
                    disabled={busyId !== null}
                    onClick={() => void remove(item)}
                    type="button"
                  >
                    删除
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function AccountNotificationsSurface() {
  return (
    <AccountSessionBoundary>
      <AccountSectionShell intro="查看任务、账号和订单通知。" title="通知">
        <section aria-label="通知" className={secondary.accountPanel}>
          <NotificationsContent />
        </section>
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
