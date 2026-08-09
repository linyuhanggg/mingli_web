"use client";

import { FortuneFlow } from "@/components/fortune-flow";
import { privateShellStyles as styles } from "@/components/private-shell";

export default function FortuneTodayPage() {
  return (
    <section className={styles.panel}>
      <FortuneFlow mode="today" />
    </section>
  );
}
