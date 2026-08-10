import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ReadingDetailPage from "@/app/app/readings/[readingId]/page";
import { resetApiCache } from "@/lib/api";

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("next/navigation", () => ({
  useParams: () => ({ readingId: VERSION_ID }),
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

const VERSION_ID = "33333333-3333-4333-8333-333333333333";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function readingSummary(status: string) {
  return {
    reading_version_id: VERSION_ID,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: "fortune",
    version: 1,
    status,
    object_id: "near_time_personal",
    dimension_ids: ["career"],
    horizon: { kind_id: "week", start: "2026-08-10", end: "2026-08-16" },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
  };
}

function readingResult() {
  return {
    reading_version_id: VERSION_ID,
    status: "accepted",
    accepted_copy: "先给结论。\n\n再说明依据，原字原序。",
    fact_panel: {
      question: "近七日最值得关注什么？",
      vocabulary: [],
      facts: [{ ref: "fact:opaque-1", subject_ref: "profile-version:secret", kind_id: "fact:career", value: { secret: true }, display_text: "当前结构更支持持续积累。" }],
      evidence: [{ ref: "evidence:opaque-1", source_title: "滴天髓", locator: "卷一", excerpt: "顺势而为，先定其基。", supports_fact_refs: ["fact:opaque-1"] }],
      findings: [],
      claim_scopes: [],
      limits: [{ kind_id: "limit:traditional", public_text: "仅供传统文化参考，不构成现实决策保证。", scope_refs: [], detail_ids: [] }],
      prior_answer: null,
      request_view: {
        subject_refs: [],
        capability_ids: ["fortune"],
        object_id: "near_time_personal",
        dimension_ids: ["career"],
        horizon: { kind_id: "week", start: "2026-08-10", end: "2026-08-16" },
      },
    },
    verification: null,
    input_request: null,
  };
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Returns the body of the first rule matching a selector outside other rules. */
function ruleFor(css: string, selector: string): string {
  const matcher = new RegExp(
    `(?:^|[^\\w-])${escapeRegExp(selector)}(?![A-Za-z0-9_-])[^{]*?\\{([^}]*)\\}`,
    "m",
  );
  return matcher.exec(css)?.[1] ?? "";
}

function mediaBlock(css: string, minWidth: string): string {
  const start = css.indexOf(`@media (min-width: ${minWidth})`);
  if (start === -1) return "";
  return css.slice(start);
}

const root = process.cwd();
const READINGS_DIR = "src/components/readings";

const READING_COMPONENT_CSS = [
  "reading-result.module.css",
  "fact-panel.module.css",
  "evidence-list.module.css",
  "accepted-copy.module.css",
  "verification-form.module.css",
  "follow-up-form.module.css",
  "need-input-form.module.css",
  "limit-notice.module.css",
].map((file) => join(root, READINGS_DIR, file));

function read(file: string): string {
  return readFileSync(file, "utf8");
}

afterEach(() => {
  vi.unstubAllGlobals();
  routerPush.mockReset();
});

beforeEach(() => {
  resetApiCache();
});

describe("reading detail route shell", () => {
  it("uses AppPageHeader as the only page h1, with no eyebrow or kicker", async () => {
    const route = read(
      join(root, "src/app/app/readings/[readingId]/page.tsx"),
    );
    expect(route).toContain('from "@/components/app-page-header"');
    expect(route).toContain("<AppPageHeader");
    expect(route).not.toMatch(/eyebrow|folio/i);

    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) return jsonResponse(readingResult());
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingDetailPage />);

    expect(await screen.findByRole("heading", { level: 1 })).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/解读详情/);
  });

  it("renders the accepted manuscript with numbered sections in true reading order", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) return jsonResponse(readingResult());
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingDetailPage />);

    const article = await screen.findByRole("article", { name: "解读正文" });
    const level2 = within(article).getAllByRole("heading", { level: 2 });
    expect(level2.map((node) => node.textContent)).toEqual([
      "近七日最值得关注什么？",
      "判断",
      "事实",
      "依据与边界",
      "复核与追问",
    ]);

    const indices = within(article)
      .getAllByText(/^0[1-4]$/)
      .map((node) => node.textContent);
    expect(indices).toEqual(["01", "02", "03", "04"]);

    expect(screen.getByRole("region", { name: "事实" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "判断" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "依据与边界" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "复核与追问" })).toBeInTheDocument();
  });

  it("keeps a sticky evidence rail on desktop and one natural column on mobile", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) return jsonResponse(readingResult());
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingDetailPage />);

    const rail = await screen.findByRole("complementary", {
      name: "阅读档案",
    });
    expect(within(rail).getByText("术法")).toBeInTheDocument();
    expect(within(rail).getByText("日运与周运")).toBeInTheDocument();
    expect(within(rail).getByText(/2026年8月10日/)).toBeInTheDocument();
    expect(within(rail).getByText("已交付")).toBeInTheDocument();
    expect(within(rail).getByText(/现实反馈/)).toBeInTheDocument();

    const appSurface = read(join(root, "src/components/app-surface.module.css"));
    const baseLayout = ruleFor(appSurface, ".readingLayout");
    expect(baseLayout).toContain("display: grid");
    expect(baseLayout).not.toContain("grid-template-columns");

    const desktop = mediaBlock(appSurface, "68rem");
    expect(ruleFor(desktop, ".readingLayout")).toContain(
      "grid-template-columns",
    );
    expect(ruleFor(desktop, ".evidenceRail")).toContain("position: sticky");
  });

  it("keeps explicit loading, input, stopped, processing, and accepted states public", () => {
    const readingResultSource = read(
      join(root, READINGS_DIR, "reading-result.tsx"),
    );
    expect(readingResultSource).toContain('role="status"');
    expect(readingResultSource).toContain('role="alert"');
    for (const label of [
      "准备解读",
      "事实已准备",
      "正在接纳正文",
      "交付延迟",
      "等待输入",
      "本次解读已停止",
      "正在读取结果",
    ]) {
      expect(readingResultSource, label).toContain(label);
    }
  });
});

describe("reading detail visual contract", () => {
  it("wraps long server copy, evidence, and archive metadata", () => {
    const accepted = read(
      join(root, READINGS_DIR, "accepted-copy.module.css"),
    );
    expect(ruleFor(accepted, ".copy")).toContain("overflow-wrap: anywhere");

    const evidence = read(
      join(root, READINGS_DIR, "evidence-list.module.css"),
    );
    expect(ruleFor(evidence, ".item")).toContain("overflow-wrap: anywhere");

    const appSurface = read(join(root, "src/components/app-surface.module.css"));
    expect(ruleFor(appSurface, ".railMeta dd")).toContain("overflow-wrap: anywhere");
  });

  it("uses radius-sm for interactive controls and never a 999px pill", () => {
    for (const file of READING_COMPONENT_CSS) {
      expect(read(file), file).not.toContain("999px");
    }

    const result = read(join(root, READINGS_DIR, "reading-result.module.css"));
    expect(ruleFor(result, ".retryButton")).toContain("var(--radius-sm)");
    expect(ruleFor(result, ".restartLink")).toContain("var(--radius-sm)");

    const verification = read(
      join(root, READINGS_DIR, "verification-form.module.css"),
    );
    expect(ruleFor(verification, ".button")).toContain("var(--radius-sm)");
    expect(ruleFor(verification, ".optionLabel")).toContain("var(--radius-sm)");

    const followUp = read(
      join(root, READINGS_DIR, "follow-up-form.module.css"),
    );
    expect(ruleFor(followUp, ".submit")).toContain("var(--radius-sm)");
    expect(ruleFor(followUp, ".recastLink")).toContain("var(--radius-sm)");

    const needInput = read(
      join(root, READINGS_DIR, "need-input-form.module.css"),
    );
    expect(ruleFor(needInput, ".submit")).toContain("var(--radius-sm)");
    expect(ruleFor(needInput, ".radioLabel")).toContain("var(--radius-sm)");
  });

  it("gives every reading input at least a 48px hit area with 1rem text", () => {
    const verification = read(
      join(root, READINGS_DIR, "verification-form.module.css"),
    );
    expect(ruleFor(verification, ".note")).toMatch(/min-height:\s*3rem/);
    expect(ruleFor(verification, ".note")).toMatch(/font-size:\s*1rem/);

    const followUp = read(
      join(root, READINGS_DIR, "follow-up-form.module.css"),
    );
    expect(ruleFor(followUp, ".input")).toMatch(/min-height:\s*3rem/);

    const needInput = read(
      join(root, READINGS_DIR, "need-input-form.module.css"),
    );
    expect(ruleFor(needInput, ".input")).toMatch(/min-height:\s*3rem/);
    expect(ruleFor(needInput, ".select")).toMatch(/min-height:\s*3rem/);
    expect(ruleFor(needInput, ".textarea")).toMatch(/min-height:\s*3rem/);
    expect(ruleFor(needInput, ".input")).toMatch(/font-size:\s*1rem/);
  });

  it("limits motion to transform/opacity/colors and honors reduced motion", () => {
    const ALLOWED = [
      "transform",
      "opacity",
      "background-color",
      "border-color",
      "color",
      "none",
    ];
    for (const file of [...READING_COMPONENT_CSS, join(root, "src/components/app-surface.module.css")]) {
      const css = read(file);
      expect(css, file).not.toContain("transition-duration: 0.001ms !important");
      expect(css, file).not.toContain("animation-duration: 0.001ms !important");
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
      if (transitions.some((value) => value.trim() !== "none")) {
        expect(css, file).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
      }
    }
  });
});
