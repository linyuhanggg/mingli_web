import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductInputForm } from "@/components/task/product-input-form";
import { RelationshipTaskPage } from "@/components/relationship/relationship-task-page";
import { WorkbenchShell } from "@/components/workbench/workbench-shell";
import { getProductDefinition } from "@/products/catalog";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(cleanup);

describe("P2 product interaction contracts", () => {
  it("opens the compact workbench menu from the keyboard and explains every disabled action", async () => {
    const user = userEvent.setup();
    const product = getProductDefinition("bazi");
    render(<WorkbenchShell product={product} onBack={vi.fn()} />);

    const trigger = document.querySelector('button[aria-label="更多"]') as HTMLButtonElement;
    trigger.focus();
    await user.keyboard("{Enter}");

    const menu = await waitFor(() => {
      const node = document.querySelector('[role="menu"][aria-label="更多任务操作"]');
      expect(node).not.toBeNull();
      return node as HTMLElement;
    });
    const items = Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]'));
    expect(items).toHaveLength(7);
    await waitFor(() => expect(document.activeElement).toHaveAttribute("role", "menuitem"));
    for (const [index, label] of ["规则", "保存", "导出", "分享", "历史", "权益", "账户"].entries()) {
      const item = items[index];
      expect(item).toHaveTextContent(label);
      expect(item).toHaveAttribute("aria-disabled", "true");
      const reasonId = item.getAttribute("aria-describedby");
      expect(reasonId).toBeTruthy();
      expect(document.getElementById(reasonId as string)).toHaveTextContent(product.unavailableReason);
    }

    await user.keyboard("{Escape}");
    await waitFor(() => expect(document.querySelector('[role="menu"][aria-label="更多任务操作"]')).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("rejects an empty relationship form, links errors, and focuses the first invalid field", async () => {
    const user = userEvent.setup();
    render(<RelationshipTaskPage productId="bazi" />);

    await user.click(screen.getByRole("button", { name: "检查双方资料" }));

    const firstField = screen.getByLabelText("甲方受测对象");
    expect(await screen.findByRole("alert", { name: "请先修正双方资料" })).toBeVisible();
    expect(screen.queryByText(/输入结构已检查/)).not.toBeInTheDocument();
    expect(firstField).toHaveAttribute("aria-invalid", "true");
    expect(firstField).toHaveFocus();
  });

  it("accepts the relationship form only after both people are complete", async () => {
    const user = userEvent.setup();
    render(<RelationshipTaskPage productId="ziwei" />);

    await user.type(screen.getByLabelText("甲方受测对象"), "甲");
    await user.selectOptions(screen.getByLabelText("甲方性别"), "male");
    await user.selectOptions(screen.getByLabelText("甲方时间口径"), "solar");
    fireEvent.change(screen.getByLabelText("甲方出生日期"), { target: { value: "1990-01-02" } });
    fireEvent.change(screen.getByLabelText("甲方出生时间"), { target: { value: "08:30" } });
    await user.type(screen.getByLabelText("甲方出生地点"), "南京");
    await user.type(screen.getByLabelText("甲方出生经度"), "118.78");
    await user.type(screen.getByLabelText("甲方出生纬度"), "32.06");
    await user.type(screen.getByLabelText("甲方坐标来源"), "用户确认");
    await user.type(screen.getByLabelText("乙方受测对象"), "乙");
    await user.selectOptions(screen.getByLabelText("乙方性别"), "female");
    await user.selectOptions(screen.getByLabelText("乙方时间口径"), "civil");
    fireEvent.change(screen.getByLabelText("乙方出生日期"), { target: { value: "1992-03-04" } });
    fireEvent.change(screen.getByLabelText("乙方出生时间"), { target: { value: "09:45" } });
    await user.type(screen.getByLabelText("乙方出生地点"), "上海");
    await user.click(screen.getByRole("button", { name: "检查双方资料" }));

    expect(await screen.findByText(/输入结构已检查/)).toBeVisible();
    expect(screen.queryByRole("alert", { name: "请先修正双方资料" })).not.toBeInTheDocument();
  });

  it("moves relationship tabs with arrows, Home, and End while keeping focus and selection together", async () => {
    const user = userEvent.setup();
    render(<RelationshipTaskPage productId="qizheng" />);

    const first = document.getElementById("qizheng-relationship-tab-0") as HTMLButtonElement;
    const second = document.getElementById("qizheng-relationship-tab-1") as HTMLButtonElement;
    const last = document.getElementById("qizheng-relationship-tab-2") as HTMLButtonElement;
    first.focus();

    await user.keyboard("{ArrowRight}");
    expect(second).toHaveFocus();
    expect(second).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{End}");
    expect(last).toHaveFocus();
    expect(last).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{Home}");
    expect(first).toHaveFocus();
    expect(first).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{ArrowLeft}");
    expect(last).toHaveFocus();
    expect(last).toHaveAttribute("aria-selected", "true");
  });

  it.each(["liuyao", "wenshi"] as const)("requires all six line records before %s input can be confirmed", async (productId) => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const product = getProductDefinition(productId);
    render(<ProductInputForm product={product} onConfirm={onConfirm} />);

    await user.type(screen.getByLabelText(productId === "wenshi" ? "同一问题" : "当前问题"), "这件事能否按期完成？");
    if (productId === "liuyao") await user.selectOptions(screen.getByLabelText("起卦方式"), "coins");
    fireEvent.change(screen.getByLabelText(productId === "wenshi" ? "同一事件时空" : "事件时间"), {
      target: { value: "2026-08-13T14:30" },
    });
    if (productId === "liuyao" || productId === "wenshi") {
      await user.type(screen.getByLabelText("事件地点"), "上海市");
    }
    await user.click(screen.getByRole("button", { name: "检查输入" }));

    const lineInputs = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"].map((name) => screen.getByLabelText(name));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(await screen.findByText("请完成六次起卦过程")).toBeVisible();
    expect(lineInputs[0]).toHaveFocus();

    for (const input of lineInputs) await user.selectOptions(input, "young-yang");
    await user.click(screen.getByRole("button", { name: "检查输入" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("uploads only after confirmation, requires a photo, and exposes quality/delete boundaries", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const product = getProductDefinition("jianxiang");
    render(<ProductInputForm product={product} onConfirm={onConfirm} />);

    expect(screen.getByRole("status", { name: "相机采集待接入" })).toBeVisible();
    await user.click(screen.getByRole("checkbox", { name: /照片处理独立同意/ }));
    await user.click(screen.getByRole("button", { name: "检查输入" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(await screen.findByText("请选择一张照片")).toBeVisible();

    const fileInput = screen.getByLabelText("选择见相照片") as HTMLInputElement;
    const file = new File(["local-image"], "face.jpg", { type: "image/jpeg" });
    await user.upload(fileInput, file);
    expect(screen.getByRole("status", { name: "已选择本地照片" })).toHaveTextContent("face.jpg");
    expect(screen.getByRole("status", { name: "服务端质量检查已接入" })).toBeVisible();

    await user.click(screen.getByRole("button", { name: "删除本地照片" }));
    expect(screen.getByRole("status", { name: "本地照片已删除" })).toBeVisible();
    expect(fileInput.files).toHaveLength(0);

    await user.upload(fileInput, file);
    await user.type(screen.getByLabelText("受测对象"), "本人");
    await user.type(screen.getByLabelText("用户补充信息"), "左侧步态需要结合本人补充");
    await user.click(screen.getByRole("checkbox", { name: /保存到见相档案/ }));
    await user.click(screen.getByRole("button", { name: "检查输入" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm.mock.calls[0][0]).toMatchObject({
      observationNotes: "左侧步态需要结合本人补充",
      photoSelected: true,
      saveToArchive: true,
    });
    expect(onConfirm.mock.calls[0][0]).not.toHaveProperty("file");
  });

  it("reserves scroll space above every sticky reading anchor target", () => {
    const css = readFileSync(resolve(process.cwd(), "src/components/reading/reading-shell.module.css"), "utf8");
    expect(css).toMatch(/\.reading\s*>\s*section\s*\{[^}]*scroll-margin-top:/s);
  });
});
