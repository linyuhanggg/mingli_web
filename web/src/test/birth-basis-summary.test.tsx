import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BirthBasisSummary, type BirthBasisSummaryValues } from "@/components/birth-basis-summary";

const baseValues: BirthBasisSummaryValues = {
  birth_datetime: "1994-04-30T05:55",
  timezone: "Asia/Shanghai",
  location: "浙江省杭州市",
  time_basis_policy: "civil",
  zi_hour_policy: "midnight",
  longitude: "",
  latitude: "",
};

describe("BirthBasisSummary", () => {
  it("restates timezone, time basis, and hour policy in plain Chinese", () => {
    render(<BirthBasisSummary values={baseValues} />);
    expect(screen.getByText("Asia/Shanghai")).toBeVisible();
    expect(screen.getByText("民用时")).toBeVisible();
    expect(screen.getByText("按午夜换日")).toBeVisible();
    expect(screen.getByText(/最终以服务端口径为准/)).toBeVisible();
    expect(screen.queryByText(/前端只预览这一选择/)).toBeNull();
  });

  it("explains reduced certainty when birth time is unknown", () => {
    render(
      <BirthBasisSummary values={{ ...baseValues, birth_datetime: "" }} />,
    );
    expect(screen.getByText(/未填写出生时间/)).toBeVisible();
    expect(screen.getByText(/时辰无法确认/)).toBeVisible();
    expect(screen.getByText(/确定性会降低/)).toBeVisible();
  });

  it("labels true-solar as a preview and shows longitude help only when relevant", () => {
    const { rerender } = render(
      <BirthBasisSummary
        values={{ ...baseValues, time_basis_policy: "solar", longitude: "" }}
      />,
    );
    expect(screen.getByText(/前端只预览这一选择/)).toBeVisible();
    expect(screen.getByText(/不在本地做真太阳时换算/)).toBeVisible();
    expect(screen.getByText(/尚未填写经度/)).toBeVisible();
    expect(screen.getByText(/服务端可能退回民用时/)).toBeVisible();
    expect(screen.queryByText(/已填写经度/)).toBeNull();

    rerender(
      <BirthBasisSummary
        values={{ ...baseValues, time_basis_policy: "solar", longitude: "120.1" }}
      />,
    );
    expect(screen.getByText(/已填写经度 120\.1°/)).toBeVisible();
    expect(screen.queryByText(/尚未填写经度/)).toBeNull();
  });

  it("notes lunar input as a recorded convention without local conversion", () => {
    render(
      <BirthBasisSummary
        values={{ ...baseValues, time_basis_policy: "lunar" }}
      />,
    );
    expect(screen.getByText("农历时间口径")).toBeVisible();
    expect(screen.getByText(/已按农历记录/)).toBeVisible();
  });

  it("keeps the summary free of client chart algorithm imports", () => {
    const source = readFileSync(
      path.resolve(import.meta.dirname, "../components/birth-basis-summary.tsx"),
      "utf8",
    );
    expect(source).not.toMatch(
      /iztro|lunar-javascript|ziwei-doushu|astro\.bySolar|generateChart/,
    );
  });
});
