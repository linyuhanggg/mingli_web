import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChartStructureSkeleton } from "@/components/readings/chart-structure-skeleton";

describe("ChartStructureSkeleton", () => {
  it("renders a four-pillar structure and only exposes return after the host allows it", () => {
    const onReturn = vi.fn();
    const { container, rerender } = render(
      <ChartStructureSkeleton onReturn={onReturn} variant="bazi" />,
    );

    expect(screen.getByRole("status", { name: "正在同步八字盘面" })).toBeVisible();
    expect(container.querySelector("[data-chart-skeleton='bazi'] [class*='pillars']")?.children)
      .toHaveLength(4);
    expect(screen.queryByRole("button", { name: "返回录入" })).not.toBeInTheDocument();

    rerender(<ChartStructureSkeleton canReturn onReturn={onReturn} variant="bazi" />);
    screen.getByRole("button", { name: "返回录入" }).click();
    expect(onReturn).toHaveBeenCalledTimes(1);
  });

  it("renders twelve palace slots plus a central information region for ziwei", () => {
    const { container } = render(<ChartStructureSkeleton variant="ziwei" />);

    expect(screen.getByRole("status", { name: "正在同步紫微盘面" })).toBeVisible();
    expect(container.querySelectorAll("[data-chart-skeleton='ziwei'] li")).toHaveLength(12);
    expect(container.querySelector("[data-chart-skeleton='ziwei'] [class*='center']"))
      .toBeInTheDocument();
  });

  it("only takes focus when the host confirms the submitted form still owns it", () => {
    const { rerender } = render(
      <>
        <button type="button">持久控件</button>
        <ChartStructureSkeleton variant="bazi" />
      </>,
    );
    const persistentControl = screen.getByRole("button", { name: "持久控件" });
    persistentControl.focus();
    expect(persistentControl).toHaveFocus();

    rerender(
      <>
        <button type="button">持久控件</button>
        <ChartStructureSkeleton focusOnMount variant="bazi" />
      </>,
    );
    expect(screen.getByLabelText("正在同步八字盘面", {
      selector: "[data-chart-skeleton='bazi']",
    })).toHaveFocus();
  });
});
