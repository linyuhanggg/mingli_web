import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductInputForm } from "@/components/task/product-input-form";
import {
  LIUYAO_COIN_KEY,
  LIUYAO_LINE_PROCESS_HINT,
} from "@/components/task/liuyao-entry-copy";
import { getProductDefinition } from "@/products/catalog";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  listProfiles: vi.fn().mockResolvedValue({ profiles: [] }),
}));

afterEach(cleanup);

function renderForm() {
  return render(
    <ProductInputForm onConfirm={vi.fn()} product={getProductDefinition("liuyao")} />,
  );
}

function lineRow(index: number) {
  const row = document.getElementById(`liuyao-line-${index}`);
  if (!row) throw new Error(`missing liuyao-line-${index}`);
  return row;
}

describe("/liuyao S1 LineRecorder", () => {
  it("stacks rows bottom-up with 爻名 headers and does not invent GAP-LY or RNG", () => {
    renderForm();

    expect(screen.getByText("初爻 · 第 1 次")).toBeVisible();
    expect(screen.getByText("上爻 · 第 6 次")).toBeVisible();
    expect(screen.getByText(LIUYAO_LINE_PROCESS_HINT)).toBeVisible();
    expect(document.getElementById("liuyao-line-0")).toBeTruthy();
    expect(document.getElementById("liuyao-line-5")).toBeTruthy();
    expect(screen.queryByLabelText("问题类别")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /摇卦|随机|代掷/ })).not.toBeInTheDocument();
    expect(screen.queryByText(LIUYAO_COIN_KEY)).not.toBeInTheDocument();
  });

  it("shows the coin dictionary only for 三枚硬币 and keeps values user-selected", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.selectOptions(screen.getByLabelText("起卦方式"), "coins");
    expect(screen.getByText(LIUYAO_COIN_KEY)).toBeVisible();

    await user.click(within(lineRow(0)).getByRole("radio", { name: "老阳（9 · 动）" }));
    expect(within(lineRow(0)).getByRole("radio", { name: "老阳（9 · 动）" })).toBeChecked();
    expect(lineRow(0).querySelector("[data-kind='yang'][data-moving='true']")).toBeTruthy();

    await user.selectOptions(screen.getByLabelText("起卦方式"), "manual");
    expect(screen.queryByText(LIUYAO_COIN_KEY)).not.toBeInTheDocument();
    expect(within(lineRow(0)).getByRole("radio", { name: "老阳（9 · 动）" })).toBeChecked();
  });

  it("blocks submit until six lines are complete and focuses the first missing row", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<ProductInputForm onConfirm={onConfirm} product={getProductDefinition("liuyao")} />);

    await user.type(screen.getByLabelText("当前问题"), "这次求财如何");
    await user.selectOptions(screen.getByLabelText("起卦方式"), "manual");
    fireEvent.change(screen.getByLabelText("事件时间"), { target: { value: "2026-08-21T22:10" } });
    await user.type(screen.getByLabelText("事件地点"), "上海市");
    await user.click(screen.getByRole("button", { name: /^立即起卦 · 查看本卦与变卦$/ }));

    expect(onConfirm).not.toHaveBeenCalled();
    expect(await screen.findByText("请完成六次起卦过程")).toBeVisible();
    expect(lineRow(0)).toHaveFocus();

    for (let index = 0; index < 6; index += 1) {
      await user.click(within(lineRow(index)).getByRole("radio", { name: "少阳（7）" }));
    }
    await user.click(screen.getByRole("button", { name: /^立即起卦 · 查看本卦与变卦$/ }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm.mock.calls[0][0].lines).toEqual([
      "young-yang",
      "young-yang",
      "young-yang",
      "young-yang",
      "young-yang",
      "young-yang",
    ]);
  });

  it("lets the keyboard walk all four line values", async () => {
    const user = userEvent.setup();
    renderForm();
    const radios = within(lineRow(0)).getAllByRole("radio");
    expect(radios).toHaveLength(4);
    radios[0].focus();
    await user.keyboard("{ArrowRight}");
    expect(radios[1]).toBeChecked();
    await user.keyboard("{ArrowRight}");
    expect(radios[2]).toBeChecked();
    await user.keyboard("{ArrowRight}");
    expect(radios[3]).toBeChecked();
  });

  it("uses a bottom-up stack, 2×2 options at 360, and clips overflow", () => {
    const css = readFileSync(resolve(process.cwd(), "src/components/task/task-shell.module.css"), "utf8");
    expect(css).toMatch(/\.lineRecorder\s*\{[^}]*flex-direction:\s*column-reverse/s);
    expect(css).toMatch(/\.lineRecorder\s*\{[^}]*overflow-x:\s*clip/s);
    expect(css).toMatch(/\.lineRecorderOptions\s*\{[^}]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/s);
    expect(css).toMatch(
      /@media \(max-width: 22\.5rem\)[\s\S]*\.lineRecorderOptions\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s,
    );
    expect(css).toMatch(/\.lineRecorderOptions \.segment\s*\{[^}]*min-height:\s*var\(--target-min\)/s);
  });
});
