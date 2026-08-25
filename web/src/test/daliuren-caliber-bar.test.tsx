import "@testing-library/jest-dom/vitest";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DaliurenCaliberBar } from "@/components/readings/daliuren-caliber-bar";
import type { DaliurenNoblePerson } from "@/view-models/registry";

const RUNTIME_SOURCE = "《钦定协纪辨方书》天乙贵人表；《六壬大全》四库提要订正说明";

function noblePerson(overrides: Partial<DaliurenNoblePerson> = {}): DaliurenNoblePerson {
  return {
    branch: "申",
    day_night_profile: "civil-double-hour",
    direction: "reverse",
    earth_position: "申",
    period: "day",
    profile: "official-corrected",
    source: RUNTIME_SOURCE,
    ...overrides,
  };
}

describe("DaliurenCaliberBar noble-person context", () => {
  it.each([
    {
      expectedProfile: "贵人口径：官修订正 · 昼夜口径：民用双时辰",
      expectedCalculation: "贵人时段：昼贵 · 天将排布：逆布",
      expectedSummary: "贵人：申",
      value: noblePerson(),
    },
    {
      expectedProfile: "贵人口径：通行口径 · 昼夜口径：民用双时辰",
      expectedCalculation: "贵人时段：夜贵 · 天将排布：顺布",
      expectedSummary: "贵人：丑",
      value: noblePerson({
        branch: "丑",
        direction: "forward",
        earth_position: "亥",
        period: "night",
        profile: "traditional-common",
        source: "《六壬大全》正文沿用的通行昼夜贵人口径",
      }),
    },
  ])(
    "renders the translated Runtime profile %# without leaking internal slugs",
    ({ value, expectedSummary, expectedCalculation, expectedProfile }) => {
      render(<DaliurenCaliberBar noblePerson={value} />);

      const region = screen.getByRole("region", { name: "起课口径" });
      expect(within(region).getByText(expectedSummary)).toBeVisible();
      expect(within(region).getByText(expectedCalculation)).toBeVisible();
      expect(within(region).getByText(expectedProfile)).toBeVisible();
      expect(within(region).getByText(`贵人取法来源：${value.source}`)).toBeVisible();
      expect(region).not.toHaveTextContent(/official-corrected|traditional-common|civil-double-hour|forward|reverse/);
    },
  );

  it.each([
    { branch: "申" },
    noblePerson({ day_night_profile: "unknown-profile" }),
    noblePerson({ profile: "unknown-profile" }),
    noblePerson({ source: "   " }),
    { ...noblePerson(), direction: "sideways" },
    { ...noblePerson(), period: "twilight" },
  ])("fail-closes a partial or unsupported Runtime profile %#", (value) => {
    render(<DaliurenCaliberBar noblePerson={value as DaliurenNoblePerson} />);

    const region = screen.getByRole("region", { name: "起课口径" });
    expect(within(region).getByText("贵人：申")).toBeVisible();
    expect(region).not.toHaveTextContent(/贵人时段|天将排布|贵人口径|昼夜口径|贵人取法来源/);
    expect(region).not.toHaveTextContent(/unknown-profile|sideways|twilight/);
  });
});
