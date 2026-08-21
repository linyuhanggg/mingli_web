import type { ReactNode } from "react";

import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";

import styles from "./secondary-surfaces.module.css";

type SecondarySurfaceFrameProps = {
  readonly eyebrow: string;
  readonly title: string;
  readonly intro: string;
  readonly children: ReactNode;
  readonly variant?: "default" | "auth";
};

export function SecondarySurfaceFrame({
  eyebrow,
  title,
  intro,
  children,
  variant = "default",
}: SecondarySurfaceFrameProps) {
  const auth = variant === "auth";
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={auth ? `${styles.container} ${styles.authContainer}` : styles.container}>
          <header aria-label={eyebrow} className={auth ? `${styles.header} ${styles.authHeader}` : styles.header}>
            <h1>{title}</h1>
            <p className={styles.intro}>{intro}</p>
          </header>
          <div className={auth ? `${styles.content} ${styles.authContent}` : styles.content}>{children}</div>
        </Container>
      </main>
    </PublicPageShell>
  );
}
