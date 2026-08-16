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

  it("scopes the approved warm homepage canvas without reviving legacy product styling", () => {
    expect(ruleFor(homeCss, ".main")).toMatch(/background:\s*var\(--home-paper\)/);
    expect(ruleFor(homeCss, ".card")).toMatch(/border:\s*1px solid var\(--home-line\)/);
    expect(ruleFor(homeCss, ".card")).toMatch(/background:\s*var\(--home-paper-surface\)/);
    expect(ruleFor(homeCss, ".observation p")).toMatch(
      /color:\s*color-mix\(in srgb, var\(--color-text-inverse\) 72%, transparent\)/,
    );
    expect(homeCss).toContain("--home-gold");
    expect(homeCss).not.toMatch(/terracotta|moss|amber/);
    expect(homeCss).not.toMatch(/priceCard|methodCard|linear-gradient|radial-gradient/);
  });

  it("keeps public navigation flat and every public link at least 44px tall", () => {
    expect(ruleFor(chromeCss, ".nav")).not.toMatch(/border-radius:\s*999px/);
    expect(ruleFor(chromeCss, ".navItem")).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(ruleFor(chromeCss, ".utilityLink")).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(ruleFor(chromeCss, ".footerColumn a")).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(ruleFor(chromeCss, ".legal a")).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(ruleFor(chromeCss, '.navItem[aria-current="page"]')).not.toMatch(
      /background:/,
    );
    expect(chromeCss).toMatch(/\.navItem\[aria-current="page"\]::after/);
  });

  it("switches cleanly to the mobile bottom navigation at the 768px boundary", () => {
    expect(chromeCss).toMatch(
      /@media \(max-width: 47\.999rem\)[\s\S]*\.desktopOnly[\s\S]*display:\s*none/,
    );
    expect(chromeCss).toMatch(
      /@media \(max-width: 47\.999rem\)[\s\S]*\.mobileBottomBar[\s\S]*display:\s*grid/,
    );
    expect(chromeCss).toMatch(
      /@media \(min-width: 48rem\)[\s\S]*\.mobileBottomBar/,
    );
    expect(chromeCss).toContain("env(safe-area-inset-bottom)");
  });
});
