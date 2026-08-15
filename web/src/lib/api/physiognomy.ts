import type {
  PhysiognomyMediaResponse,
  PhysiognomyStartRequest,
  ReadingVersionSummary,
} from "./contracts";
import { ApiError, getCsrfToken, jsonDelete, jsonPost, requestJson } from "./client";

export async function uploadPhysiognomyMedia(
  file: File,
  mode: PhysiognomyMediaResponse["mode"],
  consent: boolean,
): Promise<PhysiognomyMediaResponse> {
  const execute = async () => {
    const csrf = await getCsrfToken();
    const form = new FormData();
    form.set("file", file, file.name);
    form.set("mode", mode);
    form.set("consent", String(consent));
    return requestJson<PhysiognomyMediaResponse>("/api/v1/physiognomy/media", {
      method: "POST",
      headers: { "X-CSRF-Token": csrf },
      body: form,
    });
  };

  try {
    return await execute();
  } catch (error) {
    if (
      !(error instanceof ApiError) ||
      error.status !== 403 ||
      error.message !== "CSRF validation failed"
    ) {
      throw error;
    }
    return execute();
  }
}

export async function deletePhysiognomyMedia(assetId: string): Promise<PhysiognomyMediaResponse> {
  return jsonDelete<PhysiognomyMediaResponse>(
    `/api/v1/physiognomy/media/${encodeURIComponent(assetId)}`,
  );
}

export async function startPhysiognomyReading(
  body: PhysiognomyStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/physiognomy", body, {
    idempotencyKey,
  });
}
