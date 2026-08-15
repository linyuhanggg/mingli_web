"use client";

import { useEffect, useState } from "react";

import {
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationPreferences,
} from "@/lib/api";

import { useAccountSession } from "./account-session-context";
import surface from "./app-surface.module.css";
import { StatusPanel } from "./status-panel";
import styles from "./surfaces/secondary-surfaces.module.css";

function readableError(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message) return message;
  }
  return "服务暂时不可用，请稍后重试。";
}

const defaultPreferences: NotificationPreferences = {
  in_app_enabled: true,
  email_enabled: false,
  sms_enabled: false,
};

export default function NotificationPreferencesForm() {
  const { state } = useAccountSession();
  const userId = state.status === "signedIn" ? state.account.user_id : null;
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [loadedUserId, setLoadedUserId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!userId) return;

    let active = true;
    void getNotificationPreferences()
      .then((next) => {
        if (active) {
          setPreferences(next);
          setLoadedUserId(userId);
          setError("");
        }
      })
      .catch((nextError: unknown) => {
        if (active) {
          setLoadedUserId(userId);
          setError(readableError(nextError));
        }
      });

    return () => {
      active = false;
    };
  }, [userId]);

  if (state.status === "checking") {
    return <StatusPanel state="loading" title="正在确认账户…" description="正在确认当前设备会话。" />;
  }

  if (state.status === "signedOut") {
    return (
      <StatusPanel
        actionHref="/auth/login"
        actionLabel="前往登录"
        state="disabled"
        title="需要登录"
        description="登录后才能读取或修改通知偏好。"
      />
    );
  }

  if (state.status === "error") {
    return <StatusPanel state="error" title="无法确认账户" description={state.message} />;
  }

  if (userId !== loadedUserId || !preferences) {
    return <StatusPanel state="loading" title="正在读取通知偏好…" description="不会读取其他账户的设置。" />;
  }

  const currentPreferences = preferences;

  async function save() {
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const updated = await updateNotificationPreferences(currentPreferences);
      setPreferences(updated);
      setSaved(true);
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusy(false);
    }
  }

  function setChannel(channel: keyof NotificationPreferences, enabled: boolean) {
    setPreferences((current) => ({
      ...(current ?? defaultPreferences),
      [channel]: enabled,
    }));
    setSaved(false);
  }

  return (
    <section aria-labelledby="notification-preferences-title" className={surface.paper}>
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="notification-preferences-title">通知偏好</h2>
          <p>站内通知默认开启；邮件和短信只有在你明确打开后才会进入 Outbox。</p>
        </div>
      </div>
      <fieldset className={styles.choiceList} disabled={busy}>
        <legend className="sr-only">可选通知渠道</legend>
        <label className={styles.choice} htmlFor="notification-in-app">
          <input
            checked={preferences.in_app_enabled}
            id="notification-in-app"
            onChange={(event) => setChannel("in_app_enabled", event.target.checked)}
            type="checkbox"
          />
          <span>
            <strong>站内通知</strong>
            <small>保留任务、退款、导出和账号安全等重要状态。</small>
          </span>
        </label>
        <label className={styles.choice} htmlFor="notification-email">
          <input
            checked={preferences.email_enabled}
            id="notification-email"
            onChange={(event) => setChannel("email_enabled", event.target.checked)}
            type="checkbox"
          />
          <span>
            <strong>邮件通知</strong>
            <small>仅在你打开后允许邮件类通知进入 Outbox，供应商投递仍由服务端适配器负责。</small>
          </span>
        </label>
        <label className={styles.choice} htmlFor="notification-sms">
          <input
            checked={preferences.sms_enabled}
            id="notification-sms"
            onChange={(event) => setChannel("sms_enabled", event.target.checked)}
            type="checkbox"
          />
          <span>
            <strong>短信通知</strong>
            <small>仅在你打开后允许短信类通知进入 Outbox，不代表供应商已经发送。</small>
          </span>
        </label>
      </fieldset>
      {error ? <p role="alert">保存失败：{error}</p> : null}
      {saved ? <p role="status">通知偏好已保存</p> : null}
      <div className={surface.actionRow}>
        <button className={surface.button} disabled={busy} onClick={() => void save()} type="button">
          {busy ? "正在保存…" : "保存通知偏好"}
        </button>
      </div>
    </section>
  );
}
