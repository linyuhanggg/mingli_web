"use client";

import { FortuneFlow } from "@/components/fortune-flow";
import { privateShellStyles as styles } from "@/components/private-shell";

export default function FortuneWeekPage() {
  return (
    <section className={styles.panel}>
      <FortuneFlow mode="week" />
    </section>
  );
}
