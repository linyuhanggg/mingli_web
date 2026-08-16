import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { basename, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";


const APP_NAME = basename(resolve(fileURLToPath(import.meta.url), "..", ".."));

export function prepareStandaloneAssets(root = process.cwd()) {
  const standaloneRoot = resolve(root, ".next", "standalone");
  const runtimeRoot = resolve(standaloneRoot, APP_NAME);
  const serverFile = resolve(runtimeRoot, "server.js");
  const staticSource = resolve(root, ".next", "static");
  const staticTarget = resolve(runtimeRoot, ".next", "static");
  const cacheTarget = resolve(runtimeRoot, ".next", "cache");
  const publicSource = resolve(root, "public");
  const publicTarget = resolve(runtimeRoot, "public");

  if (!existsSync(serverFile) || !existsSync(staticSource)) {
    throw new Error("Standalone build missing. Run `npm run build` first.");
  }

  rmSync(staticTarget, { recursive: true, force: true });
  cpSync(staticSource, staticTarget, { recursive: true });

  if (existsSync(publicSource)) {
    rmSync(publicTarget, { recursive: true, force: true });
    cpSync(publicSource, publicTarget, { recursive: true });
  }

  mkdirSync(cacheTarget, { recursive: true });

  return { serverFile, standaloneRoot, runtimeRoot };
}

async function main() {
  const { serverFile, runtimeRoot } = prepareStandaloneAssets();

  if (process.argv.includes("--prepare-only")) {
    return;
  }

  process.chdir(runtimeRoot);
  await import(pathToFileURL(serverFile).href);
}

const invokedAsScript =
  process.argv[1] !== undefined &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedAsScript) {
  await main();
}
