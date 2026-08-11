import { readFileSync } from "node:fs";
import { resolve } from "node:path";


const homeCss = readFileSync(
  resolve(process.cwd(), "src/app/home.module.css"),
  "utf8",
);
const chromeCss = readFileSync(
  resolve(process.cwd(), "src/components/site-chrome.module.css"),
  "utf8",
);

function ruleFor(source: string, selector: string) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, "s"));
  expect(match, `missing CSS rule for ${selector}`).not.toBeNull();
  return match?.[1] ?? "";
}

describe("public visual contract", () => {
  it("uses warm paper by default and distinct paper, ink, and clay task tones", () => {
    expect(ruleFor(homeCss, ".main")).toMatch(/background:\s*var\(--ivory-50\)/);
    expect(homeCss).toMatch(/\.taskCardPaper\s*\{/);
    expect(homeCss).toMatch(/\.taskCardInk\s*\{/);
    expect(homeCss).toMatch(/\.taskCardClay\s*\{/);
    expect(homeCss).not.toMatch(/\.methodCard:hover/);
  });

  it("keeps public navigation flat and every public link at least 44px tall", () => {
    expect(ruleFor(chromeCss, ".nav")).not.toMatch(/border-radius:\s*999px/);
    expect(ruleFor(chromeCss, ".navItem")).toMatch(/min-height:\s*2\.75rem/);
    expect(ruleFor(chromeCss, ".utilityLink")).toMatch(/min-height:\s*2\.75rem/);
    expect(ruleFor(chromeCss, ".footerColumn a")).toMatch(/min-height:\s*2\.75rem/);
    expect(ruleFor(chromeCss, ".legalLinks a")).toMatch(/min-height:\s*2\.75rem/);
    expect(ruleFor(chromeCss, '.navItem[aria-current="page"]')).not.toMatch(
      /background:/,
    );
    expect(chromeCss).toMatch(/\.navItem\[aria-current="page"\]::after/);
  });

  it("keeps the mobile header focused on the three products and account", () => {
    expect(chromeCss).toMatch(
      /@media \(max-width: 47\.999rem\)[\s\S]*\.utilityLink:not\(:last-child\)[\s\S]*display:\s*none/,
    );
    expect(chromeCss).toMatch(
      /@media \(max-width: 47\.999rem\)[\s\S]*\.headerActions[\s\S]*grid-column:\s*2/,
    );
    expect(chromeCss).toMatch(
      /@media \(max-width: 47\.999rem\)[\s\S]*\.nav[\s\S]*grid-column:\s*1\s*\/\s*-1/,
    );
  });
});
