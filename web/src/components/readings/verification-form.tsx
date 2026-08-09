"use client";

import { useRef, useState, type FormEvent } from "react";

import {
  verifyReading,
  type ReadingVerificationSummary,
  type VerificationOutcome,
} from "@/lib/api";

import styles from "./verification-form.module.css";

const OUTCOMES: { value: VerificationOutcome; label: string }[] = [
  { value: "accepted", label: "符合" },
  { value: "partial", label: "部分符合" },
  { value: "disagreed", label: "不符合" },
  { value: "unknown", label: "暂时不知道" },
];

function outcomeLabel(outcome: VerificationOutcome): string {
  return OUTCOMES.find((item) => item.value === outcome)?.label ?? outcome;
}

export function VerificationForm({
  readingId,
  initialVerification = null,
  onVerified,
}: Readonly<{
  readingId: string;
  initialVerification?: ReadingVerificationSummary | null;
  onVerified?: () => void;
}>) {
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<ReadingVerificationSummary | null>(
    initialVerification,
  );
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<VerificationOutcome>("accepted");
  const [note, setNote] = useState("");
  const busyRef = useRef(false);

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError(null);
    try {
      const verification = await verifyReading(readingId, outcome, note);
      setSaved(verification);
      onVerified?.();
    } catch (reason) {
      setError(
        reason instanceof Error && reason.message
          ? reason.message
          : "核对结果保存失败，请稍后重试。",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  return (
    <div className={styles.section}>
      {saved ? (
        <div className={styles.success} role="status" aria-live="polite">
          <p className={styles.successTitle}>已保存核对结果</p>
          <p>已保存：{outcomeLabel(saved.outcome)}</p>
          {saved.note ? <p className={styles.savedNote}>{saved.note}</p> : null}
        </div>
      ) : (
        <form onSubmit={handleVerify} noValidate aria-busy={busy}>
          <fieldset className={styles.fieldset}>
            <legend className={styles.legend}>
              以下判断与你的现实情况是否相符？
            </legend>
            <div className={styles.outcomes}>
              {OUTCOMES.map((option) => (
                <label className={styles.optionLabel} key={option.value}>
                  <input
                    className={styles.optionInput}
                    type="radio"
                    name="verification_outcome"
                    value={option.value}
                    checked={outcome === option.value}
                    onChange={() => setOutcome(option.value)}
                    disabled={busy}
                    required
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
          <div className={styles.noteField}>
            <label className={styles.noteLabel} htmlFor="verification-note">
              补充说明（可选）
            </label>
            <textarea
              className={styles.note}
              id="verification-note"
              name="verification_note"
              rows={2}
              maxLength={500}
              autoComplete="off"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              disabled={busy}
            />
          </div>
          <button
            type="submit"
            className={styles.button}
            disabled={busy}
            aria-busy={busy}
          >
            提交核对结果{busy ? " · 正在提交…" : ""}
          </button>
          {error ? (
            <p className={styles.error} role="alert" aria-live="polite">
              {error}
            </p>
          ) : null}
        </form>
      )}
    </div>
  );
}
