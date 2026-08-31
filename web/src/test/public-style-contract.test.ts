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
const globalCss = readFileSync(
  resolve(process.cwd(), "src/app/globals.css"),
  "utf8",
);
const sharedBaseCss = readFileSync(
  resolve(process.cwd(), "../ui/base.css"),
  "utf8",
);

function ruleFor(source: string, selector: string) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const direct = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, "s"));
  const grouped = [...source.matchAll(/([^{}]+)\{([^{}]*)\}/gs)].find((match) =>
    match[1].split(",").some((item) => item.trim() === selector),
  );
  const match = direct ?? grouped;
  expect(match, `missing CSS rule for ${selector}`).not.toBeNull();
  return direct?.[1] ?? grouped?.[2] ?? "";
}

describe("public visual contract", () => {
  it("keeps cross-route navigation from inheriting a smooth scroll position", () => {
    expect(globalCss).toContain('@import "../../../ui/base.css"');
    expect(ruleFor(sharedBaseCss, "html")).not.toMatch(/scroll-behavior:\s*smooth/);
    expect(globalCss).not.toMatch(/scroll-behavior:\s*smooth/);
  });

  it("keeps the homepage on the single Xuan Order visual baseline", () => {
    expect(ruleFor(homeCss, ".main")).toMatch(/background:\s*var\(--ds-canvas\)/);
    expect(ruleFor(homeCss, ".cardGrid")).toMatch(
      /border-block:\s*1px solid var\(--ds-line\)/,
    );
    expect(ruleFor(homeCss, ".card:hover")).toMatch(
      /background:\s*var\(--ds-surface-subtle\)/,
    );
    expect(ruleFor(homeCss, ".observation")).toMatch(
      /background:\s*var\(--ds-ink\)/,
    );
    expect(ruleFor(homeCss, ".observationCopy > p:last-child")).toMatch(
      /color:\s*var\(--ds-line-strong\)/,
    );
    expect(ruleFor(homeCss, ".spotlight")).toMatch(/display:\s*none/);
    expect(homeCss).not.toMatch(/--home-|terracotta|moss|amber/);
    expect(homeCss).not.toMatch(/(?:linear|radial|conic)-gradient\s*\(/);
  });

  it("keeps public navigation flat with compact desktop and coarse-pointer targets", () => {
    expect(ruleFor(chromeCss, ".nav")).not.toMatch(/border-radius:\s*999px/);
    expect(ruleFor(chromeCss, ".navItem")).toMatch(/min-height:\s*var\(--ds-control-md\)/);
    expect(ruleFor(chromeCss, ".utilityLink")).toMatch(/min-height:\s*var\(--ds-control-md\)/);
    expect(ruleFor(chromeCss, ".footerColumn a")).toMatch(
      /min-height:\s*var\(--ds-touch-min\)/,
    );
    expect(ruleFor(chromeCss, ".legal a")).toMatch(
      /min-height:\s*var\(--ds-touch-min\)/,
    );
    expect(chromeCss).toMatch(
      /@media \(min-width: 840px\) and \(any-pointer: coarse\)[\s\S]*\.navItem,[\s\S]*\.utilityLink[\s\S]*min-height:\s*var\(--ds-touch-min\)/,
    );
    expect(ruleFor(chromeCss, '.navItem[aria-current="page"]')).not.toMatch(
      /background:/,
    );
    expect(chromeCss).toMatch(/\.navItem\[aria-current="page"\]::after/);
  });

  it("switches cleanly to the mobile bottom navigation at the 840px boundary", () => {
    expect(chromeCss).toMatch(
      /@media \(max-width: 839px\)[\s\S]*\.desktopOnly[\s\S]*display:\s*none/,
    );
    expect(chromeCss).toMatch(
      /@media \(max-width: 839px\)[\s\S]*\.mobileBottomBar[\s\S]*display:\s*grid/,
    );
    expect(chromeCss).toMatch(
      /@media \(min-width: 840px\)[\s\S]*\.mobileBottomBar/,
    );
    expect(chromeCss).toContain("env(safe-area-inset-bottom)");
  });
});
