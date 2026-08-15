"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ApiError, recordConsent } from "@/lib/api";
import { CURRENT_POLICY_VERSION } from "@/lib/policy";

import styles from "./surfaces/secondary-surfaces.module.css";

export function ConsentForm() {
  const router = useRouter();
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!privacyAccepted || !termsAccepted) {
      setError("请分别阅读并同意隐私政策和服务条款。");
      return;
    }

    setBusy(true);
    setError("");
    try {
      for (const policy_key of ["privacy", "terms"] as const) {
        await recordConsent({
          policy_key,
          policy_version: CURRENT_POLICY_VERSION,
          context: "reaccept",
        });
      }
      router.replace("/account");
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 401
          ? "请先登录后再确认政策。"
          : "政策确认服务暂时不可用，请稍后重试。",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      aria-busy={busy}
      aria-describedby="consent-help"
      aria-label="政策确认"
      className={styles.form}
      onSubmit={submit}
      noValidate
    >
      <p className={styles.field} id="consent-help">
        当前记录版本：开发预览 v0.1；隐私政策和服务条款分别保存，不使用一个模糊总开关。
      </p>
      <div className={styles.fields}>
        <label>
          <input
            checked={privacyAccepted}
            disabled={busy}
            onChange={(event) => setPrivacyAccepted(event.target.checked)}
            type="checkbox"
          />
          我已阅读并同意隐私政策
        </label>
        <label>
          <input
            checked={termsAccepted}
            disabled={busy}
            onChange={(event) => setTermsAccepted(event.target.checked)}
            type="checkbox"
          />
          我已阅读并同意服务条款
        </label>
      </div>
      {error ? <p className={styles.disabledReason} role="alert">{error}</p> : null}
      <button disabled={busy || !privacyAccepted || !termsAccepted} type="submit">
        {busy ? "正在保存…" : "确认并保存"}
      </button>
    </form>
  );
}
