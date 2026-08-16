"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminSettings, AdminSettingsResponse } from "@/lib/admin-settings";

import styles from "./admin-settings-surface.module.css";

function enabledCopy(value: boolean): string {
  return value ? "已开启" : "已关闭";
}

function SettingsDetails({ data }: { data: AdminSettings }) {
  return (
    <dl className={styles.details}>
      <div>
        <dt>运行环境</dt>
        <dd>{data.environment}</dd>
      </div>
      <div>
        <dt>Cookie Secure</dt>
        <dd>{enabledCopy(data.cookie_secure)}</dd>
      </div>
      <div>
        <dt>OTP 适配器</dt>
        <dd>{data.otp_adapter}</dd>
      </div>
      <div>
        <dt>Runtime 适配器</dt>
        <dd>{data.runtime_adapter}</dd>
      </div>
      <div>
        <dt>Admin 会话时长</dt>
        <dd>{data.admin_session_hours} 小时</dd>
      </div>
      <div>
        <dt>Dogfood 权益闸门</dt>
        <dd>{enabledCopy(data.dogfood_entitlement_gates_enabled)}</dd>
      </div>
      <div>
        <dt>真实流量</dt>
        <dd>{enabledCopy(data.real_traffic_enabled)}</dd>
      </div>
      <div>
        <dt>告警 Sink</dt>
        <dd>{enabledCopy(data.alert_sink_enabled)}</dd>
      </div>
    </dl>
  );
}

export function AdminSettingsSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<"loading" | "ready" | "error" | "forbidden" | "unavailable">("loading");
  const [data, setData] = useState<AdminSettingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminSettingsResponse>("/api/v1/admin/settings");
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
      setState("ready");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取系统设置…" description="只显示服务端允许展示的非敏感运行标志。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="系统设置只允许超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="系统设置暂不可用" description="页面不显示本地猜测或过期配置。" />
    ) : state === "error" ? (
      <Status state="error" title="系统设置读取失败" description={error ?? "请求失败，请重试。"} />
    ) : (
      <Status state="success" title="系统设置已接入" description="本页只读；数据库 URL、密钥、模型端点和密码不会返回。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      <section className={styles.panel} aria-labelledby="settings-title">
        <div className={styles.heading}>
          <div>
            <h2 id="settings-title">系统设置面</h2>
            <p>用于核对环境、会话、OTP、Runtime、流量和告警开关；当前不提供在线修改。</p>
          </div>
          <span className={styles.badge}>只读 / 无秘密</span>
        </div>
        {state === "ready" && data ? (
          <SettingsDetails data={data} />
        ) : (
          <dl className={styles.details}>
            <div>
              <dt>配置来源</dt>
              <dd>系统设置服务尚未返回</dd>
            </div>
            <div>
              <dt>当前结论</dt>
              <dd>不显示本地猜测或过期配置</dd>
            </div>
          </dl>
        )}
      </section>
    </div>
  );
}
