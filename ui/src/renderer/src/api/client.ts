import type {
  AnnotationRevision,
  BBox,
  CalibrationSnapshot,
  Claim,
  Concept,
  ConceptDefinition,
  CoverageRecord,
  CoverageState,
  DatasetVersion,
  EvaluationFeedback,
  EvaluationReport,
  Label,
  MediaRecord,
  MediaAssignment,
  ModelArtifact,
  ModelPrediction,
  ReadinessReport,
  TaskRecord,
  TrainingRecipe,
  TrainingRun,
  TrainingRunEvent,
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

export interface TeachingState {
  task: TaskRecord;
  assignment: MediaAssignment;
  concepts: ConceptDefinition[];
  coverage: CoverageRecord[];
  annotations: AnnotationRevision[];
  teacher_claims: Claim[];
}

export interface TeachResult {
  run_id: string;
  claims: Claim[];
}

export interface FreezeDatasetResult {
  version: DatasetVersion;
  readiness: ReadinessReport;
}

export interface TrainingStatusResult {
  run: TrainingRun;
  latest_event: TrainingRunEvent;
  artifact: ModelArtifact | null;
  evaluation: EvaluationReport | null;
}

export interface ApplyResult {
  artifact_id: string;
  predictions: ModelPrediction[];
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

const jsonRequest = async <T>(path: string, method: string, body?: unknown): Promise<T> => {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}${path}`, {
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: body === undefined ? undefined : { "content-type": "application/json" },
    method,
  });
  return parseResponse<T>(response);
};

export const listTasks = async (): Promise<TaskRecord[]> => jsonRequest("/tasks", "GET");

export const createTask = async (name: string): Promise<TaskRecord> =>
  jsonRequest("/tasks", "POST", { name });

export const listConcepts = async (taskId: string): Promise<ConceptDefinition[]> =>
  jsonRequest(`/tasks/${encodeURIComponent(taskId)}/concepts`, "GET");

export const createConcept = async (
  taskId: string,
  displayName: string,
): Promise<ConceptDefinition> =>
  jsonRequest(`/tasks/${encodeURIComponent(taskId)}/concepts`, "POST", {
    display_name: displayName,
  });

export const assignMedia = async (
  taskId: string,
  mediaHash: string,
): Promise<MediaAssignment> =>
  jsonRequest(
    `/tasks/${encodeURIComponent(taskId)}/media/${encodeURIComponent(mediaHash)}`,
    "POST",
    {},
  );

export const teachingState = async (
  taskId: string,
  mediaHash: string,
): Promise<TeachingState> =>
  jsonRequest(
    `/tasks/${encodeURIComponent(taskId)}/media/${encodeURIComponent(mediaHash)}/teaching`,
    "GET",
  );

export const teach = async (
  taskId: string,
  mediaHash: string,
  conceptIds: string[],
): Promise<TeachResult> =>
  jsonRequest(`/tasks/${encodeURIComponent(taskId)}/teach`, "POST", {
    concept_ids: conceptIds,
    media_hash: mediaHash,
  });

export const addAnnotation = async (body: {
  task_id: string;
  media_hash: string;
  concept_id: string;
  bbox?: BBox;
  source_claim_ref?: string;
}): Promise<AnnotationRevision> => jsonRequest("/annotations", "POST", body);

export const editAnnotation = async (
  annotationId: string,
  conceptId: string,
  bbox: BBox,
): Promise<AnnotationRevision> =>
  jsonRequest(`/annotations/${encodeURIComponent(annotationId)}`, "PATCH", {
    bbox,
    concept_id: conceptId,
  });

export const deleteAnnotation = async (
  annotationId: string,
): Promise<AnnotationRevision> =>
  jsonRequest(`/annotations/${encodeURIComponent(annotationId)}`, "DELETE");

export const updateCoverage = async (body: {
  task_id: string;
  media_hash: string;
  concept_id: string;
  state: CoverageState;
}): Promise<CoverageRecord> => jsonRequest("/coverage", "PUT", body);

export const getReadiness = async (taskId: string): Promise<ReadinessReport> =>
  jsonRequest(`/tasks/${encodeURIComponent(taskId)}/readiness`, "GET");

export const listDatasets = async (taskId: string): Promise<DatasetVersion[]> =>
  jsonRequest(`/tasks/${encodeURIComponent(taskId)}/datasets`, "GET");

export const freezeDataset = async (taskId: string): Promise<FreezeDatasetResult> =>
  jsonRequest(`/tasks/${encodeURIComponent(taskId)}/datasets/freeze`, "POST", {});

export const startTraining = async (
  datasetVersionId: string,
  recipe?: TrainingRecipe,
): Promise<TrainingRun> =>
  jsonRequest("/training", "POST", {
    dataset_version_id: datasetVersionId,
    ...(recipe === undefined ? {} : { recipe }),
  });

export const listTrainingRuns = async (taskId: string): Promise<TrainingStatusResult[]> =>
  jsonRequest(`/tasks/${encodeURIComponent(taskId)}/training`, "GET");

export const cancelTraining = async (trainingRunId: string): Promise<TrainingStatusResult> =>
  jsonRequest(`/training/${encodeURIComponent(trainingRunId)}/cancel`, "POST", {});

export const listArtifacts = async (taskId: string): Promise<ModelArtifact[]> =>
  jsonRequest(`/tasks/${encodeURIComponent(taskId)}/artifacts`, "GET");

export const sendEvaluationFeedback = async (
  evaluationId: string,
  errorIndex: number,
): Promise<EvaluationFeedback> =>
  jsonRequest(
    `/evaluations/${encodeURIComponent(evaluationId)}/errors/${errorIndex}/feedback`,
    "POST",
    {},
  );

export const applyArtifact = async (artifactId: string, file: File): Promise<ApplyResult> => {
  const baseUrl = await getBaseUrl();
  const data = new FormData();
  data.append("file", file);
  const response = await fetch(`${baseUrl}/artifacts/${encodeURIComponent(artifactId)}/infer`, {
    body: data,
    method: "POST",
  });
  return parseResponse<ApplyResult>(response);
};
