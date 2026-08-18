import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const evidenceRoot = resolve(
  repoRoot,
  process.env.ROUTE_ACCEPTANCE_ROOT
    ?? "docs/releases/evidence/2026-08-19-route-acceptance",
);
const expectedViewports = [360, 768, 1024, 1440];
const failures = [];

function readJson(pathname, label) {
  if (!existsSync(pathname)) {
    failures.push(`${label}: evidence file missing`);
    return null;
  }
  try {
    return JSON.parse(readFileSync(pathname, "utf8"));
  } catch (error) {
    failures.push(`${label}: invalid JSON (${String(error)})`);
    return null;
  }
}

const normalManifests = [];
for (const app of ["web", "admin"]) {
  for (const viewport of expectedViewports) {
    const manifest = readJson(resolve(evidenceRoot, app, `${viewport}.json`), `${app}/${viewport}`);
    if (!manifest) continue;
    if (manifest.app !== app) failures.push(`${app}/${viewport}: app=${manifest.app}`);
    if (manifest.project !== String(viewport)) {
      failures.push(`${app}/${viewport}: project=${manifest.project}`);
    }
    if (!Array.isArray(manifest.routes)) failures.push(`${app}/${viewport}: routes missing`);
    for (const failure of manifest.failures ?? []) {
      failures.push(`${app}/${viewport}: ${failure}`);
    }
    normalManifests.push(manifest);
  }
}

const routeMeasurements = normalManifests.flatMap((manifest) =>
  (manifest.routes ?? []).map((route) => ({
    app: manifest.app,
    project: manifest.project,
    ...route,
  })),
);
const routeInventory = Object.fromEntries(
  ["web", "admin"].map((app) => [
    app,
    Array.from(
      new Set(
        routeMeasurements
          .filter((measurement) => measurement.app === app)
          .map((measurement) => measurement.requestedRoute),
      ),
    ).sort(),
  ]),
);

for (const app of ["web", "admin"]) {
  const routeCount = routeInventory[app].length;
  for (const viewport of expectedViewports) {
    const count = routeMeasurements.filter(
      (measurement) => measurement.app === app
        && measurement.viewport?.width === viewport,
    ).length;
    if (count !== routeCount) {
      failures.push(`${app}/${viewport}: measured ${count} routes, expected ${routeCount}`);
    }
  }
}

const normalStateCoverage = Object.entries(
  routeMeasurements.flatMap((measurement) => measurement.canonicalStates ?? []).reduce(
    (counts, state) => ({ ...counts, [state]: (counts[state] ?? 0) + 1 }),
    {},
  ),
).map(([state, count]) => ({ state, count }));

const fixtureStateManifests = expectedViewports
  .map((viewport) => readJson(
    resolve(evidenceRoot, "ui-lab-fixture-states", `${viewport}.json`),
    `ui-lab-fixture-states/${viewport}`,
  ))
  .filter(Boolean);
for (const manifest of fixtureStateManifests) {
  if (manifest.fixtureOnly !== true || manifest.countedAsNormalPass !== false) {
    failures.push(`ui-lab-fixture-states/${manifest.project}: fixture boundary missing`);
  }
  for (const failure of manifest.failures ?? []) {
    failures.push(`ui-lab-fixture-states/${manifest.project}: ${failure}`);
  }
  const workbench = manifest.workbenchLayout;
  if (!workbench) {
    failures.push(`ui-lab-fixture-states/${manifest.project}: workbench layout missing`);
  } else if (
    workbench.expectedTwoColumn
    && (!workbench.isTwoColumn || workbench.rightReadingPaneWidthPx < 360)
  ) {
    failures.push(
      `ui-lab-fixture-states/${manifest.project}: invalid workbench right pane ${workbench.rightReadingPaneWidthPx}px`,
    );
  }
}

const twoColumnWorkbenchLayouts = fixtureStateManifests
  .map((manifest) => manifest.workbenchLayout)
  .filter((layout) => layout?.isTwoColumn);

const runtimeEvidence = readJson(
  resolve(evidenceRoot, "runtime-bazi-owner-result", "report.json"),
  "runtime-bazi-owner-result",
);
if (runtimeEvidence) {
  if (runtimeEvidence.productDataBoundary !== "signed-runtime-release-owner-result") {
    failures.push("runtime-bazi-owner-result: not a signed Runtime owner result");
  }
  if (runtimeEvidence.ok !== true) failures.push("runtime-bazi-owner-result: ok is not true");
  for (const failure of runtimeEvidence.failures ?? []) {
    failures.push(`runtime-bazi-owner-result: ${failure}`);
  }
  const expectedRelease = process.env.EXPECTED_RELEASE_MANIFEST_SHA256;
  if (expectedRelease && runtimeEvidence.releaseManifestSha256 !== expectedRelease) {
    failures.push(
      `runtime-bazi-owner-result: release ${runtimeEvidence.releaseManifestSha256} != ${expectedRelease}`,
    );
  }
}

const report = {
  schema: "mingli.route-acceptance-report/v1",
  generatedAt: new Date().toISOString(),
  sourceCommit: normalManifests[0]?.gitCommit ?? null,
  status: failures.length === 0 ? "evidence-ready-user-acceptance-pending" : "failed",
  method: {
    browser: "Playwright + system Google Chrome",
    browserExecutable: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    normalRouteFixturePolicy: "fixtures-forbidden",
    uiLabPolicy: "fixture-only-not-counted-as-normal-pass",
    viewports: expectedViewports,
  },
  summary: {
    webRoutes: routeInventory.web.length,
    adminRoutes: routeInventory.admin.length,
    normalRouteViewMeasurements: routeMeasurements.length,
    normalRouteFailures: normalManifests.reduce(
      (count, manifest) => count + (manifest.failures?.length ?? 0),
      0,
    ),
    fixtureStateMeasurements: fixtureStateManifests.reduce(
      (count, manifest) => count + (manifest.states?.length ?? 0),
      0,
    ),
    minimumTwoColumnWorkbenchRightPanePx: twoColumnWorkbenchLayouts.length > 0
      ? Math.min(...twoColumnWorkbenchLayouts.map((layout) => layout.rightReadingPaneWidthPx))
      : null,
    runtimeOwnerResultViewports: runtimeEvidence?.results?.length ?? 0,
  },
  routeInventory,
  normalStateCoverage,
  fixtureStateEvidence: {
    route: "/_ui-lab",
    fixtureOnly: true,
    countedAsNormalPass: false,
    manifests: fixtureStateManifests,
  },
  workbenchLayoutEvidence: {
    fixtureOnly: true,
    countedAsNormalPass: false,
    productionComponents: ["WorkbenchShell", "ReadingShell"],
    layouts: fixtureStateManifests.map((manifest) => manifest.workbenchLayout),
  },
  runtimeEvidence: runtimeEvidence
    ? {
        productRoute: runtimeEvidence.productRoute,
        productDataBoundary: runtimeEvidence.productDataBoundary,
        releaseManifestSha256: runtimeEvidence.releaseManifestSha256,
        readingVersionIds: runtimeEvidence.readingVersionIds,
        report: "runtime-bazi-owner-result/report.json",
        failures: runtimeEvidence.failures,
      }
    : null,
  routeMeasurements,
  failures,
};

writeFileSync(resolve(evidenceRoot, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ status: report.status, summary: report.summary, failures }, null, 2));
if (failures.length > 0) process.exitCode = 1;
