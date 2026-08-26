import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Inbox,
  Loader2,
  LockKeyhole,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useId, type MouseEventHandler } from "react";

import styles from "./status-panel.module.css";


export type StatusPanelState =
  | "loading"
  | "empty"
  | "error"
  | "processing"
  | "success"
  | "disabled";

type StatusPanelProps = {
  state: StatusPanelState;
  title?: string;
  description?: string;
  actionHref?: string;
  actionLabel?: string;
  actionOnClick?: MouseEventHandler<HTMLAnchorElement>;
};

type StatusDefinition = {
  title: string;
  description: string;
  icon: LucideIcon;
};

const statusDefinitions: Record<StatusPanelState, StatusDefinition> = {
  loading: {
    title: "正在载入…",
    description: "内容正在抵达，请稍候。",
    icon: Loader2,
  },
  empty: {
    title: "这里还没有内容",
    description: "完成第一步后，新的记录会显示在这里。",
    icon: Inbox,
  },
  error: {
    title: "暂时无法完成",
    description: "这次请求没有成功。请重试，或返回上一步检查输入。",
    icon: AlertCircle,
  },
  processing: {
    title: "正在处理中…",
    description: "请求已经收到，但结果尚未完成，请稍候查看最新状态。",
    icon: Clock3,
  },
  success: {
    title: "已经完成",
    description: "这一步已顺利完成，你可以继续下一项。",
    icon: CheckCircle2,
  },
  disabled: {
    title: "暂不可用",
    description: "当前所需条件尚未满足，因此这个入口暂时不能使用。",
    icon: LockKeyhole,
  },
};

export function StatusPanel({
  state,
  title,
  description,
  actionHref,
  actionLabel,
  actionOnClick,
}: StatusPanelProps) {
  const headingId = useId();
  const descriptionId = useId();
  const definition = statusDefinitions[state];
  const Icon = definition.icon;
  const resolvedTitle = title ?? definition.title;
  const resolvedDescription = description ?? definition.description;
  const isBusy = state === "loading" || state === "processing";
  return (
    <section
      aria-atomic="true"
      aria-busy={isBusy || undefined}
      aria-describedby={descriptionId}
      aria-labelledby={headingId}
      className={`${styles.panel} ${styles[state]}`}
      data-state={state}
      role={state === "error" ? "alert" : "status"}
    >
      <span aria-hidden="true" className={styles.icon}>
        <Icon aria-hidden="true" size={26} strokeWidth={1.75} />
      </span>

      <div className={styles.content}>
        <h2 className={styles.title} id={headingId}>
          {resolvedTitle}
        </h2>
        <p className={styles.description} id={descriptionId}>
          {resolvedDescription}
        </p>

        {actionHref && actionLabel ? (
          <Link className={styles.action} href={actionHref} onClick={actionOnClick}>
            <span>{actionLabel}</span>
            <ArrowRight aria-hidden="true" size={18} strokeWidth={1.75} />
          </Link>
        ) : null}
      </div>
    </section>
  );
}
