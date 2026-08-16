import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AboutPage from "@/app/about/page";
import HomePage from "@/app/page";
import MethodologyPage from "@/app/methodology/page";
import PrivacyPage from "@/app/privacy/page";
import SupportPage from "@/app/support/page";
import TermsPage from "@/app/terms/page";

const requestJsonMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, requestJson: requestJsonMock };
});

describe("public editorial CMS wiring", () => {
  beforeEach(() => {
    requestJsonMock.mockResolvedValue({ items: [] });
    requestJsonMock.mockClear();
  });

  it.each([
    ["home notices", HomePage, "/api/v1/content?prefix=notice&locale=zh-CN&limit=100"],
    ["about", AboutPage, "/api/v1/content/page.about"],
    ["methodology", MethodologyPage, "/api/v1/content/page.methodology"],
    ["support FAQ", SupportPage, "/api/v1/content?prefix=faq&locale=zh-CN&limit=100"],
    ["privacy", PrivacyPage, "/api/v1/content/policy.privacy"],
    ["terms", TermsPage, "/api/v1/content/policy.terms"],
  ] as const)("requests the published CMS projection for %s", async (_name, Page, url) => {
    render(<Page />);

    await waitFor(() => expect(requestJsonMock).toHaveBeenCalledWith(url));
  });
});
