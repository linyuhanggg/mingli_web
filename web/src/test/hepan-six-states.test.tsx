import { cleanup, render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import BaziHepanLabPage, { metadata } from "@/app/%5Fui-lab/bazi-hepan/page";
import { RelationshipTaskPage } from "@/components/relationship/relationship-task-page";
import { UiLab } from "@/components/ui-lab/ui-lab";

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

function renderLab() {
  return render(<UiLab demoLabel="UI 演示数据" />);
}

async function chooseRoute(id: string) {
  const user = userEvent.setup();
  renderLab();
  await user.selectOptions(screen.getByRole("combobox", { name: "页面与场景" }), id);
  return user;
}

describe("bazi hepan six states", () => {
  it("keeps the input page to back, title, both people, relationship, and one generate action", () => {
    render(<RelationshipTaskPage productId="bazi" />);

    expect(screen.getByRole("link", { name: "返回" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "八字双人合盘" })).toBeVisible();
    expect(screen.getByRole("group", { name: "甲方资料" })).toBeVisible();
    expect(screen.getByRole("group", { name: "乙方资料" })).toBeVisible();
    expect(screen.getByLabelText("关系类型")).toBeVisible();
    expect(screen.getByRole("button", { name: "生成合盘" })).toBeEnabled();
    expect(screen.getAllByRole("button", { name: "生成合盘" })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "检查双方资料" })).not.toBeInTheDocument();
    expect(screen.queryByText("甲方 / 乙方 / 关系区")).not.toBeInTheDocument();
    expect(document.querySelector('[data-state="unavailable"]')).toBeNull();
    expect(screen.queryByText(/待接入/)).not.toBeInTheDocument();
    expect(screen.queryByText("ViewModel")).not.toBeInTheDocument();
    expect(screen.queryByText("Runtime")).not.toBeInTheDocument();
    expect(screen.queryByText("ProfileVersion")).not.toBeInTheDocument();
    const css = readFileSync(
      resolve(process.cwd(), "src/components/relationship/relationship-task-page.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.pageLine h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(screen.queryByText("self_sit")).not.toBeInTheDocument();
    expect(screen.queryByText("interpretive_candidates")).not.toBeInTheDocument();
    expect(screen.queryByText("未裁定")).not.toBeInTheDocument();
  });

  it("reaches honest clickable hepan states from the production page prop", () => {
    const { rerender } = render(<RelationshipTaskPage productId="bazi" surfaceState="loading" />);
    expect(screen.getByRole("status", { name: "正在读取合盘…" })).toHaveAttribute(
      "data-state",
      "loading",
    );

    rerender(<RelationshipTaskPage productId="bazi" surfaceState="empty" />);
    expect(screen.getByRole("status", { name: "还没有可展示的盘面" })).toHaveAttribute("data-state", "empty");
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "返回合盘输入" })).toHaveAttribute("href", "/bazi/hepan");

    rerender(<RelationshipTaskPage productId="bazi" surfaceState="error" />);
    expect(screen.getByRole("alert", { name: "读取失败，请重试" })).toHaveAttribute("data-state", "error");
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();

    rerender(<RelationshipTaskPage productId="bazi" surfaceState="processing" />);
    expect(screen.getByRole("status", { name: "正在处理合盘…" })).toHaveAttribute(
      "data-state",
      "processing",
    );

    rerender(<RelationshipTaskPage productId="bazi" surfaceState="unavailable" />);
    expect(screen.getByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    expect(screen.queryByText(/待接入/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "导出待接入" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "深读待接入" })).not.toBeInTheDocument();
    expect(screen.queryByText("ViewModel")).not.toBeInTheDocument();
    expect(screen.queryByText("Runtime")).not.toBeInTheDocument();
    expect(screen.queryByText("ProfileVersion")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看术数总览" })).toHaveAttribute("href", "/arts");

    rerender(<RelationshipTaskPage productId="bazi" surfaceState="unauthorized" />);
    expect(screen.getByRole("status", { name: "需要登录才能看这份结果" })).toHaveAttribute(
      "data-state",
      "unauthorized",
    );
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
  });

  it("reaches honest clickable hepan states from UI Lab", async () => {
    const user = await chooseRoute("bazi-hepan");
    const preview = () => within(screen.getByTestId("ui-lab-preview"));

    expect(preview().getByText("八字合盘暂无结果 Fixture")).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "loading");
    expect(preview().getByRole("status", { name: "正在读取合盘…" })).toHaveAttribute(
      "data-state",
      "loading",
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "empty");
    expect(preview().getByRole("status", { name: "还没有可展示的盘面" })).toHaveAttribute(
      "data-state",
      "empty",
    );
    expect(preview().getByRole("button", { name: "重试" })).toBeEnabled();
    expect(preview().getByRole("link", { name: "返回合盘输入" })).toHaveAttribute(
      "href",
      "/bazi/hepan",
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "failed");
    expect(preview().getByRole("alert", { name: "读取失败，请重试" })).toHaveAttribute("data-state", "error");
    expect(preview().getByRole("button", { name: "重试" })).toBeEnabled();

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "queued");
    expect(preview().getByRole("status", { name: "正在处理合盘…" })).toHaveAttribute(
      "data-state",
      "processing",
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "unavailable");
    expect(preview().getByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    expect(preview().getByRole("link", { name: "查看术数总览" })).toHaveAttribute("href", "/arts");

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "unauthorized");
    expect(preview().getByRole("status", { name: "需要登录才能看这份结果" })).toHaveAttribute(
      "data-state",
      "unauthorized",
    );
    expect(preview().getByRole("link", { name: "登录后继续" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
  });

  it("lets reviewers open each of the six honest hepan states on the lab route", async () => {
    const user = userEvent.setup();
    render(<BaziHepanLabPage />);

    expect(metadata).toMatchObject({ robots: { index: false, follow: false } });
    expect(screen.getByRole("navigation", { name: "合盘六态" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "甲方 / 乙方 / 关系区" })).toBeVisible();
    expect(screen.getByText(/待接入/)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "unauthorized" }));
    expect(screen.getByRole("status", { name: "需要登录才能看这份结果" })).toBeVisible();
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
    expect(screen.queryByRole("heading", { name: "甲方 / 乙方 / 关系区" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "unavailable" }));
    expect(screen.getByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" })).toBeVisible();
    expect(screen.getByRole("link", { name: "查看术数总览" })).toHaveAttribute("href", "/arts");

    await user.click(screen.getByRole("button", { name: "已返回事实" }));
    expect(screen.getByRole("heading", { name: "甲方 / 乙方 / 关系区" })).toBeVisible();
  });
});
