import { ApiError } from "@/lib/api/client";

export type ProfileNameConflictOption = "overwrite" | "save_as" | "cancel";

export type ProfileNameConflict = {
  existingProfileId?: string;
  existingProfileVersionId?: string;
  suggestedSaveAsName: string;
  options: ProfileNameConflictOption[];
};

export function isProfileNameConflict(error: unknown): error is ApiError {
  return (
    error instanceof ApiError &&
    error.status === 409 &&
    error.code === "profile_name_conflict"
  );
}

export function readProfileNameConflict(error: ApiError): ProfileNameConflict {
  const options = (error.options ?? ["overwrite", "save_as", "cancel"]).filter(
    (item): item is ProfileNameConflictOption =>
      item === "overwrite" || item === "save_as" || item === "cancel",
  );
  return {
    existingProfileId: error.existingProfileId,
    existingProfileVersionId: error.existingProfileVersionId,
    suggestedSaveAsName: error.suggestedSaveAsName || "档案 (2)",
    options: options.length ? options : ["overwrite", "save_as", "cancel"],
  };
}
