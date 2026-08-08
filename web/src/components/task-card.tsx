import Link from "next/link";

import styles from "./task-card.module.css";


type TaskCardProps = {
  index: string;
  title: string;
  description: string;
  eyebrow: string;
  href: string;
  action: string;
};

export function TaskCard({
  index,
  title,
  description,
  eyebrow,
  href,
  action,
}: TaskCardProps) {
  return (
    <article className={styles.card}>
      <div className={styles.topline}>
        <span>{index}</span>
        <span>{eyebrow}</span>
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      <Link href={href}>{action}</Link>
    </article>
  );
}
