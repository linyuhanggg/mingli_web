import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  HomeHeroItemMotion,
  HomeHeroMotion,
  HomeLedgerItemMotion,
  HomeLedgerMotion,
  HomeSectionMotion,
  HomeStepItemMotion,
  HomeStepsMotion,
  HomeTaskGridMotion,
  HomeTaskItemMotion,
} from "@/components/home-motion";

function readHomeMotionSource() {
  return readFileSync(resolve(process.cwd(), "src/components/home-motion.tsx"), "utf8");
}

describe("home motion default visibility", () => {
  it("keeps below-fold wrappers on static markup until client motion is enabled", () => {
    const source = readHomeMotionSource();

    expect(source).toContain("function useHydrationReady()");
    expect(source).not.toMatch(/initial="hidden"/);
    expect(source).not.toMatch(/opacity:\s*0/);
    expect(source).toContain("if (reduceMotion) return <div className={className}>{children}</div>;");
    expect(source).toContain("if (reduceMotion) return <ol className={className}>{children}</ol>;");
    expect(source).toContain("if (reduceMotion) return <li>{children}</li>;");
    expect(source).toContain("if (reduceMotion) return <article>{children}</article>;");
    expect(source).not.toMatch(/if \(reduceMotion\) return <motion\./);
  });

  it("renders section, task grid, and steps content visibly in the test runtime", () => {
    render(
      <>
        <HomeSectionMotion className="section-wrap">
          <section aria-label="机制">
            <h2>机制</h2>
          </section>
        </HomeSectionMotion>
        <HomeTaskGridMotion className="task-grid">
          <HomeTaskItemMotion>
            <a href="/bazi">八字</a>
          </HomeTaskItemMotion>
        </HomeTaskGridMotion>
        <HomeStepsMotion className="steps">
          <HomeStepItemMotion>
            <span>第一步</span>
          </HomeStepItemMotion>
        </HomeStepsMotion>
        <HomeLedgerMotion className="ledger">
          <HomeLedgerItemMotion>
            <h3>命盘</h3>
          </HomeLedgerItemMotion>
        </HomeLedgerMotion>
      </>,
    );

    expect(screen.getByRole("heading", { name: "机制" })).toBeVisible();
    expect(screen.getByRole("link", { name: "八字" })).toBeVisible();
    expect(screen.getByText("第一步")).toBeVisible();
    expect(screen.getByRole("heading", { name: "命盘" })).toBeVisible();
  });

  it("renders hero items visibly without waiting for viewport or hydration motion", () => {
    render(
      <HomeHeroMotion className="hero">
        <HomeHeroItemMotion>
          <h1>十三术同根，五十五部古籍为证</h1>
        </HomeHeroItemMotion>
      </HomeHeroMotion>,
    );

    expect(screen.getByRole("heading", { level: 1, name: "十三术同根，五十五部古籍为证" })).toBeVisible();
  });

  it("preserves reduced-motion static wrappers and stagger timing constants", () => {
    const source = readHomeMotionSource();

    expect(source).toContain("staggerChildren: 0.06");
    expect(source).toContain("if (reduceMotion) return <div>{children}</div>;");
    expect(source).toContain("hidden: { opacity: 1, y: 12 }");
    expect(source).toContain("hidden: { opacity: 1, y: 16 }");
  });
});
