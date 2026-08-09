"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";

import { createFollowUp } from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import styles from "./follow-up-form.module.css";

export function FollowUpForm({
  readingId,
}: Readonly<{ readingId: string }>) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const queryRef = useRef<HTMLInputElement | null>(null);
  const intentKeyRef = useRef<IntentKey | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busyRef.current) return;

    const trimmed = query.trim();
    if (!trimmed) {
      setError("请先写下要追问的问题。");
      queryRef.current?.focus();
      return;
    }

    const payload = { query: trimmed };
    const intent = stableKeyForIntent(intentKeyRef.current, payload);
    intentKeyRef.current = intent;
    busyRef.current = true;
    setBusy(true);
    setError(null);
    try {
      const started = await createFollowUp(readingId, trimmed, intent.key);
      router.push(`/app/readings/${started.reading_version_id}`);
    } catch (reason) {
      setError(
        reason instanceof Error && reason.message
          ? reason.message
          : "追问发起失败，请稍后重试。",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  return (
    <div className={styles.section}>
      <p className={styles.hint}>
        基于当前已接纳结论继续追问，不改变原盘面。
      </p>
      <form className={styles.formRow} onSubmit={handleSubmit} noValidate aria-busy={busy}>
        <label className={styles.srOnly} htmlFor="follow-up-query">
          追问
        </label>
        <input
          ref={queryRef}
          id="follow-up-query"
          className={styles.input}
          name="follow_up_query"
          type="text"
          autoComplete="off"
          maxLength={300}
          placeholder="例如：换工作方向该怎样缩小范围？"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            if (error) setError(null);
          }}
          disabled={busy}
          required
          aria-required="true"
          aria-invalid={error ? "true" : undefined}
          aria-describedby={error ? "follow-up-error" : "follow-up-hint"}
        />
        <span className={styles.srOnly} id="follow-up-hint">
          按 Enter 即可发起追问
        </span>
        <button
          type="submit"
          className={styles.submit}
          disabled={busy}
          aria-busy={busy}
        >
          发起追问{busy ? " · 正在发起…" : ""}
        </button>
      </form>
      {error ? (
        <p className={styles.error} id="follow-up-error" role="alert" aria-live="polite">
          {error}
        </p>
      ) : null}
      <p className={styles.recast}>
        <Link className={styles.recastLink} href="/app">
          重新起卦或重新起盘
        </Link>
      </p>
    </div>
  );
}
