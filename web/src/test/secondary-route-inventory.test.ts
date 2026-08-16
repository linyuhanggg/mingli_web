import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const requiredRoutes = [
  "/arts",
  "/bazi/hepan",
  "/ziwei/hepan",
  "/qizheng/hepan",
  "/tools/[tool]",
  "/library/[slug]",
  "/workbench/[handle]",
  "/checkout/[orderId]",
  "/auth/login",
  "/auth/register",
  "/auth/verify",
  "/auth/set-password",
  "/auth/consent",
  "/auth/recover",
  "/account/profiles",
  "/account/profiles/[profileId]",
  "/account/history",
  "/account/history/[rootId]",
  "/account/orders",
  "/account/entitlements",
  "/account/invites",
  "/account/invitations",
  "/account/notifications",
  "/account/settings",
  "/account/settings/security",
  "/account/settings/preferences",
  "/account/settings/privacy-data",
  "/account/data-rights",
  "/checkout",
  "/share/[shareId]",
  "/invite/[code]",
] as const;

const secondaryFamilyRoutes = {
  publicContent: [
    "/tools",
    "/tools/[tool]",
    "/library",
    "/library/[slug]",
    "/daily",
  ],
  auth: [
    "/auth/login",
    "/auth/register",
    "/auth/verify",
    "/auth/set-password",
    "/auth/consent",
    "/auth/recover",
  ],
  account: [
    "/account/profiles",
    "/account/profiles/[profileId]",
    "/account/history",
    "/account/history/[rootId]",
    "/account/orders",
    "/account/entitlements",
    "/account/invites",
    "/account/invitations",
    "/account/notifications",
    "/account/settings",
    "/account/settings/security",
    "/account/settings/preferences",
    "/account/settings/privacy-data",
    "/account/data-rights",
  ],
  commerce: [
    "/checkout",
    "/checkout/[orderId]",
    "/share/[shareId]",
    "/invite/[code]",
  ],
} as const;

const authRouteMarkers = {
  "/auth/login": "PasswordLoginForm",
  "/auth/register": "RegistrationForm",
  "/auth/verify": "OtpForm",
  "/auth/set-password": "PasswordSetForm",
  "/auth/consent": "ConsentForm",
  "/auth/recover": "PasswordRecoveryForm",
} as const;

const routeMarkers: Record<string, string> = {
  ...authRouteMarkers,
  "/account/profiles": "AccountProfilesSurface",
  "/account/profiles/[profileId]": "AccountProfileDetailSurface",
  "/account/history": "AccountHistorySurface",
  "/account/history/[rootId]": "AccountHistorySurface",
  "/account/orders": "AccountCommerceSurface",
  "/account/entitlements": "AccountCommerceSurface",
  "/account/invites": "AccountReferralsSurface",
  "/account/invitations": "AccountReferralsSurface",
  "/account/notifications": "AccountNotificationsSurface",
  "/account/settings": "AccountSettingsSurface",
  "/account/settings/security": "AccountSecuritySurface",
  "/share/[shareId]": "SharedReadingSurface",
  "/invite/[code]": "InviteSurface",
  "/account/settings/privacy-data": "AccountDataRightsSurface",
  "/account/data-rights": "AccountDataRightsSurface",
  "/account/settings/preferences": "NotificationPreferencesForm",
};

describe("secondary product route inventory", () => {
  it("keeps every frozen secondary route present without the retired brand", () => {
    for (const route of requiredRoutes) {
      const file = resolve(process.cwd(), `src/app${route}/page.tsx`);
      expect(existsSync(file), `missing route page: ${route}`).toBe(true);
      const source = readFileSync(file, "utf8");
      expect(source).not.toContain("FateRadar");
    }
  });

  it.each(Object.entries(secondaryFamilyRoutes))(
    "uses the explicit %s surface family instead of PrebuiltPage",
    (family, routes) => {
      const expectedSurface = `${family[0]?.toUpperCase()}${family.slice(1)}Surface`;

      for (const route of routes) {
        const file = resolve(process.cwd(), `src/app${route}/page.tsx`);
        const source = readFileSync(file, "utf8");

        const marker = route in routeMarkers
          ? routeMarkers[route]
          : expectedSurface;
        expect(source, route).toContain(marker);
        expect(source, route).not.toContain("PrebuiltPage");
      }
    },
  );
});
