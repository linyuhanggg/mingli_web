import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductInputForm } from "@/components/task/product-input-form";
import { getProductDefinition } from "@/products/catalog";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  listProfiles: vi.fn().mockResolvedValue({ profiles: [] }),
}));

afterEach(cleanup);

const LINE_VALUES = [
  "老阳（9 · 动）",
  "少阴（8）",
  "少阳（7）",
  "老阴（6 · 动）",
  "少阴（8）",
  "少阳（7）",
] as const;

function renderForm() {
  return render(
    <ProductInputForm onConfirm={vi.fn()} product={getProductDefinition("liuyao")} />,
  );
}

function summary() {
  return screen.getByRole("region", { name: "提交前摘要" });
}

function termValue(region: HTMLElement, term: string) {
  const dt = within(region).getByText(term);
  return dt.nextElementSibling;
}

function lineRow(index: number) {
  const row = document.getElementById(`liuyao-line-${index}`);
  if (!row) throw new Error(`missing liuyao-line-${index}`);
  return row;
}

async function fillShared(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("当前问题"), "这次求财如何");
  await user.selectOptions(screen.getByLabelText("起卦方式"), "manual");
  fireEvent.change(screen.getByLabelText("事件时间"), { target: { value: "2026-08-21T22:10" } });
  await user.type(screen.getByLabelText("事件地点"), "上海市");
}

describe("/liuyao S2 inline summary", () => {
  it("echoes question, casting method, and event time/place without inventing 问题类别", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillShared(user);

    const region = summary();
    expect(termValue(region, "问题")).toHaveTextContent("这次求财如何");
    expect(termValue(region, "起卦方式")).toHaveTextContent("手动记录");
    expect(termValue(region, "事件时间")).toHaveTextContent("2026-08-21T22:10");
    expect(termValue(region, "事件地点")).toHaveTextContent("上海市");
    expect(within(region).queryByText("问题类别")).not.toBeInTheDocument();
    expect(within(region).queryByText("侧重")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("问题类别")).not.toBeInTheDocument();
  });

  it("stacks input glyphs bottom-up and never shows hexagram or trigram names", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillShared(user);

    for (let index = 0; index < 6; index += 1) {
      await user.click(within(lineRow(index)).getByRole("radio", { name: LINE_VALUES[index] }));
    }

    const region = summary();
    const figure = within(region).getByRole("group", { name: "六爻记录" });
    const items = figure.querySelectorAll("li");
    expect(items).toHaveLength(6);
    expect(items[5]?.querySelector("[data-kind='yang'][data-moving='true']")).toBeTruthy();
    expect(items[4]?.querySelector("[data-kind='yin'][data-moving='false']")).toBeTruthy();
    expect(items[3]?.querySelector("[data-kind='yang'][data-moving='false']")).toBeTruthy();
    expect(items[2]?.querySelector("[data-kind='yin'][data-moving='true']")).toBeTruthy();
    expect(items[1]?.querySelector("[data-kind='yin'][data-moving='false']")).toBeTruthy();
    expect(items[0]?.querySelector("[data-kind='yang'][data-moving='false']")).toBeTruthy();
    expect(items[5]?.querySelector(".movingMark, [class*='movingMark']")?.textContent).toContain("○");
    expect(items[2]?.querySelector(".movingMark, [class*='movingMark']")?.textContent).toContain("×");

    expect(within(region).queryByText("本卦")).not.toBeInTheDocument();
    expect(within(region).queryByText("变卦")).not.toBeInTheDocument();
    expect(within(region).queryByText("上卦")).not.toBeInTheDocument();
    expect(within(region).queryByText("下卦")).not.toBeInTheDocument();
    expect(region).not.toHaveTextContent("乾为天");
    expect(region.querySelector('[class*="hexName"]')).toBeNull();
    expect(region.querySelector('[class*="trigramName"]')).toBeNull();
  });
});
