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

function relativeLuminance(color: string) {
  const channels = color
    .slice(1)
    .match(/.{2}/g)!
    .map((channel) => Number.parseInt(channel, 16) / 255)
    .map((channel) =>
      channel <= 0.04045
        ? channel / 12.92
        : ((channel + 0.055) / 1.055) ** 2.4,
    );

  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(foreground: string, background: string) {
  const foregroundLuminance = relativeLuminance(foreground);
  const backgroundLuminance = relativeLuminance(background);
  return (
    (Math.max(foregroundLuminance, backgroundLuminance) + 0.05) /
    (Math.min(foregroundLuminance, backgroundLuminance) + 0.05)
  );
}

function readHexToken(css: string, name: string) {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-f]{6})`, "i"));
  expect(match, `missing hex token --${name}`).not.toBeNull();
  return match![1];
}

describe("public home shell", () => {
  it("keeps the Xuan Order heading, primary action, and product map", () => {
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
    expect(main).toHaveClass("xuan-order-home");
  });

  it("locks the homepage to the Xuan Order type and spacing scale", () => {
    const css = readFileSync(resolve(process.cwd(), "src/app/home.module.css"), "utf8");
    expect(css).toMatch(
      /\.hero h1\s*\{[^}]*font-family:\s*var\(--ds-font-domain\)[^}]*font-size:\s*clamp\(var\(--ds-text-48\),[^;]*var\(--ds-text-72\)\)/s,
    );
    expect(css).toMatch(
      /@media \(max-width: 839px\)[\s\S]*\.hero h1\s*\{[^}]*font-size:\s*clamp\(var\(--ds-text-36\),[^;]*var\(--ds-text-48\)\)/s,
    );
    expect(css).toMatch(/\.sectionDivider\s*\{[^}]*background:\s*var\(--ds-line\)/s);
    expect(css).not.toMatch(/(?:linear|radial|conic)-gradient/);
    expect(css).not.toMatch(/§10|§6\.2/);
  });

  it("keeps 12px card metadata at WCAG AA contrast on the light canvas", () => {
    const homeCss = readFileSync(resolve(process.cwd(), "src/app/home.module.css"), "utf8");
    const tokens = readFileSync(resolve(process.cwd(), "../ui/tokens.css"), "utf8");

    expect(homeCss).toMatch(
      /\.cardMeta\s*\{[^}]*color:\s*var\(--ds-muted\)[^}]*font-size:\s*var\(--ds-text-12\)/s,
    );
    expect(
      contrastRatio(readHexToken(tokens, "ds-muted"), readHexToken(tokens, "ds-canvas")),
    ).toBeGreaterThanOrEqual(4.5);
  });

  it("uses one Xuan Order visual authority instead of a second homepage brand", () => {
    const home = readFileSync(resolve(process.cwd(), "src/app/page.tsx"), "utf8");
    const homeCss = readFileSync(resolve(process.cwd(), "src/app/home.module.css"), "utf8");
    const chrome = readFileSync(resolve(process.cwd(), "src/components/site-chrome.module.css"), "utf8");
    const shell = readFileSync(resolve(process.cwd(), "src/components/public-page-shell.tsx"), "utf8");

    expect(home).toContain("xuan-order-home");
    expect(home).not.toContain("HomeAtmosphere");
    expect(home).toContain("HomeHeroMotion");
    expect(homeCss).not.toContain("--paper-");
    expect(homeCss).not.toContain("--home-paper");
    expect(shell).toContain('const isHome = pathname === "/"');
    expect(shell).toContain("<Breadcrumb pathname={pathname} />");
    expect(chrome).not.toContain("--paper-");
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
