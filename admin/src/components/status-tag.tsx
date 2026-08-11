import styles from "./ui.module.css";

type Tone = "pending" | "success" | "error" | "neutral";

const TONE_CLASS: Record<Tone, string> = {
  pending: styles.tagPending,
  success: styles.tagSuccess,
  error: styles.tagError,
  neutral: styles.tagNeutral,
};

export function StatusTag({
  tone,
  children,
}: {
  tone: Tone;
  children: string;
}) {
  return <span className={`${styles.tag} ${TONE_CLASS[tone]}`}>{children}</span>;
}
