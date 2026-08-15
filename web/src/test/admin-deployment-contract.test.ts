import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const repositoryRoot = resolve(process.cwd(), "..");

describe("Admin deployment contract", () => {
  it("publishes a standalone Admin image and local Compose service", () => {
    const dockerfilePath = resolve(repositoryRoot, "infra/docker/admin.Dockerfile");
    const composePath = resolve(repositoryRoot, "infra/compose.local.yml");

    expect(existsSync(dockerfilePath)).toBe(true);
    expect(existsSync(composePath)).toBe(true);

    const dockerfile = readFileSync(dockerfilePath, "utf8");
    const compose = readFileSync(composePath, "utf8");

    expect(dockerfile).toContain("COPY admin/package.json admin/package-lock.json ./");
    expect(dockerfile).toContain("COPY admin/ ./");
    expect(dockerfile).toContain("/srv/admin/.next/standalone/admin");
    expect(dockerfile).toContain('EXPOSE 3001');
    expect(compose).toMatch(/\n  admin:\n/);
    expect(compose).toContain("dockerfile: infra/docker/admin.Dockerfile");
    expect(compose).toContain("BACKEND_INTERNAL_URL: ${ADMIN_BACKEND_INTERNAL_URL:-http://api:8000}");
    expect(compose).toContain('"127.0.0.1:3001:3001"');
  });

  it("does not copy an untracked Admin public directory into the release image", () => {
    const dockerfilePath = resolve(repositoryRoot, "infra/docker/admin.Dockerfile");
    const dockerfile = readFileSync(dockerfilePath, "utf8");

    expect(dockerfile).not.toContain(
      "/srv/admin/public ./public",
    );
  });

  it("publishes a hardened loopback systemd unit and documents its install", () => {
    const unitPath = resolve(
      repositoryRoot,
      "infra/systemd/fateradar-test-admin.service",
    );
    const runbookPath = resolve(repositoryRoot, "infra/TEST_SERVER_RUNBOOK.md");

    expect(existsSync(unitPath)).toBe(true);
    const unit = readFileSync(unitPath, "utf8");
    const runbook = readFileSync(runbookPath, "utf8");

    expect(unit).toContain("WorkingDirectory=/opt/fateradar/current/admin/.next/standalone/admin");
    expect(unit).toContain("Environment=PORT=3001");
    expect(unit).toContain("Environment=BACKEND_INTERNAL_URL=http://127.0.0.1:8000");
    expect(unit).toContain("NoNewPrivileges=true");
    expect(unit).toContain("ProtectSystem=strict");
    expect(runbook).toContain("fateradar-test-admin.service");
    expect(runbook).toContain("127.0.0.1:3001");
  });
});
