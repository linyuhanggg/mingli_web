import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ZiweiPalaceBoard,
  ZiweiWorkspace,
  projectZiweiWorkspace,
} from "@/components/readings/ziwei-palace-board";
import type { TimeLayerEntitlementResponse } from "@/lib/api/contracts";
import type {
  ZiweiChartViewModel,
  ZiweiCoreFacts,
} from "@/view-models/registry";

afterEach(cleanup);

const BRANCHES = [
  "子",
  "丑",
  "寅",
  "卯",
  "辰",
  "巳",
  "午",
  "未",
  "申",
  "酉",
  "戌",
  "亥",
] as const;
const VISUAL_BRANCHES = [
  "巳",
  "午",
  "未",
  "申",
  "辰",
  "酉",
  "卯",
  "戌",
  "寅",
  "丑",
  "子",
  "亥",
] as const;

type Palace = ZiweiChartViewModel["palaces"][number];

function palace(
  earthly_branch: string,
  overrides: Partial<Palace> = {},
): Palace {
  return {
    palace_id: overrides.palace_id ?? `palace-${earthly_branch}`,
    label: overrides.label ?? `${earthly_branch}宫`,
    heavenly_stem: overrides.heavenly_stem ?? "甲",
    earthly_branch,
    major_stars: overrides.major_stars ?? [],
    ...overrides,
  };
}

function facts(overrides: Partial<ZiweiCoreFacts> = {}): ZiweiCoreFacts {
  return {
    five_elements_class: "水二局",
    source_conditioned_patterns: [],
    ming_shen: {
      body_star: "天相",
      ming_branch: "寅",
      shen_branch: "午",
      soul_star: "贪狼",
    },
    major_limit_direction: {
      direction: "reverse",
      gender: "male",
      year_polarity: "yang",
      year_stem: "甲",
    },
    major_limit_starting_age: 3,
    major_limit_sequence: null,
    major_limits: null,
    transformations: [
      {
        star: "紫微",
        transformation: "禄",
        palace: "命宫",
        palace_branch: "寅",
        scope: "natal",
      },
      {
        star: "天机",
        transformation: "权",
        palace: "官禄",
        palace_branch: "子",
        scope: "natal",
      },
    ],
    star_facts: [
      {
        name: "紫微",
        star_type: "major",
        scope: "natal",
        brightness: "庙",
        palace: "命宫",
        palace_branch: "寅",
        palace_index: 2,
      },
      {
        name: "太阳",
        star_type: "major",
        scope: "natal",
        brightness: "旺",
        palace: "官禄",
        palace_branch: "午",
        palace_index: 6,
      },
    ],
    ...overrides,
  };
}

function chart(
  overrides: Partial<ZiweiChartViewModel> = {},
): ZiweiChartViewModel {
  const byBranch: Record<string, Partial<Palace>> = {
    寅: {
      palace_id: "life",
      label: "命宫",
      heavenly_stem: "壬",
      major_stars: ["紫微", "天府"],
      minor_stars: [
        { name: "文昌", star_type: "minor", scope: "natal", brightness: "得" },
      ],
      adjective_stars: [
        {
          name: "天刑",
          star_type: "adjective",
          scope: "natal",
          brightness: null,
        },
      ],
      decadal: {
        age_start: 3,
        age_end: 12,
        heavenly_stem: "壬",
        earthly_branch: "寅",
      },
    },
    午: {
      palace_id: "body",
      label: "官禄",
      heavenly_stem: "丙",
      major_stars: ["太阳"],
    },
    卯: {
      palace_id: "xiong",
      label: "兄弟",
      heavenly_stem: "癸",
      major_stars: ["天机"],
    },
    子: {
      palace_id: "tian",
      label: "田宅",
      heavenly_stem: "庚",
      major_stars: ["太阴"],
    },
  };

  // 故意打乱数组下标，迫使环盘按地支落格。
  const scrambled = [
    "酉",
    "子",
    "戌",
    "寅",
    "亥",
    "卯",
    "申",
    "辰",
    "未",
    "巳",
    "丑",
    "午",
  ] as const;
  return {
    schema_version: "ziwei-chart/v1",
    subject_ref: "profile-version:fixture",
    life_palace_id: "life",
    body_palace_id: "body",
    palaces: scrambled.map((branch) => palace(branch, byBranch[branch])),
    time_layers: [],
    core_facts: facts(),
    ...overrides,
  };
}

function ziweiEntitlement(
  overrides: Partial<TimeLayerEntitlementResponse> = {},
): TimeLayerEntitlementResponse {
  return {
    schema_version: "time-layer-entitlement/v1",
    capability_id: "ziwei",
    resolution: "granted",
    free_boundary_layer_id: "year",
    paid_layer_ids: ["month", "day", "hour"],
    free_year_set: [2026],
    capability: {
      time_layers: [
        {
          layer_id: "life",
          label: "原局",
          available: true,
          unavailable_reason: null,
        },
        {
          layer_id: "year",
          label: "流年",
          available: true,
          unavailable_reason: null,
        },
        {
          layer_id: "month",
          label: "流月",
          available: true,
          unavailable_reason: null,
        },
        {
          layer_id: "day",
          label: "流日",
          available: false,
          unavailable_reason: "本次结果未返回逐日盘面。",
        },
        {
          layer_id: "hour",
          label: "流时",
          available: false,
          unavailable_reason: "本次结果未返回逐时盘面。",
        },
      ],
    },
    layers: [
      { layer_id: "life", tier: "free", access: "readable", upgrade_cta: null },
      {
        layer_id: "major_limits",
        tier: "free",
        access: "readable",
        upgrade_cta: null,
      },
      { layer_id: "year", tier: "free", access: "readable", upgrade_cta: null },
      {
        layer_id: "month",
        tier: "paid",
        access: "readable",
        upgrade_cta: null,
      },
      {
        layer_id: "day",
        tier: "paid",
        access: "unavailable",
        upgrade_cta: null,
      },
      {
        layer_id: "hour",
        tier: "paid",
        access: "unavailable",
        upgrade_cta: null,
      },
    ],
    ...overrides,
  };
}

function ziweiMonthView(
  overrides: Partial<ZiweiChartViewModel> = {},
): ZiweiChartViewModel {
  return chart({
    time_layers: [
      {
        layer_id: "month",
        label: "流月",
        available: true,
        unavailable_reason: null,
      },
    ],
    core_facts: facts({
      monthly_layers: [
        {
          year: 2026,
          month: 8,
          liu_yue: { life_palace: "申" },
          segments: [{ segment: "monthly" }],
          representative_scope: "monthly",
        },
      ],
    }),
    ...overrides,
  });
}

function boardCss() {
  return readFileSync(
    resolve(
      process.cwd(),
      "src/components/readings/ziwei-palace-board.module.css",
    ),
    "utf8",
  );
}

function ring() {
  return screen.getByRole("grid", { name: "十二宫环盘" });
}

function palaceButton(branch: string) {
  return within(ring()).getByRole("button", { name: new RegExp(`^${branch}`) });
}

describe("紫微 S3 十二宫环盘", () => {
  it("uses only a valid explicit Ziwei entitlement to unlock paid facts", () => {
    const view = ziweiMonthView();
    const granted = projectZiweiWorkspace(view, ziweiEntitlement());
    expect(granted.layers.find((layer) => layer.id === "monthly")?.status).toBe(
      "ready",
    );

    const denied = projectZiweiWorkspace(
      view,
      ziweiEntitlement({
        resolution: "denied",
        layers: ziweiEntitlement().layers.map((layer) =>
          layer.tier === "paid" && layer.access !== "unavailable"
            ? {
                ...layer,
                access: "locked_paywall" as const,
                upgrade_cta: "professional_info" as const,
              }
            : layer,
        ),
      }),
    );
    expect(denied.layers.find((layer) => layer.id === "monthly")?.status).toBe(
      "locked-paywall",
    );
    expect(
      denied.layers.find((layer) => layer.id === "monthly")?.upgradeCta,
    ).toBe("professional_info");

    const unknown = projectZiweiWorkspace(
      view,
      ziweiEntitlement({
        resolution: "unknown",
        layers: ziweiEntitlement().layers.map((layer) =>
          layer.tier === "paid" && layer.access !== "unavailable"
            ? {
                ...layer,
                access: "fail_closed_unknown" as const,
                upgrade_cta: "professional_info" as const,
              }
            : layer,
        ),
      }),
    );
    expect(unknown.layers.find((layer) => layer.id === "monthly")?.status).toBe(
      "fail-closed-unknown",
    );
    expect(
      unknown.layers.find((layer) => layer.id === "monthly")?.upgradeCta,
    ).toBe("professional_info");
    expect(
      projectZiweiWorkspace(view, null).layers.find(
        (layer) => layer.id === "monthly",
      )?.status,
    ).toBe("fail-closed-unknown");
    expect(
      projectZiweiWorkspace(view, null).layers.find(
        (layer) => layer.id === "monthly",
      )?.upgradeCta,
    ).toBeNull();
    expect(
      projectZiweiWorkspace(view, {
        ...ziweiEntitlement(),
        capability_id: "bazi",
      }).layers.find((layer) => layer.id === "monthly")?.status,
    ).toBe("fail-closed-unknown");
    expect(
      projectZiweiWorkspace(view, {
        ...ziweiEntitlement(),
        capability_id: "bazi",
      }).layers.find((layer) => layer.id === "monthly")?.upgradeCta,
    ).toBeNull();

    const contradictory = ziweiEntitlement({ resolution: "denied" });
    expect(
      projectZiweiWorkspace(view, contradictory).layers.find(
        (layer) => layer.id === "monthly",
      )?.status,
    ).toBe("fail-closed-unknown");
    expect(
      projectZiweiWorkspace(
        ziweiMonthView({ core_facts: facts({ monthly_layers: [] }) }),
        ziweiEntitlement(),
      ).layers.find((layer) => layer.id === "monthly")?.status,
    ).toBe("locked-unavailable");
    expect(
      projectZiweiWorkspace(
        ziweiMonthView({ core_facts: facts({ monthly_layers: [] }) }),
        ziweiEntitlement(),
      ).layers.find((layer) => layer.id === "monthly")?.upgradeCta,
    ).toBeNull();
    expect(
      projectZiweiWorkspace(
        ziweiMonthView({
          time_layers: [
            {
              layer_id: "month",
              label: "流月",
              available: false,
              unavailable_reason: "本次结果未返回逐月盘面。",
            },
          ],
        }),
        ziweiEntitlement(),
      ).layers.find((layer) => layer.id === "monthly")?.status,
    ).toBe("locked-unavailable");
  });

  it("keeps the frozen six-layer inventory when projector capabilities are partial", () => {
    const view = chart({
      time_layers: [
        {
          layer_id: "life",
          label: "原局",
          available: true,
          unavailable_reason: null,
        },
        {
          layer_id: "year",
          label: "流年",
          available: true,
          unavailable_reason: null,
        },
        {
          layer_id: "month",
          label: "流月",
          available: true,
          unavailable_reason: null,
        },
        {
          layer_id: "day",
          label: "流日",
          available: true,
          unavailable_reason: null,
        },
      ],
      core_facts: facts({
        annual_layers: [
          {
            year: 2026,
            coverage_start: "2026-02-17",
            coverage_end_exclusive: "2027-02-06",
            liu_nian: { life_palace: "午" },
            segments: [{ segment: "annual" }],
            representative_scope: "annual",
          },
        ],
        monthly_layers: [
          {
            year: 2026,
            month: 8,
            liu_yue: { life_palace: "申" },
            segments: [{ segment: "monthly" }],
            representative_scope: "monthly",
          },
        ],
      }),
    });
    const denied = ziweiEntitlement({
      resolution: "denied",
      layers: ziweiEntitlement().layers.map((layer) =>
        layer.tier === "paid" && layer.access !== "unavailable"
          ? {
              ...layer,
              access: "locked_paywall" as const,
              upgrade_cta: "professional_info" as const,
            }
          : layer,
      ),
    });

    const workspace = projectZiweiWorkspace(view, denied);
    expect(workspace.layers.map((layer) => layer.id)).toEqual([
      "natal",
      "decadal",
      "yearly",
      "monthly",
      "daily",
      "hourly",
    ]);
    expect(workspace.layers.map((layer) => layer.label)).toEqual([
      "原局",
      "大限",
      "流年",
      "流月",
      "流日",
      "流时",
    ]);
    expect(workspace.layers.find((layer) => layer.id === "decadal")).toMatchObject(
      {
        status: "locked-unavailable",
        summary: "暂不可用",
        upgradeCta: null,
      },
    );
    expect(workspace.layers.find((layer) => layer.id === "hourly")).toMatchObject(
      {
        status: "locked-unavailable",
        summary: "本次结果未返回逐时盘面。",
        upgradeCta: null,
      },
    );

    render(<ZiweiWorkspace timeLayerEntitlement={denied} view={view} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(6);
    const natal = screen.getByRole("tab", { name: /原局/ });
    const decadal = screen.getByRole("tab", { name: /大限/ });
    const yearly = screen.getByRole("tab", { name: /流年/ });
    const monthly = screen.getByRole("tab", { name: /流月/ });
    const hourly = screen.getByRole("tab", { name: /流时/ });
    expect(decadal).toBeDisabled();
    expect(hourly).toBeDisabled();

    natal.focus();
    fireEvent.keyDown(natal, { key: "ArrowRight" });
    expect(yearly).toHaveFocus();
    expect(yearly).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(yearly, { key: "End" });
    expect(monthly).toHaveFocus();
    expect(monthly).toHaveAttribute("aria-selected", "true");
  });

  it("renders granted month facts but keeps denied month facts at zero", () => {
    const view = ziweiMonthView();
    const { rerender } = render(
      <ZiweiWorkspace timeLayerEntitlement={ziweiEntitlement()} view={view} />,
    );

    fireEvent.click(screen.getByRole("tab", { name: /流月/ }));
    expect(
      screen.getByRole("table", { name: "流月盘面事实" }),
    ).toHaveTextContent("2026-08");

    const denied = ziweiEntitlement({
      resolution: "denied",
      layers: ziweiEntitlement().layers.map((layer) =>
        layer.tier === "paid" && layer.access !== "unavailable"
          ? {
              ...layer,
              access: "locked_paywall" as const,
              upgrade_cta: "professional_info" as const,
            }
          : layer,
      ),
    });
    rerender(<ZiweiWorkspace timeLayerEntitlement={denied} view={view} />);
    expect(screen.getByText("流月已锁定")).toBeVisible();
    expect(screen.queryByText("权益状态未确认")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "了解专业版" })).toHaveAttribute(
      "href",
      "/pricing",
    );
    expect(
      screen.queryByRole("table", { name: "流月盘面事实" }),
    ).not.toBeInTheDocument();

    rerender(<ZiweiWorkspace view={view} />);
    expect(screen.getByText("权益状态未确认")).toBeVisible();
    expect(
      screen.queryByRole("link", { name: "了解专业版" }),
    ).not.toBeInTheDocument();

    rerender(
      <ZiweiWorkspace
        timeLayerEntitlement={denied}
        view={ziweiMonthView({
          core_facts: facts({ monthly_layers: [] }),
        })}
      />,
    );
    expect(screen.getByText("流月待接入")).toBeVisible();
    expect(
      screen.queryByRole("link", { name: "了解专业版" }),
    ).not.toBeInTheDocument();
  });

  it("keeps the base palace board and its focus mounted across ready and locked layers", () => {
    render(
      <ZiweiWorkspace
        view={chart({
          time_layers: [
            {
              layer_id: "year",
              label: "流年",
              available: true,
              unavailable_reason: null,
            },
            {
              layer_id: "month",
              label: "流月",
              available: true,
              unavailable_reason: null,
            },
          ],
          core_facts: facts({
            annual_layers: [
              {
                year: 2026,
                coverage_start: "2026-02-17",
                coverage_end_exclusive: "2027-02-06",
                liu_nian: { life_palace: "午" },
                segments: [{ segment: "annual" }],
                representative_scope: "annual",
              },
            ],
            monthly_layers: [
              {
                year: 2026,
                month: 8,
                liu_yue: { life_palace: "申" },
                segments: [{ segment: "monthly" }],
                representative_scope: "monthly",
              },
            ],
          }),
        })}
      />,
    );

    const locator = screen.getByRole("navigation", { name: "十二宫定位" });
    fireEvent.click(within(locator).getByRole("button", { name: /午 官禄/ }));
    const board = screen.getByRole("grid", { name: "十二宫环盘" });
    const selectedPalace = within(board).getByRole("button", { name: /^午/ });
    act(() => selectedPalace.focus());
    expect(selectedPalace).toHaveAttribute("data-highlight", "primary");
    expect(selectedPalace).toHaveFocus();

    fireEvent.click(screen.getByRole("tab", { name: /流年/ }));
    expect(screen.getByRole("grid", { name: "十二宫环盘" })).toBe(board);
    expect(selectedPalace).toHaveAttribute("data-highlight", "primary");
    expect(selectedPalace).toHaveFocus();
    expect(screen.getByRole("table", { name: "流年盘面事实" })).toBeVisible();

    fireEvent.click(screen.getByRole("tab", { name: /流月/ }));
    expect(screen.getByRole("grid", { name: "十二宫环盘" })).toBe(board);
    expect(selectedPalace).toHaveAttribute("data-highlight", "primary");
    expect(selectedPalace).toHaveFocus();
    expect(screen.getByText("权益状态未确认")).toBeVisible();
    expect(
      screen.queryByRole("table", { name: "流月盘面事实" }),
    ).not.toBeInTheDocument();
  });

  it("gates the two-column workspace by its host container width", () => {
    const css = boardCss();

    expect(css).toMatch(
      /\.workspace\s*\{[\s\S]*container:\s*ziwei-workspace\s*\/\s*inline-size/,
    );
    expect(css).toMatch(
      /@container\s+ziwei-workspace\s*\(min-width:\s*45\.5rem\)[\s\S]*\.workspaceBody\s*\{[\s\S]*grid-template-columns:\s*minmax\(22\.5rem,\s*1\.25fr\)\s+minmax\(22\.5rem,\s*1fr\)[\s\S]*gap:\s*var\(--ds-space-2\)/,
    );
    const viewportDesktopRules =
      css.match(/@media\s*\(min-width:\s*64rem\)\s*\{([\s\S]*?)\n\}/)?.[1] ??
      "";
    expect(viewportDesktopRules).not.toContain(".workspaceBody");
  });

  it("places twelve palaces by earthly branch instead of array index", () => {
    render(<ZiweiPalaceBoard view={chart()} />);

    const cells = [...ring().querySelectorAll("[data-branch]")];
    expect(cells.map((node) => node.getAttribute("data-branch"))).toEqual([
      ...VISUAL_BRANCHES,
    ]);
    expect(chart().palaces.map((item) => item.earthly_branch)).not.toEqual([
      ...VISUAL_BRANCHES,
    ]);
    expect(chart().palaces.map((item) => item.earthly_branch)).not.toEqual([
      ...BRANCHES,
    ]);
  });

  it("renders palace facts, life and body marks, and drops missing fields", () => {
    render(<ZiweiPalaceBoard view={chart()} />);

    const yin = palaceButton("寅");
    expect(yin).toHaveAttribute("data-life", "true");
    expect(within(yin).getByText("命宫")).toBeVisible();
    expect(within(yin).getByText("壬寅")).toBeVisible();
    expect(within(yin).getByText("紫微")).toBeVisible();
    expect(within(yin).getByText("天府")).toBeVisible();
    expect(within(yin).getByText("文昌")).toBeVisible();
    expect(within(yin).getByText("天刑")).toBeVisible();
    expect(within(yin).getByText("3–12")).toBeVisible();
    expect(within(yin).getByText("命")).toBeVisible();

    const wu = palaceButton("午");
    expect(wu).toHaveAttribute("data-body", "true");
    expect(within(wu).getByText("身")).toBeVisible();
    expect(within(wu).getByText("官禄")).toBeVisible();
    expect(within(wu).queryByText("命")).not.toBeInTheDocument();

    const you = palaceButton("酉");
    expect(within(you).getByText("无主星")).toBeVisible();
    expect(within(you).queryByText("文昌")).not.toBeInTheDocument();
    expect(within(you).queryByText("3–12")).not.toBeInTheDocument();
    expect(you.textContent).not.toMatch(/undefined|null/);
  });

  it("shows brightness and transformation badges only on name-plus-branch matches", () => {
    render(<ZiweiPalaceBoard view={chart()} />);

    const yin = palaceButton("寅");
    expect(within(yin).getByText("庙")).toBeVisible();
    expect(within(yin).getByText("禄")).toBeVisible();
    expect(within(yin).queryByText("旺")).not.toBeInTheDocument();

    const mao = palaceButton("卯");
    expect(within(mao).getByText("天机")).toBeVisible();
    expect(within(mao).queryByText("庙")).not.toBeInTheDocument();
    expect(within(mao).queryByText("权")).not.toBeInTheDocument();

    const wu = palaceButton("午");
    expect(within(wu).getByText("旺")).toBeVisible();
    expect(within(wu).queryByText("禄")).not.toBeInTheDocument();
  });

  it("fills the center from ming_shen and hides empty center claims", () => {
    const { rerender } = render(<ZiweiPalaceBoard view={chart()} />);

    const center = screen.getByRole("group", { name: "中宫" });
    expect(within(center).getByText("贪狼")).toBeVisible();
    expect(within(center).getByText("天相")).toBeVisible();
    expect(within(center).getByText("水二局")).toBeVisible();
    expect(within(center).getByText("3")).toBeVisible();
    expect(within(center).getByText("逆行")).toBeVisible();
    expect(within(center).queryByText("reverse")).not.toBeInTheDocument();
    expect(within(center).queryByText("male")).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            ming_shen: null,
            major_limit_direction: null,
            major_limit_starting_age: null,
          }),
        })}
      />,
    );
    expect(screen.getByText("水二局")).toBeVisible();
    expect(screen.queryByText("贪狼")).not.toBeInTheDocument();
    expect(screen.queryByText("天相")).not.toBeInTheDocument();
    expect(screen.queryByText("逆行")).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            five_elements_class: null,
            ming_shen: null,
            major_limit_direction: null,
            major_limit_starting_age: null,
          }),
        })}
      />,
    );
    expect(screen.queryByText("水二局")).not.toBeInTheDocument();
    expect(screen.queryByText("贪狼")).not.toBeInTheDocument();
    expect(screen.queryByText(/大吉|大凶|吉凶/)).not.toBeInTheDocument();
    expect(screen.getByRole("group", { name: "中宫" })).toHaveTextContent(
      "命盘",
    );
  });

  it("locks a palace and its three harmonies without writing relation prose", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    await user.click(palaceButton("寅"));
    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("戌")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("申")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("子")).not.toHaveAttribute("data-highlight");
    expect(screen.queryByText("三方四正")).not.toBeInTheDocument();
    expect(screen.queryByText("对宫")).not.toBeInTheDocument();
    expect(screen.queryByText("三合")).not.toBeInTheDocument();

    await user.click(palaceButton("寅"));
    expect(palaceButton("寅")).not.toHaveAttribute("data-highlight");
    expect(palaceButton("午")).not.toHaveAttribute("data-highlight");
  });

  it("previews the same linked palaces on direct focus and hover without replacing the click lock", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    await act(async () => {
      palaceButton("寅").focus();
    });
    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("戌")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("申")).toHaveAttribute("data-highlight", "related");

    await act(async () => {
      palaceButton("寅").blur();
    });
    expect(ring().querySelectorAll("[data-highlight]")).toHaveLength(0);

    await user.click(palaceButton("午"));
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "primary");

    await user.hover(palaceButton("寅"));
    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("戌")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("申")).toHaveAttribute("data-highlight", "related");

    await user.unhover(palaceButton("寅"));
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "related");
  });

  it("clears a locked selection on Escape without stealing the detail drawer Escape", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    await user.click(palaceButton("寅"));
    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "primary");
    await user.keyboard("{Escape}");
    expect(palaceButton("寅")).not.toHaveAttribute("data-highlight");
    expect(palaceButton("午")).not.toHaveAttribute("data-highlight");

    palaceButton("午").focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("dialog", { name: "宫位详情" })).toBeVisible();
    await user.keyboard("{Escape}");
    expect(
      screen.queryByRole("dialog", { name: "宫位详情" }),
    ).not.toBeInTheDocument();
    expect(palaceButton("午")).toHaveFocus();
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "primary");

    await user.keyboard("{Escape}");
    expect(palaceButton("午")).not.toHaveAttribute("data-highlight");
  });

  it("moves along the earthly-branch ring and jumps with Home and End", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    palaceButton("寅").focus();
    await user.keyboard("{ArrowRight}");
    expect(palaceButton("卯")).toHaveFocus();
    expect(palaceButton("卯")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("酉")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("未")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("亥")).toHaveAttribute("data-highlight", "related");

    await user.keyboard("{ArrowLeft}");
    expect(palaceButton("寅")).toHaveFocus();

    await user.keyboard("{End}");
    expect(palaceButton("午")).toHaveFocus();
    expect(palaceButton("午")).toHaveAttribute("data-body", "true");

    await user.keyboard("{Home}");
    expect(palaceButton("寅")).toHaveFocus();
    expect(palaceButton("寅")).toHaveAttribute("data-life", "true");
  });

  it("keeps one roving locator button without tab or panel semantics", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    const locator = screen.getByRole("navigation", { name: "十二宫定位" });
    expect(within(locator).queryByRole("tablist")).not.toBeInTheDocument();
    expect(within(locator).queryByRole("tab")).not.toBeInTheDocument();
    const buttons = within(locator).getAllByRole("button");
    expect(buttons).toHaveLength(12);
    expect(buttons.filter((button) => button.tabIndex === 0)).toHaveLength(1);
    expect(
      within(locator).getByRole("button", { name: /寅 命宫/ }),
    ).toHaveAttribute("aria-current", "true");

    const noon = within(locator).getByRole("button", { name: /午 官禄/ });
    await user.click(noon);
    expect(noon).toHaveAttribute("aria-current", "true");
    expect(noon).not.toHaveAttribute("aria-controls");
    expect(noon).not.toHaveAttribute("aria-selected");
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "primary");

    noon.focus();
    await user.keyboard("{ArrowRight}");
    expect(
      within(locator).getByRole("button", { name: /未 未宫/ }),
    ).toHaveFocus();
    expect(palaceButton("未")).toHaveAttribute("data-highlight", "primary");
  });

  it("omits the locator when twelve palaces are not uniquely addressable", () => {
    render(
      <ZiweiPalaceBoard
        view={chart({
          palaces: Array.from({ length: 12 }, (_, index) =>
            palace("子", { palace_id: String(index), label: `宫${index}` }),
          ),
        })}
      />,
    );

    expect(
      screen.queryByRole("navigation", { name: "十二宫定位" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("grid", { name: "十二宫环盘" })).toBeVisible();
    expect(within(palaceButton("巳")).getByText("巳宫 · 未返回")).toBeVisible();
  });

  it("exposes a semantic table of palace, stars, stems and decade", () => {
    render(<ZiweiPalaceBoard view={chart()} />);

    const table = screen.getByRole("table", { name: "十二宫星曜" });
    expect(
      within(table).getByRole("columnheader", { name: "宫" }),
    ).toBeTruthy();
    expect(
      within(table).getByRole("columnheader", { name: "星曜" }),
    ).toBeTruthy();
    expect(
      within(table).getByRole("columnheader", { name: "干支" }),
    ).toBeTruthy();
    expect(
      within(table).getByRole("columnheader", { name: "大限" }),
    ).toBeTruthy();
    expect(within(table).getByText("命宫")).toBeTruthy();
    expect(within(table).getByText("紫微 天府")).toBeTruthy();
    expect(within(table).getByText("壬寅")).toBeTruthy();
    expect(within(table).getByText("3–12")).toBeTruthy();
    expect(getComputedStyle(table).width).toBe("1px");
  });

  it("renders the list layout from the life palace when layout is list", () => {
    render(<ZiweiPalaceBoard view={chart()} layout="list" />);

    expect(
      screen.queryByRole("grid", { name: "十二宫环盘" }),
    ).not.toBeInTheDocument();
    const thumbs = screen.getByRole("navigation", { name: "宫位缩略" });
    expect(thumbs.querySelectorAll("[data-branch]")).toHaveLength(12);
    expect(thumbs).toHaveAttribute("data-columns", "3");

    const cards = screen.getByRole("list", { name: "十二宫列表" });
    const items = within(cards).getAllByRole("listitem");
    expect(items[0]).toHaveAttribute("data-slot", "center");
    expect(items[0]).toHaveTextContent("贪狼");
    expect(
      items.slice(1).map((item) => item.getAttribute("data-branch")),
    ).toEqual([
      "寅",
      "卯",
      "辰",
      "巳",
      "午",
      "未",
      "申",
      "酉",
      "戌",
      "亥",
      "子",
      "丑",
    ]);
    expect(items[1]).toHaveTextContent("命宫");
    expect(items[1]).toHaveTextContent("紫微");
  });

  it("keeps loading and silhouette modes free of sample stars", () => {
    const { rerender } = render(<ZiweiPalaceBoard mode="silhouette" />);
    expect(
      screen
        .getByRole("grid", { name: "十二宫环盘" })
        .querySelectorAll("[data-branch]"),
    ).toHaveLength(12);
    expect(screen.queryByText("天机")).not.toBeInTheDocument();
    expect(screen.queryByText("甲子")).not.toBeInTheDocument();

    rerender(<ZiweiPalaceBoard mode="loading" />);
    expect(screen.getByRole("grid", { name: "十二宫环盘" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    expect(screen.queryByText("紫微")).not.toBeInTheDocument();
    expect(screen.queryByText("水二局")).not.toBeInTheDocument();
  });

  it("groups transformations by raw server scope and omits the table when missing", () => {
    const { rerender } = render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            transformations: [
              {
                star: "紫微",
                transformation: "禄",
                palace: "命宫",
                palace_branch: "寅",
                scope: "natal",
              },
              {
                star: "天机",
                transformation: "权",
                palace: "官禄",
                palace_branch: "子",
                scope: "natal",
              },
              {
                star: "太阳",
                transformation: "科",
                palace: "官禄",
                palace_branch: "午",
                scope: "decade",
              },
              {
                star: "太阴",
                transformation: "忌",
                palace: "田宅",
                palace_branch: "子",
                scope: "decade",
              },
            ],
          }),
        })}
      />,
    );

    const panel = screen.getByRole("region", { name: "四化" });
    expect(
      within(panel).getAllByRole("columnheader", { name: "星" }).length,
    ).toBeGreaterThan(0);
    expect(
      within(panel).getAllByRole("columnheader", { name: "化" }).length,
    ).toBeGreaterThan(0);
    expect(
      within(panel).getAllByRole("columnheader", { name: "所在宫" }).length,
    ).toBeGreaterThan(0);

    const natal = within(panel).getByRole("group", { name: "natal" });
    expect(within(natal).getByRole("button", { name: "紫微" })).toBeVisible();
    expect(within(natal).getByText("禄")).toBeVisible();
    expect(within(natal).getByText("命宫寅")).toBeVisible();
    expect(within(natal).getByRole("button", { name: "天机" })).toBeVisible();
    expect(within(natal).getByText("权")).toBeVisible();
    expect(within(natal).getByText("官禄子")).toBeVisible();

    const decade = within(panel).getByRole("group", { name: "decade" });
    expect(within(decade).getByRole("button", { name: "太阳" })).toBeVisible();
    expect(within(decade).getByText("科")).toBeVisible();
    expect(within(decade).getByText("官禄午")).toBeVisible();
    expect(within(decade).getByRole("button", { name: "太阴" })).toBeVisible();
    expect(within(decade).getByText("忌")).toBeVisible();
    expect(within(decade).getByText("田宅子")).toBeVisible();

    expect(within(panel).queryByText("本命")).not.toBeInTheDocument();
    expect(within(panel).queryByText("大限")).not.toBeInTheDocument();
    expect(within(panel).queryByText(/吉凶|大吉|大凶/)).not.toBeInTheDocument();
    expect(within(panel).queryByText(/GAP-ZW/)).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({ core_facts: facts({ transformations: null }) })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "四化" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("group", { name: "natal" }),
    ).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({ core_facts: facts({ transformations: [] }) })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "四化" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("禄")).not.toBeInTheDocument();
  });

  it("highlights the palace_branch cell when a transformation star is clicked", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    const panel = screen.getByRole("region", { name: "四化" });
    await user.click(within(panel).getByRole("button", { name: "天机" }));

    expect(palaceButton("子")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("卯")).not.toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("辰")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("申")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("寅")).not.toHaveAttribute("data-highlight");
  });

  it("lists major-limit sequence, palace, stem-branch and ages on a track", () => {
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            major_limits: [
              {
                palace: "命宫",
                palace_index: 2,
                palace_branch: "寅",
                age_start: 3,
                age_end: 12,
                sequence: 1,
                heavenly_stem: "壬",
                earthly_branch: "寅",
                direction: "reverse",
              },
              {
                palace: "官禄",
                palace_index: 6,
                palace_branch: "午",
                age_start: 13,
                age_end: 22,
                sequence: 2,
                heavenly_stem: "丙",
                earthly_branch: "午",
                direction: "reverse",
              },
            ],
          }),
        })}
      />,
    );

    const track = screen.getByRole("region", { name: "大限" });
    expect(within(track).getByText("1")).toBeVisible();
    expect(within(track).getByText("命宫")).toBeVisible();
    expect(within(track).getByText("壬寅")).toBeVisible();
    expect(within(track).getByText("3–12")).toBeVisible();
    expect(within(track).getByText("2")).toBeVisible();
    expect(within(track).getByText("官禄")).toBeVisible();
    expect(within(track).getByText("丙午")).toBeVisible();
    expect(within(track).getByText("13–22")).toBeVisible();
    expect(within(track).queryByText("当前")).not.toBeInTheDocument();
    expect(within(track).queryByText(/吉凶|大吉|大凶/)).not.toBeInTheDocument();
    expect(within(track).queryByText(/GAP-ZW/)).not.toBeInTheDocument();
  });

  it("prefers major_limits over major_limit_sequence when both exist", () => {
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            major_limits: [
              {
                palace: "命宫",
                palace_index: 2,
                palace_branch: "寅",
                age_start: 3,
                age_end: 12,
                sequence: 1,
                heavenly_stem: "壬",
                earthly_branch: "寅",
                direction: "reverse",
              },
            ],
            major_limit_sequence: [
              {
                palace: "假宫",
                palace_index: 3,
                palace_branch: "卯",
                age_start: 99,
                age_end: 108,
                sequence: 9,
                heavenly_stem: "癸",
                earthly_branch: "卯",
                direction: "forward",
              },
            ],
          }),
        })}
      />,
    );

    const track = screen.getByRole("region", { name: "大限" });
    expect(within(track).getByText("命宫")).toBeVisible();
    expect(within(track).getByText("壬寅")).toBeVisible();
    expect(within(track).getByText("3–12")).toBeVisible();
    expect(within(track).queryByText("假宫")).not.toBeInTheDocument();
    expect(within(track).queryByText("癸卯")).not.toBeInTheDocument();
    expect(within(track).queryByText("99–108")).not.toBeInTheDocument();
    expect(within(track).queryByText("9")).not.toBeInTheDocument();
  });

  it("falls back to major_limit_sequence when major_limits is missing or empty", () => {
    const { rerender } = render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            major_limits: null,
            major_limit_sequence: [
              {
                palace: "兄弟",
                palace_index: 3,
                palace_branch: "卯",
                age_start: 23,
                age_end: 32,
                sequence: 3,
                heavenly_stem: "癸",
                earthly_branch: "卯",
                direction: null,
              },
            ],
          }),
        })}
      />,
    );

    let track = screen.getByRole("region", { name: "大限" });
    expect(within(track).getByText("3")).toBeVisible();
    expect(within(track).getByText("兄弟")).toBeVisible();
    expect(within(track).getByText("癸卯")).toBeVisible();
    expect(within(track).getByText("23–32")).toBeVisible();

    rerender(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            major_limits: [],
            major_limit_sequence: [
              {
                palace: "兄弟",
                palace_index: 3,
                palace_branch: "卯",
                age_start: 23,
                age_end: 32,
                sequence: 3,
                heavenly_stem: "癸",
                earthly_branch: "卯",
                direction: null,
              },
            ],
          }),
        })}
      />,
    );
    track = screen.getByRole("region", { name: "大限" });
    expect(within(track).getByText("兄弟")).toBeVisible();
    expect(within(track).getByText("23–32")).toBeVisible();
  });

  it("highlights the palace_branch cell when a major-limit step is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            major_limits: [
              {
                palace: "命宫",
                palace_index: 2,
                palace_branch: "寅",
                age_start: 3,
                age_end: 12,
                sequence: 1,
                heavenly_stem: "壬",
                earthly_branch: "寅",
                direction: "reverse",
              },
              {
                palace: "官禄",
                palace_index: 6,
                palace_branch: "午",
                age_start: 13,
                age_end: 22,
                sequence: 2,
                heavenly_stem: "丙",
                earthly_branch: "午",
                direction: "reverse",
              },
            ],
          }),
        })}
      />,
    );

    await user.click(
      within(screen.getByRole("region", { name: "大限" })).getByRole("button", {
        name: /官禄/,
      }),
    );

    expect(palaceButton("午")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("戌")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("子")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("申")).not.toHaveAttribute("data-highlight");
    expect(screen.queryByText("流年")).not.toBeInTheDocument();
    expect(screen.queryByText("当前层")).not.toBeInTheDocument();
  });

  it("omits the track when both major_limits and sequence are missing", () => {
    const { rerender } = render(<ZiweiPalaceBoard view={chart()} />);
    expect(
      screen.queryByRole("region", { name: "大限" }),
    ).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({ major_limits: [], major_limit_sequence: [] }),
        })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "大限" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("13–22")).not.toBeInTheDocument();
  });

  it("does not mark a current limit even when active_major_limit is present", () => {
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            active_major_limit: {
              sequence: 1,
              palace: "命宫",
              palace_branch: "寅",
            },
            major_limits: [
              {
                palace: "命宫",
                palace_index: 2,
                palace_branch: "寅",
                age_start: 3,
                age_end: 12,
                sequence: 1,
                heavenly_stem: "壬",
                earthly_branch: "寅",
                direction: "reverse",
              },
              {
                palace: "官禄",
                palace_index: 6,
                palace_branch: "午",
                age_start: 13,
                age_end: 22,
                sequence: 2,
                heavenly_stem: "丙",
                earthly_branch: "午",
                direction: "reverse",
              },
            ],
          }),
        })}
      />,
    );

    const track = screen.getByRole("region", { name: "大限" });
    expect(within(track).getByText("命宫")).toBeVisible();
    expect(within(track).queryByText("当前")).not.toBeInTheDocument();
    expect(within(track).queryByText("当年所在")).not.toBeInTheDocument();
    expect(track.querySelector("[data-current]")).toBeNull();
    expect(track.querySelector("[data-active]")).toBeNull();
  });

  it("keeps the transformation table off shared pages", () => {
    const board = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-palace-board.tsx"),
      "utf8",
    );
    const table = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-transformation-table.tsx",
      ),
      "utf8",
    );
    const runtime = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const experience = readFileSync(
      resolve(process.cwd(), "src/components/task/product-task-experience.tsx"),
      "utf8",
    );
    expect(board).toContain("ziwei-transformation-table");
    expect(table).not.toMatch(/runtime-chart|product-task-experience|GAP-ZW/);
    expect(runtime).not.toContain("ziwei-transformation-table");
    expect(experience).not.toContain("ziwei-transformation-table");
  });

  it("keeps the major-limit track off shared pages", () => {
    const board = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-palace-board.tsx"),
      "utf8",
    );
    const track = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-major-limit-track.tsx",
      ),
      "utf8",
    );
    const runtime = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const experience = readFileSync(
      resolve(process.cwd(), "src/components/task/product-task-experience.tsx"),
      "utf8",
    );
    expect(board).toContain("ziwei-major-limit-track");
    expect(track).not.toMatch(
      /runtime-chart|product-task-experience|GAP-ZW|active_major_limit|当前/,
    );
    expect(runtime).not.toContain("ziwei-major-limit-track");
    expect(experience).not.toContain("ziwei-major-limit-track");
  });

  it("lists star facts by palace branch with raw type, brightness and palace", () => {
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            star_facts: [
              {
                name: "太阳",
                star_type: "major",
                scope: "natal",
                brightness: "旺",
                palace: "官禄",
                palace_branch: "午",
                palace_index: 6,
              },
              {
                name: "天梁",
                star_type: "major",
                scope: "natal",
                brightness: "得",
                palace: "父母",
                palace_branch: "亥",
                palace_index: 11,
              },
              {
                name: "紫微",
                star_type: "major",
                scope: "natal",
                brightness: "庙",
                palace: "命宫",
                palace_branch: "寅",
                palace_index: 2,
              },
              {
                name: "文昌",
                star_type: "minor",
                scope: "natal",
                brightness: null,
                palace: "命宫",
                palace_branch: "寅",
                palace_index: 2,
              },
              {
                name: "太阴",
                star_type: "major",
                scope: "decade",
                brightness: "陷",
                palace: "田宅",
                palace_branch: "子",
                palace_index: 0,
              },
            ],
          }),
        })}
      />,
    );

    const panel = screen.getByRole("region", { name: "星曜明细" });
    expect(panel.querySelector("details")).toHaveAttribute("open");
    expect(within(panel).getByText("星曜明细")).toBeVisible();
    expect(within(panel).getByLabelText("过滤星曜")).toBeVisible();

    const groups = within(panel)
      .getAllByRole("group")
      .filter((group) => group.getAttribute("aria-label"));
    expect(groups.map((group) => group.getAttribute("aria-label"))).toEqual([
      "田宅",
      "命宫",
      "官禄",
      "父母",
    ]);
    expect(
      within(groups[0]).getByRole("button", { name: "太阴" }),
    ).toBeVisible();
    expect(
      within(groups[1]).getByRole("button", { name: "紫微" }),
    ).toBeVisible();
    expect(
      within(groups[1]).getByRole("button", { name: "文昌" }),
    ).toBeVisible();
    expect(
      within(groups[2]).getByRole("button", { name: "太阳" }),
    ).toBeVisible();
    expect(
      within(groups[3]).getByRole("button", { name: "天梁" }),
    ).toBeVisible();

    const ziweiRow = within(groups[1])
      .getByRole("button", { name: "紫微" })
      .closest("tr");
    expect(ziweiRow).toHaveTextContent("major");
    expect(ziweiRow).toHaveTextContent("natal");
    expect(ziweiRow).toHaveTextContent("庙");
    expect(ziweiRow).toHaveTextContent("命宫寅");

    const wenchangRow = within(groups[1])
      .getByRole("button", { name: "文昌" })
      .closest("tr");
    expect(wenchangRow).toHaveTextContent("minor");
    expect(wenchangRow?.textContent).not.toMatch(/庙|旺|得|利|平|不|陷/);

    expect(within(panel).queryByText("主星")).not.toBeInTheDocument();
    expect(within(panel).queryByText("吉星")).not.toBeInTheDocument();
    expect(within(panel).queryByText("辅星")).not.toBeInTheDocument();
    expect(within(panel).queryByText("本命")).not.toBeInTheDocument();
    expect(within(panel).queryByText("大限")).not.toBeInTheDocument();
    expect(within(panel).queryByText("天府")).not.toBeInTheDocument();
    expect(
      within(panel).queryByText(/吉凶|大吉|大凶|GAP-ZW/),
    ).not.toBeInTheDocument();
  });

  it("filters star facts by text and keeps the filter when nothing matches", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    const panel = screen.getByRole("region", { name: "星曜明细" });
    const filter = within(panel).getByLabelText("过滤星曜");
    await user.type(filter, "太阳");

    expect(within(panel).getByRole("button", { name: "太阳" })).toBeVisible();
    expect(within(panel).getByText("官禄")).toBeVisible();
    expect(
      within(panel).queryByRole("button", { name: "紫微" }),
    ).not.toBeInTheDocument();
    expect(
      within(panel).queryByRole("group", { name: "命宫" }),
    ).not.toBeInTheDocument();

    await user.clear(filter);
    await user.type(filter, "没有这颗星");
    expect(
      within(panel).queryByRole("button", { name: "太阳" }),
    ).not.toBeInTheDocument();
    expect(
      within(panel)
        .queryAllByRole("group")
        .filter((group) => group.getAttribute("aria-label")),
    ).toEqual([]);
    expect(within(panel).getByLabelText("过滤星曜")).toBeVisible();
    expect(within(panel).getByText("星曜明细")).toBeVisible();
  });

  it("highlights the palace_branch cell when a star-fact name is clicked", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    const panel = screen.getByRole("region", { name: "星曜明细" });
    await user.click(within(panel).getByRole("button", { name: "紫微" }));

    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("戌")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("申")).toHaveAttribute("data-highlight", "related");
    expect(
      within(panel).getByRole("button", { name: "紫微" }).closest("tr"),
    ).toHaveAttribute("data-highlight", "true");
    expect(
      within(panel).getByRole("button", { name: "太阳" }).closest("tr"),
    ).not.toHaveAttribute("data-highlight");
  });

  it("highlights matching star-fact rows when a palace is selected", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    await user.click(palaceButton("午"));

    const panel = screen.getByRole("region", { name: "星曜明细" });
    expect(
      within(panel).getByRole("button", { name: "太阳" }).closest("tr"),
    ).toHaveAttribute("data-highlight", "true");
    expect(
      within(panel).getByRole("button", { name: "紫微" }).closest("tr"),
    ).not.toHaveAttribute("data-highlight");
  });

  it("omits the star-fact list when star_facts is missing or empty", () => {
    const { rerender } = render(
      <ZiweiPalaceBoard
        view={chart({ core_facts: facts({ star_facts: null }) })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "星曜明细" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("星曜明细")).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({ core_facts: facts({ star_facts: [] }) })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "星曜明细" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText("过滤星曜")).not.toBeInTheDocument();
  });

  it("keeps the star-fact list off shared pages", () => {
    const board = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-palace-board.tsx"),
      "utf8",
    );
    const list = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-star-fact-list.tsx",
      ),
      "utf8",
    );
    const css = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-star-fact-list.module.css",
      ),
      "utf8",
    );
    const runtime = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const experience = readFileSync(
      resolve(process.cwd(), "src/components/task/product-task-experience.tsx"),
      "utf8",
    );
    expect(board).toContain("ziwei-star-fact-list");
    expect(list).not.toMatch(
      /runtime-chart|product-task-experience|GAP-ZW|主星|吉星|本命/,
    );
    expect(css).not.toMatch(
      /color-success|color-danger|surface-success|surface-danger/,
    );
    expect(runtime).not.toContain("ziwei-star-fact-list");
    expect(experience).not.toContain("ziwei-star-fact-list");
  });

  it("renders nailed source_conditioned_patterns and resolves indexed paths against the actual palace array", async () => {
    const user = userEvent.setup();
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            source_conditioned_patterns: [
              {
                rule_id: "ziwei/taiwei-fu#TR-01",
                local_rule_id: "TR-01",
                title: "至玄至微",
                source_pack: "ziwei/taiwei-fu",
                source_anchor: "rules.md#L9-L16",
                status: "predicate_matched_not_verdict",
                fact_paths: ["fact:/chart_facts/output/palaces/0/name"],
                predicate_audit: [
                  "/output/palaces:descendant_eq:命宫",
                  "命宫可见",
                ],
              },
              {
                rule_id: "ziwei/unknown-pack#U-02",
                local_rule_id: "U-02",
                title: "先看命身",
                source_pack: "ziwei/unknown-pack",
                source_anchor: "notes.md#L2",
                status: "predicate_matched_not_verdict",
                fact_paths: ["fact:/chart_facts/output/star_facts/紫微/palace"],
                predicate_audit: ["紫微坐命"],
              },
            ],
          }),
        })}
      />,
    );

    const block = screen.getByRole("region", { name: "古法命中" });
    const fold = block.querySelector("details");
    expect(fold).not.toBeNull();
    expect(fold).not.toHaveAttribute("open");
    expect(within(block).getByText("命中古法 2 条 · 可核验")).toBeVisible();
    expect(within(block).queryByText("至玄至微")).not.toBeVisible();
    expect(
      screen.queryByText("source_conditioned_patterns"),
    ).not.toBeInTheDocument();
    expect(
      within(block).queryByText(
        /fact_paths|chart_facts|palaces\/0|predicate_matched/,
      ),
    ).not.toBeInTheDocument();
    expect(
      within(block).queryByText(/吉凶|大吉|大凶|GAP-ZW/),
    ).not.toBeInTheDocument();

    await user.click(within(block).getByText("命中古法 2 条 · 可核验"));
    expect(fold).toHaveAttribute("open");
    expect(within(block).getByText("至玄至微")).toBeVisible();
    expect(within(block).getByText("太微赋")).toBeVisible();
    expect(within(block).getByText("先看命身")).toBeVisible();
    expect(within(block).queryByText("unknown-pack")).not.toBeInTheDocument();
    expect(within(block).queryByText("斗数骨髓赋")).not.toBeInTheDocument();
    expect(within(block).getAllByText("条件命中，非断语")).toHaveLength(2);
    expect(within(block).getByText("rules.md#L9-L16")).toBeVisible();
    expect(within(block).getByText("notes.md#L2")).toBeVisible();
    expect(
      within(block).getByText("/output/palaces:descendant_eq:命宫"),
    ).toBeVisible();
    expect(within(block).getByText("命宫可见")).toBeVisible();
    expect(within(block).getByText("紫微坐命")).toBeVisible();
    expect(within(block).queryByText("服务端已记录")).not.toBeInTheDocument();
    expect(
      within(block).queryByText(/fact_paths|chart_facts|palaces\/0/),
    ).not.toBeInTheDocument();

    await user.click(within(block).getByRole("button", { name: "至玄至微" }));
    expect(chart().palaces[0]?.earthly_branch).toBe("酉");
    expect(palaceButton("酉")).toHaveAttribute("data-highlight", "primary");
    expect(palaceButton("卯")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("丑")).toHaveAttribute("data-highlight", "related");
    expect(palaceButton("巳")).toHaveAttribute("data-highlight", "related");
    expect(within(block).getByText("至玄至微").closest("li")).toHaveAttribute(
      "data-highlight",
      "true",
    );
    expect(
      within(block).getByText("先看命身").closest("li"),
    ).not.toHaveAttribute("data-highlight");
  });

  it("removes candidate, summary and deep-read sections when interpretation is gated", () => {
    const gatedView = chart({
      core_facts: facts({
        source_conditioned_patterns: [
          {
            rule_id: "ziwei/taiwei-fu#TR-01",
            local_rule_id: "TR-01",
            title: "至玄至微",
            source_pack: "ziwei/taiwei-fu",
            source_anchor: "rules.md#L9-L16",
            status: "predicate_matched_not_verdict",
            fact_paths: ["fact:/chart_facts/output/palaces/0/name"],
            predicate_audit: ["/output/palaces:descendant_eq:命宫"],
          },
        ],
      }),
    });
    const { rerender } = render(
      <ZiweiPalaceBoard showInterpretiveSections={false} view={gatedView} />,
    );

    expect(ring()).toBeVisible();
    expect(
      screen.queryByRole("region", { name: "古法命中" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: "基础摘要" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "深读" }),
    ).not.toBeInTheDocument();

    rerender(<ZiweiPalaceBoard showInterpretiveSections view={gatedView} />);
    expect(screen.getByRole("region", { name: "古法命中" })).toBeVisible();
    expect(screen.getByRole("region", { name: "基础摘要" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
  });

  it("does not invent a palace click when fact_paths do not map", async () => {
    const user = userEvent.setup();
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            source_conditioned_patterns: [
              {
                rule_id: "ziwei/taiwei-fu#TR-09",
                local_rule_id: "TR-09",
                title: "先看命身",
                source_pack: "ziwei/taiwei-fu",
                source_anchor: "rules.md#L20",
                status: "predicate_matched_not_verdict",
                fact_paths: [
                  "fact:/chart_facts/output/palaces/12/name",
                  "fact:/chart_facts/output/ming_shen",
                ],
                predicate_audit: ["命身已返回"],
              },
            ],
          }),
        })}
      />,
    );

    const block = screen.getByRole("region", { name: "古法命中" });
    await user.click(within(block).getByText("命中古法 1 条 · 可核验"));
    expect(within(block).getByText("先看命身")).toBeVisible();
    expect(
      within(block).queryByRole("button", { name: "先看命身" }),
    ).not.toBeInTheDocument();
    expect(palaceButton("子")).not.toHaveAttribute("data-highlight");
  });

  it("maps a branch segment in fact_paths and reverse-highlights the card", async () => {
    const user = userEvent.setup();
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            source_conditioned_patterns: [
              {
                rule_id: "ziwei/ziwei-doushu-quanshu#ZW-01",
                local_rule_id: "ZW-01",
                title: "紫微坐命",
                source_pack: "ziwei/ziwei-doushu-quanshu",
                source_anchor: "juan-01#L10",
                status: "predicate_matched_not_verdict",
                fact_paths: ["fact:/chart_facts/output/palaces/寅/major_stars"],
                predicate_audit: ["紫微在寅"],
              },
            ],
          }),
        })}
      />,
    );

    const block = screen.getByRole("region", { name: "古法命中" });
    await user.click(within(block).getByText("命中古法 1 条 · 可核验"));
    expect(within(block).getByText("紫微斗数全书")).toBeVisible();
    await user.click(within(block).getByRole("button", { name: "紫微坐命" }));
    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "primary");
    expect(within(block).getByText("紫微坐命").closest("li")).toHaveAttribute(
      "data-highlight",
      "true",
    );

    await user.click(palaceButton("午"));
    expect(palaceButton("午")).toHaveAttribute("data-highlight", "primary");
    expect(
      within(block).getByText("紫微坐命").closest("li"),
    ).not.toHaveAttribute("data-highlight");
  });

  it("drops the whole drawer when patterns are missing, empty, malformed, or not a match", () => {
    const { rerender } = render(<ZiweiPalaceBoard view={chart()} />);
    expect(
      screen.queryByRole("region", { name: "古法命中" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("命中古法")).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            source_conditioned_patterns: [],
          }),
        })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "古法命中" }),
    ).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            source_conditioned_patterns: [
              {
                title: "至玄至微",
                source_pack: "ziwei/taiwei-fu",
              },
            ] as unknown as ZiweiCoreFacts["source_conditioned_patterns"],
          }),
        })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "古法命中" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("至玄至微")).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            source_conditioned_patterns: [
              {
                rule_id: "ziwei/taiwei-fu#TR-01",
                local_rule_id: "TR-01",
                title: "至玄至微",
                source_pack: "ziwei/taiwei-fu",
                source_anchor: "rules.md#L9-L16",
                status: "candidate_only",
                fact_paths: ["fact:/chart_facts/output/palaces/0/name"],
                predicate_audit: ["/output/palaces:descendant_eq:命宫"],
              },
            ] as unknown as ZiweiCoreFacts["source_conditioned_patterns"],
          }),
        })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "古法命中" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("至玄至微")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-ZW/)).not.toBeInTheDocument();
  });

  it("keeps the source-pattern drawer off shared pages", () => {
    const board = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-palace-board.tsx"),
      "utf8",
    );
    const drawer = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-source-pattern-drawer.tsx",
      ),
      "utf8",
    );
    const css = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-source-pattern-drawer.module.css",
      ),
      "utf8",
    );
    const runtime = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const experience = readFileSync(
      resolve(process.cwd(), "src/components/task/product-task-experience.tsx"),
      "utf8",
    );
    expect(board).toContain("ziwei-source-pattern-drawer");
    expect(drawer).not.toMatch(
      /runtime-chart|product-task-experience|GAP-ZW|bazi-chart|evidence\[\]|服务端已记录/,
    );
    expect(css).toMatch(/--color-evidence/);
    expect(css).toMatch(/--color-evidence-line/);
    expect(css).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(css).not.toMatch(
      /color-success|color-danger|surface-success|surface-danger/,
    );
    expect(runtime).not.toContain("ziwei-source-pattern-drawer");
    expect(experience).not.toContain("ziwei-source-pattern-drawer");
  });

  it("uses Xuan Order hairlines and keeps a 360 list fallback", () => {
    const css = boardCss();
    const board = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-palace-board.tsx"),
      "utf8",
    );
    expect(css).toMatch(/\.ring\s*\{[^}]*grid-template-columns:\s*repeat\(4,/s);
    expect(css).toMatch(/\[data-branch="巳"\]\s*\{[^}]*grid-column:\s*1/s);
    expect(css).toMatch(/\[data-branch="午"\]\s*\{[^}]*grid-column:\s*2/s);
    expect(css).toMatch(/\[data-branch="亥"\]\s*\{[^}]*grid-column:\s*4/s);
    expect(css).toMatch(/\[data-life="true"\]\s*\{[^}]*1px/s);
    expect(css).toMatch(/font-family:\s*var\(--font-domain\)/);
    expect(css).toMatch(/--color-evidence/);
    expect(css).toMatch(/--ds-accent-soft/);
    expect(css).toMatch(/--ds-line-strong/);
    expect(css).toMatch(/--ds-focus/);
    expect(css).toMatch(/min-height:\s*var\(--ds-touch-min\)/);
    expect(board).toMatch(/max-width:\s*22\.5rem/);
    expect(css).not.toMatch(
      /color-success|color-danger|surface-success|surface-danger/,
    );
    expect(css).not.toMatch(
      /linear-gradient|radial-gradient|text-shadow|box-shadow:\s*0 0/,
    );
    expect(css).not.toMatch(/星曙/);
  });

  it("keeps the ring grid ownership valid for interactive and structural cells", () => {
    const { rerender } = render(<ZiweiPalaceBoard view={chart()} />);

    const readyRows = [...ring().children];
    expect(readyRows).toHaveLength(13);
    for (const row of readyRows) {
      expect(row).toHaveAttribute("role", "row");
      expect(row.children).toHaveLength(1);
      expect(row.children[0]).toHaveAttribute("role", "gridcell");
    }

    rerender(<ZiweiPalaceBoard mode="silhouette" />);
    const structuralRows = [...ring().children];
    expect(structuralRows).toHaveLength(13);
    for (const row of structuralRows) {
      expect(row).toHaveAttribute("role", "row");
      expect(row.children[0]).toHaveAttribute("role", "gridcell");
    }
  });
});

describe("紫微 S3 M8 免费基础摘要 + 深读入口", () => {
  type Limit = NonNullable<ZiweiCoreFacts["major_limits"]>[number];

  function limit(overrides: Partial<Limit> = {}): Limit {
    return {
      palace: "命宫",
      palace_index: 2,
      palace_branch: "寅",
      age_start: 3,
      age_end: 12,
      sequence: 1,
      heavenly_stem: "壬",
      earthly_branch: "寅",
      direction: "reverse",
      ...overrides,
    };
  }

  const TWO_LIMITS = [
    limit(),
    limit({
      palace: "官禄",
      palace_index: 6,
      palace_branch: "午",
      age_start: 13,
      age_end: 22,
      sequence: 2,
      heavenly_stem: "丙",
      earthly_branch: "午",
    }),
  ] as const;

  const OFFER = {
    name: "紫微宫位深读",
    coverage: "当前这张已排出命盘的宫位与四化",
    priceText: "由服务端标价",
    refundBoundary: "未交付可退",
  };

  function summary() {
    return screen.getByRole("region", { name: "基础摘要" });
  }

  function withoutLifeStars(view: ZiweiChartViewModel): ZiweiChartViewModel {
    return {
      ...view,
      palaces: view.palaces.map((item) =>
        item.palace_id === view.life_palace_id
          ? { ...item, major_stars: [] }
          : item,
      ),
    };
  }

  it("restates on-screen life-palace majors, five-elements class and listed major-limit steps", () => {
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            major_limits: [...TWO_LIMITS],
            active_major_limit: { palace: "命宫" },
          }),
        })}
      />,
    );

    const block = summary();
    expect(block).toHaveTextContent("命宫主星 紫微、天府");
    expect(block).toHaveTextContent("水二局");
    expect(block).toHaveTextContent("大限 2 步已列");
    expect(block).not.toHaveTextContent("贪狼");
    expect(block).not.toHaveTextContent("当前");
    expect(block).not.toHaveTextContent(/强弱|喜忌|吉凶|旺衰|大吉|大凶/);
    expect(block).not.toHaveTextContent(/GAP-ZW/);
  });

  it("drops missing clauses and never fills life-palace stars from soul_star or star_facts", () => {
    const { rerender } = render(
      <ZiweiPalaceBoard
        view={withoutLifeStars(
          chart({
            core_facts: facts({
              five_elements_class: "水二局",
              major_limits: null,
            }),
          }),
        )}
      />,
    );

    expect(summary()).toHaveTextContent("水二局");
    expect(summary()).not.toHaveTextContent("命宫主星");
    expect(summary()).not.toHaveTextContent("紫微");
    expect(summary()).not.toHaveTextContent("贪狼");
    expect(summary()).not.toHaveTextContent("大限");

    rerender(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            five_elements_class: null,
            major_limits: null,
          }),
        })}
      />,
    );
    expect(summary()).toHaveTextContent("命宫主星 紫微、天府");
    expect(summary()).not.toHaveTextContent("水二局");
    expect(summary()).not.toHaveTextContent("大限");
  });

  it("hides the whole summary when no clause can be restated", () => {
    render(
      <ZiweiPalaceBoard
        view={withoutLifeStars(
          chart({
            core_facts: facts({
              five_elements_class: null,
              major_limits: null,
            }),
          }),
        )}
      />,
    );

    expect(
      screen.queryByRole("region", { name: "基础摘要" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("命宫主星")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
  });

  it("does not restate sequence-only limits in the summary", () => {
    render(
      <ZiweiPalaceBoard
        view={chart({
          core_facts: facts({
            major_limits: null,
            major_limit_sequence: [
              limit({
                palace: "假宫",
                sequence: 9,
                age_start: 99,
                age_end: 108,
                heavenly_stem: "癸",
                earthly_branch: "卯",
                palace_branch: "卯",
              }),
            ],
          }),
        })}
      />,
    );

    expect(screen.getByRole("region", { name: "大限" })).toBeVisible();
    expect(summary()).not.toHaveTextContent("大限");
    expect(summary()).not.toHaveTextContent("假宫");
  });

  it("shows the no-offer deep-read gate without prices or checkout", () => {
    render(<ZiweiPalaceBoard view={chart()} />);

    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(
      screen.getByRole("status", { name: "测试期未开放" }),
    ).toHaveAttribute("data-state", "unavailable");
    const deep = screen
      .getByRole("heading", { name: "深读" })
      .closest("section");
    expect(deep).toHaveTextContent("命宫");
    expect(deep).toHaveTextContent("紫微");
    expect(deep).toHaveTextContent("禄");
    expect(deep).not.toHaveTextContent(/吉凶|大吉|大凶|旺衰/);
    expect(deep).not.toHaveTextContent(/GAP-ZW/);
    expect(screen.queryByText(/¥|￥|\d+\s*元/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /结账|购买|支付/ }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("reading_version_id")).not.toBeInTheDocument();
    expect(screen.queryByText("offer_id")).not.toBeInTheDocument();
  });

  it("does not quote missing palace stars or transformations", () => {
    render(
      <ZiweiPalaceBoard
        view={withoutLifeStars(
          chart({
            core_facts: facts({
              transformations: null,
              five_elements_class: null,
              major_limits: null,
            }),
          }),
        )}
      />,
    );

    const deep = screen
      .getByRole("heading", { name: "深读" })
      .closest("section");
    expect(deep).not.toHaveTextContent("紫微");
    expect(deep).not.toHaveTextContent("禄");
    expect(deep).not.toHaveTextContent("化禄");
  });

  it("renders a passed offer card without inventing checkout, and confirming only says 确认中", () => {
    const { rerender } = render(
      <ZiweiPalaceBoard view={chart()} offer={OFFER} />,
    );

    expect(screen.getByText("紫微宫位深读")).toBeVisible();
    expect(screen.getByText("当前这张已排出命盘的宫位与四化")).toBeVisible();
    expect(screen.getByText("由服务端标价")).toBeVisible();
    expect(screen.getByText("未交付可退")).toBeVisible();
    expect(screen.getByText("绑定当前这张已排出的命盘")).toBeVisible();
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(
      screen.queryByRole("status", { name: "测试期未开放" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /结账|购买/ }),
    ).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard view={chart()} offer={OFFER} s4Phase="confirming" />,
    );

    expect(screen.getByRole("status", { name: "确认中" })).toBeVisible();
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(screen.queryByText(/订单号/)).not.toBeInTheDocument();
  });

  it("uses locked and fake-gateway copy without treating them as paid", () => {
    const { rerender } = render(
      <ZiweiPalaceBoard view={chart()} s4Phase="locked" />,
    );

    expect(
      screen.getByRole("status", { name: "深读暂未解锁" }),
    ).toHaveAttribute("data-state", "locked");
    expect(
      screen.queryByRole("status", { name: "测试期未开放" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /结账|购买/ }),
    ).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart()}
        offer={OFFER}
        s4Phase="gateway_unavailable"
      />,
    );

    expect(
      screen.getByRole("status", { name: "支付暂时不可用" }),
    ).toHaveAttribute("data-state", "unavailable");
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /结账|购买|支付/ }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/订单号/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "登录后继续" }),
    ).not.toBeInTheDocument();
  });

  it("keeps silhouette and loading free of summary and deep-read copy", () => {
    const { rerender } = render(<ZiweiPalaceBoard mode="silhouette" />);
    expect(
      screen.queryByRole("region", { name: "基础摘要" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "深读" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("测试期未开放")).not.toBeInTheDocument();

    rerender(<ZiweiPalaceBoard mode="loading" />);
    expect(
      screen.queryByRole("region", { name: "基础摘要" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "深读" }),
    ).not.toBeInTheDocument();
  });

  it("keeps the free-summary module off shared pages and off other arts", () => {
    const board = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-palace-board.tsx"),
      "utf8",
    );
    const summarySource = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-free-summary.tsx"),
      "utf8",
    );
    const css = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-free-summary.module.css",
      ),
      "utf8",
    );
    const runtime = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const experience = readFileSync(
      resolve(process.cwd(), "src/components/task/product-task-experience.tsx"),
      "utf8",
    );
    expect(board).toContain("ziwei-free-summary");
    expect(summarySource).not.toMatch(
      /bazi-chart|liuyao-line-tower|runtime-chart|product-task-experience|GAP-ZW/,
    );
    expect(css).toMatch(/--color-text/);
    expect(css).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(css).not.toMatch(
      /color-success|color-danger|surface-success|surface-danger/,
    );
    expect(css).not.toMatch(
      /linear-gradient|radial-gradient|box-shadow:\s*0 0/,
    );
    expect(runtime).not.toContain("ziwei-free-summary");
    expect(experience).not.toContain("ziwei-free-summary");
  });
});

describe("紫微 S3 M1 口径条", () => {
  function caliber() {
    return screen.getByRole("region", { name: "口径" });
  }

  it("renders chinese_date as-is above the ring and list", () => {
    const view = chart({
      core_facts: facts({
        chinese_date: "农历甲戌年三月二十 卯时",
        chart_convention: { leap_month: "后月", zi_hour: "晚子" },
      }),
    });
    const { rerender } = render(<ZiweiPalaceBoard view={view} />);

    expect(caliber()).toHaveTextContent("农历甲戌年三月二十 卯时");
    expect(screen.queryByText("leap_month")).not.toBeInTheDocument();
    expect(screen.queryByText("后月")).not.toBeInTheDocument();
    expect(screen.queryByText("晚子")).not.toBeInTheDocument();
    expect(screen.queryByText("chart_convention")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-ZW/)).not.toBeInTheDocument();

    rerender(<ZiweiPalaceBoard layout="list" view={view} />);
    expect(caliber()).toHaveTextContent("农历甲戌年三月二十 卯时");
  });

  it("hides the whole bar when chinese_date is missing or blank", () => {
    const { rerender } = render(<ZiweiPalaceBoard view={chart()} />);
    expect(
      screen.queryByRole("region", { name: "口径" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("农历")).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({ core_facts: facts({ chinese_date: "" }) })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "口径" }),
    ).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({ core_facts: facts({ chinese_date: "   " }) })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "口径" }),
    ).not.toBeInTheDocument();

    rerender(
      <ZiweiPalaceBoard
        view={chart({ core_facts: facts({ chinese_date: null }) })}
      />,
    );
    expect(
      screen.queryByRole("region", { name: "口径" }),
    ).not.toBeInTheDocument();
  });

  it("keeps silhouette and loading free of the caliber bar", () => {
    const view = chart({
      core_facts: facts({ chinese_date: "农历甲戌年三月二十 卯时" }),
    });
    const { rerender } = render(
      <ZiweiPalaceBoard mode="silhouette" view={view} />,
    );
    expect(
      screen.queryByRole("region", { name: "口径" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("农历甲戌年三月二十 卯时"),
    ).not.toBeInTheDocument();

    rerender(<ZiweiPalaceBoard mode="loading" view={view} />);
    expect(
      screen.queryByRole("region", { name: "口径" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("农历甲戌年三月二十 卯时"),
    ).not.toBeInTheDocument();
  });

  it("keeps the caliber module off shared pages", () => {
    const board = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-palace-board.tsx"),
      "utf8",
    );
    const caliberSource = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-caliber-bar.tsx"),
      "utf8",
    );
    const css = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-caliber-bar.module.css",
      ),
      "utf8",
    );
    const runtime = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const experience = readFileSync(
      resolve(process.cwd(), "src/components/task/product-task-experience.tsx"),
      "utf8",
    );
    expect(board).toContain("ziwei-caliber-bar");
    expect(caliberSource).not.toMatch(
      /bazi-chart|daliuren-board|runtime-chart|product-task-experience|GAP-ZW/,
    );
    expect(css).toMatch(/--color-text/);
    expect(css).not.toMatch(
      /color-success|color-danger|surface-success|surface-danger/,
    );
    expect(css).not.toMatch(
      /linear-gradient|radial-gradient|box-shadow:\s*0 0/,
    );
    expect(runtime).not.toContain("ziwei-caliber-bar");
    expect(experience).not.toContain("ziwei-caliber-bar");
  });
});

describe("紫微 S3 360 环转列表", () => {
  function thumbs() {
    return screen.getByRole("navigation", { name: "宫位缩略" });
  }

  function list() {
    return screen.getByRole("list", { name: "十二宫列表" });
  }

  function thumb(branch: string) {
    return thumbs().querySelector(`[data-branch="${branch}"]`) as HTMLElement;
  }

  function card(branch: string) {
    return list().querySelector(`[data-branch="${branch}"]`) as HTMLElement;
  }

  it("turns ready-state thumbs into 44px buttons that select a card and scroll to it", async () => {
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard layout="list" view={chart()} />);

    const noon = within(thumbs()).getByRole("button", { name: /午/ });
    expect(noon).toHaveAttribute("data-branch", "午");
    expect(noon.textContent).toBe("官");
    expect(noon.textContent).not.toContain("太阳");
    expect(thumbs().querySelectorAll("button[data-branch]")).toHaveLength(12);

    await user.click(noon);
    expect(thumb("午")).toHaveAttribute("data-highlight", "primary");
    expect(card("午")).toHaveAttribute("data-highlight", "primary");
    expect(card("午")).toHaveAttribute("id", "ziwei-list-午");
    expect(noon).toHaveAttribute("aria-controls", "ziwei-list-午");
    expect(scrollIntoView).toHaveBeenCalled();

    await user.click(noon);
    expect(thumb("午")).toHaveAttribute("data-highlight", "primary");
    expect(card("午")).toHaveAttribute("data-highlight", "primary");
    expect(screen.queryByText(/吉凶|大吉|大凶|GAP-ZW/)).not.toBeInTheDocument();
  });

  it("writes the current branch back when a list card is clicked or focused", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard layout="list" view={chart()} />);

    await user.click(card("卯"));
    expect(card("卯")).toHaveAttribute("data-highlight", "primary");
    expect(thumb("卯")).toHaveAttribute("data-highlight", "primary");

    await act(async () => {
      card("子").focus();
    });
    expect(card("子")).toHaveAttribute("data-highlight", "primary");
    expect(thumb("子")).toHaveAttribute("data-highlight", "primary");
    expect(thumb("卯")).not.toHaveAttribute("data-highlight", "primary");
  });

  it("keeps silhouette thumbs inert and free of invented stars", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard layout="list" mode="silhouette" view={chart()} />);

    expect(within(thumbs()).queryByRole("button")).not.toBeInTheDocument();
    expect(thumbs().querySelectorAll("[data-branch]")).toHaveLength(12);
    expect(screen.queryByText("紫微")).not.toBeInTheDocument();
    expect(screen.queryByText("太阳")).not.toBeInTheDocument();

    await user.click(thumb("午"));
    expect(thumb("午")).not.toHaveAttribute("data-highlight");
    expect(card("午")).not.toHaveAttribute("data-highlight");
  });

  it("keeps list-thumb styles at 44px without luck colors", () => {
    const css = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-palace-board.module.css",
      ),
      "utf8",
    );
    expect(css).toMatch(
      /\.thumb[^{]*\{[\s\S]*min-height:\s*var\(--target-min\)/,
    );
    expect(css).not.toMatch(
      /color-success|color-danger|surface-success|surface-danger/,
    );
    expect(css).not.toMatch(/GAP-ZW/);
  });
});

describe("紫微 S3 360 默认窄屏真渲 list", () => {
  const originalMatchMedia = window.matchMedia;

  function mockNarrow(matches: boolean) {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === "(max-width: 22.5rem)" ? matches : false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  }

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  it("renders the list DOM when layout is omitted and the 22.5rem query matches", async () => {
    mockNarrow(true);
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={chart()} />);

    await waitFor(() =>
      expect(
        screen.queryByRole("grid", { name: "十二宫环盘" }),
      ).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("navigation", { name: "宫位缩略" })).toBeVisible();
    expect(screen.getByRole("list", { name: "十二宫列表" })).toBeVisible();
    expect(
      screen
        .getByRole("navigation", { name: "宫位缩略" })
        .querySelectorAll("button[data-branch]"),
    ).toHaveLength(12);

    await user.click(
      within(screen.getByRole("navigation", { name: "宫位缩略" })).getByRole(
        "button",
        { name: /午/ },
      ),
    );
    expect(
      screen
        .getByRole("navigation", { name: "宫位缩略" })
        .querySelector('[data-branch="午"]'),
    ).toHaveAttribute("data-highlight", "primary");
    expect(
      screen
        .getByRole("list", { name: "十二宫列表" })
        .querySelector('[data-branch="午"]'),
    ).toHaveAttribute("data-highlight", "primary");
  });

  it("keeps the ring when the query does not match, and honors an explicit layout", () => {
    mockNarrow(false);
    const { rerender } = render(<ZiweiPalaceBoard view={chart()} />);
    expect(screen.getByRole("grid", { name: "十二宫环盘" })).toBeVisible();
    expect(
      screen.queryByRole("navigation", { name: "宫位缩略" }),
    ).not.toBeInTheDocument();

    mockNarrow(true);
    rerender(<ZiweiPalaceBoard layout="ring" view={chart()} />);
    expect(screen.getByRole("grid", { name: "十二宫环盘" })).toBeVisible();
    expect(
      screen.queryByRole("navigation", { name: "宫位缩略" }),
    ).not.toBeInTheDocument();

    mockNarrow(false);
    rerender(<ZiweiPalaceBoard layout="list" view={chart()} />);
    expect(
      screen.queryByRole("grid", { name: "十二宫环盘" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "宫位缩略" })).toBeVisible();
  });

  it("does not hide an explicit ring with a 22.5rem display:none rule", () => {
    const css = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-palace-board.module.css",
      ),
      "utf8",
    );
    expect(css).not.toMatch(
      /max-width:\s*22\.5rem[\s\S]*\.ring\s*\{[\s\S]*display:\s*none/,
    );
    expect(css).not.toMatch(/GAP-ZW/);
  });
});

describe("紫微 S3 M2 十二神足注", () => {
  function godsView() {
    return chart({
      palaces: chart().palaces.map((item) => {
        if (item.earthly_branch === "寅") {
          return {
            ...item,
            changsheng12: "长生",
            boshi12: "博士",
            jiangqian12: "将星",
            suiqian12: "岁建",
          };
        }
        if (item.earthly_branch === "午") {
          return {
            ...item,
            changsheng12: "  ",
            boshi12: "力士",
            jiangqian12: null,
            suiqian12: "晦气",
          };
        }
        return item;
      }),
    });
  }

  it("defaults to compact changsheng12 only and expands four sets in order", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={godsView()} />);

    const density = screen.getByRole("group", { name: "十二神密度" });
    expect(
      within(density).getByRole("button", { name: "精简" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(within(palaceButton("寅")).getByText("长生")).toBeVisible();
    expect(
      within(palaceButton("寅")).queryByText("博士"),
    ).not.toBeInTheDocument();
    expect(
      within(palaceButton("寅")).queryByText("将星"),
    ).not.toBeInTheDocument();
    expect(
      within(palaceButton("寅")).queryByText("岁建"),
    ).not.toBeInTheDocument();
    expect(
      within(palaceButton("午")).queryByText("力士"),
    ).not.toBeInTheDocument();
    expect(
      within(palaceButton("午")).queryByText("晦气"),
    ).not.toBeInTheDocument();
    expect(
      within(palaceButton("午")).queryByLabelText("十二神"),
    ).not.toBeInTheDocument();

    await user.click(within(density).getByRole("button", { name: "完整" }));
    const lifeGods = [
      ...within(palaceButton("寅"))
        .getByLabelText("十二神")
        .querySelectorAll("[data-god]"),
    ].map((node) => node.textContent);
    expect(lifeGods).toEqual(["长生", "博士", "将星", "岁建"]);
    const noonGods = [
      ...within(palaceButton("午"))
        .getByLabelText("十二神")
        .querySelectorAll("[data-god]"),
    ].map((node) => node.getAttribute("data-god"));
    expect(noonGods).toEqual(["boshi12", "suiqian12"]);
    expect(within(palaceButton("午")).getByText("力士")).toBeVisible();
    expect(within(palaceButton("午")).getByText("晦气")).toBeVisible();
    expect(
      within(palaceButton("午")).queryByText("长生"),
    ).not.toBeInTheDocument();
  });

  it("applies the same density switch to the 360 list and hides the switch when no gods exist", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <ZiweiPalaceBoard layout="list" view={godsView()} />,
    );
    const list = screen.getByRole("list", { name: "十二宫列表" });
    expect(
      within(list.querySelector('[data-branch="寅"]') as HTMLElement).getByText(
        "长生",
      ),
    ).toBeVisible();
    expect(
      within(
        list.querySelector('[data-branch="寅"]') as HTMLElement,
      ).queryByText("博士"),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "完整" }));
    expect(
      within(list.querySelector('[data-branch="寅"]') as HTMLElement).getByText(
        "博士",
      ),
    ).toBeVisible();

    rerender(<ZiweiPalaceBoard view={chart()} />);
    expect(
      screen.queryByRole("group", { name: "十二神密度" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("长生")).not.toBeInTheDocument();
    expect(screen.queryByText("博士")).not.toBeInTheDocument();
  });

  it("does not invent twelve gods in silhouette or loading", () => {
    const { rerender } = render(
      <ZiweiPalaceBoard mode="silhouette" view={godsView()} />,
    );
    expect(
      screen.queryByRole("group", { name: "十二神密度" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("长生")).not.toBeInTheDocument();
    expect(screen.queryByText("博士")).not.toBeInTheDocument();
    rerender(<ZiweiPalaceBoard mode="loading" view={godsView()} />);
    expect(screen.queryByText("将星")).not.toBeInTheDocument();
    expect(screen.queryByText("岁建")).not.toBeInTheDocument();
  });

  it("keeps twelve-god footnotes in paper-ink tokens", () => {
    const css = boardCss();
    expect(css).toMatch(
      /\.gods[^{]*\{[\s\S]*font-size:\s*var\(--font-size-meta\)/,
    );
    expect(css).not.toMatch(
      /color-success|color-danger|surface-success|surface-danger/,
    );
    expect(css).not.toMatch(/GAP-ZW/);
  });
});

describe("紫微 S3 M2 宫位详情抽屉", () => {
  function drawerView() {
    return chart({
      palaces: chart().palaces.map((item) => {
        if (item.earthly_branch === "寅") {
          return {
            ...item,
            changsheng12: "长生",
            boshi12: "博士",
            ages: [4, 16, 28],
          };
        }
        if (item.earthly_branch === "午") {
          return { ...item, ages: undefined };
        }
        return item;
      }),
    });
  }

  function detail() {
    return screen.getByRole("dialog", { name: "宫位详情" });
  }

  it("opens the current palace on Enter and keeps a click as highlight-only", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={drawerView()} />);

    expect(
      screen.queryByRole("dialog", { name: "宫位详情" }),
    ).not.toBeInTheDocument();
    await user.click(palaceButton("寅"));
    expect(palaceButton("寅")).toHaveAttribute("data-highlight", "primary");
    expect(
      screen.queryByRole("dialog", { name: "宫位详情" }),
    ).not.toBeInTheDocument();

    palaceButton("寅").focus();
    await user.keyboard("{Enter}");
    expect(detail()).toBeVisible();
    expect(within(detail()).getByText("命宫")).toBeVisible();
    expect(within(detail()).getByText("壬寅")).toBeVisible();
    expect(within(detail()).getByText("命")).toBeVisible();
    expect(within(detail()).getByText("3–12")).toBeVisible();
    expect(within(detail()).getByText("4、16、28")).toBeVisible();
    expect(within(detail()).getByText("紫微")).toBeVisible();
    expect(within(detail()).getByText("天府")).toBeVisible();
    expect(within(detail()).getByText("文昌")).toBeVisible();
    expect(within(detail()).getByText("天刑")).toBeVisible();
    expect(within(detail()).getByText("长生")).toBeVisible();
    expect(within(detail()).getByText("博士")).toBeVisible();
    expect(screen.queryByText(/吉凶|大吉|大凶|GAP-ZW/)).not.toBeInTheDocument();
  });

  it("omits missing ages and restores focus after Escape", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard view={drawerView()} />);

    palaceButton("午").focus();
    await user.keyboard("{Enter}");
    expect(within(detail()).getByText("官禄")).toBeVisible();
    expect(within(detail()).getByText("太阳")).toBeVisible();
    expect(within(detail()).queryByText("小限")).not.toBeInTheDocument();
    expect(within(detail()).queryByText("4、16、28")).not.toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(
      screen.queryByRole("dialog", { name: "宫位详情" }),
    ).not.toBeInTheDocument();
    expect(palaceButton("午")).toHaveFocus();
  });

  it("traps forward and reverse Tab inside the modal drawer before restoring its trigger", async () => {
    const user = userEvent.setup();
    render(<ZiweiPalaceBoard layout="list" view={drawerView()} />);
    const lifeCard = screen
      .getByRole("list", { name: "十二宫列表" })
      .querySelector('[data-branch="寅"]') as HTMLElement;
    const trigger = within(lifeCard).getByRole("button", { name: "详情" });

    await user.click(trigger);
    const close = within(detail()).getByRole("button", { name: "关闭" });
    expect(close).toHaveFocus();

    await user.tab();
    expect(close).toHaveFocus();
    await user.tab({ shift: true });
    expect(close).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(
      screen.queryByRole("dialog", { name: "宫位详情" }),
    ).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("opens from the list 详情 control and stays closed in silhouette or loading", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <ZiweiPalaceBoard layout="list" view={drawerView()} />,
    );
    const list = screen.getByRole("list", { name: "十二宫列表" });
    const lifeCard = list.querySelector('[data-branch="寅"]') as HTMLElement;
    await user.click(within(lifeCard).getByRole("button", { name: "详情" }));
    expect(within(detail()).getByText("紫微")).toBeVisible();

    await user.click(within(detail()).getByRole("button", { name: "关闭" }));
    expect(
      screen.queryByRole("dialog", { name: "宫位详情" }),
    ).not.toBeInTheDocument();

    rerender(<ZiweiPalaceBoard mode="silhouette" view={drawerView()} />);
    expect(
      screen.queryByRole("dialog", { name: "宫位详情" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "详情" }),
    ).not.toBeInTheDocument();
    rerender(<ZiweiPalaceBoard mode="loading" view={drawerView()} />);
    expect(
      screen.queryByRole("dialog", { name: "宫位详情" }),
    ).not.toBeInTheDocument();
  });

  it("keeps the palace drawer off shared pages and off the source-pattern drawer", () => {
    const board = readFileSync(
      resolve(process.cwd(), "src/components/readings/ziwei-palace-board.tsx"),
      "utf8",
    );
    const drawer = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-palace-detail-drawer.tsx",
      ),
      "utf8",
    );
    const css = readFileSync(
      resolve(
        process.cwd(),
        "src/components/readings/ziwei-palace-detail-drawer.module.css",
      ),
      "utf8",
    );
    const runtime = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const experience = readFileSync(
      resolve(process.cwd(), "src/components/task/product-task-experience.tsx"),
      "utf8",
    );
    expect(board).toContain("ziwei-palace-detail-drawer");
    expect(drawer).not.toMatch(
      /ziwei-source-pattern-drawer|runtime-chart|product-task-experience|GAP-ZW/,
    );
    expect(css).toMatch(/--color-text/);
    expect(css).not.toMatch(
      /color-success|color-danger|surface-success|surface-danger/,
    );
    expect(runtime).not.toContain("ziwei-palace-detail-drawer");
    expect(experience).not.toContain("ziwei-palace-detail-drawer");
  });
});
