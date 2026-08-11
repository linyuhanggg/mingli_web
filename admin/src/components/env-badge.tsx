import { getDeployEnv } from "@/lib/env";
import styles from "./ui.module.css";

const LABELS = {
  local: "local",
  test: "test",
  staging: "staging",
  production: "prod",
} as const;

export function EnvBadge() {
  const env = getDeployEnv();
  const className =
    env === "production" ? `${styles.env} ${styles.envProd}` : styles.env;
  return <span className={className}>{LABELS[env]}</span>;
}
