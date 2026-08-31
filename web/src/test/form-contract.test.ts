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

function ruleBodiesFor(css: string, selector: string): string[] {
  return [...css.matchAll(/([^{}]+)\{([^{}]*)\}/gs)]
    .filter((match) =>
      match[1].split(",").some((item) => item.trim() === selector),
    )
    .map((match) => match[2]);
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

  it("gives inputs the Xuan Order large-control size and surface", () => {
    const input = ruleFor(css, ".input");
    expect(input).toContain("min-height: var(--ds-control-lg)");
    expect(input).toContain("var(--color-surface)");
    expect(input).toContain("border-radius: var(--ds-radius-1)");
  });

  it("styles actions with the shared compact radius, never a 999px pill", () => {
    const action = ruleFor(css, ".action");
    const primary = ruleFor(css, ".actionPrimary");
    expect(action).toContain("border-radius: var(--ds-radius-2)");
    expect(primary).not.toContain("999px");
  });

  it("marks disabled actions as visibly non-interactive without hiding them", () => {
    const disabled = ruleFor(css, ".action:disabled");
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
    expect(tagRule).toMatch(/border-radius:\s*(999px|var\(--radius-pill\))/);
  });
});

describe("disabled controls must carry a visible reason", () => {
  it("keeps the reason text visually available, not sr-only or collapsed", () => {
    const reason = ruleBodiesFor(
      read("form-controls.module.css"),
      ".disabledReason",
    ).join("\n");
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
    expect(pageHeaderH1).toContain("var(--font-sans)");
    expect(pageHeaderH1).toMatch(/font-size:\s*(clamp\(1\.45rem|var\(--font-size-page\))/);
    expect(pageHeaderH1).not.toContain("6rem");

    const privateShell = read("private-shell.module.css");
    const panelH1 = ruleFor(privateShell, ".panel h1");
    expect(panelH1).toMatch(/font-size:\s*(clamp\(1\.45rem|var\(--font-size-page\))/);
    expect(panelH1).not.toContain("6rem");
  });

  it("lets the desktop private rail use the inverse action surface", () => {
    const shell = read("private-shell.module.css");
    const desktopShell = shell.slice(shell.indexOf("@media (min-width: 64rem)"));
    const aside = ruleFor(desktopShell, ".aside");
    expect(aside).toContain("var(--color-surface-inverse)");
    expect(aside).toContain("var(--color-text-inverse)");
    expect(aside).toContain("1px solid");
    expect(aside).not.toMatch(/169 133 63|248 243 231|linear-gradient|radial-gradient/);
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
