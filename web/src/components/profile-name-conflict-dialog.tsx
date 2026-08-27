"use client";

import { Dialog as DialogPrimitive } from "radix-ui";
import { useEffect, useRef } from "react";

import type { ProfileNameConflict } from "@/lib/profile-conflict";

import dialogStyles from "./ui/dialog.module.css";
import styles from "./profile-name-conflict-dialog.module.css";

export function ProfileNameConflictDialog({
  conflict,
  busy = false,
  onOverwrite,
  onSaveAs,
  onCancel,
}: Readonly<{
  conflict: ProfileNameConflict | null;
  busy?: boolean;
  onOverwrite: () => void;
  onSaveAs: () => void;
  onCancel: () => void;
}>) {
  const firstActionRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const canOverwrite = conflict?.options.includes("overwrite") ?? false;
  const canSaveAs = conflict?.options.includes("save_as") ?? false;

  useEffect(() => {
    function handleFocusIn(event: FocusEvent) {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest('[role="alertdialog"]')) return;
      triggerRef.current = target;
    }
    document.addEventListener("focusin", handleFocusIn, true);
    return () => document.removeEventListener("focusin", handleFocusIn, true);
  }, []);

  function restoreTrigger() {
    triggerRef.current?.focus();
  }

  return (
    <DialogPrimitive.Root
      open={conflict !== null}
      onOpenChange={(open) => {
        if (!open) {
          restoreTrigger();
          onCancel();
        }
      }}
    >
      {conflict ? (
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className={dialogStyles.overlay} />
          <DialogPrimitive.Content
            aria-describedby="profile-name-conflict-desc"
            aria-labelledby="profile-name-conflict-title"
            className={`${dialogStyles.content} ${styles.dialog}`}
            role="alertdialog"
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              restoreTrigger();
            }}
            onOpenAutoFocus={(event) => {
              event.preventDefault();
              queueMicrotask(() => firstActionRef.current?.focus());
            }}
          >
            <DialogPrimitive.Title className={dialogStyles.title} id="profile-name-conflict-title">
              档案名称已存在
            </DialogPrimitive.Title>
            <DialogPrimitive.Description className={dialogStyles.description} id="profile-name-conflict-desc">
              已有同名且同生日的档案。可以覆盖现有档案、另存为「{conflict.suggestedSaveAsName}」，或取消这次保存。
            </DialogPrimitive.Description>
            <div className={styles.actions}>
              {canOverwrite ? (
                <button
                  ref={firstActionRef}
                  disabled={busy}
                  type="button"
                  onClick={onOverwrite}
                >
                  覆盖
                </button>
              ) : null}
              {canSaveAs ? (
                <button
                  ref={canOverwrite ? undefined : firstActionRef}
                  disabled={busy}
                  type="button"
                  onClick={onSaveAs}
                >
                  另存为「{conflict.suggestedSaveAsName}」
                </button>
              ) : null}
              <button
                ref={canOverwrite || canSaveAs ? undefined : firstActionRef}
                disabled={busy}
                type="button"
                onClick={onCancel}
              >
                取消
              </button>
            </div>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      ) : null}
    </DialogPrimitive.Root>
  );
}
