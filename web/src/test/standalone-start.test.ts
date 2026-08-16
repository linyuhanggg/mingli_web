import { execFileSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";


describe("standalone production startup", () => {
  const script = resolve(process.cwd(), "scripts/start-standalone.mjs");
  const appName = "web";

  it("copies static and public assets beside the nested canonical server.js", () => {
    const fixture = mkdtempSync(join(tmpdir(), "mingli-web-start-"));

    try {
      mkdirSync(join(fixture, ".next", "standalone", appName), { recursive: true });
      mkdirSync(join(fixture, ".next", "static"), { recursive: true });
      mkdirSync(join(fixture, "public"), { recursive: true });
      writeFileSync(join(fixture, ".next", "standalone", appName, "server.js"), "");
      writeFileSync(join(fixture, ".next", "static", "app.css"), "body{}");
      writeFileSync(join(fixture, "public", "asset.txt"), "public");

      execFileSync(process.execPath, [script, "--prepare-only"], {
        cwd: fixture,
      });

      expect(
        existsSync(
          join(fixture, ".next", "standalone", appName, ".next", "static", "app.css"),
        ),
      ).toBe(true);
      expect(
        existsSync(join(fixture, ".next", "standalone", appName, "public", "asset.txt")),
      ).toBe(true);
      expect(
        existsSync(join(fixture, ".next", "standalone", appName, ".next", "cache")),
      ).toBe(true);
    } finally {
      rmSync(fixture, { recursive: true, force: true });
    }
  });

  it("rejects the retired flat root server.js and has no dual-path fallback", () => {
    const fixture = mkdtempSync(join(tmpdir(), "mingli-web-flat-"));
    const source = readFileSync(script, "utf8");

    expect(source).toContain('resolve(runtimeRoot, "server.js")');
    expect(source).toContain("APP_NAME");
    expect(source).not.toContain("existsSync(nested");
    expect(source).not.toContain("canonicalServer");

    try {
      mkdirSync(join(fixture, ".next", "standalone"), { recursive: true });
      mkdirSync(join(fixture, ".next", "static"), { recursive: true });
      writeFileSync(join(fixture, ".next", "standalone", "server.js"), "");
      writeFileSync(join(fixture, ".next", "static", "app.css"), "body{}");

      expect(() =>
        execFileSync(process.execPath, [script, "--prepare-only"], {
          cwd: fixture,
          stdio: ["ignore", "ignore", "pipe"],
        }),
      ).toThrow(/Standalone build missing/);
    } finally {
      rmSync(fixture, { recursive: true, force: true });
    }
  });
});
