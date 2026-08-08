import { execFileSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";


describe("standalone production startup", () => {
  it("copies static and public assets beside the standalone server", () => {
    const fixture = mkdtempSync(join(tmpdir(), "mingli-web-start-"));
    const script = resolve(process.cwd(), "scripts/start-standalone.mjs");

    try {
      mkdirSync(join(fixture, ".next", "standalone"), { recursive: true });
      mkdirSync(join(fixture, ".next", "static"), { recursive: true });
      mkdirSync(join(fixture, "public"), { recursive: true });
      writeFileSync(join(fixture, ".next", "standalone", "server.js"), "");
      writeFileSync(join(fixture, ".next", "static", "app.css"), "body{}");
      writeFileSync(join(fixture, "public", "asset.txt"), "public");

      execFileSync(process.execPath, [script, "--prepare-only"], {
        cwd: fixture,
      });

      expect(
        existsSync(
          join(fixture, ".next", "standalone", ".next", "static", "app.css"),
        ),
      ).toBe(true);
      expect(
        existsSync(join(fixture, ".next", "standalone", "public", "asset.txt")),
      ).toBe(true);
    } finally {
      rmSync(fixture, { recursive: true, force: true });
    }
  });
});
