import { describe, expect, it } from "vitest";

import { countClassicalSourcesByPillar } from "@/lib/classical-source-markers";

/**
 * DESIGN.md §21.3 第 1 级要求盘面元素旁出现「有涉及规则时才出现」的来源标记。
 * 归属只允许走显式路径表（§19.1：映射表必须是显式常量，不得启发式猜测），
 * 未登记的 fact path 一律不归属，宁可不标也不错标。
 */
describe("countClassicalSourcesByPillar", () => {
  it("attributes four_pillars paths to their own pillar", () => {
    const counts = countClassicalSourcesByPillar([
      {
        fact_paths: [
          "fact:/chart_facts/output/four_pillars/year",
          "fact:/chart_facts/output/four_pillars/month",
        ],
      },
    ]);

    expect(counts).toEqual({ year: 1, month: 1, day: 0, hour: 0 });
  });

  it("attributes hidden stems and ten gods to the owning pillar", () => {
    const counts = countClassicalSourcesByPillar([
      {
        fact_paths: [
          "fact:/chart_facts/output/hidden_stems/day/stems/0",
          "fact:/chart_facts/output/ten_gods/hidden_stems/hour/0/ten_god",
        ],
      },
    ]);

    expect(counts).toEqual({ year: 0, month: 0, day: 1, hour: 1 });
  });

  it("maps day_master to the day pillar and month_command to the month pillar", () => {
    const counts = countClassicalSourcesByPillar([
      { fact_paths: ["fact:/chart_facts/output/day_master/stem"] },
      { fact_paths: ["fact:/chart_facts/output/month_command/branch"] },
    ]);

    expect(counts).toEqual({ year: 0, month: 1, day: 1, hour: 0 });
  });

  it("counts one pattern once per pillar even with many matching paths", () => {
    const counts = countClassicalSourcesByPillar([
      {
        fact_paths: [
          "fact:/chart_facts/output/hidden_stems/year/branch",
          "fact:/chart_facts/output/hidden_stems/year/stems/0",
          "fact:/chart_facts/output/hidden_stems/year/stems/1",
          "fact:/chart_facts/output/ten_gods/hidden_stems/year/0/stem",
        ],
      },
    ]);

    expect(counts.year).toBe(1);
  });

  it("does not attribute calendar paths that merely contain a pillar word", () => {
    const counts = countClassicalSourcesByPillar([
      {
        fact_paths: [
          "fact:/chart_facts/calendar_normalization/effective_lunar_date/day",
          "fact:/chart_facts/calendar_normalization/ganzhi/year",
        ],
      },
    ]);

    expect(counts).toEqual({ year: 0, month: 0, day: 0, hour: 0 });
  });

  it("accepts both the runtime full path and the short projected path", () => {
    const full = countClassicalSourcesByPillar([
      { fact_paths: ["fact:/chart_facts/output/day_master/stem"] },
    ]);
    const short = countClassicalSourcesByPillar([{ fact_paths: ["/day_master/stem"] }]);

    expect(full).toEqual(short);
    expect(short.day).toBe(1);
  });

  it("ignores unregistered paths instead of guessing", () => {
    const counts = countClassicalSourcesByPillar([
      { fact_paths: ["fact:/chart_facts/output/something_new/day/value"] },
    ]);

    expect(counts).toEqual({ year: 0, month: 0, day: 0, hour: 0 });
  });
});
