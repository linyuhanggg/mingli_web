export type AdminCapability = {
  capability_id: string;
  label: string;
  release_state: "PUBLIC" | "INTERNAL_TEST";
  audience: "P0 产品" | "内部 Provider";
  product_actions: readonly string[];
};

export type AdminCapabilitiesResponse = {
  environment: "local" | "test" | "staging" | "production";
  runtime_adapter: "fake" | "one-shot";
  runtime_health: "unverified";
  production_ready: boolean;
  capabilities: readonly AdminCapability[];
};
