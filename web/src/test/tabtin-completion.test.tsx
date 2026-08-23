import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "@/app/page";

function readWeb(relative: string) {
  return readFileSync(resolve(process.cwd(), relative), "utf8");
}

describe("TabTin completion: chapters, folio, motion tokens", () => {
  it("exposes homepage chapters 01–07 and a desktop folio with empty-chart silhouette", () => {
    render(<HomePage />);
    const main = screen.getByRole("main");
    for (const index of ["01", "02", "03", "04", "05", "06", "07"]) {
      expect(main.querySelector(`[data-chapter="${index}"]`)).not.toBeNull();
    }
    const folio = main.querySelector("[data-folio='true']");
    expect(folio).not.toBeNull();
    expect(folio?.textContent).toMatch(/空盘/);
    expect(folio?.textContent).not.toMatch(/[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]/);
    expect(within(main).getByRole("heading", { name: "命盘" })).toBeVisible();
    const startLinks = within(main).getAllByRole("link", { name: /开始排盘/ });
    expect(startLinks.length).toBeGreaterThan(0);
    expect(startLinks[0]).toHaveAttribute("href", "/bazi");
  });

  it("pins chapter duration 480ms, overlay 220ms, stagger 60ms, and expo easing", () => {
    const tokens = readWeb("../ui/tokens.css");
    expect(tokens).toMatch(/--duration-chapter:\s*480ms/);
    expect(tokens).toMatch(/--duration-overlay:\s*220ms/);
    expect(tokens).toMatch(/--ease-out:\s*cubic-bezier\(0\.16,\s*1,\s*0\.3,\s*1\)/);
    expect(tokens).toMatch(/--font-size-chapter:\s*clamp\(2rem,\s*3vw,\s*2\.5rem\)/);

    const primitives = readWeb("src/components/motion-primitives.tsx");
    expect(primitives).toContain("chapter: 0.48");
    expect(primitives).toContain("stagger = 0.06");
    expect(primitives).toContain("y = 16");
    expect(primitives).toMatch(/if \(reduceMotion\) \{\s*return <Component className=\{className\}>\{children\}<\/Component>;/s);

    const homeMotion = readWeb("src/components/home-motion.tsx");
    expect(homeMotion).toContain("staggerChildren: 0.06");
    expect(homeMotion).toContain("if (reduceMotion) return <div className={className}>{children}</div>;");
    expect(homeMotion).toContain("if (reduceMotion) return <div>{children}</div>;");
    expect(homeMotion).not.toMatch(/if \(reduceMotion\) return <motion\./);
  });

  it("keeps homepage chapter titles on the 32–40px token and hides the folio on small screens", () => {
    const css = readWeb("src/app/home.module.css");
    expect(css).toMatch(/\.quickStartHead h2\s*\{[^}]*font-size:\s*var\(--font-size-chapter\)/s);
    expect(css).toMatch(/\.sectionHead h2,\s*\n\.chapterTitle\s*\{[^}]*font-size:\s*var\(--font-size-chapter\)/s);
    expect(css).toMatch(/\.folio\s*\{[^}]*display:\s*none/s);
    expect(css).toMatch(/@media \(min-width: 48rem\)[\s\S]*\.folio\s*\{[^}]*display:\s*block/s);
    expect(css).not.toMatch(/neon|rotateY|lenis|gsap/i);
  });

  it("frames the four pillars without per-cell stagger and uses overlay fade only", () => {
    const chart = readWeb("src/components/readings/bazi-chart.tsx");
    expect(chart).toContain('role="group" aria-label="四柱"');
    expect(chart).toContain("BaziEmptySilhouette");
    expect(chart).not.toMatch(/staggerChildren|animationDelay|animation-delay/);

    const css = readWeb("src/components/readings/bazi-chart.module.css");
    expect(css).toMatch(/\.folio\s*\{/);
    expect(css).toMatch(
      /\.transitHead,\s*\n\.matrix td\[data-active="true"\]\s*\{\s*\n\s*transition: opacity var\(--duration-overlay\) var\(--ease-out\);/,
    );
    expect(css).not.toMatch(/@keyframes|animation:/);
    expect(css).not.toMatch(/rotateY|scale\(\s*1\.[1-9]/);
  });

  it("frames the meihua triad as one group and does not stagger hexagrams", () => {
    const source = readWeb("src/components/readings/meihua-chart.tsx");
    expect(source).toContain("<Reveal y={16}>");
    expect(source).toContain('className={styles.folio}');
    expect(source).not.toMatch(/triad[\s\S]{0,200}staggerChildren/);
    expect(source).toContain("id=\"meihua-s3-board-title\"");

    const css = readWeb("src/components/readings/meihua-chart.module.css");
    expect(css).toMatch(/\.folio\s*\{/);
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
  });
});
