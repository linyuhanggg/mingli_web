export type AdminReadingJob = {
  id: string;
  reading_version_id: string;
  reading_root_id: string;
  reading_version: number;
  capability_id: string;
  reading_status: string;
  job_status: string;
  language: string;
  narrative_policy_version: string;
  max_attempts: number;
  available_at: string;
  lease_generation: number;
  created_at: string;
};

export type AdminReadingJobsResponse = {
  jobs: readonly AdminReadingJob[];
};
