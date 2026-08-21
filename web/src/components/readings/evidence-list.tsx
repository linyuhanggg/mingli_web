import type { ReadingEvidence, ReadingFact } from "@/lib/api";
import { formatReadingFact } from "@/lib/reading-display";

import styles from "./evidence-list.module.css";

function isNonEmptyText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function formatPublicEvidenceSource(
  sourceTitle: string,
  locator: string | null | undefined,
): { title: string; locator: string | null } {
  const lineMatch = locator?.match(
    /(?:^|\/)fulltext\.md#L(\d+)(?:-L?(\d+))?$/i,
  );
  if (!lineMatch) {
    return { title: sourceTitle, locator: locator || null };
  }

  const title = /^《.*》$/.test(sourceTitle)
    ? sourceTitle
    : `《${sourceTitle}》`;
  const lineLabel = lineMatch[2]
    ? `第 ${lineMatch[1]}–${lineMatch[2]} 行`
    : `第 ${lineMatch[1]} 行`;
  return { title, locator: lineLabel };
}

function isVerifiedExactEvidence(item: ReadingEvidence): boolean {
  if (
    !isNonEmptyText(item.ref) ||
    item.evidence_ref !== item.ref ||
    !isNonEmptyText(item.rule_id) ||
    item.verification_status !== "verified_exact" ||
    !isNonEmptyText(item.verbatim_excerpt) ||
    !Array.isArray(item.verbatim_citations) ||
    item.verbatim_citations.length === 0
  ) {
    return false;
  }

  const firstCitation = item.verbatim_citations[0];
  return (
    Boolean(firstCitation) &&
    isNonEmptyText(firstCitation.source_title) &&
    isNonEmptyText(firstCitation.locator) &&
    isNonEmptyText(firstCitation.verbatim_excerpt) &&
    firstCitation.verification_status === "verified_exact" &&
    firstCitation.source_title === item.source_title &&
    firstCitation.locator === item.locator &&
    firstCitation.verbatim_excerpt === item.verbatim_excerpt
  );
}

export function EvidenceList({
  evidence,
  facts = [],
  exactOnly = false,
}: Readonly<{
  evidence?: ReadingEvidence[] | null;
  facts?: ReadingFact[];
  exactOnly?: boolean;
}>) {
  const items = (Array.isArray(evidence) ? evidence : []).filter(
    (item) => !exactOnly || isVerifiedExactEvidence(item),
  );
  const publicFactText = new Map(
    facts.map((fact, index) => [fact.ref, formatReadingFact(fact, index).text]),
  );

  return items.length > 0 ? (
    <ul className={styles.list}>
      {items.map((item) => {
        const publicSource = formatPublicEvidenceSource(
          item.source_title,
          item.locator,
        );
        const supportedFacts = Array.from(
          new Set(
            item.supports_fact_refs
              .map((ref) => publicFactText.get(ref))
              .filter((text): text is string => Boolean(text)),
          ),
        );

        return (
          <li className={styles.item} key={item.ref}>
            <p className={styles.source}>
              {publicSource.title}
              {publicSource.locator ? (
                <span className={styles.locator}> · {publicSource.locator}</span>
              ) : null}
            </p>
            {(exactOnly ? item.verbatim_excerpt : item.excerpt) ? (
              <p className={styles.excerpt}>
                {exactOnly ? item.verbatim_excerpt : item.excerpt}
              </p>
            ) : null}
            {supportedFacts.length > 0 ? (
              <p className={styles.supportedFacts}>
                {`支持事实：${supportedFacts.join("；")}`}
              </p>
            ) : null}
          </li>
        );
      })}
    </ul>
  ) : (
    <p className={styles.empty}>服务端暂未返回公开依据来源。</p>
  );
}
