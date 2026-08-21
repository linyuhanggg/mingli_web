import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RuntimeChart } from "@/components/readings/runtime-chart";
import { ProductInputForm } from "@/components/task/product-input-form";
import { ProductTaskExperience } from "@/components/task/product-task-experience";
import { ApiError } from "@/lib/api";
import { getProductDefinition } from "@/products/catalog";
import type { HecanViewModel } from "@/view-models/registry";

const mockRouterPush = vi.hoisted(() => vi.fn());
const mockListProfiles = vi.hoisted(() => vi.fn());
const mockStartHecanReading = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: mockRouterPush }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  listProfiles: mockListProfiles,
  startHecanReading: mockStartHecanReading,
}));

beforeEach(() => {
  mockRouterPush.mockReset();
  mockStartHecanReading.mockReset().mockResolvedValue({ reading_version_id: "hecan-reading-1" });
  mockListProfiles.mockReset().mockResolvedValue({ profiles: [] });
});

describe("jianxiang + hecan three items", () => {
  it("keeps the jianxiang first screen to mode, consent, and file select", () => {
    render(<ProductInputForm product={getProductDefinition("jianxiang")} onConfirm={() => undefined} />);

    expect(screen.getByLabelText("观照模式")).toBeVisible();
    expect(screen.getByRole("checkbox", { name: /照片处理独立同意/ })).toBeVisible();
    expect(screen.getByLabelText("选择见相照片")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "当前不使用相机采集" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "服务端质量检查已接入" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "检查照片质量" })).not.toBeInTheDocument();
    expect(screen.queryByText("不使用相机")).not.toBeInTheDocument();
    expect(screen.queryByText("已接入")).not.toBeInTheDocument();
  });

  it("uses confirm-then-generate copy on hecan instead of 计算服务", () => {
    render(<ProductInputForm product={getProductDefinition("hecan")} onConfirm={() => undefined} />);

    expect(screen.getByText("确认后生成")).toBeVisible();
    expect(screen.getByRole("button", { name: /立即合参/ })).toBeVisible();
    expect(screen.queryByText(/计算服务/)).not.toBeInTheDocument();
    expect(screen.getByText("八字为主理，再从紫微、七政中选择。没有结果就说没有可展示的互证。")).toBeVisible();
    expect(screen.queryByText(/接入/)).not.toBeInTheDocument();
  });

  it("selects a confirmed archive without exposing its internal identifier", async () => {
    const profileVersionId = "22222222-2222-4222-8222-222222222222";
    mockListProfiles.mockResolvedValue({
      profiles: [{
        profile_id: "11111111-1111-4111-8111-111111111111",
        profile_version_id: profileVersionId,
        subject_ref: `profile-version:${profileVersionId}`,
        version: 3,
        created_at: "2026-08-12T06:08:00Z",
      }],
    });
    const user = userEvent.setup();

    render(<ProductTaskExperience product={getProductDefinition("hecan")} />);

    const selector = await screen.findByRole("combobox", { name: "立命资料" });
    expect(selector).toHaveValue(profileVersionId);
    expect(screen.getByRole("option", { name: /档案 3 ·/ })).toBeVisible();
    expect(screen.getByRole("region", { name: "提交前摘要" })).toHaveTextContent(/立命资料档案 3 ·/);
    expect(screen.queryByText(/ProfileVersion|UUID/)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "立命资料" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: /八字/ }));
    await user.click(screen.getByRole("checkbox", { name: /紫微/ }));
    await user.click(screen.getByRole("button", { name: /立即合参/ }));

    await waitFor(() => expect(mockStartHecanReading).toHaveBeenCalledTimes(1));
    expect(mockStartHecanReading).toHaveBeenCalledWith(
      expect.objectContaining({
        profile_version_id: profileVersionId,
        selected_art_ids: ["bazi", "ziwei"],
      }),
      expect.any(String),
    );
  });

  it("offers login or birth details to a guest instead of an internal-id fallback", async () => {
    mockListProfiles.mockRejectedValue(new ApiError("需要登录", 401));

    render(<ProductTaskExperience product={getProductDefinition("hecan")} />);

    expect(await screen.findByRole("link", { name: "登录后选择已有档案" })).toHaveAttribute(
      "href",
      "/auth/login?returnTo=/hecan",
    );
    expect(screen.getByRole("group", { name: "出生资料（建立新档案）" })).toBeVisible();
    expect(screen.getByLabelText("受测对象")).toBeVisible();
    expect(screen.queryByText(/ProfileVersion|UUID/)).not.toBeInTheDocument();
  });

  it("says 没有可展示的互证 when hecan has no returned facts", () => {
    const empty: HecanViewModel = {
      schema_version: "hecan-view/v1",
      subject_ref: "profile-version:test",
      selected_art_ids: ["bazi", "ziwei"],
      dimensions: [],
    };

    render(<RuntimeChart viewModel={empty} />);

    expect(screen.getByText("没有可展示的互证")).toBeVisible();
    expect(screen.queryByText(/Runtime/)).not.toBeInTheDocument();
    expect(screen.queryByText(/接入/)).not.toBeInTheDocument();
    expect(screen.queryByText(/计算服务/)).not.toBeInTheDocument();
  });

  it("keeps 八字为主理 when hecan already has returned facts", () => {
    const filled: HecanViewModel = {
      schema_version: "hecan-view/v1",
      subject_ref: "profile-version:test",
      selected_art_ids: ["bazi", "ziwei"],
      dimensions: [
        {
          dimension_id: "career",
          signals: [{ art_id: "bazi", subject_refs: ["profile-version:test"], signal_id: "career-bazi", display_text: "日主为甲", fact_refs: [] }],
          convergence: ["两术目前只声明共同事实范围。"],
          disagreements: [],
          missing_art_ids: [],
        },
      ],
    };

    render(<RuntimeChart viewModel={filled} />);

    expect(screen.getByText("八字为主理。")).toBeVisible();
    expect(screen.queryByText("没有可展示的互证")).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime/)).not.toBeInTheDocument();
  });

  it("does not leave construction copy in the production files for this knife", () => {
    const files = [
      "src/components/task/product-input-form.tsx",
      "src/components/readings/runtime-chart.tsx",
    ];
    for (const rel of files) {
      const source = readFileSync(resolve(process.cwd(), rel), "utf8");
      expect(source).not.toMatch(/检查照片质量|当前不使用相机采集|服务端质量检查已接入|计算服务|结构接入|quality-unavailable/);
      expect(source).not.toMatch(/Runtime 已声明的共同事实范围/);
    }
  });
});
