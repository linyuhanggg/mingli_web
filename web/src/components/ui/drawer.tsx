"use client";

import clsx from "clsx";
import { Dialog as DialogPrimitive } from "radix-ui";
import type { ReactNode } from "react";

import styles from "./drawer.module.css";


export type DrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  side?: "bottom" | "right";
  contentClassName?: string;
  /** Required: owns the element that focus returns to when the drawer closes. */
  trigger: ReactNode;
  children: ReactNode;
};

export function Drawer({
  open,
  onOpenChange,
  title,
  description,
  side = "bottom",
  contentClassName,
  trigger,
  children,
}: DrawerProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={styles.overlay} />
        <DialogPrimitive.Content className={clsx(styles.content, styles[side], contentClassName)}>
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
