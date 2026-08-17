import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvidenceList } from "@/components/readings/evidence-list";
import type { ReadingEvidence } from "@/lib/api/contracts";

const legacyEvidence: ReadingEvidence[] = [
  {
    ref: "evidence:bazi/legacy-rule",
    source_title: "穷通宝鉴",
    locator: "rules.md#legacy-rule",
    excerpt: "这是规则摘要，不是古籍逐字原文。",
    supports_fact_refs: [],
  },
];

const exactEvidenceWithLegacyConflict: ReadingEvidence[] = [
  {
    ref: "evidence:bazi/bazi/test-rule",
    evidence_ref: "evidence:bazi/bazi/test-rule",
    rule_id: "bazi/test-rule",
    source_title: "穷通宝鉴",
    locator: "fulltext.md#L10",
    excerpt: "这是旧的规则摘要。",
    verification_status: "verified_exact",
    verbatim_excerpt: "这是首条逐字原文。",
    verbatim_citations: [
      {
        source_title: "穷通宝鉴",
        locator: "fulltext.md#L10",
        verbatim_excerpt: "这是首条逐字原文。",
        verification_status: "verified_exact",
      },
      {
        source_title: "穷通宝鉴",
        locator: "fulltext.md#L12",
        verbatim_excerpt: "这是第二条逐字原文。",
        verification_status: "verified_exact",
      },
    ],
    supports_fact_refs: [],
  },
];

describe("EvidenceList exact-only presentation", () => {
  it("hides legacy evidence when exact-only mode is enabled", () => {
    render(<EvidenceList evidence={legacyEvidence} exactOnly />);

    expect(
      screen.queryByText("这是规则摘要，不是古籍逐字原文。"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("服务端暂未返回公开依据来源。")).toBeVisible();
  });

  it("renders the verified excerpt instead of a conflicting legacy excerpt", () => {
    render(
      <EvidenceList evidence={exactEvidenceWithLegacyConflict} exactOnly />,
    );

    expect(screen.getByText("这是首条逐字原文。")).toBeVisible();
    expect(screen.queryByText("这是旧的规则摘要。")).not.toBeInTheDocument();
  });
});
