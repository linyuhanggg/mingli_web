import { cpSync, existsSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";


export function prepareStandaloneAssets(root = process.cwd()) {
  const standaloneRoot = resolve(root, ".next", "standalone");
  const serverFile = resolve(standaloneRoot, "server.js");
  const staticSource = resolve(root, ".next", "static");
  const staticTarget = resolve(standaloneRoot, ".next", "static");
  const publicSource = resolve(root, "public");
  const publicTarget = resolve(standaloneRoot, "public");

  if (!existsSync(serverFile) || !existsSync(staticSource)) {
    throw new Error("Standalone build missing. Run `npm run build` first.");
  }

  rmSync(staticTarget, { recursive: true, force: true });
  cpSync(staticSource, staticTarget, { recursive: true });

  if (existsSync(publicSource)) {
    rmSync(publicTarget, { recursive: true, force: true });
    cpSync(publicSource, publicTarget, { recursive: true });
  }

  return { serverFile, standaloneRoot };
}

async function main() {
  const { serverFile, standaloneRoot } = prepareStandaloneAssets();

  if (process.argv.includes("--prepare-only")) {
    return;
  }

  process.chdir(standaloneRoot);
  await import(pathToFileURL(serverFile).href);
}

const invokedAsScript =
  process.argv[1] !== undefined &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedAsScript) {
  await main();
}
