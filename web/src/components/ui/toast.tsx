import clsx from "clsx";
import { AlertCircle, CheckCircle2, Info, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import styles from "./toast.module.css";

export type ToastTone = "neutral" | "success" | "error";

export type ToastProps = {
  title: string;
  description?: ReactNode;
  tone?: ToastTone;
  className?: string;
};

const icons: Readonly<Record<ToastTone, LucideIcon>> = {
  neutral: Info,
  success: CheckCircle2,
  error: AlertCircle,
};

export function Toast({
  title,
  description,
  tone = "neutral",
  className,
}: ToastProps) {
  const Icon = icons[tone];

  return (
    <div
      aria-atomic="true"
      aria-live="polite"
      className={clsx(styles.toast, className)}
      data-tone={tone}
      role="status"
    >
      <span aria-hidden="true" className={styles.icon}>
        <Icon aria-hidden="true" size={18} strokeWidth={1.8} />
      </span>
      <div className={styles.copy}>
        <p className={styles.title}>{title}</p>
        {description ? <div className={styles.description}>{description}</div> : null}
      </div>
    </div>
  );
}
