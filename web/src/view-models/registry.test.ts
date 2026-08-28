import { describe, expect, it } from "vitest";

import type {
  DaliurenDimensionFact,
  ZiweiCoreFacts,
  ZiweiMajorLimitSegment,
} from "./registry";
import {
  VIEW_MODEL_FIXTURES,
  VIEW_MODEL_VERSIONS,
  getViewModelFixture,
} from "./registry";

const EXPECTED_VERSIONS = [
  "bazi-chart/v1",
  "bazi-relationship/v1",
  "canwen-view/v1",
  "chart-similarity-view/v1",
  "daliuren-chart/v1",
  "fengshui-view/v1",
  "five-elements-facts-view/v1",
  "fortune-facts-view/v1",
  "hecan-view/v1",
  "liuyao-chart/v1",
  "luming-nayin-chart/v1",
  "rhythm-facts-view/v1",
  "meihua-chart/v1",
  "physiognomy-view/v1",
  "qimen-chart/v1",
  "qizheng-chart/v1",
  "qizheng-relationship/v1",
  "selection-chart/v1",
  "taiyi-chart/v1",
  "time-check-view/v1",
  "wenshi-view/v1",
  "ziwei-chart/v1",
  "ziwei-relationship/v1",
] as const;

describe("versioned ViewModel registry", () => {
  it("registers every published ViewModel version", () => {
    expect(VIEW_MODEL_VERSIONS).toEqual(EXPECTED_VERSIONS);
    expect(Object.keys(VIEW_MODEL_FIXTURES).sort()).toEqual(
      [...EXPECTED_VERSIONS].sort(),
    );
  });

  it("uses an explicit unavailable fixture until a real ViewModel is connected", () => {
    for (const version of EXPECTED_VERSIONS) {
      const fixture = getViewModelFixture(version);

      expect(fixture).toMatchObject({
        version,
        state: "unavailable",
      });
      expect(fixture).not.toHaveProperty("value");
      expect(fixture.description).toBeTruthy();
    }
  });

  it("does not resolve an unregistered version", () => {
    expect(getViewModelFixture("reading-document/v1")).toBeUndefined();
  });

  it("keeps dated Ziwei major-limit segments typed as complete ViewModel facts", () => {
    const segment: ZiweiMajorLimitSegment = {
      start_inclusive: "2025-01-01",
      end_exclusive: "2026-01-01",
      major_limit: { index: 2 },
    };
    const segments: NonNullable<
      ZiweiCoreFacts["active_major_limit_segments"]
    > = [segment];

    expect(segments).toEqual([segment]);
    expect(Object.keys(segments[0])).toEqual([
      "start_inclusive",
      "end_exclusive",
      "major_limit",
    ]);

    // @ts-expect-error A dated segment without Runtime major-limit facts is incomplete.
    const missingMajorLimit: ZiweiMajorLimitSegment = {
      start_inclusive: "2025-01-01",
      end_exclusive: "2026-01-01",
    };
    void missingMajorLimit;
  });

  it("requires the complete Runtime envelope on every Daliuren dimension fact", () => {
    const validEnvelope: DaliurenDimensionFact = {
      canonical_dimension: "timing",
      requested_dimension: "timing",
      status: "calculated_facts_not_verdict",
      source_rule_ids: ["DLR-16"],
      rule_evidence: {} as DaliurenDimensionFact["rule_evidence"],
    };

    // @ts-expect-error Runtime dimension facts always require status.
    const missingStatus: DaliurenDimensionFact = {
      canonical_dimension: "timing",
      requested_dimension: "timing",
      source_rule_ids: ["DLR-16"],
      rule_evidence: {} as DaliurenDimensionFact["rule_evidence"],
    };

    // @ts-expect-error Runtime dimension facts always require source_rule_ids.
    const missingSourceRuleIds: DaliurenDimensionFact = {
      canonical_dimension: "timing",
      requested_dimension: "timing",
      status: "calculated_facts_not_verdict",
      rule_evidence: {} as DaliurenDimensionFact["rule_evidence"],
    };

    const invalidSourceRuleId: DaliurenDimensionFact = {
      canonical_dimension: "timing",
      requested_dimension: "timing",
      status: "calculated_facts_not_verdict",
      // @ts-expect-error Runtime source rule ids are strings.
      source_rule_ids: [42],
      rule_evidence: {} as DaliurenDimensionFact["rule_evidence"],
    };

    expect(validEnvelope.source_rule_ids).toEqual(["DLR-16"]);
    void missingStatus;
    void missingSourceRuleIds;
    void invalidSourceRuleId;
  });
});
