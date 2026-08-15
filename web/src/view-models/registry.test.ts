import { describe, expect, it } from "vitest";

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
});
