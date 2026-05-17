import type { ImportPreviewSummary, NormalizedMessage, UUID } from "@agent/shared";

import { API_BASE_URL, apiFetch, type BootstrapUserResponse } from "@/lib/api";

export type ImportPreview = ImportPreviewSummary & {
  normalized_messages: NormalizedMessage[];
};

export type ImportDetail = {
  import_job: {
    id: UUID;
    user_id: UUID;
    file_name: string;
    source_type: string;
    status: string;
    created_at: string;
    preview_payload?: Record<string, unknown>;
    normalized_summary: Record<string, unknown>;
  };
  normalized_messages: NormalizedMessage[];
};

export async function bootstrapUser() {
  return apiFetch<BootstrapUserResponse>("/users/bootstrap", {
    method: "POST"
  });
}

export async function listImports() {
  return apiFetch<ImportDetail[]>("/imports");
}

export async function previewImport(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/imports/preview`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return (await response.json()) as ImportPreview;
}

export async function commitImport(payload: {
  user_id: UUID;
  file_name: string;
  source_type: "txt" | "csv" | "json" | "xlsx";
  file_size: number;
  normalized_messages: NormalizedMessage[];
  preview?: Record<string, unknown>;
}) {
  return apiFetch<ImportDetail>("/imports/commit", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      preview: payload.preview ?? {
        total_messages: payload.normalized_messages.length
      }
    })
  });
}
