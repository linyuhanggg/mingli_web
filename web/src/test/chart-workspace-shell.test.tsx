import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState, type KeyboardEvent } from "react";
import { describe, expect, it } from "vitest";

import { ChartWorkspaceShell } from "@/components/readings/chart-workspace-shell";
import {
  buildBaziWorkspaceView,
  resolveBaziFocusDetail,
  type ChartWorkspaceView,
  type WorkspaceCell,
} from "@/lib/chart-workspace";

const FOUR_PILLARS = {
  year: "甲子",
  month: "丙寅",
  day: "戊午",
  hour: "丁卯",
};

/**
 * Minimal board harness mirroring the pillar board interaction grammar:
 * focusable cells with roving tabindex, arrow-key movement, Enter activation.
 */
function PillarBoard({
  cells,
  selected,
  onSelect,
}: Readonly<{
  cells: WorkspaceCell[];
  selected: string | null;
  onSelect: (cellId: string) => void;
}>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  function focusAt(index: number) {
    if (index >= 0 && index < refs.current.length) {
      refs.current[index]?.focus();
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      focusAt((index + 1) % cells.length);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      focusAt((index - 1 + cells.length) % cells.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusAt(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusAt(cells.length - 1);
    }
  }

  return (
    <div role="group" aria-label="四柱">
      {cells.map((cell, index) => (
        <button
          key={cell.id}
          type="button"
          ref={(element) => {
            refs.current[index] = element;
          }}
          tabIndex={index === 0 ? 0 : -1}
          aria-pressed={cell.id === selected}
          onClick={() => onSelect(cell.id)}
          onKeyDown={(event) => handleKeyDown(event, index)}
        >
          <span>{cell.label}</span>
          <span>{cell.value}</span>
        </button>
      ))}
    </div>
  );
}

function WorkspaceFixture({ view }: Readonly<{ view: ChartWorkspaceView }>) {
  const [selected, setSelected] = useState<string | null>(null);
  const detail = selected ? resolveBaziFocusDetail(view, selected) : null;
  return (
    <ChartWorkspaceShell
      view={view}
      renderBoard={() => (
        <PillarBoard
          cells={view.cells}
          selected={selected}
          onSelect={setSelected}
        />
      )}
      detail={detail}
      onCloseDetail={() => setSelected(null)}
    />
  );
}

describe("ChartWorkspaceShell", () => {
  it("opens the chart and reading split only for a real detail on a roomy desktop", () => {
    const css = readFileSync(
      join(
        process.cwd(),
        "src/components/readings/chart-workspace-shell.module.css",
      ),
      "utf8",
    );

    expect(css).toMatch(/@media \(min-width: 80rem\)/);
    expect(css).toMatch(
      /\.body\[data-has-detail="true"\]\s*\{[\s\S]*?grid-template-columns:\s*minmax\(30rem, 32\.5rem\) minmax\(22\.5rem, 1fr\)/,
    );
    expect(css).not.toMatch(/@media \(min-width: 1024px\)/);
  });

  it("renders layer tabs from the view model with the natal layer active", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      activeLuck: "丙午大运",
    });
    render(<WorkspaceFixture view={view} />);

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(6);
    expect(tabs[0]).toHaveTextContent("本命");
    expect(tabs[1]).toHaveTextContent("大运");
    expect(tabs[1]).toHaveTextContent("当前大运 丙午大运");
    expect(tabs[2]).toHaveTextContent("流年");
    expect(tabs[3]).toHaveTextContent("流月");
    expect(tabs[4]).toHaveTextContent("流日");
    expect(tabs[5]).toHaveTextContent("流时");
    expect(screen.getByRole("tab", { name: /^本命/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: /^大运/ })).not.toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("connects every tab to its panel and keeps only the active tab in the tab order", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      activeLuck: "丙午大运",
    });
    render(<WorkspaceFixture view={view} />);

    const tabs = screen.getAllByRole("tab");
    const panels = screen.getAllByRole("tabpanel", { hidden: true });

    expect(panels).toHaveLength(tabs.length);
    tabs.forEach((tab, index) => {
      const panelId = tab.getAttribute("aria-controls");
      expect(panelId).toBeTruthy();
      expect(panels[index]).toHaveAttribute("id", panelId);
      expect(panels[index]).toHaveAttribute("aria-labelledby", tab.id);
    });
    expect(tabs[0]).toHaveAttribute("tabindex", "0");
    expect(tabs[1]).toHaveAttribute("tabindex", "-1");
    expect(tabs[2]).toHaveAttribute("tabindex", "-1");
    expect(tabs[3]).toHaveAttribute("tabindex", "-1");
    expect(tabs[4]).toHaveAttribute("tabindex", "-1");
    expect(tabs[5]).toHaveAttribute("tabindex", "-1");
  });

  it("moves and activates every inspectable layer with arrows, Home, and End", async () => {
    const user = userEvent.setup();
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      activeLuck: "丙午大运",
      yearlyReady: true,
      yearlySummary: "2026 丙午",
      monthlyReady: true,
      monthlySummary: "2026-08 丙午",
      dailyReady: true,
      dailySummary: "2026-08-15 丙午",
    });
    render(<WorkspaceFixture view={view} />);

    const natal = screen.getByRole("tab", { name: /^本命/ });
    const decadal = screen.getByRole("tab", { name: /^大运/ });
    const yearly = screen.getByRole("tab", { name: /^流年/ });

    natal.focus();
    await user.keyboard("{ArrowRight}");
    expect(decadal).toHaveFocus();
    expect(decadal).toHaveAttribute("aria-selected", "true");
    expect(decadal).toHaveAttribute("tabindex", "0");
    expect(natal).toHaveAttribute("tabindex", "-1");
    expect(screen.getByRole("tabpanel", { name: /^大运/ })).toBeVisible();

    await user.keyboard("{ArrowRight}");
    expect(yearly).toHaveFocus();
    expect(yearly).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{ArrowLeft}");
    expect(decadal).toHaveFocus();
    expect(decadal).toHaveAttribute("aria-selected", "true");
    expect(yearly).not.toHaveFocus();

    await user.keyboard("{Home}");
    expect(natal).toHaveFocus();
    expect(natal).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{End}");
    const daily = screen.getByRole("tab", { name: /流日/ });
    expect(daily).toHaveFocus();
    expect(daily).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /流时/ })).toBeDisabled();
  });

  it("keeps unavailable layers visible, disabled, and free of upgrade actions", async () => {
    const user = userEvent.setup();
    const view = buildBaziWorkspaceView({ pillars: FOUR_PILLARS });
    render(<WorkspaceFixture view={view} />);

    const natal = screen.getByRole("tab", { name: /^本命/ });
    const yearly = screen.getByRole("tab", { name: /流年/ });
    expect(yearly).toBeVisible();
    expect(yearly).toBeDisabled();
    expect(yearly).toHaveAttribute("aria-disabled", "true");
    expect(yearly).toHaveAttribute("tabindex", "-1");
    expect(yearly).not.toHaveAttribute("aria-selected", "true");
    expect(within(yearly).getByText("待接入")).toBeVisible();

    await user.click(yearly);
    expect(natal).toHaveAttribute("aria-selected", "true");

    natal.focus();
    await user.keyboard("{ArrowRight}");
    expect(natal).toHaveFocus();
    expect(natal).toHaveAttribute("aria-selected", "true");

    const panel = document.getElementById(yearly.getAttribute("aria-controls") ?? "");
    expect(panel).toHaveTextContent("流年待接入");
    expect(panel).toHaveAttribute("aria-hidden", "true");
    expect(
      within(panel as HTMLElement).queryByRole("link", { name: "了解专业版" }),
    ).not.toBeInTheDocument();
  });

  it("locks returned paid facts when entitlement is unknown without leaking their values", async () => {
    const user = userEvent.setup();
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      yearlyReady: true,
      yearlySummary: "2026 丙午",
      monthlyReady: true,
      monthlySummary: "2026-08 丙午",
    });
    render(<WorkspaceFixture view={view} />);

    const monthly = screen.getByRole("tab", { name: /流月/ });
    expect(within(monthly).getByText("权益未确认")).toBeVisible();
    await user.click(monthly);

    const panel = screen.getByRole("tabpanel", { name: /流月/ });
    expect(within(panel).getByText("流月已锁定")).toBeVisible();
    expect(within(panel).getByText("权益状态未确认")).toBeVisible();
    expect(within(panel).getByRole("link", { name: "了解专业版" })).toHaveAttribute(
      "href",
      "/pricing",
    );
    expect(within(panel).queryByText(/2026-08|丙午/)).not.toBeInTheDocument();
  });

  it("opens the focus detail drawer with title and server facts on cell click", async () => {
    const user = userEvent.setup();
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      timezone: "Asia/Shanghai",
      timeBasis: "民用时",
    });
    render(<WorkspaceFixture view={view} />);

    const drawer = screen.getByRole("region", { name: "聚焦详情" });
    expect(
      within(drawer).getByText("选择一个柱位后，这里只显示服务端已公开的聚焦事实。"),
    ).toBeVisible();

    await user.click(screen.getByRole("button", { name: /年柱/ }));

    expect(within(drawer).getByText("年柱 · 甲子")).toBeVisible();
    expect(within(drawer).getByText("Asia/Shanghai")).toBeVisible();
    expect(within(drawer).getByText("民用时")).toBeVisible();
    expect(
      within(drawer).getByText(/暂无与该柱直接关联的公开依据/),
    ).toBeVisible();
    expect(
      within(drawer).getByText(/前端不进行本地排盘或星曜推算/),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "关闭聚焦详情" }),
    ).toBeVisible();
  });

  it("moves focus with arrow keys and activates a cell with Enter", async () => {
    const user = userEvent.setup();
    const view = buildBaziWorkspaceView({ pillars: FOUR_PILLARS });
    render(<WorkspaceFixture view={view} />);

    const year = screen.getByRole("button", { name: /年柱/ });
    year.focus();
    expect(year).toHaveFocus();

    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("button", { name: /月柱/ })).toHaveFocus();

    await user.keyboard("{Enter}");
    const drawer = screen.getByRole("region", { name: "聚焦详情" });
    expect(within(drawer).getByText("月柱 · 丙寅")).toBeVisible();
  });

  it("closes the focus detail drawer and clears the selection", async () => {
    const user = userEvent.setup();
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      timezone: "Asia/Shanghai",
    });
    render(<WorkspaceFixture view={view} />);

    await user.click(screen.getByRole("button", { name: /时柱/ }));
    const drawer = screen.getByRole("region", { name: "聚焦详情" });
    expect(within(drawer).getByText("时柱 · 丁卯")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "关闭聚焦详情" }));
    expect(
      within(drawer).getByText("选择一个柱位后，这里只显示服务端已公开的聚焦事实。"),
    ).toBeVisible();
    expect(within(drawer).queryByText("时柱 · 丁卯")).not.toBeInTheDocument();
  });

  it("restores focus to the pillar that opened the detail", async () => {
    const user = userEvent.setup();
    const view = buildBaziWorkspaceView({ pillars: FOUR_PILLARS });
    render(<WorkspaceFixture view={view} />);

    const month = screen.getByRole("button", { name: /月柱/ });
    await user.click(month);
    expect(screen.getByText("月柱 · 丙寅")).toHaveFocus();
    const close = screen.getByRole("button", { name: "关闭聚焦详情" });

    await user.click(close);
    expect(month).toHaveFocus();
  });

  it("renders an honest empty workspace with no fabricated cells", () => {
    const view = buildBaziWorkspaceView({});
    render(<WorkspaceFixture view={view} />);

    expect(screen.getByText("服务端尚未返回可展示的公开事实")).toBeVisible();
    expect(
      screen.getByText("服务端尚未返回可展示的四柱结构"),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: /年柱/ })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^本命/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("keeps the reduced-motion path showing the final focus state", async () => {
    const user = userEvent.setup();
    const css = readFileSync(
      join(
        process.cwd(),
        "src/components/readings/focus-detail-drawer.module.css",
      ),
      "utf8",
    );
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)/);

    const view = buildBaziWorkspaceView({ pillars: FOUR_PILLARS });
    render(<WorkspaceFixture view={view} />);
    await user.click(screen.getByRole("button", { name: /年柱/ }));
    expect(
      within(screen.getByRole("region", { name: "聚焦详情" })).getByText(
        "年柱 · 甲子",
      ),
    ).toBeVisible();
  });
});
