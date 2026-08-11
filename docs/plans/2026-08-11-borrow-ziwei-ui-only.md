# Borrow Ziwei UI Only Implementation Plan

> Scope update (2026-08-11): this plan is intentionally limited to birth-confirmation and chart-workspace interaction. It does **not** deliver authentication-aware navigation, a personal home, or an account center. Those product-shell requirements are tracked separately in [2026-08-11-auth-aware-app-shell-rebuild.md](./2026-08-11-auth-aware-app-shell-rebuild.md).

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Borrow only interaction patterns from `Renhuai123/ziwei-doushu` to make FateRadar's existing archive/reading surfaces feel like a calm chart workspace, without adopting its algorithm, brand, Tailwind stack, prompts, or sample data.

**Architecture:** Keep `mingli_web` as the product host and `mingli-master` as the only calculation authority. Treat ziwei-doushu as an interaction reference, not a dependency. Introduce a frontend-only display model and workspace shell that render server-provided fact panels / Accepted copy. Enhance current bazi/profile/reading flows first; reserve a later ziwei board adapter that still consumes only backend-public structures.

**Tech Stack:** Next.js App Router, React 19, TypeScript, CSS Modules, motion/react, Radix UI, React Hook Form, Zod, Vitest, Testing Library. No Tailwind, no `iztro`, no `lunar-javascript`, no direct import of ziwei-doushu source.

---

## Authority and freeze

Read before implementation:

- [DESIGN.md](../../DESIGN.md)
- [PRODUCT.md](../../PRODUCT.md)
- [web/AGENTS.md](../../web/AGENTS.md)
- [docs/METIS_REFERENCE_AUDIT_2026-08-09.md](../METIS_REFERENCE_AUDIT_2026-08-09.md)
- [docs/MINGLI_V51_WEB_INTEGRATION.md](../MINGLI_V51_WEB_INTEGRATION.md)
- [docs/adr/0002-isolate-mingli-core-behind-json-adapter.md](../adr/0002-isolate-mingli-core-behind-json-adapter.md)

Frozen decisions:

1. Algorithm authority stays in mingli-master via backend Runtime Adapter. Frontend never calculates charts.
2. Visual authority stays FateRadar Eastern Editorial Archive. Do not copy Metis/ziwei-doushu branding, copy, or dark neon styling.
3. Style system stays CSS Modules + semantic tokens in `web/src/app/globals.css`.
4. P0 product entries remain: profile/free overview, today/near-seven, liuyao one question. Do not productize `ziwei` as a public entry in this plan.
5. ziwei-doushu may inspire interaction only. Do not vendor its algorithm files, patterns engine, Insight prompts, or 518k sample dataset.
6. If any substantial code is copied, keep MIT attribution. Prefer rewrite over paste.

## Scope

### In scope

- Birth-input confirmation UX improvements on existing profile form
- Chart workspace interaction on existing bazi / reading result surfaces
- Shared display models for focusable chart layers
- Desktop dual-pane and mobile summary-first reading layout
- Tests and docs that lock the "UI only" boundary

### Out of scope

- Replacing or dual-running ziwei/bazi calculation
- Adding frontend `iztro` / `lunar-javascript`
- Opening a public ziwei product route
- Importing patterns.ts as authority
- Migrating classics corpus or sample dataset
- Payment, real Runtime, model quality, or backend contract redesign
- Tailwind / second design system

## Borrow matrix

| Reference from ziwei-doushu | Borrow as | Do not borrow as |
|---|---|---|
| BirthForm true-solar / city / unknown-time flow | Confirmation UX and progressive disclosure | Final true-solar calculation authority |
| ChartBoard + PalaceCell focus / san-fang highlight | Focus interaction grammar | Chart generation |
| TimeNav natal / decadal / yearly tabs | Layer switching UI | Client-side sihua overlay calculation |
| Star/palace detail side panel structure | Focus detail drawer layout | Ni Haixia long-form copy dump |
| PatternsCard density | Highlight card presentation | Local pattern detection engine |
| Desktop board + side panel | Information architecture | Brand shell / chat interpret panel |
| Home marketing / share cards / prompts | Nothing | Everything |

## Target shape

```text
API / reading-display facts
        |
        v
chart-workspace view model
        |
        +-- TimeLayerTabs
        +-- Chart board (bazi now, ziwei later)
        +-- FocusDetailDrawer
                |
                v
Accepted copy remains the only delivered prose
```

Desktop:

```text
[ Time layers ]
[ Chart workspace | Focus detail ]
[ Accepted reading anatomy ]
```

Mobile:

```text
1. Conclusion summary
2. Compact chart + expand
3. Layer tabs
4. Focus sheet
5. Full accepted copy
```

## File plan

Expected create/modify set:

- Create: `docs/plans/2026-08-11-borrow-ziwei-ui-only.md` (this file)
- Create: `web/src/lib/chart-workspace.ts`
- Create: `web/src/components/readings/chart-workspace-shell.tsx`
- Create: `web/src/components/readings/chart-workspace-shell.module.css`
- Create: `web/src/components/readings/time-layer-tabs.tsx`
- Create: `web/src/components/readings/time-layer-tabs.module.css`
- Create: `web/src/components/readings/focus-detail-drawer.tsx`
- Create: `web/src/components/readings/focus-detail-drawer.module.css`
- Create: `web/src/components/birth-basis-summary.tsx`
- Create: `web/src/components/birth-basis-summary.module.css`
- Create: `web/src/test/chart-workspace.test.ts`
- Create: `web/src/test/chart-workspace-shell.test.tsx`
- Create: `web/src/test/birth-basis-summary.test.tsx`
- Create: `web/src/test/chart-workspace-boundary.test.ts`
- Modify: `web/src/lib/reading-display.ts`
- Modify: `web/src/components/profile-form.tsx`
- Modify: `web/src/components/profile-form.module.css`
- Modify: `web/src/components/readings/bazi-chart.tsx`
- Modify: `web/src/components/readings/bazi-chart.module.css`
- Modify: `web/src/components/readings/reading-result.tsx`
- Modify: `web/src/components/readings/reading-result.module.css`
- Modify: `web/src/components/readings/fact-panel.tsx` only if needed for shared focus data
- Modify: existing reading/profile tests as assertions grow
- Optional later: `web/src/components/readings/ziwei-chart-board.tsx` after backend public ziwei facts exist

Do not create:

- `web/src/lib/ziwei/**`
- any frontend algorithm package
- public `/app/ziwei` product route in this plan

---

### Task 0: Freeze the UI-only boundary in docs and tests

**Files:**
- Modify/keep: `docs/plans/2026-08-11-borrow-ziwei-ui-only.md`
- Create: `web/src/test/chart-workspace-boundary.test.ts`

**Step 1: Add a boundary test that fails if forbidden deps appear**

```ts
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = path.resolve(__dirname, "..");

function read(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("ziwei UI-only boundary", () => {
  it("does not depend on iztro or lunar-javascript", () => {
    const pkg = read("../package.json");
    expect(pkg).not.toMatch(/"iztro"/);
    expect(pkg).not.toMatch(/"lunar-javascript"/);
  });

  it("does not import ziwei-doushu algorithm paths in chart code", () => {
    const files = [
      "lib/chart-workspace.ts",
      "components/readings/bazi-chart.tsx",
      "components/readings/chart-workspace-shell.tsx",
    ];
    for (const file of files) {
      const source = read(file);
      expect(source).not.toMatch(/generateChart|astro\.bySolar|from ['"]iztro['"]|ziwei-doushu/);
    }
  });
});
```

**Step 2: Run the boundary test**

```bash
npm --prefix web test -- chart-workspace-boundary.test.ts
```

Expected: FAIL until `chart-workspace` files exist, or PASS on package assertions and FAIL on missing files. Keep package assertions green forever.

**Step 3: Commit boundary freeze after first green package assertions**

```bash
git add docs/plans/2026-08-11-borrow-ziwei-ui-only.md web/src/test/chart-workspace-boundary.test.ts
git commit -m "docs(web): freeze ziwei UI-only borrow boundary"
```

---

### Task 1: Define the chart workspace display model

**Files:**
- Create: `web/src/lib/chart-workspace.ts`
- Create: `web/src/test/chart-workspace.test.ts`
- Modify: `web/src/lib/reading-display.ts`

**Step 1: Write failing model tests**

Cover:

- empty facts => empty workspace with honest empty state
- bazi pillars map into focusable cells with stable ids
- missing layer stays present as `unavailable`, never fabricated
- selected focus resolves label/facts/limits without inventing stars

```ts
import { describe, expect, it } from "vitest";
import { buildBaziWorkspaceView } from "@/lib/chart-workspace";

describe("buildBaziWorkspaceView", () => {
  it("marks missing layers unavailable instead of inventing them", () => {
    const view = buildBaziWorkspaceView({
      pillars: { year: "甲子", month: "丙寅", day: "戊午", hour: null },
      activeLuck: null,
      highlights: [],
    });
    expect(view.layers.find((l) => l.id === "decadal")?.status).toBe("unavailable");
    expect(view.cells.find((c) => c.id === "hour")?.value).toBeNull();
  });
});
```

**Step 2: Run RED**

```bash
npm --prefix web test -- chart-workspace.test.ts
```

Expected: FAIL because module/export missing.

**Step 3: Implement minimal view model**

Suggested types in `chart-workspace.ts`:

```ts
export type WorkspaceLayerId = "natal" | "decadal" | "yearly";
export type WorkspaceLayerStatus = "ready" | "unavailable" | "empty";

export interface WorkspaceLayer {
  id: WorkspaceLayerId;
  label: string;
  status: WorkspaceLayerStatus;
  summary?: string | null;
}

export interface WorkspaceCell {
  id: string;
  label: string;
  value: string | null;
  kind: "pillar" | "palace" | "meta";
  badges?: string[];
  relatedFactKeys?: string[];
}

export interface WorkspaceFocusDetail {
  id: string;
  title: string;
  facts: Array<{ label: string; text: string }>;
  limits: string[];
  sources: string[];
  proseExcerpt?: string | null;
}

export interface ChartWorkspaceView {
  title: string;
  subtitle?: string | null;
  layers: WorkspaceLayer[];
  activeLayerId: WorkspaceLayerId;
  cells: WorkspaceCell[];
  highlights: Array<{
    id: string;
    title: string;
    body: string;
    tone?: "neutral" | "emphasis" | "caution";
  }>;
  basis?: Array<{ label: string; text: string }>;
}
```

Rules:

- Build only from `reading-display` / public fact structures already available
- No chart math
- No pattern detection
- No hard-coded Ni Haixia prose

**Step 4: Run GREEN**

```bash
npm --prefix web test -- chart-workspace.test.ts
```

**Step 5: Commit**

```bash
git add web/src/lib/chart-workspace.ts web/src/test/chart-workspace.test.ts web/src/lib/reading-display.ts
git commit -m "feat(web): add chart workspace display model from public facts"
```

---

### Task 2: Improve birth basis confirmation UX on profile form

**Files:**
- Create: `web/src/components/birth-basis-summary.tsx`
- Create: `web/src/components/birth-basis-summary.module.css`
- Create: `web/src/test/birth-basis-summary.test.tsx`
- Modify: `web/src/components/profile-form.tsx`
- Modify: `web/src/components/profile-form.module.css`
- Modify: `web/src/test/profile-form.test.tsx`

**Step 1: Write failing UX tests**

Assert:

- timezone, time basis, unknown-hour, longitude/location hints are visible before submit
- summary restates user choices in plain Chinese
- true-solar hint is labeled as preview / server-final, not final calculation
- no client algorithm import

Example assertions:

- "最终以服务端口径为准"
- unknown hour explains reduced certainty
- solar basis shows longitude help only when relevant

**Step 2: Run RED**

```bash
npm --prefix web test -- profile-form.test.tsx birth-basis-summary.test.tsx
```

**Step 3: Implement summary component and wire into profile form**

Interaction to borrow:

- progressive disclosure of place / time basis
- live restatement of confirmed inputs

Interaction not to borrow:

- frontend true-solar branch calculation as authority

Implementation notes:

- Keep React Hook Form + Zod
- Keep IANA timezone list
- Render `BirthBasisSummary` from current form values
- Use existing tokens / form-controls styles
- Touch targets remain >= 44px

**Step 4: Run GREEN + typecheck**

```bash
npm --prefix web test -- profile-form.test.tsx birth-basis-summary.test.tsx
npm --prefix web run typecheck
```

**Step 5: Commit**

```bash
git add web/src/components/birth-basis-summary.tsx web/src/components/birth-basis-summary.module.css web/src/components/profile-form.tsx web/src/components/profile-form.module.css web/src/test/profile-form.test.tsx web/src/test/birth-basis-summary.test.tsx
git commit -m "feat(web): restate birth time basis before profile submit"
```

---

### Task 3: Build reusable chart workspace shell

**Files:**
- Create: `web/src/components/readings/time-layer-tabs.tsx`
- Create: `web/src/components/readings/time-layer-tabs.module.css`
- Create: `web/src/components/readings/focus-detail-drawer.tsx`
- Create: `web/src/components/readings/focus-detail-drawer.module.css`
- Create: `web/src/components/readings/chart-workspace-shell.tsx`
- Create: `web/src/components/readings/chart-workspace-shell.module.css`
- Create: `web/src/test/chart-workspace-shell.test.tsx`

**Step 1: Write failing interaction tests**

Cover:

- renders layer tabs from view model
- unavailable layer is visible but not fake-ready
- clicking a cell opens focus detail with title + facts
- keyboard can move focus and activate a cell
- reduced-motion path still shows final state
- empty workspace shows honest empty copy

**Step 2: Run RED**

```bash
npm --prefix web test -- chart-workspace-shell.test.tsx
```

**Step 3: Implement shell with FateRadar styling**

Shell responsibilities:

- top: `TimeLayerTabs`
- main: slot for chart board children
- side/bottom: `FocusDetailDrawer`
- no data fetching
- no calculation

Accessibility:

- tabs are real tabs or clearly labeled radio-like controls
- selected cell has aria-pressed / aria-current
- drawer/sheet labeled and escapable
- focus ring visible

Visual:

- ivory paper panels
- ink green selection
- gold only for hierarchy accents
- no neon sihua palette copy

**Step 4: Run GREEN**

```bash
npm --prefix web test -- chart-workspace-shell.test.tsx
npm --prefix web run lint
```

**Step 5: Commit**

```bash
git add web/src/components/readings/time-layer-tabs.tsx web/src/components/readings/time-layer-tabs.module.css web/src/components/readings/focus-detail-drawer.tsx web/src/components/readings/focus-detail-drawer.module.css web/src/components/readings/chart-workspace-shell.tsx web/src/components/readings/chart-workspace-shell.module.css web/src/test/chart-workspace-shell.test.tsx
git commit -m "feat(web): add reusable chart workspace shell"
```

---

### Task 4: Upgrade bazi chart into a focusable board inside the shell

**Files:**
- Modify: `web/src/components/readings/bazi-chart.tsx`
- Modify: `web/src/components/readings/bazi-chart.module.css`
- Modify: `web/src/components/readings/reading-result.tsx`
- Modify: `web/src/components/readings/reading-result.module.css`
- Modify: `web/src/test/reading-result.test.tsx`
- Modify: `web/src/test/reading-display.test.ts` if view mapping changes

**Step 1: Write failing result-page tests**

Assert:

- bazi result renders workspace shell
- pillar click shows focus detail drawn from public facts
- accepted copy remains verbatim below/aside
- no client chart generation strings/functions appear

**Step 2: Run RED**

```bash
npm --prefix web test -- reading-result.test.tsx reading-display.test.ts
```

**Step 3: Wire bazi board through workspace shell**

Implementation order:

1. Map existing `BaziChartView` -> `ChartWorkspaceView`
2. Render pillars as focusable cells
3. Put meta basis rows into workspace basis/summary
4. Keep current empty-structure fallback copy
5. Desktop: board | detail
6. Mobile: board then detail section/sheet

Do not:

- invent day-unluck/sihua overlays
- invent patterns
- change backend payload requirements in this task unless already present and unused

**Step 4: Run GREEN**

```bash
npm --prefix web test -- reading-result.test.tsx reading-display.test.ts chart-workspace.test.ts chart-workspace-shell.test.tsx
npm --prefix web run typecheck
```

**Step 5: Visual pass checklist**

Manual:

- 360, 768, 1024, 1440 widths
- keyboard only
- `prefers-reduced-motion: reduce`
- confirm no horizontal overflow

**Step 6: Commit**

```bash
git add web/src/components/readings/bazi-chart.tsx web/src/components/readings/bazi-chart.module.css web/src/components/readings/reading-result.tsx web/src/components/readings/reading-result.module.css web/src/test/reading-result.test.tsx web/src/test/reading-display.test.ts web/src/lib/reading-display.ts web/src/lib/chart-workspace.ts
git commit -m "feat(web): make bazi reading board focusable in workspace shell"
```

---

### Task 5: Align reading page information architecture with workspace grammar

**Files:**
- Modify: `web/src/components/readings/reading-result.tsx`
- Modify: `web/src/components/readings/reading-anatomy.tsx` only if needed for order/slots
- Modify: `web/src/components/readings/fact-panel.tsx` only if shared summary extraction helps
- Modify: related CSS modules and tests

**Step 1: Lock reading order with tests**

Desired order:

1. status / title
2. conclusion summary from accepted copy structure already used
3. chart workspace
4. fact panel / limits / evidence
5. full accepted anatomy and follow-up/verification actions

Borrow:

- "board first for specialists" is rejected
- FateRadar stays "conclusion first, board as evidence instrument"

**Step 2: Implement layout only**

- no new product claims
- no fake live runtime badges
- preserve noindex private behavior already elsewhere

**Step 3: Run tests**

```bash
npm --prefix web test -- reading-result.test.tsx reading-flows.test.tsx
```

**Step 4: Commit**

```bash
git add web/src/components/readings web/src/test/reading-result.test.tsx web/src/test/reading-flows.test.tsx
git commit -m "feat(web): order reading page as conclusion then workspace evidence"
```

---

### Task 6: Optional ziwei board adapter reservation only

Do this task only if backend already exposes enough public ziwei facts for honest rendering. Otherwise stop after Task 5 and leave a stub note in this plan status section.

**Files:**
- Create: `web/src/components/readings/ziwei-chart-board.tsx`
- Create: `web/src/components/readings/ziwei-chart-board.module.css`
- Modify: `web/src/lib/chart-workspace.ts`
- Create: `web/src/test/ziwei-chart-board.test.tsx`

**Rules if executed:**

- adapter only
- no public route
- no capability policy change
- unavailable fields render unavailable
- never call iztro

**If backend facts are insufficient:**

- write a short blocked note in this plan under "Status"
- do not fake a 12-palace board from prose

---

### Task 7: Full verification and release note

**Files:**
- Create: `docs/releases/2026-08-11-borrow-ziwei-ui-only.md`
- Modify tests only if final polish requires

**Step 1: Run full web gates**

```bash
npm --prefix web test
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
```

Expected: all green.

**Step 2: Boundary re-check**

```bash
npm --prefix web test -- chart-workspace-boundary.test.ts
rg -n "iztro|lunar-javascript|generateChart|astro\\.bySolar|ziwei-doushu" web/src web/package.json
```

Expected:

- boundary tests pass
- rg finds only comments/docs explanations if any, never dependencies or calculation calls

**Step 3: Write release note**

Include:

- borrowed interactions
- explicitly not borrowed algorithm/data
- pages affected
- test counts
- remaining non-goals (no public ziwei entry, no Runtime change)

**Step 4: Commit**

```bash
git add docs/releases/2026-08-11-borrow-ziwei-ui-only.md
git commit -m "docs(release): record ziwei UI-only workspace adoption"
```

---

## Implementation notes for executors

### What "rewrite, don't paste" means

Good:

- re-implement a 4-tab layer switcher in CSS Modules
- re-implement click-to-focus board state
- re-implement birth basis restatement card

Bad:

- copy `PalaceCell.tsx` className soup
- copy `InsightPanel` prompts
- copy `patterns.ts` and run it in browser
- add Tailwind just because the reference used it

### Honesty rules in UI copy

Allowed:

- "服务端尚未返回可展示的结构"
- "此时间层未生成"
- "最终以服务端口径为准"

Forbidden:

- "已本地排盘完成"
- "格局识别（严格古书条件）" without server-provided pattern facts
- any claim that ziwei product entry is live

### Motion rules

- use `motion/react` only if needed
- prefer CSS for simple opacity/transform
- honor `prefers-reduced-motion`
- no staggered 12-cell circus on mobile if it harms readability

### Accessibility minimum

- 44px targets
- visible focus
- labeled tabs/cells
- drawer close path
- status not color-only
- screen-reader names for pillar/palace cells

## Acceptance checklist

- [ ] No frontend algorithm dependency added
- [ ] Profile form restates timezone / time basis / unknown-hour / location hints
- [ ] Bazi reading board is focusable and uses workspace shell
- [ ] Focus detail only shows server-backed facts/limits/sources
- [ ] Reading page remains conclusion-first
- [ ] FateRadar visual language preserved
- [ ] 360/768/1024/1440 usable
- [ ] Web tests/lint/typecheck/build green
- [ ] Release note documents borrow boundary

## Suggested execution order

1. Task 0 boundary freeze
2. Task 1 display model
3. Task 2 profile birth basis UX
4. Task 3 workspace shell
5. Task 4 bazi board upgrade
6. Task 5 reading IA alignment
7. Task 7 verification/release
8. Task 6 only if ziwei public facts already exist

## Status

- Plan accepted for implementation: 2026-08-11
- Code implementation: Task 0–5 and Task 7 complete on 2026-08-11
- Task 6 ziwei board adapter: **blocked / skipped** — web public reading facts and product capability surface only expose `bazi` / `fortune` / `liuyao`; no honest public ziwei palace/star structure is available for rendering without inventing a board from prose. No public ziwei route added.
- Public ziwei productization: blocked by product policy and backend exposure, intentionally out of this plan
