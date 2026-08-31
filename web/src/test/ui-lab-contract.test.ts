import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";
import { STATUS_STATES } from "@/components/ui/status";
import { VIEW_MODEL_VERSIONS } from "@/view-models/registry";

const EXPECTED_STATUS_STATES = [
  "loading",
  "empty",
  "ready",
  "locked",
  "need-input",
  "error",
  "processing",
  "success",
  "unavailable",
  "unauthorized",
] as const;

const EXPECTED_UI_LAB_STATES = [
  "pristine",
  "filled",
  "validation-error",
  "submitting",
  "loading",
  "camera-prompt",
  "camera-allowed",
  "camera-denied",
  "photo-selected",
  "photo-cropping",
  "photo-rotating",
  "photo-quality-failed",
  "photo-retake",
  "observation-failed",
  "observation-processing",
  "source-expiring",
  "archive-consent",
  "source-deleting",
  "source-deleted",
  "source-expired-result-ready",
  "empty",
  "ready",
  "free-summary",
  "locked",
  "need-login",
  "need-input",
  "queued",
  "preparing",
  "generating",
  "validating",
  "accepted",
  "delayed",
  "failed",
  "follow-up",
  "unauthorized",
  "forbidden",
  "unavailable",
  "maintenance",
  "payment-confirming",
  "payment-success",
  "payment-failed",
  "refund",
  "reversed",
  "invite-planned",
  "invite-active",
  "invite-paused",
  "invite-full",
  "invite-ended",
  "invite-invalid",
  "invite-self",
] as const;

const EXPECTED_ROUTE_PATTERNS = [
  "/",
  "/arts",
  "/daily",
  "/tools",
  "/tools/time-check",
  "/tools/chart-similarity",
  "/tools/rhythm",
  "/tools/five-elements",
  "/tools/dream",
  "/tools/name",
  "/library",
  "/library/[slug]",
  "/about",
  "/pricing",
  "/methodology",
  "/support",
  "/privacy",
  "/terms",
  "/bazi",
  "/_ui-lab/bazi-result",
  "/bazi/hepan",
  "/ziwei",
  "/ziwei/hepan",
  "/qizheng",
  "/qizheng/hepan",
  "/liuyao",
  "/qimen",
  "/daliuren",
  "/jianxiang",
  "/hecan",
  "/wenshi",
  "/canwen",
  "/workbench/[handle]",
  "/checkout/[orderId]",
  "/share/[shareId]",
  "/invite/[code]",
  "/auth/login",
  "/auth/register",
  "/auth/verify",
  "/auth/set-password",
  "/auth/recover",
  "/auth/consent",
  "/account",
  "/account/profiles",
  "/account/profiles/[profileId]",
  "/account/history",
  "/account/history/[rootId]",
  "/account/orders",
  "/account/entitlements",
  "/account/invitations",
  "/account/notifications",
  "/account/settings",
  "/account/settings/security",
  "/account/settings/preferences",
  "/account/settings/privacy-data",
  "/account/data-rights",
] as const;

describe("UI Lab boundary", () => {
  it("is not reachable from production output", () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/%5Fui-lab/page.tsx"), "utf8");
    expect(source).toContain('process.env.NODE_ENV === "production"');
    expect(source).toContain("notFound()");
  });

  it("renders the versioned ViewModel fixture registry", () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/%5Fui-lab/page.tsx"), "utf8");
    expect(source).toContain("UiLab");
    expect(source).not.toContain("VIEW_MODEL_FIXTURES");
    expect(source).not.toContain("@/view-models/registry");
  });

  it("owns its state contract, fixtures, and interactive surface", () => {
    const ownedFiles = [
      "src/lib/ui-lab-contract.ts",
      "src/fixtures/ui-lab/index.ts",
      "src/components/ui-lab/ui-lab.tsx",
    ];

    for (const file of ownedFiles) {
      expect(existsSync(resolve(process.cwd(), file)), `${file} should exist`).toBe(true);
    }
  });

  it("keeps the demo-data warning in the route source", () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/%5Fui-lab/page.tsx"), "utf8");
    expect(source).toContain("UI 演示数据");
  });

  it("publishes every detailed state from the DESIGN UI Lab contract", async () => {
    const contract = await import("@/lib/ui-lab-contract");
    expect(contract.UI_LAB_STATES).toEqual(EXPECTED_UI_LAB_STATES);
  });

  it("publishes the frozen viewport, role, and capability controls", async () => {
    const contract = await import("@/lib/ui-lab-contract");
    expect(contract.UI_LAB_VIEWPORTS).toEqual([360, 768, 1024, 1440]);
    expect(contract.UI_LAB_ROLES).toEqual(["guest", "member", "test-account"]);
    expect(contract.UI_LAB_CAPABILITIES.map((capability) => capability.id)).toEqual([
      "ui-prebuilt",
      "adapting",
      "internal-test",
      "public",
      "paused",
    ]);
  });

  it("registers every frozen Web route pattern from CHECKLIST 4.1–4.3", async () => {
    const fixtures = await import("@/fixtures/ui-lab");
    const entries = fixtures.UI_LAB_FIXTURES ?? [];
    expect(entries.map((fixture) => fixture.routePattern)).toEqual(EXPECTED_ROUTE_PATTERNS);
    expect(new Set(entries.map((fixture) => fixture.routePattern)).size).toBe(EXPECTED_ROUTE_PATTERNS.length);
    expect(new Set(entries.map((fixture) => fixture.category))).toEqual(
      new Set(["public", "product", "auth", "account"]),
    );
  });

  it("uses registered product ViewModel versions and labels UI-Lab-only schemas truthfully", async () => {
    const fixtures = await import("@/fixtures/ui-lab");
    const entries = fixtures.UI_LAB_FIXTURES ?? [];

    for (const fixture of entries) {
      expect(fixture.routePattern).toMatch(/^\//);
      expect(fixture.schemaVersion).toMatch(/\/v1$/);
      if (fixture.schemaSource === "view-model-registry") {
        expect(VIEW_MODEL_VERSIONS).toContain(fixture.schemaVersion);
      } else {
        expect(fixture.schemaSource).toBe("ui-lab-surface-schema");
        expect(VIEW_MODEL_VERSIONS).not.toContain(fixture.schemaVersion);
      }
    }
  });

  it("composes formal production surfaces instead of bespoke preview shells", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src/components/ui-lab/preview-shells.tsx"),
      "utf8",
    );
    for (const productionComponent of [
      "ProductInputForm",
      "WorkbenchShell",
      "ReadingShell",
      "AccountSurface",
      "AuthSurface",
      "CommerceSurface",
      "PublicContentSurface",
      "Status",
    ]) {
      expect(source).toContain(productionComponent);
    }
    for (const bespokeShell of [
      "TaskInputPreview",
      "WorkbenchPreview",
      "ReadingPreview",
      "AccountPreview",
      "CommercePreview",
    ]) {
      expect(source).not.toContain(bespokeShell);
    }
    expect(source).not.toContain("RelationshipTaskPage");
  });

  it("publishes the complete shared status state set", () => {
    expect(STATUS_STATES).toEqual(EXPECTED_STATUS_STATES);
  });
});
