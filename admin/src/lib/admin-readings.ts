export type AdminReading = {
  reading_version_id: string;
  reading_root_id: string;
  capability_id: string;
  version: number;
  status: string;
  dimension_count: number;
  created_at: string;
};

export type AdminReadingsResponse = {
  readings: readonly AdminReading[];
};

export type AdminReadingDetail = AdminReading & {
  job_count: number;
  verification_event_count: number;
  document_available: boolean;
};
