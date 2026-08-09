import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const COMPONENTS = path.resolve(import.meta.dirname, "../components");

function read(fileName: string): string {
  return readFileSync(path.join(COMPONENTS, fileName), "utf8");
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Returns the body of the first rule matching a selector outside other rules. */
function ruleFor(css: string, selector: string): string {
  const matcher = new RegExp(
    `(?:^|[^\\w-])${escapeRegExp(selector)}\\s*\\{([^}]*)\\}`,
    "m",
  );
  return matcher.exec(css)?.[1] ?? "";
}

const FORM_CSS = [
  "form-controls.module.css",
  "profile-form.module.css",
  "liuyao-form.module.css",
  "fortune-flow.module.css",
];

describe("shared form-control primitives", () => {
  const css = read("form-controls.module.css");

  it("defines field / input / error / hint / disabledReason / actions primitives", () => {
    for (const selector of [
      ".field",
      ".input",
      ".error",
      ".hint",
      ".disabledReason",
      ".actions",
      ".action",
      ".actionPrimary",
    ]) {
      expect(ruleFor(css, selector), selector).not.toBe("");
    }
  });

  it("gives inputs an ivory-50 background and at least 48px hit area", () => {
    const input = ruleFor(css, ".input");
    expect(input).toContain("min-height: 3rem");
    expect(input).toContain("var(--ivory-50)");
    expect(input).toContain("border-radius: var(--radius-sm)");
  });

  it("styles primary actions with radius-sm, never a 999px pill", () => {
    const primary = ruleFor(css, ".actionPrimary");
    expect(primary).toContain("border-radius: var(--radius-sm)");
    expect(primary).not.toContain("999px");
  });

  it("marks disabled actions as visibly non-interactive without hiding them", () => {
    const disabled = ruleFor(css, ".action[disabled]");
    expect(disabled).toContain("cursor: not-allowed");
    expect(disabled).not.toContain("display: none");
  });
});

describe("no pill buttons in form surfaces", () => {
  it("forbids 999px button radius across every form css surface", () => {
    for (const file of FORM_CSS) {
      expect(read(file), file).not.toContain("999px");
    }
  });

  it("keeps the capsule only for short status tags in the wider surface", () => {
    const appSurface = read("app-surface.module.css");
    const tagRule = ruleFor(appSurface, ".stateTag");
    expect(tagRule).toContain("border-radius: 999px");
  });
});

describe("disabled controls must carry a visible reason", () => {
  it("keeps the reason text visually available, not sr-only or collapsed", () => {
    const reason = ruleFor(read("form-controls.module.css"), ".disabledReason");
    expect(reason).not.toBe("");
    expect(reason).not.toContain("display: none");
    expect(reason).not.toContain("position: absolute");
    expect(reason).toMatch(/color:/);
  });

  it("wires the reason primitive into every owned interactive form", () => {
    for (const file of ["profile-form.tsx", "liuyao-form.tsx", "fortune-flow.tsx"]) {
      const source = read(file);
      expect(source, file).toContain("formControls.disabledReason");
      expect(source, file).toMatch(/已暂时锁定/);
    }
  });
});

describe("form surfaces consume the shared primitives", () => {
  it.each(["profile-form.tsx", "liuyao-form.tsx", "fortune-flow.tsx"])(
    "%s wires field/input/error/hint/actions from form-controls",
    (file) => {
      const source = read(file);
      expect(source).toContain("formControls.field");
      expect(source).toContain("formControls.input");
      expect(source).toContain("formControls.error");
      expect(source).toContain("formControls.hint");
      expect(source).toContain("formControls.action");
    },
  );
});

describe("email OTP content handling", () => {
  it("keeps a long submitted email from overflowing the verification card", () => {
    const codeMeta = ruleFor(read("otp-form.module.css"), ".codeMeta");
    expect(codeMeta).not.toBe("");
    expect(codeMeta).toContain("overflow-wrap: anywhere");
  });
});

describe("private title scale and shell surface contract", () => {
  it("moves private page headers off the homepage display scale onto title scale", () => {
    const appSurface = read("app-surface.module.css");
    const pageHeaderH1 = ruleFor(appSurface, ".pageHeader h1");
    expect(pageHeaderH1).toContain("var(--font-serif)");
    expect(pageHeaderH1).toContain("clamp(1.45rem");
    expect(pageHeaderH1).not.toContain("6rem");

    const privateShell = read("private-shell.module.css");
    const panelH1 = ruleFor(privateShell, ".panel h1");
    expect(panelH1).toContain("clamp(1.45rem");
    expect(panelH1).not.toContain("6rem");
  });

  it("lets the desktop private rail use deep ink with a fine gold line", () => {
    const shell = read("private-shell.module.css");
    const desktopShell = shell.slice(shell.indexOf("@media (min-width: 64rem)"));
    const aside = ruleFor(desktopShell, ".aside");
    expect(aside).toContain("background: var(--ink-900)");
    expect(aside).toMatch(/border-right: 1px solid var\(--border-hero-orbit\)/);
  });

  it("keeps the five-item mobile bottom bar and its safe-area padding", () => {
    const mobile = ruleFor(read("private-shell.module.css"), ".mobileNav");
    expect(mobile).toContain("repeat(5,");
    expect(mobile).toContain("env(safe-area-inset-bottom)");
  });

  it("keeps the private header free of an eyebrow above the h1", () => {
    const source = read("app-page-header.tsx");
    expect(source).not.toMatch(/eyebrow|folio/i);
    expect((source.match(/<h1>/g) ?? []).length).toBe(1);
  });
});

describe("motion contract", () => {
  const ALLOWED = [
    "transform",
    "opacity",
    "background-color",
    "border-color",
    "color",
    "none",
  ];

  it("limits transitions to transform/opacity/colors and honors reduced motion", () => {
    for (const file of [
      "form-controls.module.css",
      "app-surface.module.css",
      "private-shell.module.css",
    ]) {
      const css = read(file);
      const transitions = [...css.matchAll(/transition:\s*([^;]+);/g)].map(
        (match) => match[1],
      );
      for (const value of transitions) {
        const props = value
          .split(",")
          .map((part) => part.trim().split(/\s+/)[0])
          .filter(Boolean);
        for (const prop of props) {
          expect(ALLOWED, `${file}: ${value}`).toContain(prop);
        }
      }
      expect(css, file).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
    }
  });
});
