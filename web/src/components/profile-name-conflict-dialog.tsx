"use client";

import type { ProfileNameConflict } from "@/lib/profile-conflict";

import styles from "./profile-name-conflict-dialog.module.css";

export function ProfileNameConflictDialog({
  conflict,
  busy = false,
  onOverwrite,
  onSaveAs,
  onCancel,
}: Readonly<{
  conflict: ProfileNameConflict;
  busy?: boolean;
  onOverwrite: () => void;
  onSaveAs: () => void;
  onCancel: () => void;
}>) {
  const canOverwrite = conflict.options.includes("overwrite");
  const canSaveAs = conflict.options.includes("save_as");
  return (
    <div className={styles.backdrop} role="presentation">
      <div
        className={styles.dialog}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="profile-name-conflict-title"
        aria-describedby="profile-name-conflict-desc"
      >
        <h2 id="profile-name-conflict-title">档案名称已存在</h2>
        <p id="profile-name-conflict-desc">
          已有同名且同生日的档案。可以覆盖现有档案、另存为「{conflict.suggestedSaveAsName}」，或取消这次保存。
        </p>
        <div className={styles.actions}>
          {canOverwrite ? (
            <button type="button" disabled={busy} onClick={onOverwrite}>
              覆盖
            </button>
          ) : null}
          {canSaveAs ? (
            <button type="button" disabled={busy} onClick={onSaveAs}>
              另存为「{conflict.suggestedSaveAsName}」
            </button>
          ) : null}
          <button type="button" disabled={busy} onClick={onCancel}>
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
