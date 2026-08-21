import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

const PRODUCT_ENTRIES = [
  ["八字", "/bazi"],
  ["紫微", "/ziwei"],
  ["七政", "/qizheng"],
  ["六爻", "/liuyao"],
  ["奇门", "/qimen"],
  ["大六壬", "/daliuren"],
  ["见相", "/jianxiang"],
  ["命盘合参", "/hecan"],
  ["问事合参", "/wenshi"],
  ["每日", "/daily"],
  ["工具", "/tools"],
  ["知识内容", "/library"],
] as const;

describe("public home shell", () => {
  it("keeps the Direction C heading, black primary action, and product map", () => {
    render(<HomePage />);

    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { level: 1, name: "十三术同根，五十五部古籍为证" })).toBeVisible();
    const hero = within(main).getByRole("region", { name: "十三术同根，五十五部古籍为证" });
    expect(within(hero).getByRole("link", { name: /开始排盘/ })).toHaveAttribute("href", "/bazi");

    const links = within(main).getAllByRole("link");
    for (const [name, href] of PRODUCT_ENTRIES) {
      const matching = links.filter((entry) => entry.getAttribute("href") === href);
      expect(matching.length, `missing home task link: ${href}`).toBeGreaterThan(0);
      expect(
        matching.some((entry) => new RegExp(name).test(entry.textContent ?? "")),
        `home link ${href} should expose ${name}`,
      ).toBe(true);
    }

    expect(within(main).getByText("13")).toBeVisible();
    expect(within(main).getByText("个术数体系")).toBeVisible();
    expect(within(main).getByText("55")).toBeVisible();
    expect(within(main).getByText("部古籍")).toBeVisible();
    expect(within(main).getByText("1328")).toBeVisible();
    expect(within(main).getByText("条证据索引")).toBeVisible();
    expect(within(main).queryByText("11")).not.toBeInTheDocument();
    expect(within(main).queryByText("46")).not.toBeInTheDocument();
    expect(within(main).queryByText("1114")).not.toBeInTheDocument();

    const invented = ["/meihua", "/taiyi", "/selection", "/fengshui", "/luming-nayin", "/canwen"];
    for (const href of invented) {
      expect(
        links.some((entry) => entry.getAttribute("href") === href),
        `homepage must not invent a product-map entry: ${href}`,
      ).toBe(false);
    }

    expect(within(main).queryByText("待接入")).not.toBeInTheDocument();
    expect(within(main).queryByText(/Runtime|Provider|适配器/)).not.toBeInTheDocument();
    expect(main).toHaveClass("liquid-home-prototype");
  });

  it("locks the homepage h1 to the 40-64px hero scale and the primary button to --color-action", () => {
    const css = readFileSync(resolve(process.cwd(), "src/app/home.module.css"), "utf8");
    expect(css).toMatch(
      /\.hero h1\s*\{[^}]*font-size:\s*clamp\(3rem,[^;]*var\(--font-size-hero\)\)/s,
    );
    expect(css).toMatch(
      /@media \(max-width: 47\.999rem\)[\s\S]*\.hero h1\s*\{[^}]*font-size:\s*2\.5rem/s,
    );
    expect(css).toMatch(/\.heroPrimary\s*\{[^}]*background:\s*var\(--color-action\)/s);
    expect(css).not.toMatch(/§10|§6\.2/);
  });

  it("strictly gates paper chrome to the homepage", () => {
    const home = readFileSync(resolve(process.cwd(), "src/app/page.tsx"), "utf8");
    const homeCss = readFileSync(resolve(process.cwd(), "src/app/home.module.css"), "utf8");
    const chrome = readFileSync(resolve(process.cwd(), "src/components/site-chrome.module.css"), "utf8");
    const shell = readFileSync(resolve(process.cwd(), "src/components/public-page-shell.tsx"), "utf8");
    const header = readFileSync(resolve(process.cwd(), "src/components/site-header.tsx"), "utf8");

    expect(home).toContain("liquid-home-prototype");
    expect(home).toContain("HomeAtmosphere");
    expect(home).toContain("HomeHeroMotion");
    expect(homeCss).toMatch(/--home-glass:\s*var\(--paper-glass\)/);
    expect(shell).toContain('const isHome = pathname === "/"');
    expect(header).toContain('data-home-chrome={pathname === "/" ? "true" : undefined}');
    expect(chrome).toMatch(/\.header\[data-home-chrome="true"\][^{]*\{[^}]*paper-glass-strong/s);
    expect(chrome).toMatch(/\.mobileBottomBar\[data-home-chrome="true"\][^{]*\{[^}]*paper-surface/s);
    expect(chrome).toMatch(/\.footer\[data-home-chrome="true"\][^{]*\{[^}]*paper-text/s);
    expect(home).not.toMatch(/Provider|Runtime|适配器|待接入|reference pack|evidence index/);
    expect(home).not.toMatch(/§10|§6\.2/);
  });

  it("keeps the mobile bottom navigation after main content in DOM order", () => {
    const shell = readFileSync(resolve(process.cwd(), "src/components/public-page-shell.tsx"), "utf8");
    expect(shell.indexOf("{children}")).toBeLessThan(shell.indexOf("<MobileNavigation"));
  });

  it("leaves reduced-motion content in native static wrappers", () => {
    const motionSource = readFileSync(
      resolve(process.cwd(), "src/components/home-motion.tsx"),
      "utf8",
    );

    expect(motionSource).not.toMatch(/if \(reduceMotion\) return <motion\./);
    expect(motionSource).toContain(
      "if (reduceMotion) return <div className={className}>{children}</div>;",
    );
    expect(motionSource).toContain("if (reduceMotion) return <div>{children}</div>;");
  });
});
