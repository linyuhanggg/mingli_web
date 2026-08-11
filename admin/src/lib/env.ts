export type DeployEnv = "local" | "test" | "staging" | "production";

export function getDeployEnv(): DeployEnv {
  const raw = (process.env.NEXT_PUBLIC_MINGLI_ENV ?? "local").toLowerCase();
  if (raw === "test" || raw === "staging" || raw === "production" || raw === "local") {
    return raw;
  }
  return "local";
}
