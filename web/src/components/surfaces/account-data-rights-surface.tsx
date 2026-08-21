"use client";

import { useEffect, useState } from "react";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
import {
  cancelAccountClosure,
  exportAccountData,
  getAccountClosure,
  requestAccountClosure,
  type AccountClosure,
} from "@/lib/api";

import surface from "../app-surface.module.css";
import { StatusPanel } from "../status-panel";
import styles from "./secondary-surfaces.module.css";

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
  return "服务暂时不可用，请稍后重试。";
}

function downloadExport(payload: Record<string, unknown>): void {
  if (typeof URL.createObjectURL !== "function") return;
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `mingli-data-export-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function DataRightsContent() {
  const { state } = useAccountSession();
  const userId = state.status === "signedIn" ? state.account.user_id : null;
  const [closure, setClosure] = useState<AccountClosure | null>(null);
  const [loadingClosure, setLoadingClosure] = useState(true);
  const [loadedUserId, setLoadedUserId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportReady, setExportReady] = useState(false);

  useEffect(() => {
    if (!userId) return;

    let active = true;
    void getAccountClosure()
      .then((next) => {
        if (active) {
          setClosure(next);
          setLoadedUserId(userId);
          setError(null);
        }
      })
      .catch((nextError: unknown) => {
        if (active) {
          setLoadedUserId(userId);
          setError(readableError(nextError));
        }
      })
      .finally(() => {
        if (active) setLoadingClosure(false);
      });

    return () => {
      active = false;
    };
  }, [userId]);

  if (state.status === "checking") {
    return <StatusPanel state="loading" title="正在确认账户…" description="正在确认数据权利访问权限。" />;
  }

  if (state.status === "error") {
    return <StatusPanel state="error" title="无法确认账户" description={state.message} />;
  }

  if (state.status === "signedOut") {
    return (
      <StatusPanel
        actionHref="/auth/login"
        actionLabel="前往登录"
        state="disabled"
        title="需要登录"
        description="登录后才能导出资料或管理注销申请。"
      />
    );
  }

  async function handleExport() {
    setBusy(true);
    setError(null);
    setExportReady(false);
    try {
      const exported = await exportAccountData();
      downloadExport(exported);
      setExportReady(true);
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function handleRequestClosure() {
    if (!window.confirm("注销申请会进入 7 天可撤销期，确认继续吗？")) return;
    setBusy(true);
    setError(null);
    try {
      setClosure(await requestAccountClosure());
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancelClosure() {
    setBusy(true);
    setError(null);
    try {
      await cancelAccountClosure();
      setClosure(null);
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section aria-labelledby="data-export-title" className={surface.paper}>
        <div className={surface.sectionHeader}>
          <div>
            <h2 id="data-export-title">数据导出</h2>
            <p>导出一份你的账户资料。</p>
          </div>
        </div>
        <button className={surface.button} disabled={busy} onClick={() => void handleExport()} type="button">
          {busy ? "正在准备…" : "导出我的数据"}
        </button>
        {exportReady ? (
          <StatusPanel
            state="success"
            title="数据导出已准备"
            description="下载已触发；页面只保留完成状态，不保留导出正文。"
          />
        ) : null}
      </section>

      <section aria-labelledby="account-closure-title" className={surface.paper}>
        <div className={surface.sectionHeader}>
          <div>
            <h2 id="account-closure-title">账号注销</h2>
            <p>注销申请先进入 7 天撤销期；在期限内可以撤销，执行由后台队列处理。</p>
          </div>
        </div>
        {loadingClosure || loadedUserId !== userId ? (
          <p role="status">正在读取注销状态…</p>
        ) : null}
        {!loadingClosure && loadedUserId === userId && closure ? (
          <>
            <p>注销申请已提交，可撤销至 {formatDateTime(closure.cancel_until)}。</p>
            <button
              className={surface.secondaryButton}
              disabled={busy}
              onClick={() => void handleCancelClosure()}
              type="button"
            >
              撤销注销申请
            </button>
          </>
        ) : null}
        {!loadingClosure && loadedUserId === userId && !closure ? (
          <button
            className={surface.secondaryButton}
            disabled={busy}
            onClick={() => void handleRequestClosure()}
            type="button"
          >
            申请注销账号
          </button>
        ) : null}
      </section>

      {error ? <p role="alert">操作失败：{error}</p> : null}
    </>
  );
}

export function AccountDataRightsSurface({
  title = "隐私与数据",
}: {
  readonly title?: string;
}) {
  return (
    <AccountSessionBoundary>
      <AccountSectionShell intro="导出资料，或申请注销账号。" title={title}>
        <section aria-label="隐私与数据" className={styles.accountPanel}>
          <DataRightsContent />
        </section>
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
