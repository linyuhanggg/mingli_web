import { describe, expect, it } from "vitest";

import {
  buildLiveAdminCatalogViewModel,
  hydrateLiveProductCatalog,
  type AdminCatalogApiResponse,
} from "@/lib/admin-catalog";
import { resolveAdminRoute } from "@/lib/admin-route-catalog";

describe("admin catalog view model", () => {
  it("keeps normal routes empty until a real platform adapter supplies records", () => {
    const route = resolveAdminRoute("/users");
    expect(route).not.toBeNull();

    const model = buildLiveAdminCatalogViewModel(route!);

    expect(model.schema).toBe("admin-catalog/v1");
    expect(model.source).toBe("live");
    expect(model.records).toEqual([]);
    expect(model.state).toBe("unavailable");
    expect(model.notice).toMatch(/尚未接入/);
  });

  it("projects real catalog families and version details into the admin contract", () => {
    const familyRoute = resolveAdminRoute("/products");
    const versionRoute = resolveAdminRoute("/products/family-1/versions");
    expect(familyRoute).not.toBeNull();
    expect(versionRoute).not.toBeNull();

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
              status: "active",
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

    const familyModel = hydrateLiveProductCatalog(
      buildLiveAdminCatalogViewModel(familyRoute!),
      payload,
    );
    expect(familyModel.state).toBe("ready");
    expect(familyModel.records[0]?.primary).toBe("八字深度解读");
    expect(familyModel.records[0]?.cells.publishState).toBe("active");

    const versionModel = hydrateLiveProductCatalog(
      buildLiveAdminCatalogViewModel(versionRoute!, "/products/family-1/versions"),
      payload,
    );
    expect(versionModel.state).toBe("ready");
    expect(versionModel.records[0]?.primary).toBe("v1");
    expect(versionModel.records[0]?.details).toEqual(
      expect.arrayContaining([
        { label: "价格", value: "CNY 9900" },
        { label: "启用报价", value: "closed · bazi-deep-reading-v1" },
      ]),
    );
  });
});
