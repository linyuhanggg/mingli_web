"use client";

import { useParams } from "next/navigation";

import { ReadingResult } from "@/components/readings/reading-result";
import { privateShellStyles as styles } from "@/components/private-shell";

export default function ReadingPage() {
  const params = useParams<{ readingId?: string | string[] }>();
  const readingId = typeof params?.readingId === "string" ? params.readingId : null;

  return (
    <section className={styles.panel}>
      <h1>解读结果</h1>
      {readingId ? (
        <ReadingResult readingId={readingId} />
      ) : (
        <p role="alert">未找到解读编号，请返回重新发起解读。</p>
      )}
    </section>
  );
}
