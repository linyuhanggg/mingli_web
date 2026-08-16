"use client";

import clsx from "clsx";
import { Dialog as DialogPrimitive } from "radix-ui";
import type { ReactNode, RefObject } from "react";

import styles from "./drawer.module.css";


export type DrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  side?: "bottom" | "right";
  /** Owns the element that focus returns to when the drawer closes. */
  trigger?: ReactNode;
  /** For controlled drawers opened by an external control such as a table row action. */
  restoreFocusRef?: RefObject<HTMLElement | null>;
  children: ReactNode;
};

export function Drawer({
  open,
  onOpenChange,
  title,
  description,
  side = "bottom",
  trigger,
  restoreFocusRef,
  children,
}: DrawerProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      {trigger ? <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger> : null}
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={styles.overlay} />
        <DialogPrimitive.Content
          className={clsx(styles.content, styles[side])}
          onCloseAutoFocus={(event) => {
            if (!restoreFocusRef?.current) return;
            event.preventDefault();
            restoreFocusRef.current.focus();
          }}
        >
          <div className={styles.header}>
            <DialogPrimitive.Title className={styles.title}>{title}</DialogPrimitive.Title>
            {description ? (
              <DialogPrimitive.Description className={styles.description}>
                {description}
              </DialogPrimitive.Description>
            ) : (
              <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
            )}
          </div>
          <DialogPrimitive.Close className={styles.close} aria-label="关闭">
            ×
          </DialogPrimitive.Close>
          <div className={styles.body}>{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
