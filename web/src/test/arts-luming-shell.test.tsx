import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ArtsPage from "@/app/arts/page";
import { NATAL_PRODUCTS, PRODUCT_CATALOG } from "@/products/catalog";

const LUMING = PRODUCT_CATALOG["luming-nayin"];

const ARTS_SINGLE_ARTS = [
  PRODUCT_CATALOG.bazi,
  PRODUCT_CATALOG["luming-nayin"],
  PRODUCT_CATALOG.ziwei,
  PRODUCT_CATALOG.qizheng,
  PRODUCT_CATALOG.liuyao,
  PRODUCT_CATALOG.meihua,
  PRODUCT_CATALOG.qimen,
  PRODUCT_CATALOG.daliuren,
  PRODUCT_CATALOG.taiyi,
  PRODUCT_CATALOG.selection,
  PRODUCT_CATALOG.jianxiang,
  PRODUCT_CATALOG.fengshui,
] as const;

const ARTS_CROSS = [PRODUCT_CATALOG.hecan, PRODUCT_CATALOG.wenshi] as const;
const ARTS_HEPAN = ["/bazi/hepan", "/ziwei/hepan", "/qizheng/hepan"] as const;

function mainProductHrefs(): string[] {
  return [...document.querySelectorAll("main a")]
    .map((anchor) => anchor.getAttribute("href"))
    .filter((href): href is string => Boolean(href));
}

describe("/arts luming-nayin directory", () => {
  it("lists catalog 禄命纳音 in the natal section", () => {
    render(<ArtsPage />);

    expect(LUMING.id).toBe("luming-nayin");
    expect(LUMING.name).toBe("禄命纳音");
    expect(LUMING.href).toBe("/luming-nayin");

    const natal = screen.getByRole("heading", { level: 2, name: "命盘" }).closest("section");
    expect(natal?.querySelector(`a[href="${LUMING.href}"]`), "禄命纳音 missing from natal board").not.toBeNull();
    expect(natal?.querySelector(`a[href="${LUMING.href}"]`)?.textContent).toContain(LUMING.name);
    expect(natal?.querySelector(`a[href="${LUMING.href}"]`)?.textContent).toContain(LUMING.summary);
  });

  it("keeps twelve catalog single arts plus luming, without invented extras", () => {
    render(<ArtsPage />);

    expect(ARTS_SINGLE_ARTS).toHaveLength(12);
    expect(ARTS_SINGLE_ARTS.map((product) => product.id)).toContain("luming-nayin");

    for (const product of [...ARTS_SINGLE_ARTS, ...ARTS_CROSS]) {
      expect(document.querySelector(`main a[href="${product.href}"]`), `missing ${product.href}`).not.toBeNull();
    }

    const hrefs = mainProductHrefs();
    const allowed = new Set<string>([
      ...ARTS_SINGLE_ARTS.map((product) => product.href),
      ...ARTS_CROSS.map((product) => product.href),
      ...ARTS_HEPAN,
    ]);
    expect(hrefs.filter((href) => !allowed.has(href))).toEqual([]);
    expect(hrefs).not.toContain("/canwen");
    expect(screen.queryByText("多盘问答")).not.toBeInTheDocument();
  });

  it("does not put luming back on the homepage natal grouping", () => {
    expect(NATAL_PRODUCTS.map((product) => product.id)).toEqual(["bazi", "ziwei", "qizheng"]);
  });

  it("keeps the accepted public shell", () => {
    render(<ArtsPage />);

    expect(screen.getByRole("heading", { level: 1, name: "术数总览" })).toBeVisible();
    expect(screen.getByText("按任务选择公开产品。")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "待接入" })).not.toBeInTheDocument();
    expect(screen.queryByText(/内部计算模块|伪装成独立入口|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText(/provider/i)).not.toBeInTheDocument();

    const source = readFileSync(resolve(process.cwd(), "src/app/arts/page.tsx"), "utf8");
    expect(source).toMatch(/AccountSectionShell/);
    expect(source).toMatch(/luming-nayin/);
    expect(source).not.toMatch(/SecondarySurfaceFrame|AuthShell|AppPageHeader|§10|§6\.2/);
  });
});
