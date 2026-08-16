export type AdminRuntimeRelease = {
  id: string;
  name: string;
  version: string;
  source_commit: string;
  protocol_version: string;
  production_ready: boolean;
  created_at: string;
};

export type AdminRuntimeReleasesResponse = {
  releases: readonly AdminRuntimeRelease[];
};
