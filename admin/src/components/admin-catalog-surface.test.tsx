import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminCatalogSurface } from "@/components/admin-catalog-surface";
import {
  buildLiveAdminCatalogViewModel,
  type AdminCatalogApiResponse,
} from "@/lib/admin-catalog";
import { resolveAdminRoute } from "@/lib/admin-route-catalog";
import { buildAdminUiLabCatalogViewModel } from "@/lib/admin-ui-lab";

describe("AdminCatalogSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("loads real Catalog data and exposes audited product commands to an operator", async () => {
    const user = userEvent.setup();
    const route = resolveAdminRoute("/products");
    expect(route).not.toBeNull();
    const payload: AdminCatalogApiResponse = {
      families: [
        {
          id: "family-1",
          key: "bazi-deep-reading",
          label: "八字深度解读",
          status: "active",
          created_at: "2026-08-14T00:00:00Z",
          versions: [
            {
              id: "version-1",
              family_id: "family-1",
              version: "v1",
              price_minor: 9900,
              currency: "CNY",
              contract_version: "reading-document-v1",
              follow_up_count: 2,
              follow_up_window_seconds: 90 * 86400,
              status: "draft",
              created_at: "2026-08-14T00:00:00Z",
              offers: [
                {
                  id: "offer-1",
                  product_version_id: "version-1",
                  channel: "closed",
                  channel_sku: "bazi-deep-reading-v1",
                  price_minor: 9900,
                  currency: "CNY",
                  enabled: true,
                  created_at: "2026-08-14T00:00:00Z",
                },
              ],
            },
          ],
        },
      ],
    };
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: payload });
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        id: "family-2",
        key: "ziwei-deep-reading",
        label: "紫微深度解读",
        status: "active",
        created_at: "2026-08-14T00:00:00Z",
        versions: [],
      },
    });
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: payload });

    render(<AdminCatalogSurface model={buildLiveAdminCatalogViewModel(route!)} role="ops" />);

    expect((await screen.findAllByText("八字深度解读")).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Catalog 管理命令" })).toBeVisible();
    expect(screen.getByRole("button", { name: "创建商品族" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "发布 v1" })).toBeEnabled();
    await user.type(screen.getByLabelText("商品族 key"), "ziwei-deep-reading");
    await user.type(screen.getByLabelText("商品族名称"), "紫微深度解读");
    await user.type(screen.getByLabelText("Catalog 操作原因"), "建立第二个商品族");
    await user.click(screen.getByRole("button", { name: "创建商品族" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/catalog/families",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          key: "ziwei-deep-reading",
          label: "紫微深度解读",
          reason: "建立第二个商品族",
        }),
      }),
    );
    expect(await screen.findByText("商品族已创建，Catalog 已刷新。")).toBeVisible();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/catalog");
  });

  it("renders an honest filterable list shell without fixture records", () => {
    const route = resolveAdminRoute("/users");
    expect(route).not.toBeNull();

    render(<AdminCatalogSurface model={buildLiveAdminCatalogViewModel(route!)} role="support" />);

    expect(screen.getByRole("status", { name: "平台数据待接入" })).toBeVisible();
    expect(screen.getByRole("searchbox", { name: "筛选用户与身份" })).toBeVisible();
    expect(screen.getByRole("table", { name: "用户与身份列表" })).toBeVisible();
    expect(screen.getByText("没有可显示的真实记录")).toBeVisible();
    const writeButton = screen.getByRole("button", { name: "发起密码重置" });
    expect(writeButton).toBeDisabled();
    expect(screen.getByText(/控件保持只读/)).toBeVisible();
    expect(screen.queryByText("UI 演示数据")).not.toBeInTheDocument();
  });

  it("opens a detail drawer and completes a reasoned audited demo write", async () => {
    const user = userEvent.setup();
    const route = resolveAdminRoute("/refunds");
    expect(route).not.toBeNull();
    const model = buildAdminUiLabCatalogViewModel(route!, {
      state: "ready",
      role: "finance",
      capabilityState: "INTERNAL_TEST",
      writeState: "原因",
    });

    render(
      <AdminCatalogSurface model={model} role="finance" writeState={model.writeState} />,
    );

    const detailTrigger = screen.getByRole("button", {
      name: `查看详情 ${model.records[1].id}`,
    });
    await user.click(detailTrigger);
    expect(
      screen.getByRole("dialog", { name: `${model.records[1].primary}详情` }),
    ).toBeVisible();
    expect(screen.getByText("UI Lab 响应式与可访问性验收")).toBeVisible();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(detailTrigger).toHaveFocus();

    const writeButton = screen.getByRole("button", { name: "审批退款" });
    expect(writeButton).toBeDisabled();
    await user.click(
      screen.getByRole("checkbox", { name: `选择 ${model.records[1].id}` }),
    );
    expect(writeButton).toBeEnabled();
    await user.click(writeButton);
    const writeDialog = screen.getByRole("dialog", { name: "确认审批退款" });
    expect(writeDialog).toHaveTextContent(model.records[1].primary);
    expect(within(writeDialog).queryByText(model.records[0].primary)).not.toBeInTheDocument();
    const reason = screen.getByRole("textbox", { name: "操作原因" });
    await user.type(reason, "用户提交退款申请，财务核对完成");
    await user.click(screen.getByRole("button", { name: "确认并记录审计" }));
    expect(screen.getByRole("status", { name: "审计记录已完成" })).toBeVisible();
  });

  it("keeps confirmation and reason write states distinct", async () => {
    const user = userEvent.setup();
    const route = resolveAdminRoute("/refunds");
    expect(route).not.toBeNull();
    const model = buildAdminUiLabCatalogViewModel(route!, {
      state: "ready",
      role: "finance",
      capabilityState: "INTERNAL_TEST",
      writeState: "确认",
    });

    const { unmount } = render(
      <AdminCatalogSurface model={model} role="finance" writeState="确认" />,
    );
    await user.click(
      screen.getByRole("checkbox", { name: `选择 ${model.records[0].id}` }),
    );
    await user.click(screen.getByRole("button", { name: "审批退款" }));

    const confirmationDialog = screen.getByRole("dialog", { name: "确认审批退款" });
    expect(confirmationDialog).toHaveTextContent(
      "提交前展示对象、范围和影响，要求主动确认。",
    );
    expect(
      within(confirmationDialog).queryByRole("textbox", { name: "操作原因" }),
    ).not.toBeInTheDocument();
    expect(
      within(confirmationDialog).getByRole("button", { name: "确认并提交" }),
    ).toBeVisible();

    await user.keyboard("{Escape}");
    unmount();

    const reasonModel = buildAdminUiLabCatalogViewModel(route!, {
      state: "ready",
      role: "finance",
      capabilityState: "INTERNAL_TEST",
      writeState: "原因",
    });
    render(
      <AdminCatalogSurface model={reasonModel} role="finance" writeState="原因" />,
    );
    await user.click(
      screen.getByRole("checkbox", { name: `选择 ${reasonModel.records[0].id}` }),
    );
    await user.click(screen.getByRole("button", { name: "审批退款" }));
    expect(screen.getByRole("textbox", { name: "操作原因" })).toBeVisible();
  });

  it("renders route-specific detail and operational surfaces instead of a generic list", () => {
    const scenarios = [
      ["/users/demo-user", "用户详情字段"],
      ["/runtime", "运行时控制面"],
      ["/health", "健康检查面"],
      ["/settings", "系统设置面"],
    ] as const;

    for (const [pathname, heading] of scenarios) {
      const route = resolveAdminRoute(pathname);
      expect(route).not.toBeNull();
      const { unmount } = render(
        <AdminCatalogSurface model={buildLiveAdminCatalogViewModel(route!)} role="superadmin" />,
      );

      expect(screen.getByRole("heading", { name: heading })).toBeVisible();
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      unmount();
    }
  });

  it("keeps support read-only on users but enables a support-case application", async () => {
    const user = userEvent.setup();
    const usersRoute = resolveAdminRoute("/users");
    expect(usersRoute).not.toBeNull();
    const usersModel = buildAdminUiLabCatalogViewModel(usersRoute!, {
      state: "ready",
      role: "support",
      capabilityState: "INTERNAL_TEST",
      writeState: "确认",
    });

    const { unmount } = render(
      <AdminCatalogSurface model={usersModel} role="support" writeState="确认" />,
    );
    const usersButton = screen.getByRole("button", { name: "发起密码重置" });
    await user.click(
      screen.getByRole("checkbox", { name: `选择 ${usersModel.records[0].id}` }),
    );
    expect(usersButton).toBeDisabled();
    expect(screen.getByText(/查看“允许” · 写入“只读”/)).toBeVisible();
    unmount();

    const casesRoute = resolveAdminRoute("/support-cases");
    expect(casesRoute).not.toBeNull();
    const casesModel = buildAdminUiLabCatalogViewModel(casesRoute!, {
      state: "ready",
      role: "support",
      capabilityState: "INTERNAL_TEST",
      writeState: "确认",
    });
    render(<AdminCatalogSurface model={casesModel} role="support" writeState="确认" />);
    const caseButton = screen.getByRole("button", { name: "提交补偿申请" });
    await user.click(
      screen.getByRole("checkbox", { name: `选择 ${casesModel.records[0].id}` }),
    );
    expect(caseButton).toBeEnabled();
    expect(screen.getByText(/查看“允许” · 写入“提交申请”/)).toBeVisible();
  });

  it("uses domain-specific columns for representative Admin list families", () => {
    const scenarios = [
      ["/users", ["身份", "会话", "同意", "状态", "更新时间"]],
      ["/payments", ["支付尝试", "订单", "渠道", "到账事实", "状态"]],
      ["/staff", ["员工", "角色", "会话", "状态", "更新时间"]],
      ["/readings", ["任务根", "版本", "阶段", "受测对象", "更新时间"]],
      ["/cms/pages", ["内容", "版本", "发布态", "更新时间", "责任人"]],
    ] as const;

    for (const [pathname, expectedHeaders] of scenarios) {
      const route = resolveAdminRoute(pathname);
      expect(route).not.toBeNull();
      const model = buildAdminUiLabCatalogViewModel(route!, {
        state: "ready",
        role: "superadmin",
        capabilityState: "INTERNAL_TEST",
        writeState: "确认",
      });
      const { container, unmount } = render(
        <AdminCatalogSurface model={model} role="superadmin" writeState="确认" />,
      );

      expect(
        screen.getAllByRole("columnheader").map((header) => header.textContent?.trim()),
      ).toEqual(["", ...expectedHeaders, "操作"]);
      expect(
        container.querySelector(`td[data-label="${expectedHeaders[0]}"]`),
      ).toBeInTheDocument();
      unmount();
    }
  });
});
