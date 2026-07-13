import type {
  CalibrationSnapshot,
  Claim,
  Concept,
  Label,
  MediaRecord,
} from "../../../shared/contracts.generated";

export interface MediaPage {
  items: MediaRecord[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ImportResult {
  media_hash: string;
  deduplicated: boolean;
  record: MediaRecord;
}

export interface InferResult {
  claims: Claim[];
  provider_id: string;
}

export interface PendingItem {
  claim: Claim;
  run_ref: string;
  media_hash: string;
}

export interface ReviewDecisionInput {
  claim_id: string;
  reviewer: string;
}

export interface RejectResult {
  event_id: string;
  to_status: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const getBaseUrl = async (): Promise<string> => window.bridge.getApiBaseUrl();

const parseResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new ApiError(detail || `HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as T;
};

export const listMedia = async (limit = 100, offset = 0): Promise<MediaPage> => {
  const baseUrl = await getBaseUrl();
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const response = await fetch(`${baseUrl}/media?${params.toString()}`);
  return parseResponse<MediaPage>(response);
};

export const importFile = async (file: File): Promise<ImportResult> => {
  const baseUrl = await getBaseUrl();
  const data = new FormData();
  data.append("file", file);
  const response = await fetch(`${baseUrl}/import`, {
    body: data,
    method: "POST",
  });
  return parseResponse<ImportResult>(response);
};

export const thumbnailUrl = async (mediaHash: string): Promise<string> => {
  const baseUrl = await getBaseUrl();
  return `${baseUrl}/media/${encodeURIComponent(mediaHash)}/thumbnail`;
};

export const infer = async (mediaHash: string, concepts: string[]): Promise<InferResult> => {
  const baseUrl = await getBaseUrl();
  const payload: { media_hash: string; concepts: Concept[] } = {
    concepts: concepts.map((raw_text) => ({ raw_text })),
    media_hash: mediaHash,
  };
  const response = await fetch(`${baseUrl}/infer`, {
    body: JSON.stringify(payload),
    headers: { "content-type": "application/json" },
    method: "POST",
  });
  return parseResponse<InferResult>(response);
};

export const reviewPending = async (): Promise<PendingItem[]> => {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/review/pending`);
  return parseResponse<PendingItem[]>(response);
};

export const approveClaim = async (body: ReviewDecisionInput): Promise<Label> => {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/review/approve`, {
    body: JSON.stringify(body),
    headers: { "content-type": "application/json" },
    method: "POST",
  });
  return parseResponse<Label>(response);
};

export const rejectClaim = async (body: ReviewDecisionInput): Promise<RejectResult> => {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/review/reject`, {
    body: JSON.stringify(body),
    headers: { "content-type": "application/json" },
    method: "POST",
  });
  return parseResponse<RejectResult>(response);
};

export const recalibrate = async (): Promise<CalibrationSnapshot | null> => {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/recalibrate`, { method: "POST" });
  if (response.status === 204) {
    return null;
  }
  return parseResponse<CalibrationSnapshot>(response);
};
