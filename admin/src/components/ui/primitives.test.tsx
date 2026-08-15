import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fireEvent } from "@testing-library/react";
import { useState } from "react";

import {
  Button,
  Dialog,
  Drawer,
  Field,
  Segmented,
  Status,
  Table,
  Tabs,
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
  it("renders every variant and keeps a 44px target", () => {
    const { rerender } = render(<Button>保存</Button>);
    const primary = screen.getByRole("button", { name: "保存" });
    expect(primary).toHaveAttribute("data-variant", "primary");
    expect(primary).toHaveStyle({ minHeight: "var(--target-min)", minWidth: "var(--target-min)" });

    for (const variant of ["secondary", "ghost", "destructive"] as const) {
      rerender(<Button variant={variant}>操作</Button>);
      expect(screen.getByRole("button", { name: "操作" })).toHaveAttribute(
        "data-variant",
        variant,
      );
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
    expect(button).toHaveStyle({ width: "var(--target-min)", height: "var(--target-min)" });
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

  it("shows a spinner, exposes aria-busy, and blocks native activation while loading", async () => {
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
    expect(container.querySelector("[class*='spinner']")).toBeInTheDocument();
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("blocks an asChild disabled/loading target from pointer and keyboard activation", () => {
    const onNavigate = vi.fn();
    render(
      <Button asChild disabled>
        <a href="#next" onClick={onNavigate}>
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

  it("renders the spinner inside an asChild loading target", () => {
    const { container } = render(
      <Button asChild loading>
        <a href="#next">保存</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "保存" });
    expect(link).toHaveAttribute("aria-disabled", "true");
    expect(link).toHaveAttribute("aria-busy", "true");
    expect(container.querySelector("[class*='spinner']")).toBeInTheDocument();
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

describe("Table responsive summary rows", () => {
  it("labels every mobile summary value while preserving selection and detail actions", () => {
    const { container } = render(
      <Table
        caption="订单列表"
        columns={sampleColumns}
        rows={sampleRows}
        selectable
        onRowActivate={() => undefined}
      />,
    );

    expect(container.querySelector('td[data-label="名称"]')).toHaveTextContent("甲");
    expect(container.querySelector('td[data-label="金额"]')).toHaveTextContent("300");
    expect(screen.getByRole("checkbox", { name: "选择 A-1" })).toBeVisible();
    expect(screen.getByRole("button", { name: "查看详情 A-1" })).toBeVisible();
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
    const loading = screen.getByRole("status", { name: "正在载入…" });
    expect(loading).toHaveAttribute("data-state", "loading");
    expect(loading).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("status", { name: "正在载入…" }).textContent).toMatch(/…/);

    rerender(<Status state="empty" />);
    expect(screen.getByRole("status", { name: "暂无内容" })).toHaveAttribute(
      "data-state",
      "empty",
    );

    rerender(<Status state="error" />);
    expect(screen.getByRole("alert", { name: "出现错误" })).toHaveAttribute(
      "data-state",
      "error",
    );

    rerender(<Status state="processing" />);
    const processing = screen.getByRole("status", { name: "正在处理…" });
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
    expect(screen.getByRole("status", { name: "已锁定" })).toHaveAttribute(
      "data-state",
      "locked",
    );
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
