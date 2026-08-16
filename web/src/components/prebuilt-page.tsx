import type { ReactNode } from "react";

import { EditorialPage, editorialStyles as styles } from "@/components/editorial-page";
import { StatusPanel } from "@/components/status-panel";

export function PrebuiltPage({
  eyebrow,
  title,
  intro,
  statusTitle = "能力待接入",
  statusDescription,
  children,
}: {
  eyebrow: string;
  title: string;
  intro: string;
  statusTitle?: string;
  statusDescription: string;
  children?: ReactNode;
}) {
  return (
    <EditorialPage eyebrow={eyebrow} title={title} intro={intro}>
      {children ?? (
        <section className={styles.prose}>
          <h2>页面已预制</h2>
          <p>正式接入后，这里会显示明确的输入、状态、结果和下一步。</p>
        </section>
      )}
      <StatusPanel state="disabled" title={statusTitle} description={statusDescription} />
    </EditorialPage>
  );
}
