import type {
  BaziDeepStartRequest,
  CanwenStartRequest,
  ChartSimilarityStartRequest,
  EventArtStartRequest,
  FengshuiStartRequest,
  FiveElementsFactsStartRequest,
  FortuneStartRequest,
  HecanStartRequest,
  LiuyaoStartRequest,
  LumingNayinStartRequest,
  MeihuaStartRequest,
  PreviewStartRequest,
  QimenDeepStartRequest,
  RelationshipStartRequest,
  ReadingFactPanel,
  ReadingExportCreateResponse,
  ReadingExportFormat,
  ReadingListResponse,
  ReadingResultResponse,
  ReadingShareCreateResponse,
  ReadingShareResponse,
  ReadingVersionSummary,
  ReadingVerificationSummary,
  RecastRequest,
  RhythmStartRequest,
  SelectionStartRequest,
  TaiyiStartRequest,
  TimeCheckStartRequest,
  VerificationOutcome,
  WenshiStartRequest,
} from "./contracts";
import { getCsrfToken, jsonDelete, jsonPost, requestJson } from "./client";

const RAW_INPUT_FACT_REF = /\/input\/[^/]+$/;

function removePrivateFactRefs(
  items: unknown[],
  removedRefs: Set<string>,
): unknown[] {
  return items.map((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return item;
    const record = item as Record<string, unknown>;
    if (!Array.isArray(record.fact_refs)) return item;
    return {
      ...record,
      fact_refs: record.fact_refs.filter(
        (ref): ref is string => typeof ref === "string" && !removedRefs.has(ref),
      ),
    };
  });
}

/**
 * Defense in depth for the result UI: raw caller inputs are never retained in
 * React state. The browser only keeps derived, publicly presentable facts.
 */
function projectClientSafeFactPanel(panel: ReadingFactPanel): ReadingFactPanel {
  const removedRefs = new Set(
    panel.facts
      .filter((fact) => RAW_INPUT_FACT_REF.test(fact.ref))
      .map((fact) => fact.ref),
  );
  if (removedRefs.size === 0) return panel;

  return {
    ...panel,
    facts: panel.facts.filter((fact) => !removedRefs.has(fact.ref)),
    evidence: panel.evidence.map((item) => ({
      ...item,
      supports_fact_refs: item.supports_fact_refs.filter(
        (ref) => !removedRefs.has(ref),
      ),
    })),
    findings: removePrivateFactRefs(panel.findings, removedRefs),
    claim_scopes: removePrivateFactRefs(panel.claim_scopes, removedRefs),
  };
}

export async function listReadings(): Promise<ReadingListResponse> {
  await getCsrfToken();
  return requestJson<ReadingListResponse>("/api/v1/readings");
}

export async function startPreviewReading(
  body: PreviewStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/preview", body, {
    idempotencyKey,
  });
}

export async function startBaziDeepReading(
  body: BaziDeepStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/bazi-deep", body, {
    idempotencyKey,
  });
}

export async function startQimenDeepReading(
  body: QimenDeepStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/qimen-deep", body, {
    idempotencyKey,
  });
}

export async function startCanwenReading(
  body: CanwenStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/canwen", body, {
    idempotencyKey,
  });
}

export async function startHecanReading(
  body: HecanStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/hecan", body, {
    idempotencyKey,
  });
}

export async function startBaziRelationshipReading(
  body: RelationshipStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    "/api/v1/readings/bazi-relationship",
    body,
    { idempotencyKey },
  );
}

export async function startZiweiRelationshipReading(
  body: RelationshipStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    "/api/v1/readings/ziwei-relationship",
    body,
    { idempotencyKey },
  );
}

export async function startQizhengRelationshipReading(
  body: RelationshipStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    "/api/v1/readings/qizheng-relationship",
    body,
    { idempotencyKey },
  );
}

export async function startZiweiReading(
  body: PreviewStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/ziwei", body, {
    idempotencyKey,
  });
}

export async function startQizhengReading(
  body: PreviewStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/qizheng", body, {
    idempotencyKey,
  });
}

export async function startLumingNayinReading(
  body: LumingNayinStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/luming-nayin", body, {
    idempotencyKey,
  });
}

export async function startRhythmReading(
  body: RhythmStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/rhythm", body, {
    idempotencyKey,
  });
}

export async function startFiveElementsFactsReading(
  body: FiveElementsFactsStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    "/api/v1/readings/five-elements-facts",
    body,
    { idempotencyKey },
  );
}

export async function startChartSimilarityReading(
  body: ChartSimilarityStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    "/api/v1/readings/chart-similarity",
    body,
    { idempotencyKey },
  );
}

export async function startTimeCheckReading(
  body: TimeCheckStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    "/api/v1/readings/time-check",
    body,
    { idempotencyKey },
  );
}

export async function startTaiyiReading(
  body: TaiyiStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/taiyi", body, {
    idempotencyKey,
  });
}

export async function startSelectionReading(
  body: SelectionStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/selection", body, {
    idempotencyKey,
  });
}

export async function startFengshuiReading(
  body: FengshuiStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/fengshui", body, {
    idempotencyKey,
  });
}

export async function startTodayReading(
  body: FortuneStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/today", body, {
    idempotencyKey,
  });
}

export async function startWeekReading(
  body: FortuneStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/week", body, {
    idempotencyKey,
  });
}

export async function startLiuyaoReading(
  body: LiuyaoStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/liuyao", body, {
    idempotencyKey,
  });
}

export async function startWenshiReading(
  body: WenshiStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/wenshi", body, {
    idempotencyKey,
  });
}

export async function startQimenReading(
  body: EventArtStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/qimen", body, {
    idempotencyKey,
  });
}

export async function startDaliurenReading(
  body: EventArtStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/daliuren", body, {
    idempotencyKey,
  });
}

export async function startMeihuaReading(
  body: MeihuaStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/meihua", body, {
    idempotencyKey,
  });
}

export async function pollReading(
  readingVersionId: string,
): Promise<ReadingVersionSummary> {
  return requestJson<ReadingVersionSummary>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}`,
  );
}

export async function getReadingResult(
  readingVersionId: string,
): Promise<ReadingResultResponse> {
  const result = await requestJson<ReadingResultResponse>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/result`,
  );
  return {
    ...result,
    fact_panel: result.fact_panel
      ? projectClientSafeFactPanel(result.fact_panel)
      : null,
  };
}

export async function getReadingShare(token: string): Promise<ReadingShareResponse> {
  return requestJson<ReadingShareResponse>(
    `/api/v1/share/${encodeURIComponent(token)}`,
  );
}

export async function createReadingShare(
  readingVersionId: string,
  ttlSeconds = 86_400,
): Promise<ReadingShareCreateResponse> {
  return jsonPost<ReadingShareCreateResponse>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/share`,
    { ttl_seconds: ttlSeconds },
  );
}

export async function revokeReadingShare(
  readingVersionId: string,
  snapshotId: string,
): Promise<void> {
  await jsonDelete<void>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/share/${encodeURIComponent(snapshotId)}`,
  );
}

export async function createReadingExport(
  readingVersionId: string,
  format: ReadingExportFormat,
  ttlSeconds = 86_400,
): Promise<ReadingExportCreateResponse> {
  return jsonPost<ReadingExportCreateResponse>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/export`,
    { format, ttl_seconds: ttlSeconds },
  );
}

export async function submitReadingInput(
  readingVersionId: string,
  values: Record<string, unknown>,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/input`,
    { values },
  );
}

export async function verifyReading(
  readingVersionId: string,
  outcome: VerificationOutcome,
  note?: string,
): Promise<ReadingVerificationSummary> {
  const payload: { outcome: VerificationOutcome; note?: string } = { outcome };
  if (note?.trim()) {
    payload.note = note.trim();
  }
  return jsonPost<ReadingVerificationSummary>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/verification`,
    payload,
  );
}

export async function createFollowUp(
  readingVersionId: string,
  query: string,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/follow-up`,
    { query },
    { idempotencyKey },
  );
}

export async function createReadingRecast(
  sourceReadingVersionId: string,
  body: RecastRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    `/api/v1/readings/${encodeURIComponent(sourceReadingVersionId)}/recast`,
    body,
    { idempotencyKey },
  );
}
