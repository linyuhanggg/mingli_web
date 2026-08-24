import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductInputForm } from "@/components/task/product-input-form";
import {
  MEIHUA_S1_CASTING_METHOD_HELP,
  MEIHUA_S1_EVENT_TIME_HELP,
  MEIHUA_S1_HEXAGRAM_HELP,
  MEIHUA_S1_ISSUE_HELP,
  MEIHUA_S1_NUMBER_SOURCE_HELP,
  MEIHUA_S1_OBSERVATION_HELP,
  MEIHUA_S1_TIME_HELP,
} from "@/components/task/meihua-entry-copy";
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

function methodSelect() {
  return screen.getByLabelText("梅花起卦方式");
}

describe("/meihua S1 five casting methods", () => {
  it("pins accepted help copy on shared fields", () => {
    renderForm();
    expect(screen.getByText(MEIHUA_S1_ISSUE_HELP)).toBeVisible();
    expect(screen.getByText(MEIHUA_S1_EVENT_TIME_HELP)).toBeVisible();
    expect(screen.getByText(MEIHUA_S1_CASTING_METHOD_HELP)).toBeVisible();
    expect(screen.getByText(MEIHUA_S1_TIME_HELP)).toBeVisible();
  });

  it("shows only the fields that belong to the selected method", async () => {
    const user = userEvent.setup();
    renderForm();

    expect(screen.queryByLabelText("起卦数字")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("声数")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("上卦")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("动爻")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("数字资料来源")).not.toBeInTheDocument();

    await user.selectOptions(methodSelect(), "supplied_number");
    expect(screen.getByLabelText("起卦数字")).toBeVisible();
    expect(screen.getByLabelText("数字资料来源")).toBeVisible();
    expect(screen.getByText(MEIHUA_S1_NUMBER_SOURCE_HELP)).toBeVisible();
    expect(screen.queryByLabelText("声数")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("上卦")).not.toBeInTheDocument();
    expect(screen.queryByText(MEIHUA_S1_TIME_HELP)).not.toBeInTheDocument();

    await user.selectOptions(methodSelect(), "sound_count");
    expect(screen.getByLabelText("声数")).toBeVisible();
    expect(screen.getByLabelText("声数观察来源")).toBeVisible();
    expect(screen.queryByLabelText("起卦数字")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("动爻")).not.toBeInTheDocument();

    await user.selectOptions(methodSelect(), "observation");
    expect(screen.getByLabelText("上卦")).toBeVisible();
    expect(screen.getByLabelText("下卦")).toBeVisible();
    expect(screen.getByLabelText("观察来源")).toBeVisible();
    expect(screen.getByText(MEIHUA_S1_OBSERVATION_HELP)).toBeVisible();
    expect(screen.queryByLabelText("动爻")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("声数")).not.toBeInTheDocument();
    expect(screen.getByLabelText("上卦").parentElement?.querySelector('[class*="trigram"]')).toBeTruthy();

    await user.selectOptions(methodSelect(), "supplied_hexagram");
    expect(screen.getByLabelText("上卦")).toBeVisible();
    expect(screen.getByLabelText("下卦")).toBeVisible();
    expect(screen.getByLabelText("动爻")).toBeVisible();
    expect(screen.getByLabelText("卦象资料来源")).toBeVisible();
    expect(screen.getByText(MEIHUA_S1_HEXAGRAM_HELP)).toBeVisible();
    expect(screen.getAllByRole("option", { name: "☰ 乾" })).toHaveLength(2);
  });

  it("keeps exclusive values after switching away and back", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.selectOptions(methodSelect(), "supplied_number");
    await user.type(screen.getByLabelText("起卦数字"), "42");
    await user.type(screen.getByLabelText("数字资料来源"), "用户现场报数");
    await user.selectOptions(methodSelect(), "time");
    expect(screen.queryByLabelText("起卦数字")).not.toBeInTheDocument();
    await user.selectOptions(methodSelect(), "supplied_number");
    expect(screen.getByLabelText("起卦数字")).toHaveValue(42);
    expect(screen.getByLabelText("数字资料来源")).toHaveValue("用户现场报数");
  });

  it("intercepts an empty source next to the source field", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillShared(user);
    await user.selectOptions(methodSelect(), "supplied_number");
    await user.type(screen.getByLabelText("起卦数字"), "7");
    await user.click(screen.getByRole("button", { name: /立即起卦/ }));

    const nearby = await screen.findByText("请说明数字资料来源");
    expect(nearby).toBeVisible();
    expect(nearby).toHaveAttribute("id", "meihua-source-error");
    expect(screen.getByLabelText("数字资料来源")).toHaveAccessibleDescription(/请说明数字资料来源/);
  });

  it("fades method fields in 120ms, stacks trigrams at 360, and clips overflow", () => {
    const css = readFileSync(resolve(process.cwd(), "src/components/task/task-shell.module.css"), "utf8");
    expect(css).toMatch(/\.meihuaMethodFields\s*\{[^}]*animation:[^;\n]*120ms/s);
    expect(css).toMatch(/prefers-reduced-motion:\s*reduce[\s\S]*\.meihuaMethodFields\s*\{[^}]*animation:\s*none/s);
    expect(css).toMatch(
      /@media \(max-width: 22\.5rem\)[\s\S]*\.meihuaTrigramRow\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/s,
    );
    expect(css).toMatch(/\.meihuaMethodFields\s*\{[^}]*min-width:\s*0/s);
    expect(css).toMatch(/\.meihuaMethodFields\s*\{[^}]*overflow-x:\s*clip/s);
  });
});
