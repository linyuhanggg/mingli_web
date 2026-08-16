import {
  dynamic as accountDynamic,
  fetchCache as accountFetchCache,
  metadata as accountMetadata,
  revalidate as accountRevalidate,
} from "@/app/account/layout";
import {
  dynamic as appDynamic,
  fetchCache as appFetchCache,
  metadata as appMetadata,
  revalidate as appRevalidate,
} from "@/app/app/layout";


describe("private route metadata", () => {
  it.each([
    ["app", appMetadata, appDynamic, appRevalidate, appFetchCache],
    ["account", accountMetadata, accountDynamic, accountRevalidate, accountFetchCache],
  ])("marks %s as noindex and dynamic", (_, metadata, dynamic, revalidate, fetchCache) => {
    expect(metadata.robots).toMatchObject({ index: false, follow: false, nocache: true });
    expect(dynamic).toBe("force-dynamic");
    expect(revalidate).toBe(0);
    expect(fetchCache).toBe("force-no-store");
  });
});
