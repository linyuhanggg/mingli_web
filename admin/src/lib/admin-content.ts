export type AdminContentState =
  | "draft"
  | "preview"
  | "scheduled"
  | "published"
  | "withdrawn"
  | "archived";

export type AdminContentIndexItem = {
  revision_id: string;
  content_key: string;
  locale: string;
  revision: number;
  state: AdminContentState;
  title: string | null;
  summary: string | null;
  topic: string | null;
  source_title: string | null;
  source_url: string | null;
  author_ref: string;
  publish_at: string | null;
  withdrawn_reason: string | null;
  created_at: string;
};

export type AdminContentIndexResponse = {
  revisions: readonly AdminContentIndexItem[];
};

export type AdminContentRevision = AdminContentIndexItem & {
  body: string;
};

export type AdminContentHistoryResponse = {
  revisions: readonly AdminContentRevision[];
};
