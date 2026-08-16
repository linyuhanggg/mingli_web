import type { ReactNode } from "react";

import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";

import styles from "./secondary-surfaces.module.css";

type SecondarySurfaceFrameProps = {
  readonly eyebrow: string;
  readonly title: string;
  readonly intro: string;
  readonly children: ReactNode;
};

export function SecondarySurfaceFrame({
  eyebrow,
  title,
  intro,
  children,
}: SecondarySurfaceFrameProps) {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <header aria-label={eyebrow} className={styles.header}>
            <h1>{title}</h1>
            <p className={styles.intro}>{intro}</p>
          </header>
          <div className={styles.content}>{children}</div>
        </Container>
      </main>
    </PublicPageShell>
  );
}
