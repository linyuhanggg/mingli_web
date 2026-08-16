import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminCmsSurface } from "@/components/admin-cms-surface";

describe("AdminCmsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows the latest CMS revision metadata without a content body", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        revisions: [
          {
            revision_id: "revision-1",
            content_key: "faq.home",
            locale: "zh-CN",
            revision: 2,
            state: "draft",
            author_ref: "ops@example.com",
            publish_at: null,
            withdrawn_reason: null,
            created_at: "2026-08-14T01:00:00Z",
          },
        ],
      },
    });

    render(<AdminCmsSurface title="CMS 帮助" prefix="faq" role="ops" />);

    expect(await screen.findByText("faq.home")).toBeVisible();
    expect(screen.getByText("草稿")).toBeVisible();
    expect(screen.getByText("ops@example.com")).toBeVisible();
    expect(screen.queryByText("正文秘密")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/cms?prefix=faq&locale=zh-CN&limit=100",
    );
  });

  it("keeps the pages panel scoped to page-facing CMS namespaces", async () => {
    const revision = (contentKey: string) => ({
      revision_id: `${contentKey}-revision`,
      content_key: contentKey,
      locale: "zh-CN",
      revision: 1,
      state: "published" as const,
      title: contentKey,
      summary: null,
      topic: null,
      source_title: null,
      source_url: null,
      author_ref: "ops@example.com",
      publish_at: null,
      withdrawn_reason: null,
      created_at: "2026-08-14T01:00:00Z",
    });
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { revisions: [revision("home.hero")] } })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [revision("page.about")] } })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [revision("notice")] } })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [revision("seo.home")] } });

    render(
      <AdminCmsSurface
        title="CMS 页面"
        prefixes={["home.", "page.", "notice", "seo."]}
        role="ops"
      />,
    );

    expect((await screen.findAllByText("home.hero")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("page.about").length).toBeGreaterThan(0);
    expect(screen.getAllByText("notice").length).toBeGreaterThan(0);
    expect(screen.getAllByText("seo.home").length).toBeGreaterThan(0);
    expect(adminFetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/admin/cms?prefix=home.&locale=zh-CN&limit=100",
    );
    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/cms?prefix=page.&locale=zh-CN&limit=100",
    );
    expect(adminFetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/admin/cms?prefix=notice&locale=zh-CN&limit=100",
    );
    expect(adminFetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/v1/admin/cms?prefix=seo.&locale=zh-CN&limit=100",
    );
  });

  it("keeps CMS data away from support staff", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "CMS editor permission required",
    });

    render(<AdminCmsSurface title="CMS 帮助" prefix="faq" role="support" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByText("faq.home")).not.toBeInTheDocument();
  });

  it("loads the selected content history and displays the stored body", async () => {
    adminFetchMock
      .mockResolvedValueOnce({
        ok: true,
        data: {
          revisions: [
            {
              revision_id: "revision-1",
              content_key: "faq.home",
              locale: "zh-CN",
              revision: 2,
              state: "draft",
              title: "帮助标题",
              summary: "帮助摘要",
              topic: "方法与边界",
              source_title: "公开来源",
              source_url: "https://example.com/source",
              author_ref: "ops@example.com",
              publish_at: null,
              withdrawn_reason: null,
              created_at: "2026-08-14T01:00:00Z",
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        ok: true,
        data: {
          revisions: [
            {
              revision_id: "revision-1",
              content_key: "faq.home",
              locale: "zh-CN",
              revision: 2,
              state: "draft",
              title: "帮助标题",
              summary: "帮助摘要",
              topic: "方法与边界",
              source_title: "公开来源",
              source_url: "https://example.com/source",
              body: "真实帮助正文",
              author_ref: "ops@example.com",
              publish_at: null,
              withdrawn_reason: null,
              created_at: "2026-08-14T01:00:00Z",
            },
          ],
        },
      });

    const user = userEvent.setup();
    render(<AdminCmsSurface title="CMS 帮助" prefix="faq" role="ops" />);

    await user.click(await screen.findByRole("button", { name: "查看历史 faq.home" }));

    expect(await screen.findByText("真实帮助正文")).toBeVisible();
    expect(screen.getByText("帮助标题")).toBeVisible();
    expect(screen.getByText("帮助摘要")).toBeVisible();
    expect(screen.getByText("方法与边界")).toBeVisible();
    expect(screen.getByRole("link", { name: "公开来源" })).toHaveAttribute(
      "href",
      "https://example.com/source",
    );
    expect(screen.getByText("修订历史")).toBeVisible();
    expect(adminFetchMock).toHaveBeenLastCalledWith(
      "/api/v1/admin/cms/faq.home/history?locale=zh-CN",
    );
  });

  it("edits structured CMS metadata with the draft body and audit reason", async () => {
    const draft = {
      revision_id: "revision-metadata",
      content_key: "library.intro",
      locale: "zh-CN",
      revision: 1,
      state: "draft" as const,
      title: "旧标题",
      summary: "旧摘要",
      topic: "术数基础",
      source_title: "旧来源",
      source_url: "https://example.com/old",
      author_ref: "ops@example.com",
      publish_at: null,
      withdrawn_reason: null,
      created_at: "2026-08-14T01:00:00Z",
      body: "旧正文",
    };
    const updated = {
      ...draft,
      title: "新标题",
      summary: "新摘要",
      topic: "方法与边界",
      source_title: "新来源",
      source_url: "https://example.com/new",
      body: "新正文",
    };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { revisions: [draft] } })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [draft] } })
      .mockResolvedValueOnce({ ok: true, data: updated })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [updated] } });

    const user = userEvent.setup();
    render(<AdminCmsSurface title="CMS 知识" prefix="library" role="ops" />);

    await user.click(await screen.findByRole("button", { name: "查看历史 library.intro" }));
    const title = await screen.findByRole("textbox", { name: "标题 修订 1" });
    await user.clear(title);
    await user.type(title, "新标题");
    const summary = screen.getByRole("textbox", { name: "摘要 修订 1" });
    await user.clear(summary);
    await user.type(summary, "新摘要");
    const topic = screen.getByRole("textbox", { name: "主题 修订 1" });
    await user.clear(topic);
    await user.type(topic, "方法与边界");
    const sourceTitle = screen.getByRole("textbox", { name: "来源标题 修订 1" });
    await user.clear(sourceTitle);
    await user.type(sourceTitle, "新来源");
    const sourceUrl = screen.getByRole("textbox", { name: "来源链接 修订 1" });
    await user.clear(sourceUrl);
    await user.type(sourceUrl, "https://example.com/new");
    const body = screen.getByRole("textbox", { name: "正文 修订 1" });
    await user.clear(body);
    await user.type(body, "新正文");
    await user.type(screen.getByRole("textbox", { name: "操作原因" }), "补充公开内容元数据");
    await user.click(screen.getByRole("button", { name: "保存草稿" }));

    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/cms/revision-metadata",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          body: "新正文",
          reason: "补充公开内容元数据",
          title: "新标题",
          summary: "新摘要",
          topic: "方法与边界",
          source_title: "新来源",
          source_url: "https://example.com/new",
        }),
      }),
    );
  });

  it("creates a namespaced CMS draft with metadata and an audit reason", async () => {
    const created = {
      revision_id: "revision-created",
      content_key: "faq.new-entry",
      locale: "zh-CN",
      revision: 1,
      state: "draft" as const,
      title: "新的帮助标题",
      summary: "新的帮助摘要",
      topic: "方法与边界",
      source_title: "公开来源",
      source_url: "https://example.com/help",
      body: "新的帮助正文",
      author_ref: "ops@example.com",
      publish_at: null,
      withdrawn_reason: null,
      created_at: "2026-08-14T01:00:00Z",
    };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { revisions: [] } })
      .mockResolvedValueOnce({ ok: true, data: created })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [created] } });

    const user = userEvent.setup();
    render(<AdminCmsSurface title="CMS 帮助" prefix="faq" role="ops" />);

    await screen.findByText("暂无 CMS 版本");
    await user.type(screen.getByRole("textbox", { name: "内容键" }), "faq.new-entry");
    await user.type(screen.getByRole("textbox", { name: "标题" }), "新的帮助标题");
    await user.type(screen.getByRole("textbox", { name: "摘要" }), "新的帮助摘要");
    await user.type(screen.getByRole("textbox", { name: "主题" }), "方法与边界");
    await user.type(screen.getByRole("textbox", { name: "来源标题" }), "公开来源");
    await user.type(screen.getByRole("textbox", { name: "来源链接" }), "https://example.com/help");
    await user.type(screen.getByRole("textbox", { name: "正文" }), "新的帮助正文");
    await user.type(screen.getByRole("textbox", { name: "新建操作原因" }), "新增帮助入口");
    await user.click(screen.getByRole("button", { name: "创建草稿" }));

    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/cms",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          content_key: "faq.new-entry",
          locale: "zh-CN",
          body: "新的帮助正文",
          reason: "新增帮助入口",
          title: "新的帮助标题",
          summary: "新的帮助摘要",
          topic: "方法与边界",
          source_title: "公开来源",
          source_url: "https://example.com/help",
        }),
      }),
    );
    expect(await screen.findByText("CMS 草稿已创建")).toBeVisible();
    expect(await screen.findByText("faq.new-entry")).toBeVisible();
  });

  it("rejects an unregistered key on the pages panel before writing", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { revisions: [] } });

    const user = userEvent.setup();
    render(<AdminCmsSurface title="CMS 页面" role="ops" />);

    await screen.findByText("暂无 CMS 版本");
    await user.type(screen.getByRole("textbox", { name: "内容键" }), "unregistered.random");
    await user.type(screen.getByRole("textbox", { name: "正文" }), "不应登记的内容");
    await user.type(screen.getByRole("textbox", { name: "新建操作原因" }), "验证内容命名空间");
    await user.click(screen.getByRole("button", { name: "创建草稿" }));

    expect(await screen.findByText("页面面板只允许已登记的 home、page、notice 或 seo 命名空间。")).toBeVisible();
    expect(adminFetchMock).toHaveBeenCalledTimes(1);
  });

  it("edits a draft through the audited CMS command", async () => {
    const draft = {
      revision_id: "revision-1",
      content_key: "faq.home",
      locale: "zh-CN",
      revision: 2,
      state: "draft" as const,
      author_ref: "ops@example.com",
      publish_at: null,
      withdrawn_reason: null,
      created_at: "2026-08-14T01:00:00Z",
    };
    const updated = { ...draft, body: "新的帮助正文" };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { revisions: [draft] } })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [updated] } })
      .mockResolvedValueOnce({ ok: true, data: updated })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [updated] } })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [updated] } });

    const user = userEvent.setup();
    render(<AdminCmsSurface title="CMS 帮助" prefix="faq" role="ops" />);

    await user.click(await screen.findByRole("button", { name: "查看历史 faq.home" }));
    const body = await screen.findByRole("textbox", { name: "正文 修订 2" });
    await user.clear(body);
    await user.type(body, "新的帮助正文");
    await user.type(screen.getByRole("textbox", { name: "操作原因" }), "修正事实表述");
    await user.click(screen.getByRole("button", { name: "保存草稿" }));

    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/cms/revision-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ body: "新的帮助正文", reason: "修正事实表述" }),
      }),
    );
    expect(await screen.findByText("CMS 命令已完成")).toBeVisible();
  });

  it("does not claim a clean success when the post-command history refresh fails", async () => {
    const draft = {
      revision_id: "revision-1",
      content_key: "faq.home",
      locale: "zh-CN",
      revision: 2,
      state: "draft" as const,
      author_ref: "ops@example.com",
      publish_at: null,
      withdrawn_reason: null,
      created_at: "2026-08-14T01:00:00Z",
    };
    const updated = { ...draft, body: "新的帮助正文" };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { revisions: [draft] } })
      .mockResolvedValueOnce({ ok: true, data: { revisions: [updated] } })
      .mockResolvedValueOnce({ ok: true, data: updated })
      .mockResolvedValueOnce({ ok: false, status: 503, title: "CMS history unavailable" });

    const user = userEvent.setup();
    render(<AdminCmsSurface title="CMS 帮助" prefix="faq" role="ops" />);

    await user.click(await screen.findByRole("button", { name: "查看历史 faq.home" }));
    await user.type(screen.getByRole("textbox", { name: "操作原因" }), "修正事实表述");
    await user.click(screen.getByRole("button", { name: "保存草稿" }));

    expect(await screen.findByText("CMS 命令已完成，但历史刷新失败，请重新读取。")).toBeVisible();
    expect(screen.queryByText("CMS 命令已完成", { exact: true })).not.toBeInTheDocument();
  });
});
