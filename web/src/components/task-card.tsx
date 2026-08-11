import Link from "next/link";

import styles from "./task-card.module.css";


type TaskCardProps = {
  title: string;
  description: string;
  label: string;
  href: string;
  action: string;
  tone: "paper" | "ink" | "clay";
};

export function TaskCard({
  title,
  description,
  label,
  href,
  action,
  tone,
}: TaskCardProps) {
  return (
    <article className={styles.card} data-tone={tone}>
      <h3>{title}</h3>
      <p>{description}</p>
      <span className={styles.label}>{label}</span>
      <Link className={styles.action} href={href}>
        <span>{action}</span>
        <span aria-hidden="true" className={styles.arrow}>
          →
        </span>
      </Link>
    </article>
  );
}
