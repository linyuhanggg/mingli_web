import type { ReactNode } from "react";

import { Container } from "./container";
import styles from "./editorial-page.module.css";
import { PublicPageShell } from "./public-page-shell";


type EditorialPageProps = {
  eyebrow: string;
  title: string;
  intro: string;
  children: ReactNode;
};

export function EditorialPage({ eyebrow, title, intro, children }: EditorialPageProps) {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container>
          <header className={styles.hero}>
            <div className={styles.heroCopy}>
              <h1>{title}</h1>
              <p className={styles.folio}>{eyebrow}</p>
            </div>
            <p className={styles.intro}>{intro}</p>
          </header>
          <div className={styles.content}>{children}</div>
        </Container>
      </main>
    </PublicPageShell>
  );
}

export { styles as editorialStyles };
