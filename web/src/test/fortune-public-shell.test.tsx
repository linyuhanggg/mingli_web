import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import FortunePage from "@/app/fortune/page";
import { NATAL_PRODUCTS, PRODUCT_CATALOG } from "@/products/catalog";

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/fortune",
  useSearchParams: () => new URLSearchParams(),
}));

const { PROFILE } = vi.hoisted(() => ({
  PROFILE: {
    profile_id: "11111111-1111-4111-8111-111111111111",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
    version: 1,
    created_at: "2026-08-09T12:00:00Z",
  },
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  listProfiles: vi.fn().mockResolvedValue({ profiles: [PROFILE] }),
}));

afterEach(cleanup);

describe("/fortune public shell", () => {
  it("uses the accepted public-shell line, Chinese copy, and profile select", async () => {
    render(<FortunePage />);

    const heading = screen.getByRole("heading", { level: 1, name: "今日与近七日" });
    const line = heading.closest("header");
    expect(heading).toBeVisible();
    expect(line?.textContent).toContain("返回");
    expect(line?.querySelector("a")).toHaveAttribute("href", "/arts");
    expect(line?.textContent).toContain(
      "选一份已确认的出生档案，查看今天或近七日的事业与工作节奏。",
    );

    const select = await screen.findByLabelText("档案版本");
    expect(select).toBeVisible();
    expect(screen.getByRole("option", { name: "请选择档案" })).toBeVisible();
    expect(screen.getByRole("button", { name: "开始今日解读" })).toBeVisible();
    expect(screen.getByRole("button", { name: "开始近七日解读" })).toBeVisible();

    const user = userEvent.setup();
    await user.selectOptions(select, PROFILE.profile_version_id);
    expect(select).toHaveValue(PROFILE.profile_version_id);

    expect(screen.queryByText(/This page could not be found/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/404/)).not.toBeInTheDocument();
  });

  it("does not add fortune to the product map", () => {
    expect(Object.keys(PRODUCT_CATALOG)).not.toContain("fortune");
    expect(NATAL_PRODUCTS.map((product) => product.id)).toEqual(["bazi", "ziwei", "qizheng"]);

    const page = readFileSync(resolve(process.cwd(), "src/app/fortune/page.tsx"), "utf8");
    const catalog = readFileSync(resolve(process.cwd(), "src/products/catalog.ts"), "utf8");
    expect(page).not.toMatch(/§10|§6\.2|DESIGN/);
    expect(catalog).not.toMatch(/id:\s*"fortune"/);
  });
});
