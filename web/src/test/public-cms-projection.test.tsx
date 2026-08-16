import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PublicCmsProjection } from "@/components/public-cms-projection";

const requestJsonMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, requestJson: requestJsonMock };
});

describe("public CMS editorial projection", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it("keeps an explicit empty state when an item is not published", async () => {
    requestJsonMock.mockRejectedValue({ status: 404 });

    render(
      <PublicCmsProjection
        heading="已发布政策内容"
        source={{ kind: "item", contentKey: "policy.privacy" }}
      />,
    );

    expect(await screen.findByRole("status", { name: "没有已发布的 CMS 内容" })).toHaveAttribute(
      "data-state",
      "empty",
    );
    expect(requestJsonMock).toHaveBeenCalledWith("/api/v1/content/policy.privacy");
  });

  it("renders published help items and their public source metadata", async () => {
    requestJsonMock.mockResolvedValue({
      items: [
        {
          content_key: "faq.login",
          locale: "zh-CN",
          revision: 2,
          title: "如何登录",
          summary: "先完成验证码核验。",
          topic: "账号",
          source_title: "账号说明",
          source_url: "https://example.com/help",
          body: "登录服务开放后，从登录入口开始。",
          created_at: "2026-08-14T04:00:00Z",
        },
      ],
    });

    render(
      <PublicCmsProjection
        heading="已发布帮助"
        source={{ kind: "index", prefix: "faq" }}
      />,
    );

    expect(await screen.findByRole("heading", { name: "如何登录" })).toBeVisible();
    expect(screen.getByText("先完成验证码核验。")).toBeVisible();
    expect(screen.getByText("账号")).toBeVisible();
    expect(screen.getByText("登录服务开放后，从登录入口开始。")).toBeVisible();
    expect(screen.getByRole("link", { name: "账号说明" })).toHaveAttribute(
      "href",
      "https://example.com/help",
    );
    expect(requestJsonMock).toHaveBeenCalledWith(
      "/api/v1/content?prefix=faq&locale=zh-CN&limit=100",
    );
  });
});
