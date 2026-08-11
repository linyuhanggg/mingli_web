"use client";

import { useRef, useState, type FormEvent } from "react";

import {
  verifyReading,
  type ReadingFact,
  type ReadingVerificationSummary,
  type VerificationOutcome,
} from "@/lib/api";

import styles from "./verification-form.module.css";

const REQUIRED_RESULT_COUNT = 3;

const OUTCOMES: { value: VerificationOutcome; label: string }[] = [
  { value: "accepted", label: "符合" },
  { value: "partial", label: "部分符合" },
  { value: "disagreed", label: "不符合" },
  { value: "unknown", label: "暂时不知道" },
];

function outcomeLabel(outcome: VerificationOutcome): string {
  return OUTCOMES.find((item) => item.value === outcome)?.label ?? outcome;
}

function factLabel(fact: ReadingFact): string {
  return fact.display_text || fact.ref;
}

export function VerificationForm({
  readingId,
  facts,
  initialVerification = null,
  onVerified,
}: Readonly<{
  readingId: string;
  facts: ReadingFact[];
  initialVerification?: ReadingVerificationSummary | null;
  onVerified?: () => void;
}>) {
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<ReadingVerificationSummary | null>(
    initialVerification,
  );
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const busyRef = useRef(false);

  const judgedFacts = facts.slice(0, REQUIRED_RESULT_COUNT);
  const labelsByRef = new Map(facts.map((fact) => [fact.ref, factLabel(fact)]));

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busyRef.current) return;
    const data = new FormData(event.currentTarget);
    const results = judgedFacts.map((fact, index) => ({
      fact_ref: fact.ref,
      outcome: String(
        data.get(`verification_outcome_${index}`) ?? "",
      ) as VerificationOutcome,
    }));
    busyRef.current = true;
    setBusy(true);
    setError(null);
    try {
      const verification = await verifyReading(readingId, results, note);
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
          <ul className={styles.savedResults}>
            {saved.results.map((item) => (
              <li key={item.fact_ref}>
                {labelsByRef.get(item.fact_ref) ?? item.fact_ref}：
                {outcomeLabel(item.outcome)}
              </li>
            ))}
          </ul>
          {saved.note ? <p className={styles.savedNote}>{saved.note}</p> : null}
        </div>
      ) : judgedFacts.length < REQUIRED_RESULT_COUNT ? (
        <p className={styles.insufficient}>
          可用于核对的公开事实不足三条，本次不收集核对结果；解读正文与事实仍可正常回看。
        </p>
      ) : (
        <form onSubmit={handleVerify} aria-busy={busy}>
          <p className={styles.legend}>
            以下三条事实与你的现实情况是否相符？每条独立核对，反馈不会改写盘面。
          </p>
          {judgedFacts.map((fact, index) => (
            <fieldset className={styles.fieldset} key={fact.ref}>
              <legend className={styles.factLegend}>{factLabel(fact)}</legend>
              <div className={styles.outcomes}>
                {OUTCOMES.map((option) => (
                  <label className={styles.optionLabel} key={option.value}>
                    <input
                      className={styles.optionInput}
                      type="radio"
                      name={`verification_outcome_${index}`}
                      value={option.value}
                      disabled={busy}
                      required
                    />
                    {option.label}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
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
