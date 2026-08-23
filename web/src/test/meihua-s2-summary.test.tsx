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

function renderForm() {
  return render(
    <ProductInputForm onConfirm={vi.fn()} product={getProductDefinition("meihua")} />,
  );
}

async function fillShared(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("当前问题"), "这件事后续如何");
  await user.selectOptions(screen.getByLabelText("判断侧重"), "outcome");
  fireEvent.change(screen.getByLabelText("事件时间"), {
    target: { value: "2026-08-21T09:30" },
  });
  await user.type(screen.getByLabelText("事件地点"), "上海市");
}

function summary() {
  return screen.getByRole("region", { name: "提交前摘要" });
}

function termValue(region: HTMLElement, term: string) {
  const dt = within(region).getByText(term);
  return dt.nextElementSibling;
}

describe("/meihua S2 method-parameter inline summary", () => {
  it("echoes question, focus, method, and event time; time method shows no trigram or derived hexagram", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillShared(user);

    const region = summary();
    expect(termValue(region, "问题")).toHaveTextContent("这件事后续如何");
    expect(termValue(region, "判断侧重")).toHaveTextContent("结果观察");
    expect(termValue(region, "梅花起卦方式")).toHaveTextContent("按时间起卦");
    expect(termValue(region, "事件时间")).toHaveTextContent("2026-08-21T09:30");
    expect(termValue(region, "事件时间口径")).toHaveTextContent("民用钟表时间");

    expect(within(region).queryByText("起卦数字")).not.toBeInTheDocument();
    expect(within(region).queryByText("声数")).not.toBeInTheDocument();
    expect(within(region).queryByText("上卦")).not.toBeInTheDocument();
    expect(within(region).queryByText("下卦")).not.toBeInTheDocument();
    expect(within(region).queryByText("动爻")).not.toBeInTheDocument();
    expect(region.querySelector('[class*="trigram"]')).toBeNull();
    expect(region).not.toHaveTextContent("互卦");
    expect(region).not.toHaveTextContent("变卦");
    expect(region).not.toHaveTextContent("本卦");
  });

  it("echoes number and source for supplied_number without glyphs", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillShared(user);
    await user.selectOptions(screen.getByLabelText("梅花起卦方式"), "supplied_number");
    await user.type(screen.getByLabelText("起卦数字"), "42");
    await user.type(screen.getByLabelText("数字资料来源"), "用户现场报数");

    const region = summary();
    expect(termValue(region, "梅花起卦方式")).toHaveTextContent("按数字起卦");
    expect(termValue(region, "起卦数字")).toHaveTextContent("42");
    expect(termValue(region, "数字资料来源")).toHaveTextContent("用户现场报数");
    expect(region.querySelector('[class*="trigram"]')).toBeNull();
    expect(region).not.toHaveTextContent("互卦");
    expect(region).not.toHaveTextContent("变卦");
  });

  it("echoes count and source for sound_count", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillShared(user);
    await user.selectOptions(screen.getByLabelText("梅花起卦方式"), "sound_count");
    await user.type(screen.getByLabelText("声数"), "9");
    await user.type(screen.getByLabelText("声数观察来源"), "现场声音计数");

    const region = summary();
    expect(termValue(region, "梅花起卦方式")).toHaveTextContent("按声数起卦");
    expect(termValue(region, "声数")).toHaveTextContent("9");
    expect(termValue(region, "声数观察来源")).toHaveTextContent("现场声音计数");
    expect(region.querySelector('[class*="trigram"]')).toBeNull();
  });

  it("echoes observation trigrams as input glyphs, never derived hexagram names", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillShared(user);
    await user.selectOptions(screen.getByLabelText("梅花起卦方式"), "observation");
    await user.selectOptions(screen.getByLabelText("上卦"), "离");
    await user.selectOptions(screen.getByLabelText("下卦"), "兑");
    await user.type(screen.getByLabelText("观察来源"), "用户现场记录");

    const region = summary();
    expect(termValue(region, "梅花起卦方式")).toHaveTextContent("按观察起卦");
    expect(termValue(region, "上卦")).toHaveTextContent("离");
    expect(termValue(region, "下卦")).toHaveTextContent("兑");
    expect(termValue(region, "观察来源")).toHaveTextContent("用户现场记录");
    expect(termValue(region, "上卦")?.querySelector('[class*="trigram"]')).toBeTruthy();
    expect(termValue(region, "下卦")?.querySelector('[class*="trigram"]')).toBeTruthy();
    expect(within(region).queryByText("动爻")).not.toBeInTheDocument();
    expect(region).not.toHaveTextContent("互卦");
    expect(region).not.toHaveTextContent("变卦");
    expect(region).not.toHaveTextContent("本卦");
  });

  it("echoes supplied hexagram trigrams, moving line, and source", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillShared(user);
    await user.selectOptions(screen.getByLabelText("梅花起卦方式"), "supplied_hexagram");
    await user.selectOptions(screen.getByLabelText("上卦"), "震");
    await user.selectOptions(screen.getByLabelText("下卦"), "艮");
    await user.selectOptions(screen.getByLabelText("动爻"), "3");
    await user.type(screen.getByLabelText("卦象资料来源"), "已有卦象复盘");

    const region = summary();
    expect(termValue(region, "梅花起卦方式")).toHaveTextContent("提供完整卦象");
    expect(termValue(region, "上卦")).toHaveTextContent("震");
    expect(termValue(region, "下卦")).toHaveTextContent("艮");
    expect(termValue(region, "动爻")).toHaveTextContent("3 爻");
    expect(termValue(region, "卦象资料来源")).toHaveTextContent("已有卦象复盘");
    expect(termValue(region, "上卦")?.querySelector('[class*="trigram"]')).toBeTruthy();
    expect(region).not.toHaveTextContent("互卦");
    expect(region).not.toHaveTextContent("变卦");
  });
});
