import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import BaziResultLabPage, { metadata } from "@/app/%5Fui-lab/bazi-result/page";

afterEach(cleanup);

describe("direct UI Lab bazi result route", () => {
  it("publishes a non-indexable direct preview route with no business controls", async () => {
    const source = await import("node:fs").then(({ readFileSync }) =>
      readFileSync("src/app/%5Fui-lab/bazi-result/page.tsx", "utf8"),
    );

    expect(metadata).toMatchObject({ robots: { index: false, follow: false } });
    expect(source).toContain("BAZI_EVIDENCE_RESULT_VIEW_MODEL");
    expect(source).toContain("BAZI_EVIDENCE_RESULT_EVIDENCE");
    expect(source).toContain("BaziChart");
    expect(source).not.toContain("notFound");
    expect(source).not.toMatch(/fetch\s*\(/);
    expect(source).not.toMatch(/login|登录|session/i);
  });

  it("renders only the fixture boundary and production BaziChart", () => {
    render(<BaziResultLabPage />);

    expect(screen.getByRole("main")).toBeVisible();
    expect(screen.getByRole("note", { name: "演示数据边界" })).toHaveTextContent(
      "演示 Fixture",
    );
    expect(screen.getByText("不代表 Runtime 已发布")).toBeVisible();
    expect(screen.getByRole("heading", { name: "八字结果页验收切片" })).toBeVisible();
    expect(screen.getByText("排盘采用时刻")).toBeVisible();
    expect(screen.getByText("命中古法 1 条 · 可核验")).toBeVisible();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByText("页面与场景")).not.toBeInTheDocument();
  });
});
