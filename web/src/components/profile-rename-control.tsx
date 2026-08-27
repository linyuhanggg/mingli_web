"use client";

import { useState } from "react";

import { updateProfileDisplayName, type ProfileSummary } from "@/lib/api";

import formControls from "./form-controls.module.css";
import styles from "./profile-rename-control.module.css";

export function ProfileRenameControl({
  profile,
  onRenamed,
}: Readonly<{
  profile: ProfileSummary;
  onRenamed?: (next: ProfileSummary) => void;
}>) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(profile.display_name ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    const nextName = value.trim();
    if (!nextName) {
      setError("请填写档案名称");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const next = await updateProfileDisplayName(profile.profile_id, nextName);
      onRenamed?.(next);
      setOpen(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "重命名失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className={styles.trigger}
        onClick={() => {
          setValue(profile.display_name ?? "");
          setError("");
          setOpen(true);
        }}
      >
        重命名
      </button>
    );
  }

  return (
    <div className={styles.form}>
      <label className={formControls.field} htmlFor={`rename-${profile.profile_id}`}>
        档案名称
        <input
          id={`rename-${profile.profile_id}`}
          className={formControls.input}
          value={value}
          disabled={busy}
          onChange={(event) => setValue(event.target.value)}
        />
      </label>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
      <div className={styles.actions}>
        <button type="button" disabled={busy} onClick={() => void handleSave()}>
          保存名称
        </button>
        <button type="button" disabled={busy} onClick={() => setOpen(false)}>
          取消
        </button>
      </div>
    </div>
  );
}
