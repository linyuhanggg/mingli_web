import {
  dynamic as accountDynamic,
  metadata as accountMetadata,
  revalidate as accountRevalidate,
} from "@/app/account/layout";
import {
  dynamic as appDynamic,
  metadata as appMetadata,
  revalidate as appRevalidate,
} from "@/app/app/layout";


describe("private route metadata", () => {
  it.each([
    ["app", appMetadata, appDynamic, appRevalidate],
    ["account", accountMetadata, accountDynamic, accountRevalidate],
  ])("marks %s as noindex and dynamic", (_, metadata, dynamic, revalidate) => {
    expect(metadata.robots).toMatchObject({ index: false, follow: false });
    expect(dynamic).toBe("force-dynamic");
    expect(revalidate).toBe(0);
  });
});
