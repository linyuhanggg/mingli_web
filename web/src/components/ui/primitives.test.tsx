import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fireEvent } from "@testing-library/react";
import { useState } from "react";
import { vi } from "vitest";

import {
  Button,
  Dialog,
  Drawer,
  Field,
  LocalLoader,
  Segmented,
  Status,
  Table,
  Tabs,
  Toast,
  type ButtonProps,
} from "@/components/ui";


function SegmentedHarness() {
  const [value, setValue] = useState("solar");
  return (
    <Segmented
      aria-label="历法"
      value={value}
      onValueChange={setValue}
      options={[
        { value: "solar", label: "公历" },
        { value: "lunar", label: "农历" },
        { value: "unknown", label: "未知" },
      ]}
    />
  );
}

function TabsHarness() {
  const [value, setValue] = useState("one");
  return (
    <Tabs
      aria-label="工作台"
      value={value}
      onValueChange={setValue}
      items={[
        { value: "one", label: "盘面", panel: <p>盘面内容</p> },
        { value: "two", label: "报告", panel: <p>报告内容</p> },
        { value: "three", label: "核对", panel: <p>核对内容</p> },
      ]}
    />
  );
}

function DialogHarness() {
  const [open, setOpen] = useState(false);
  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title="确认删除"
      description="删除后不可恢复。"
      trigger={<Button>打开对话框</Button>}
    >
      <p>请再次确认。</p>
      <button type="button">确认删除</button>
    </Dialog>
  );
}

function DrawerHarness() {
  const [open, setOpen] = useState(false);
  return (
    <Drawer
      open={open}
      onOpenChange={setOpen}
      title="更多操作"
      description="移动端操作面板"
      trigger={<Button>打开抽屉</Button>}
    >
      <button type="button">第一个操作</button>
      <button type="button">第二个操作</button>
    </Drawer>
  );
}

const sampleColumns = [
  { key: "name", header: "名称", sortable: true },
  { key: "amount", header: "金额", sortable: true },
];

const sampleRows = [
  { id: "A-1", name: "甲", amount: 300 },
  { id: "A-2", name: "乙", amount: 100 },
  { id: "A-3", name: "丙", amount: 200 },
];

describe("Button", () => {
  it("keeps every button at least 44px tall when any coarse pointer is available", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/ui/button.module.css"),
      "utf8",
    );

    expect(css).toMatch(
      /@media \(max-width: 839px\), \(any-pointer: coarse\)\s*\{[\s\S]*?\.button\s*\{[^}]*min-width:\s*var\(--ds-touch-min\)[^}]*min-height:\s*var\(--ds-touch-min\)/,
    );
  });

  it("renders the canonical variants and size contract", () => {
    const { rerender } = render(<Button>保存</Button>);
    const primary = screen.getByRole("button", { name: "保存" });
    expect(primary).toHaveAttribute("data-variant", "primary");
    expect(primary).toHaveAttribute("data-size", "md");

    for (const variant of ["secondary", "quiet", "signal", "danger"] as const) {
      rerender(<Button variant={variant}>操作</Button>);
      expect(screen.getByRole("button", { name: "操作" })).toHaveAttribute(
        "data-variant",
        variant,
      );
    }

    for (const size of ["sm", "md", "lg"] as const) {
      rerender(<Button size={size}>尺寸</Button>);
      expect(screen.getByRole("button", { name: "尺寸" })).toHaveAttribute("data-size", size);
    }
  });

  it("gives an icon-only Button a 44×44 target and an accessible name", () => {
    render(
      <Button variant="icon" aria-label="关闭">
        ×
      </Button>,
    );
    const button = screen.getByRole("button", { name: "关闭" });
    expect(button).toHaveAttribute("data-variant", "icon");
    expect(button).toHaveStyle({ width: "var(--ds-touch-min)", height: "var(--ds-touch-min)" });
  });

  it("rejects an icon Button without a non-empty aria-label", () => {
    // @ts-expect-error icon Buttons require an aria-label at the API boundary.
    const missingLabel: ButtonProps = { variant: "icon", children: "×" };
    const blankLabel = {
      variant: "icon",
      "aria-label": "   ",
      children: "×",
    } as ButtonProps;

    expect(() => Button(missingLabel)).toThrow(/aria-label/);
    expect(() => Button(blankLabel)).toThrow(/aria-label/);
  });

  it("shows dots, exposes aria-busy, and blocks native activation while loading", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    const { container } = render(
      <Button loading onClick={onClick}>
        删除
      </Button>,
    );
    const button = screen.getByRole("button", { name: "删除" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveAttribute("data-loading", "true");
    expect(container.querySelector("[data-loader-variant='dots']")).toBeInTheDocument();
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("blocks an asChild disabled/loading target from pointer and keyboard activation", () => {
    const onNavigate = vi.fn();
    render(
      <Button asChild disabled>
        <a href="/next" onClick={onNavigate}>
          继续
        </a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "继续" });
    expect(link).toHaveAttribute("aria-disabled", "true");
    expect(link).toHaveAttribute("tabindex", "-1");
    fireEvent.click(link);
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("renders dots inside an asChild loading target", () => {
    const { container } = render(
      <Button asChild loading>
        <a href="/next">保存</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "保存" });
    expect(link).toHaveAttribute("aria-disabled", "true");
    expect(link).toHaveAttribute("aria-busy", "true");
    expect(container.querySelector("[data-loader-variant='dots']")).toBeInTheDocument();
  });

  it("keeps controlled state labels width-stable and exposes non-color feedback", () => {
    const { rerender } = render(
      <Button
        errorLabel="保存失败"
        loadingLabel="正在保存"
        state="idle"
        successLabel="保存成功"
      >
        保存
      </Button>,
    );

    const button = screen.getByRole("button", { name: "保存" });
    expect(button).toHaveAttribute("data-state", "idle");
    expect(within(button).getByText("正在保存")).toHaveAttribute("aria-hidden", "true");
    expect(within(button).getByText("保存成功")).toHaveAttribute("aria-hidden", "true");
    expect(within(button).getByText("保存失败")).toHaveAttribute("aria-hidden", "true");

    rerender(
      <Button
        errorLabel="保存失败"
        loadingLabel="正在保存"
        state="loading"
        successLabel="保存成功"
      >
        保存
      </Button>,
    );
    expect(screen.getByRole("button", { name: "正在保存" })).toBeDisabled();

    rerender(
      <Button
        errorLabel="保存失败"
        loadingLabel="正在保存"
        state="success"
        successLabel="保存成功"
      >
        保存
      </Button>,
    );
    expect(screen.getByRole("button", { name: "保存成功" })).toBeEnabled();

    rerender(
      <Button
        errorLabel="保存失败"
        loadingLabel="正在保存"
        state="error"
        successLabel="保存成功"
      >
        保存
      </Button>,
    );
    const failed = screen.getByRole("button", { name: "保存失败" });
    expect(failed).toBeEnabled();
    expect(failed.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("uses feedback-only transforms and removes motion when requested", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/ui/button.module.css"),
      "utf8",
    );

    expect(css).not.toContain("button-spin");
    expect(css).toMatch(/button-state-error[\s\S]*translateX\(-4px\)[\s\S]*translateX\(4px\)/);
    expect(css).toMatch(/prefers-reduced-motion:[\s\S]*button\[data-state="error"\][\s\S]*animation:\s*none/);
  });

  it("normalizes a single-element children array for an asChild target", () => {
    render(
      <Button asChild>
        {[<a href="/next" key="next">继续</a>]}
      </Button>,
    );

    expect(screen.getByRole("link", { name: "继续" })).toHaveAttribute("href", "/next");
  });
});

describe("LocalLoader", () => {
  it("names standalone dots and keeps decorative button dots out of the accessibility tree", () => {
    const { rerender } = render(<LocalLoader label="正在保存档案" />);
    expect(screen.getByRole("status", { name: "正在保存档案" })).toHaveAttribute(
      "data-loader-variant",
      "dots",
    );

    rerender(<LocalLoader variant="dot-matrix" />);
    const matrix = document.querySelector("[data-loader-variant='dot-matrix']");
    expect(matrix).toHaveAttribute("aria-hidden", "true");
    expect(matrix?.children).toHaveLength(4);
  });
});

describe("Field", () => {
  it("reflects required as both the native and ARIA constraint", () => {
    render(
      <Field label="邮箱" required>
        <input name="email" />
      </Field>,
    );
    const input = screen.getByLabelText(/邮箱/);
    expect(input).toBeRequired();
    expect(input).toHaveAttribute("aria-required", "true");
  });

  it("preserves a control's own aria-invalid when there is no error", () => {
    render(
      <Field label="邮箱">
        <input name="email" aria-invalid />
      </Field>,
    );
    expect(screen.getByLabelText(/邮箱/)).toHaveAttribute("aria-invalid", "true");
  });

  it("links description, error, and disabled reason to the control", () => {
    render(
      <Field
        label="邮箱"
        description="用于登录通知"
        error="格式不正确"
        disabledReason="需要先完成验证"
        required
      >
        <input name="email" aria-describedby="existing-hint" />
      </Field>,
    );
    const input = screen.getByLabelText(/邮箱/);
    expect(input).toHaveAttribute("aria-invalid", "true");
    const describedBy = input.getAttribute("aria-describedby") ?? "";
    expect(describedBy).toContain("existing-hint");
    expect(describedBy).toContain(screen.getByText("用于登录通知").id);
    expect(describedBy).toContain(screen.getByRole("alert").id);
    expect(describedBy).toContain(screen.getByText("需要先完成验证").id);
  });
});

describe("Toast", () => {
  it("announces polite short feedback without moving focus", () => {
    const focusBeforeRender = document.activeElement;
    const { container } = render(
      <Toast description="档案仍保留在当前页面。" title="保存成功" tone="success" />,
    );

    const toast = screen.getByRole("status");
    expect(toast).toHaveAttribute("aria-live", "polite");
    expect(toast).toHaveAttribute("aria-atomic", "true");
    expect(toast).toHaveAttribute("data-tone", "success");
    expect(toast).toHaveTextContent("保存成功");
    expect(toast).toHaveTextContent("档案仍保留在当前页面。");
    expect(document.activeElement).toBe(focusBeforeRender);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("keeps neutral feedback as a polite status", () => {
    render(<Toast title="已复制链接" />);

    const toast = screen.getByRole("status");
    expect(toast).toHaveAttribute("aria-live", "polite");
    expect(toast).toHaveAttribute("aria-atomic", "true");
    expect(toast).toHaveAttribute("data-tone", "neutral");
  });

  it("announces error feedback immediately as an assertive alert", () => {
    render(<Toast title="保存失败" tone="error" />);

    const toast = screen.getByRole("alert");
    expect(toast).toHaveAttribute("aria-live", "assertive");
    expect(toast).toHaveAttribute("aria-atomic", "true");
    expect(toast).toHaveAttribute("data-tone", "error");
  });

  it("uses the frozen 420ms transform entrance and near-instant reduced motion", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/ui/toast.module.css"),
      "utf8",
    );

    expect(css).toMatch(/animation:\s*toast-enter var\(--ds-duration-slow\) var\(--ds-ease-out\) both/);
    expect(css).toMatch(/@keyframes toast-enter[\s\S]*opacity:\s*0[\s\S]*transform:\s*translateY/);
    expect(css).toMatch(/\[data-tone="success"\][^}]*border-left:\s*2px solid var\(--color-success\)/);
    expect(css).toMatch(/@media \(prefers-reduced-motion:\s*reduce\)[\s\S]*animation-duration:\s*1ms/);
  });
});

describe("Segmented", () => {
  it("moves real focus with Arrow, Home, and End keys", async () => {
    const user = userEvent.setup();
    render(<SegmentedHarness />);
    const group = screen.getByRole("radiogroup", { name: "历法" });
    const solar = within(group).getByRole("radio", { name: "公历" });
    const lunar = within(group).getByRole("radio", { name: "农历" });
    const unknown = within(group).getByRole("radio", { name: "未知" });

    expect(solar).toHaveAttribute("aria-checked", "true");
    solar.focus();
    expect(solar).toHaveFocus();

    await user.keyboard("{ArrowRight}");
    await waitFor(() => {
      expect(lunar).toHaveAttribute("aria-checked", "true");
      expect(lunar).toHaveFocus();
    });

    await user.keyboard("{End}");
    await waitFor(() => {
      expect(unknown).toHaveAttribute("aria-checked", "true");
      expect(unknown).toHaveFocus();
    });

    await user.keyboard("{Home}");
    await waitFor(() => {
      expect(solar).toHaveAttribute("aria-checked", "true");
      expect(solar).toHaveFocus();
    });
  });
});

describe("Tabs", () => {
  it("moves real focus between tabs with Arrow, Home, and End keys", async () => {
    const user = userEvent.setup();
    render(<TabsHarness />);
    const tablist = screen.getByRole("tablist", { name: "工作台" });
    const first = within(tablist).getByRole("tab", { name: "盘面" });
    const second = within(tablist).getByRole("tab", { name: "报告" });
    const last = within(tablist).getByRole("tab", { name: "核对" });

    expect(first).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("盘面内容");

    first.focus();
    expect(first).toHaveFocus();

    await user.keyboard("{ArrowRight}");
    await waitFor(() => {
      expect(second).toHaveAttribute("aria-selected", "true");
      expect(second).toHaveFocus();
    });

    await user.keyboard("{End}");
    await waitFor(() => {
      expect(last).toHaveAttribute("aria-selected", "true");
      expect(last).toHaveFocus();
    });

    await user.keyboard("{Home}");
    await waitFor(() => {
      expect(first).toHaveAttribute("aria-selected", "true");
      expect(first).toHaveFocus();
    });
  });
});

describe("Dialog", () => {
  it("closes on Escape and restores focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);
    const trigger = screen.getByRole("button", { name: "打开对话框" });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "确认删除" })).toBeVisible();
    expect(screen.getByText("删除后不可恢复。")).toBeVisible();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("traps Tab and Shift+Tab within the dialog", async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);
    await user.click(screen.getByRole("button", { name: "打开对话框" }));

    const dialog = screen.getByRole("dialog", { name: "确认删除" });
    const close = within(dialog).getByRole("button", { name: "关闭" });
    const confirm = within(dialog).getByRole("button", { name: "确认删除" });

    await waitFor(() => expect(close).toHaveFocus());
    await user.tab();
    expect(confirm).toHaveFocus();
    await user.tab();
    expect(close).toHaveFocus();
    await user.tab({ shift: true });
    expect(confirm).toHaveFocus();
  });
});

describe("Drawer", () => {
  it("closes on Escape and restores focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<DrawerHarness />);
    const trigger = screen.getByRole("button", { name: "打开抽屉" });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "更多操作" })).toBeVisible();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("traps Tab and Shift+Tab within the drawer", async () => {
    const user = userEvent.setup();
    render(<DrawerHarness />);
    await user.click(screen.getByRole("button", { name: "打开抽屉" }));

    const drawer = screen.getByRole("dialog", { name: "更多操作" });
    const close = within(drawer).getByRole("button", { name: "关闭" });
    const firstAction = within(drawer).getByRole("button", { name: "第一个操作" });
    const secondAction = within(drawer).getByRole("button", { name: "第二个操作" });

    await waitFor(() => expect(close).toHaveFocus());
    await user.tab();
    expect(firstAction).toHaveFocus();
    await user.tab();
    expect(secondAction).toHaveFocus();
    await user.tab();
    expect(close).toHaveFocus();
    await user.tab({ shift: true });
    expect(secondAction).toHaveFocus();
  });
});

describe("Status", () => {
  it("renders every state with the correct live-region semantics", () => {
    const { rerender } = render(<Status state="loading" />);
    const loading = screen.getByRole("status", { name: "正在同步出盘" });
    expect(loading).toHaveAttribute("data-state", "loading");
    expect(loading).toHaveAttribute("data-core-state", "loading");
    expect(loading).toHaveAttribute("aria-busy", "true");

    rerender(<Status state="empty" />);
    expect(screen.getByRole("status", { name: "还没有盘面" })).toHaveAttribute(
      "data-state",
      "empty",
    );

    rerender(<Status state="ready" />);
    expect(screen.getByRole("status", { name: "盘面已就绪" })).toHaveAttribute(
      "data-core-state",
      "ready",
    );

    rerender(<Status state="need-input" />);
    expect(screen.getByRole("status", { name: "需要补充信息" })).toHaveAttribute(
      "data-core-state",
      "need-input",
    );

    rerender(<Status state="error" />);
    expect(screen.getByRole("alert", { name: "暂时无法完成" })).toHaveAttribute(
      "data-state",
      "error",
    );

    rerender(<Status state="processing" />);
    const processing = screen.getByRole("status", { name: "正在处理" });
    expect(processing).toHaveAttribute("data-state", "processing");
    expect(processing).toHaveAttribute("aria-busy", "true");

    rerender(<Status state="success" />);
    expect(screen.getByRole("status", { name: "已完成" })).toHaveAttribute(
      "data-state",
      "success",
    );

    rerender(<Status state="unavailable" />);
    expect(screen.getByRole("status", { name: "暂不可用" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );

    rerender(<Status state="unauthorized" />);
    expect(screen.getByRole("status", { name: "需要登录" })).toHaveAttribute(
      "data-state",
      "unauthorized",
    );

    rerender(<Status state="locked" />);
    expect(screen.getByRole("status", { name: "深读暂未解锁" })).toHaveAttribute(
      "data-state",
      "locked",
    );
    expect(screen.getByText(/免费盘面事实仍可查看/)).toBeVisible();
  });

  it("renders clickable recovery actions without changing live-region semantics", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <Status
        actions={<button onClick={onRetry} type="button">重试</button>}
        description="这次请求没有成功。"
        state="error"
        title="出现错误"
      />,
    );
    const alert = screen.getByRole("alert", { name: "出现错误" });
    expect(alert).toHaveAttribute("data-state", "error");
    await user.click(screen.getByRole("button", { name: "重试" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("keeps the icon decorative for screen readers", () => {
    render(<Status state="success" />);
    const icons = document.querySelectorAll("svg");
    expect(icons.length).toBeGreaterThan(0);
    icons.forEach((icon) => expect(icon).toHaveAttribute("aria-hidden", "true"));
  });
});

describe("Table", () => {
  it("sorts columns and sets aria-sort", async () => {
    const user = userEvent.setup();
    render(<Table caption="订单" columns={sampleColumns} rows={sampleRows} />);
    const amountHeader = screen.getByRole("columnheader", { name: "金额" });
    expect(amountHeader).toHaveAttribute("aria-sort", "none");

    await user.click(screen.getByRole("button", { name: "金额" }));
    expect(amountHeader).toHaveAttribute("aria-sort", "ascending");
    const ascendingRows = screen.getAllByRole("row").slice(1).map((row) => row.textContent);
    expect(ascendingRows[0]).toContain("乙");
    expect(ascendingRows[2]).toContain("甲");

    await user.click(screen.getByRole("button", { name: "金额" }));
    expect(amountHeader).toHaveAttribute("aria-sort", "descending");
    const descendingRows = screen.getAllByRole("row").slice(1).map((row) => row.textContent);
    expect(descendingRows[0]).toContain("甲");
    expect(descendingRows[2]).toContain("乙");
  });

  it("filters rows through an accessible input", async () => {
    const user = userEvent.setup();
    render(<Table caption="订单" columns={sampleColumns} rows={sampleRows} filterLabel="筛选订单" />);
    const filter = screen.getByRole("searchbox", { name: "筛选订单" });
    expect(filter).toHaveAttribute("name", "table-filter");
    expect(filter).toHaveAttribute("autocomplete", "off");
    await user.type(filter, "丙");
    expect(screen.getByRole("cell", { name: "丙" })).toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: "甲" })).not.toBeInTheDocument();
  });

  it("selects rows and supports select-all", async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();
    render(
      <Table
        caption="订单"
        columns={sampleColumns}
        rows={sampleRows}
        selectable
        onSelectionChange={onSelectionChange}
      />,
    );
    await user.click(screen.getByRole("checkbox", { name: "全选" }));
    expect(onSelectionChange).toHaveBeenCalledWith(["A-1", "A-2", "A-3"]);
    expect(screen.getByRole("checkbox", { name: "选择 A-1" })).toBeChecked();
  });

  it("gives selection labels and sortable headers a 44×44 hit target", () => {
    render(<Table caption="订单" columns={sampleColumns} rows={sampleRows} selectable />);

    for (const checkbox of screen.getAllByRole("checkbox")) {
      const hitTarget = checkbox.closest("label");
      expect(hitTarget).not.toBeNull();
      expect(hitTarget).toHaveStyle({
        minHeight: "var(--target-min)",
        minWidth: "var(--target-min)",
      });
    }

    for (const sortButton of [
      screen.getByRole("button", { name: "名称" }),
      screen.getByRole("button", { name: "金额" }),
    ]) {
      expect(sortButton).toHaveStyle({
        minHeight: "var(--target-min)",
        minWidth: "var(--target-min)",
      });
    }
  });

  it("keeps hidden selected IDs in callbacks while filtering", async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();
    render(
      <Table
        caption="订单"
        columns={sampleColumns}
        rows={sampleRows}
        filterLabel="筛选订单"
        selectable
        onSelectionChange={onSelectionChange}
      />,
    );

    await user.click(screen.getByRole("checkbox", { name: "选择 A-1" }));
    expect(onSelectionChange).toHaveBeenLastCalledWith(["A-1"]);

    const filter = screen.getByRole("searchbox", { name: "筛选订单" });
    await user.type(filter, "乙");
    await user.click(screen.getByRole("checkbox", { name: "选择 A-2" }));
    expect(onSelectionChange).toHaveBeenLastCalledWith(["A-1", "A-2"]);

    await user.clear(filter);
    expect(screen.getByRole("checkbox", { name: "选择 A-1" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "选择 A-2" })).toBeChecked();
    expect(onSelectionChange).toHaveBeenLastCalledWith(["A-1", "A-2"]);
  });

  it("keeps hidden selected IDs when select-all targets filtered rows", async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();
    render(
      <Table
        caption="订单"
        columns={sampleColumns}
        rows={sampleRows}
        filterLabel="筛选订单"
        selectable
        onSelectionChange={onSelectionChange}
      />,
    );

    await user.click(screen.getByRole("checkbox", { name: "选择 A-1" }));
    const filter = screen.getByRole("searchbox", { name: "筛选订单" });
    await user.type(filter, "乙");
    await user.click(screen.getByRole("checkbox", { name: "全选" }));

    expect(onSelectionChange).toHaveBeenLastCalledWith(["A-1", "A-2"]);
    await user.clear(filter);
    expect(screen.getByRole("checkbox", { name: "选择 A-1" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "选择 A-2" })).toBeChecked();
  });

  it("paginates with disabled boundaries", async () => {
    const user = userEvent.setup();
    render(<Table caption="订单" columns={sampleColumns} rows={sampleRows} pageSize={2} />);
    expect(screen.getByRole("navigation", { name: "分页" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上一页" })).toBeDisabled();
    expect(screen.getByText("第 1 / 2 页")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "下一页" }));
    expect(screen.getByText("第 2 / 2 页")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下一页" })).toBeDisabled();
  });

  it("fires the detail callback for a row", async () => {
    const user = userEvent.setup();
    const onRowActivate = vi.fn();
    render(
      <Table
        caption="订单"
        columns={sampleColumns}
        rows={sampleRows}
        onRowActivate={onRowActivate}
        rowActionLabel="查看详情"
      />,
    );
    await user.click(screen.getByRole("button", { name: "查看详情 A-2" }));
    expect(onRowActivate).toHaveBeenCalledWith(
      expect.objectContaining({ id: "A-2", name: "乙" }),
    );
  });

  it("shows an empty state and keeps native table semantics", () => {
    const { container } = render(
      <Table caption="订单" columns={sampleColumns} rows={[]} emptyState="还没有订单" />,
    );
    expect(screen.getByRole("table", { name: "订单" })).toBeVisible();
    expect(screen.getByText("还没有订单")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "名称" })).toHaveAttribute("scope", "col");
    expect(container.querySelector("[class*='scroller']")).toHaveStyle({
      overflowX: "auto",
    });
  });
});
