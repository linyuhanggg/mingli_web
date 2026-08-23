import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductInputForm } from "@/components/task/product-input-form";
import { RelationshipTaskPage } from "@/components/relationship/relationship-task-page";
import { WorkbenchShell } from "@/components/workbench/workbench-shell";
import { getProductDefinition } from "@/products/catalog";

const relationshipMocks = vi.hoisted(() => ({
  confirmProfileDraft: vi.fn().mockResolvedValue({
    profile_id: "profile-p2",
    profile_version_id: "version-p2",
    subject_ref: "profile-version:version-p2",
    version: 1,
    created_at: "2026-08-15T00:00:00Z",
  }),
  createProfileDraft: vi.fn().mockResolvedValue({ draft_id: "draft-p2", status: "draft" }),
  startBaziRelationshipReading: vi.fn().mockResolvedValue({ reading_version_id: "reading-p2" }),
  startQizhengRelationshipReading: vi.fn().mockResolvedValue({ reading_version_id: "reading-p2" }),
  startZiweiRelationshipReading: vi.fn().mockResolvedValue({ reading_version_id: "reading-p2" }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  ...relationshipMocks,
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(cleanup);

function submitButton(productId: string) {
  const labels: Record<string, RegExp> = {
    liuyao: /^立即起卦 · 查看本卦与变卦$/,
    wenshi: /^立即起卦 · 三术分别呈现$/,
    jianxiang: /^开始观照 · 生成结构化观察$/,
  };
  return screen.getByRole("button", { name: labels[productId] ?? /^(立即|开始)/ });
}

describe("P2 product interaction contracts", () => {
  it("keeps the birth date and time controls top-aligned after the time hint appears", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/task/task-shell.module.css"),
      "utf8",
    );

    expect(css).toMatch(/\.dateTimeRow\s*\{[^}]*align-items:\s*start/s);
    expect(css).toMatch(
      /\.dateParts select,\s*\n\.timeParts select\s*\{[^}]*height:\s*var\(--target-min\)/s,
    );
  });

  it("keeps the shared input first screen to a 30px page line and a centered 496px form", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/task/task-shell.module.css"),
      "utf8",
    );
    const tokens = readFileSync(
      resolve(process.cwd(), "../ui/tokens.css"),
      "utf8",
    );

    expect(tokens).toMatch(/--font-size-page:\s*30px/);
    expect(tokens).toMatch(/--container-form:\s*31rem/);
    expect(css).toMatch(/\.pageLine h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(css).toMatch(/\.inputLayout\s*\{[^}]*justify-items:\s*center/s);
    expect(css).toMatch(/\.formPanel[^{]*\{[^}]*max-width:\s*var\(--container-form\)/s);
    expect(css).toMatch(/\.belowFold[^{]*\{[^}]*margin-top:\s*var\(--space-3xl\)/s);
  });

  it.each(["bazi", "ziwei", "qizheng", "luming-nayin"] as const)(
    "disables unknown hour on %s with the frozen reason",
    (productId) => {
      render(<ProductInputForm product={getProductDefinition(productId)} onConfirm={vi.fn()} />);

      const checkbox = screen.getByRole("checkbox", { name: /不知道出生时辰/ });
      expect(checkbox).toBeVisible();
      expect(checkbox).toBeDisabled();
      expect(screen.getByText("请填写明确的出生时间。")).toBeVisible();
      expect(screen.getByText("确认后生成盘面")).toBeVisible();
      expect(screen.queryByText("确认后提交到对应计算服务")).not.toBeInTheDocument();
      if (productId === "ziwei") {
        expect(screen.queryByText(/后续会单独确认闰月、命宫起法与四化版本/)).not.toBeInTheDocument();
      }
    },
  );

  it("does not put the natal unknown-hour control on liuyao", () => {
    render(<ProductInputForm product={getProductDefinition("liuyao")} onConfirm={vi.fn()} />);

    expect(screen.queryByRole("checkbox", { name: /不知道出生时辰/ })).not.toBeInTheDocument();
    expect(screen.getByText("确认后生成盘面")).toBeVisible();
  });

  it("puts time basis on the main natal form", () => {
    render(<ProductInputForm product={getProductDefinition("bazi")} onConfirm={vi.fn()} />);

    expect(screen.getByRole("group", { name: "时间口径" })).toBeVisible();
    expect(screen.getByRole("group", { name: "出生资料" })).toBeVisible();
  });

  it("puts qizheng coordinates in 出生地点与坐标 on the main form", () => {
    render(<ProductInputForm product={getProductDefinition("qizheng")} onConfirm={vi.fn()} />);

    const group = screen.getByRole("group", { name: "出生地点与坐标" });
    expect(group).toBeVisible();
    expect(group).toHaveTextContent("出生经度");
    expect(group).toHaveTextContent("出生纬度");
    expect(group).toHaveTextContent("坐标来源");
  });

  it("exposes the three mutually exclusive Bazi temporal targets in advanced options", async () => {
    const user = userEvent.setup();
    render(<ProductInputForm product={getProductDefinition("bazi")} onConfirm={vi.fn()} />);

    await user.click(screen.getByText("高级排盘选项"));

    expect(screen.getByRole("group", { name: "目标时间层（可选，三选一）" })).toBeVisible();
    expect(screen.getByLabelText("流年目标年份")).toHaveAttribute("inputmode", "numeric");
    expect(screen.getByLabelText("流月目标月份")).toHaveAttribute("type", "month");
    expect(screen.getByLabelText("流日目标日期")).toHaveAttribute("type", "date");
  });

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

  it("rejects an empty relationship form, links errors, and keeps a single generate action", async () => {
    const user = userEvent.setup();
    render(<RelationshipTaskPage productId="bazi" />);

    await user.click(screen.getByRole("button", { name: "生成合盘" }));

    const firstField = screen.getByLabelText("甲方受测对象");
    expect(await screen.findByRole("alert", { name: "请先修正双方资料" })).toBeVisible();
    expect(screen.getAllByRole("button", { name: "生成合盘" })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "检查双方资料" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "创建档案并生成合盘" })).not.toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: "生成合盘" }));

    expect(screen.queryByRole("alert", { name: "请先修正双方资料" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /生成合盘/ })).toHaveLength(1);
  });

  it("does not render the empty hepan workbench or region tabs on input", () => {
    render(<RelationshipTaskPage productId="qizheng" />);

    expect(document.getElementById("qizheng-relationship-tab-0")).toBeNull();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.queryByText("甲方 / 乙方 / 关系区")).not.toBeInTheDocument();
    expect(document.querySelector('[data-state="unavailable"]')).toBeNull();
    expect(screen.queryByText(/待接入/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "检查双方资料" })).not.toBeInTheDocument();
    expect(screen.queryByText("ViewModel")).not.toBeInTheDocument();
    expect(screen.queryByText("Runtime")).not.toBeInTheDocument();
    expect(screen.queryByText("ProfileVersion")).not.toBeInTheDocument();
    const css = readFileSync(
      resolve(process.cwd(), "src/components/relationship/relationship-task-page.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.pageLine h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
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
    await user.click(submitButton(productId));

    expect(onConfirm).not.toHaveBeenCalled();
    expect(await screen.findByText("请完成六次起卦过程")).toBeVisible();
    expect(document.getElementById(`${productId}-line-0`)).toHaveFocus();

    for (let index = 0; index < 6; index += 1) {
      const row = document.getElementById(`${productId}-line-${index}`);
      if (!row) throw new Error(`missing ${productId}-line-${index}`);
      await user.click(within(row).getByRole("radio", { name: "少阳（7）" }));
    }
    await user.click(submitButton(productId));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("requires a bounded timing window before Daliuren timing can be confirmed", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<ProductInputForm product={getProductDefinition("daliuren")} onConfirm={onConfirm} />);

    await user.type(screen.getByLabelText("当前问题"), "这件事何时可能出现回应？");
    await user.selectOptions(screen.getByLabelText("判断侧重"), "timing");
    fireEvent.change(screen.getByLabelText("事件时间"), {
      target: { value: "2026-08-14T10:00" },
    });
    await user.type(screen.getByLabelText("事件地点"), "上海市");
    await user.click(submitButton("daliuren"));

    expect(onConfirm).not.toHaveBeenCalled();
    expect(await screen.findByText("请选择应期观察开始日期")).toBeVisible();

    fireEvent.change(screen.getByLabelText("应期观察开始"), {
      target: { value: "2026-08-15" },
    });
    fireEvent.change(screen.getByLabelText("应期观察结束"), {
      target: { value: "2026-09-14" },
    });
    await user.click(submitButton("daliuren"));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm.mock.calls[0][0]).toMatchObject({
      focus: "timing",
      timingStart: "2026-08-15",
      timingEnd: "2026-09-14",
    });
  });

  it("uploads only after confirmation, requires a photo, and exposes delete/consent boundaries", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const product = getProductDefinition("jianxiang");
    render(<ProductInputForm product={product} onConfirm={onConfirm} />);

    expect(screen.getByLabelText("观照模式")).toBeVisible();
    expect(screen.getByRole("checkbox", { name: /照片处理独立同意/ })).toBeVisible();
    expect(screen.getByLabelText("选择见相照片")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "当前不使用相机采集" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "服务端质量检查已接入" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "检查照片质量" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: /照片处理独立同意/ }));
    await user.click(submitButton("jianxiang"));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(await screen.findByText("请选择一张照片")).toBeVisible();

    const fileInput = screen.getByLabelText("选择见相照片") as HTMLInputElement;
    const file = new File(["local-image"], "face.jpg", { type: "image/jpeg" });
    await user.upload(fileInput, file);
    expect(screen.getByRole("status", { name: "已选择本地照片" })).toHaveTextContent("face.jpg");

    await user.click(screen.getByRole("button", { name: "删除本地照片" }));
    expect(screen.getByRole("status", { name: "本地照片已删除" })).toBeVisible();
    expect(fileInput.files).toHaveLength(0);

    await user.upload(fileInput, file);
    await user.type(screen.getByLabelText("受测对象"), "本人");
    await user.type(screen.getByLabelText("用户补充信息"), "左侧步态需要结合本人补充");
    await user.click(screen.getByRole("checkbox", { name: /保存到见相档案/ }));
    await user.click(submitButton("jianxiang"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm.mock.calls[0][0]).toMatchObject({
      observationNotes: "左侧步态需要结合本人补充",
      photoSelected: true,
      saveToArchive: true,
    });
    expect(onConfirm.mock.calls[0][0]).not.toHaveProperty("file");
  });

  it("does not use 待接入 as a Status title on the jianxiang capture panel", () => {
    render(<ProductInputForm product={getProductDefinition("jianxiang")} onConfirm={vi.fn()} />);

    expect(screen.queryByRole("status", { name: /待接入/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "当前不使用相机采集" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "服务端质量检查已接入" })).not.toBeInTheDocument();
  });

  it("reserves scroll space above every sticky reading anchor target", () => {
    const css = readFileSync(resolve(process.cwd(), "src/components/reading/reading-shell.module.css"), "utf8");
    expect(css).toMatch(/\.reading\s*>\s*section\s*\{[^}]*scroll-margin-top:/s);
  });
});
