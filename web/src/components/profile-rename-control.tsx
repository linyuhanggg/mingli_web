"use client";

import { useEffect, useId, useRef, useState } from "react";

import { updateProfileDisplayName, type ProfileSummary } from "@/lib/api";

import formControls from "./form-controls.module.css";
import styles from "./profile-rename-control.module.css";
import { Button, type ButtonState } from "./ui";

const SAVE_FEEDBACK_MS = 220;

export function ProfileRenameControl({
  profile,
  onRenamed,
}: Readonly<{
  profile: ProfileSummary;
  onRenamed?: (next: ProfileSummary) => void;
}>) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(profile.display_name ?? "");
  const [saveState, setSaveState] = useState<ButtonState>("idle");
  const [error, setError] = useState("");
  const inputId = useId();
  const errorId = `${inputId}-error`;
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const restoreFocusRef = useRef(false);
  const feedbackTimerRef = useRef<number | null>(null);
  const mountedRef = useRef(false);
  const busy = saveState === "loading";
  const locked = busy || saveState === "success";

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (feedbackTimerRef.current !== null) {
        window.clearTimeout(feedbackTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus({ preventScroll: true });
    } else if (restoreFocusRef.current) {
      triggerRef.current?.focus({ preventScroll: true });
      restoreFocusRef.current = false;
    }
  }, [open]);

  useEffect(() => {
    if (error && saveState === "error") {
      inputRef.current?.focus({ preventScroll: true });
    }
  }, [error, saveState]);

  function clearFeedbackTimer() {
    if (feedbackTimerRef.current !== null) {
      window.clearTimeout(feedbackTimerRef.current);
      feedbackTimerRef.current = null;
    }
  }

  function scheduleIdleState() {
    clearFeedbackTimer();
    feedbackTimerRef.current = window.setTimeout(() => {
      setSaveState((current) => (current === "error" ? "idle" : current));
      feedbackTimerRef.current = null;
    }, SAVE_FEEDBACK_MS);
  }

  function closeEditor() {
    clearFeedbackTimer();
    restoreFocusRef.current = true;
    setError("");
    setSaveState("idle");
    setOpen(false);
  }

  async function handleSave() {
    if (locked) return;
    const nextName = value.trim();
    if (!nextName) {
      setError("请填写档案名称");
      setSaveState("error");
      scheduleIdleState();
      return;
    }
    clearFeedbackTimer();
    setSaveState("loading");
    setError("");
    try {
      const next = await updateProfileDisplayName(profile.profile_id, nextName);
      if (!mountedRef.current) return;
      onRenamed?.(next);
      setSaveState("success");
      feedbackTimerRef.current = window.setTimeout(() => {
        restoreFocusRef.current = true;
        setSaveState("idle");
        setOpen(false);
        feedbackTimerRef.current = null;
      }, SAVE_FEEDBACK_MS);
    } catch (reason) {
      if (!mountedRef.current) return;
      setError(reason instanceof Error ? reason.message : "重命名失败，请稍后重试。");
      setSaveState("error");
      scheduleIdleState();
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className={styles.trigger}
        ref={triggerRef}
        onClick={() => {
          clearFeedbackTimer();
          setValue(profile.display_name ?? "");
          setError("");
          setSaveState("idle");
          setOpen(true);
        }}
      >
        重命名
      </button>
    );
  }

  return (
    <form
      aria-busy={busy || undefined}
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        void handleSave();
      }}
    >
      <label className={formControls.field} htmlFor={inputId}>
        档案名称
        <input
          aria-describedby={error ? errorId : undefined}
          aria-invalid={error ? "true" : undefined}
          className={formControls.input}
          disabled={locked}
          id={inputId}
          ref={inputRef}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            if (error) setError("");
            if (saveState === "error") {
              clearFeedbackTimer();
              setSaveState("idle");
            }
          }}
        />
      </label>
      {error ? (
        <p className={styles.error} id={errorId} role="alert">
          {error}
        </p>
      ) : null}
      <div className={styles.actions}>
        <Button
          className={styles.saveButton}
          disabled={locked}
          errorLabel="保存失败"
          loadingLabel="正在保存名称…"
          state={saveState}
          successLabel="名称已保存"
          type="submit"
        >
          保存名称
        </Button>
        <button
          className={styles.cancel}
          disabled={locked}
          type="button"
          onClick={closeEditor}
        >
          取消
        </button>
      </div>
    </form>
  );
}
