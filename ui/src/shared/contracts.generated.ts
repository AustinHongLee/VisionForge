/* AUTO-GENERATED — 由 schema 生成，請勿手改 */

export type AnnotationId = string;
export type Type = "bbox";
export type X1 = number;
export type X2 = number;
export type Y1 = number;
export type Y2 = number;
export type ConceptId = string;
export type CreatedAt = string;
export type CreatedBy = string;
export type MediaHash = string;
export type ReplacesRevisionId = string | null;
export type RevisionId = string;
export type SchemaVersion = "1.0";
export type AnnotationSource = "manual" | "teacher_accepted" | "teacher_edited" | "imported";
export type SourceClaimRef = string | null;
export type Status = "active" | "retracted";
export type TaskId = string;
/**
 * @minItems 1
 */
export type Points = [MappingPoint, ...MappingPoint[]];
export type Calibrated = number;
export type Raw = number;
export type CalibrationId = string;
export type ConceptKey = string;
export type NSamples = number;
export type Reliability = "none" | "low" | "high";
export type ShrinkageWeight = number;
export type Threshold = number;
export type Classes = ClassCalibration[];
export type CreatedAt1 = string;
export type GlobalThreshold = number;
export type GoldenManifestRef = string;
export type Method = "shrinkage_eb_v1";
export type PrecisionTarget = number;
export type PriorStrength = number;
export type SchemaVersion1 = "1.0";
export type AuditionScore = number | null;
export type CapabilityOk = boolean;
export type EstimatedCostRef = string | null;
export type ProviderId = string;
export type ProviderVersion = string;
export type RejectedReason = string | null;
export type Assertion = "presence" | "absence";
export type ClaimId = string;
export type Actor = string;
export type Kind = "human" | "rule" | "model";
export type MappedAt = string;
export type RawText = string;
export type TaxonomyNodeId = string | null;
export type Calibrated1 = number | null;
export type CalibrationRef = string | null;
export type Raw1 = number;
export type Reliability1 = "none" | "low" | "high";
export type Geometry = BBox | Polygon | MaskRef | Keypoints | WholeImage | UnknownGeometry;
/**
 * @minItems 3
 */
export type Points1 = [Point, Point, Point, ...Point[]];
export type X = number;
export type Y = number;
export type Type1 = "polygon";
export type Format = "rle_coco";
export type MaskHash = string;
export type Type2 = "mask_ref";
/**
 * @minItems 1
 */
export type Points2 = [KeypointPoint, ...KeypointPoint[]];
export type Visible = boolean;
export type X3 = number;
export type Y3 = number;
export type SkeletonRef = string;
export type Type3 = "keypoints";
export type Type4 = "whole_image";
export type Type5 = string;
export type ProviderExtra = {
  [k: string]: unknown;
} | null;
export type ReviewedAt = string | null;
export type Reviewer = string | null;
export type ReviewStatus =
  "draft" | "queued_fast" | "queued_detail" | "queued_manual" | "approved" | "edited_approved" | "rejected";
export type ClaimId1 = string;
export type ConceptId1 = string;
export type TaskId1 = string;
export type Aliases = string[];
export type ConceptId2 = string;
export type CreatedAt2 = string;
export type DisplayName = string;
export type SchemaVersion2 = "1.0";
export type TaskId2 = string;
export type Id = string;
export type Kind1 = "provider" | "human";
export type Version = string | null;
export type At = string;
export type CostId = string;
export type EstimateRef = string | null;
/**
 * @minItems 1
 */
export type Measurements = [CostMeasurement, ...CostMeasurement[]];
export type Amount = number | string;
export type Unit = string;
export type Phase = "estimate" | "actual";
export type SchemaVersion3 = "1.0";
export type Id1 = string;
export type Kind2 =
  | "media"
  | "claim"
  | "run"
  | "label"
  | "dataset_version"
  | "golden_entry"
  | "batch"
  | "report"
  | "calibration"
  | "cost"
  | "decision"
  | "review_event"
  | "training_run"
  | "export_job"
  | "data_job";
export type ConceptId3 = string;
export type MediaHash1 = string;
export type Reviewer1 = string | null;
export type SchemaVersion4 = "1.0";
export type CoverageState = "unverified" | "verified_complete" | "verified_absent";
export type TaskId3 = string;
export type VerifiedAt = string | null;
export type CreatedAt3 = string;
export type LabelRefs = string[];
export type MediaHash2 = string;
export type Split = "train" | "val";
export type Entries = ManifestEntry[];
export type GateDecisionRef = string | null;
export type Note = string;
export type ParentRef = string | null;
export type Human = number;
export type Imported = number;
export type MachineAssisted = number;
export type SchemaVersion5 = "1.0";
export type VersionId = string;
export type VersionNumber = number;
export type ReasonCode = string;
export type Target = string;
export type At1 = string;
export type DecisionRef = string;
export type Detail = string;
export type OutcomeId = string;
export type ProducedRefs = InputRef[];
export type SchemaVersion6 = "1.0";
export type Status1 = "success" | "failure" | "cancelled" | "partial";
export type Actor1 = string;
export type At2 = string;
export type Candidates = CandidateProvider[];
export type DecisionId = string;
export type EvidenceRefs = InputRef[];
/**
 * @minItems 1
 */
export type Inputs = [InputRef, ...InputRef[]];
export type Kind3 =
  "invoke_provider" | "route_claim" | "escalate_human" | "cache_reuse" | "gate_verdict" | "human_override";
export type OverridesRef = string | null;
export type PolicyHash = string;
export type PolicyLabel = string;
export type SchemaVersion7 = "1.0";
export type AddedAt = string;
export type AddedBy = string;
export type EntryId = string;
export type LabelRef = string;
export type MediaHash3 = string;
export type RetiredReason = string | null;
export type SchemaVersion8 = "1.0";
export type Status2 = "active" | "retired";
export type Claims = Claim[];
export type CostRef = string;
export type CreatedAt4 = string;
export type DecisionRef1 = string;
export type DurationMs = number;
export type ParamsHash = string;
export type PromptRef = string | null;
export type ProviderId1 = string;
export type ProviderVersion1 = string;
export type RunId = string;
export type SchemaVersion9 = "1.0";
export type HeightPx = number;
export type MediaHash4 = string;
export type WidthPx = number;
export type Task = string;
export type Assertion1 = "presence" | "absence";
export type ClaimRef = string;
export type FinalGeometry = BBox | Polygon | MaskRef | Keypoints | WholeImage | UnknownGeometry;
export type LabelId = string;
export type MediaHash5 = string;
export type ReviewedAt1 = string;
export type Reviewer2 = string;
export type RunRef = string;
export type SchemaVersion10 = "1.0";
export type SourceStatus = "approved" | "edited_approved";
export type AssignedAt = string;
export type MediaHash6 = string;
export type SchemaVersion11 = "1.0";
export type SourceGroupId = string;
export type TaskId4 = string;
export type ByteSize = number;
export type ExifNormalized = boolean;
export type Format1 = "jpeg" | "png" | "webp" | "bmp" | "tiff";
export type HeightPx1 = number;
export type ImportedAt = string;
export type MediaHash7 = string;
export type SchemaVersion12 = "1.0";
export type Detail1 = string;
export type Kind4 = "file" | "folder" | "clipboard" | "video_frame" | "pdf_page" | "camera" | "screen" | "url";
export type WidthPx1 = number;
export type CostProfile = "free_local" | "local_compute" | "api_metered" | "api_flat";
export type Locality = "local" | "cloud";
/**
 * @minItems 1
 */
export type PromptableBy = [
  "text" | "box" | "point" | "example" | "none",
  ...("text" | "box" | "point" | "example" | "none")[]
];
export type ProviderId2 = string;
export type Reproducible = boolean;
export type Role = "teacher" | "student";
export type SchemaVersion13 = "1.0";
/**
 * @minItems 1
 */
export type Tasks = [
  "detect" | "segment" | "classify" | "describe" | "ocr" | "keypoints",
  ...("detect" | "segment" | "classify" | "describe" | "ocr" | "keypoints")[]
];
export type Trainable = boolean;
export type Version1 = string;
export type Actor2 = string;
export type At3 = string;
export type ClaimRef1 = string;
export type Context = "normal" | "blind_audit" | "honeypot";
export type DurationMs1 = number | null;
export type EventId = string;
export type ReviewStatus1 =
  "draft" | "queued_fast" | "queued_detail" | "queued_manual" | "approved" | "edited_approved" | "rejected";
export type LabelRef1 = string | null;
export type SchemaVersion14 = "1.0";
export type ReviewStatus2 =
  "draft" | "queued_fast" | "queued_detail" | "queued_manual" | "approved" | "edited_approved" | "rejected";
export type CreatedAt5 = string;
export type Kind5 = "detect";
export type Name = string;
export type SchemaVersion15 = "1.0";
export type TaskId5 = string;
export type CreatedAt6 = string;
export type NodeId = string;
export type RawText1 = string;
export type SchemaVersion16 = "1.0";

export interface VisionForgeContracts {
  [k: string]: unknown;
}
/**
 * 標註的不可變修訂；刪除是 retracted revision，不抹去舊資料。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "AnnotationRevision".
 */
export interface AnnotationRevision {
  annotation_id: AnnotationId;
  bbox: BBox | null;
  concept_id: ConceptId;
  created_at: CreatedAt;
  created_by: CreatedBy;
  media_hash: MediaHash;
  replaces_revision_id?: ReplacesRevisionId;
  revision_id: RevisionId;
  schema_version?: SchemaVersion;
  source: AnnotationSource;
  source_claim_ref?: SourceClaimRef;
  status?: Status;
  task_id: TaskId;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "BBox".
 */
export interface BBox {
  type?: Type;
  x1: X1;
  x2: X2;
  y1: Y1;
  y2: Y2;
}
/**
 * raw→calibrated 的單調階梯映射；points 依 raw 遞增、calibrated 非遞減。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "CalibrationMapping".
 */
export interface CalibrationMapping {
  points: Points;
}
/**
 * 等滲回歸斷點：raw 門檻 → 校準後信心（P(correct|raw) 的單調估計）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "MappingPoint".
 */
export interface MappingPoint {
  calibrated: Calibrated;
  raw: Raw;
}
/**
 * 一次校準的不可變快照；calibration_ref 指向它＝信賴度的可驗證背書。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "CalibrationSnapshot".
 */
export interface CalibrationSnapshot {
  calibration_id: CalibrationId;
  classes?: Classes;
  created_at: CreatedAt1;
  global_threshold: GlobalThreshold;
  golden_manifest_ref: GoldenManifestRef;
  method?: Method;
  precision_target: PrecisionTarget;
  prior_strength: PriorStrength;
  schema_version?: SchemaVersion1;
}
/**
 * 逐類校準結果。none 級不輸出映射、退回保守全域門檻（R2 9.2）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "ClassCalibration".
 */
export interface ClassCalibration {
  concept_key: ConceptKey;
  mapping?: CalibrationMapping | null;
  n_samples: NSamples;
  reliability: Reliability;
  shrinkage_weight: ShrinkageWeight;
  threshold: Threshold;
}
/**
 * 候選 Provider 的證據列（A6：沒有證據的選擇等於沒發生）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "CandidateProvider".
 */
export interface CandidateProvider {
  audition_score?: AuditionScore;
  capability_ok: CapabilityOk;
  estimated_cost_ref?: EstimatedCostRef;
  provider_id: ProviderId;
  provider_version: ProviderVersion;
  rejected_reason?: RejectedReason;
}
/**
 * 單一實例的陳述。Claim 是有出處的意見，不是事實（憲法 §3）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Claim".
 */
export interface Claim {
  assertion?: Assertion;
  claim_id: ClaimId;
  concept: Concept;
  confidence: Confidence;
  geometry: Geometry;
  provider_extra?: ProviderExtra;
  review?: Review;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Concept".
 */
export interface Concept {
  mapping_provenance?: ConceptMappingProvenance | null;
  raw_text: RawText;
  taxonomy_node_id?: TaxonomyNodeId;
}
/**
 * 「rusty bolt 算不算本專案的『鏽蝕』」——映射本身也是有出處的意見。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "ConceptMappingProvenance".
 */
export interface ConceptMappingProvenance {
  actor: Actor;
  kind: Kind;
  mapped_at: MappedAt;
}
/**
 * 分流邏輯只准讀 calibrated；reliability 為 none/low 時憲法規定一律人審。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Confidence".
 */
export interface Confidence {
  calibrated?: Calibrated1;
  calibration_ref?: CalibrationRef;
  raw: Raw1;
  reliability?: Reliability1;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Polygon".
 */
export interface Polygon {
  points: Points1;
  type?: Type1;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Point".
 */
export interface Point {
  x: X;
  y: Y;
}
/**
 * mask 本體不內嵌，走內容雜湊定址檔案（ADR-0003 裁決 #1：RLE/COCO）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "MaskRef".
 */
export interface MaskRef {
  format?: Format;
  mask_hash: MaskHash;
  type?: Type2;
}
/**
 * 骨架定義由任務模組擁有（ADR-0003 裁決 #3），此處只存登記名。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Keypoints".
 */
export interface Keypoints {
  points: Points2;
  skeleton_ref: SkeletonRef;
  type?: Type3;
}
export interface KeypointPoint {
  visible?: Visible;
  x: X3;
  y: Y3;
}
/**
 * 圖級陳述（無幾何）；absence 斷言的唯一合法幾何。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "WholeImage".
 */
export interface WholeImage {
  type?: Type4;
}
/**
 * 前向相容（F1）：未知幾何型別保留原文、標記不可解讀，不得丟棄。
 *
 * 注意：已知型別若格式錯誤，必須報錯而非落入本類——否則壞資料會偽裝成未來資料。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "UnknownGeometry".
 */
export interface UnknownGeometry {
  type: Type5;
  [k: string]: unknown;
}
export interface Review {
  reviewed_at?: ReviewedAt;
  reviewer?: Reviewer;
  status?: ReviewStatus;
}
/**
 * 把舊 Claim 的 provider 原話，可靠地綁回本次 Task/Concept。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "ClaimTeachingContext".
 */
export interface ClaimTeachingContext {
  claim_id: ClaimId1;
  concept_id: ConceptId1;
  task_id: TaskId1;
}
/**
 * 概念身分只在所屬 Task 內有意義，不再使用全專案隱式類別表。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "ConceptDefinition".
 */
export interface ConceptDefinition {
  aliases?: Aliases;
  concept_id: ConceptId2;
  created_at: CreatedAt2;
  display_name: DisplayName;
  schema_version?: SchemaVersion2;
  task_id: TaskId2;
}
/**
 * 誰產生了這筆消耗——Provider 或人（C5：人工有價）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "CostAgent".
 */
export interface CostAgent {
  id: Id;
  kind: Kind1;
  version?: Version;
}
/**
 * 一筆消耗分錄。estimate 與 actual 是兩筆獨立分錄，actual 以 estimate_ref
 * 回指配對——預測必可證偽（C6），對帳查詢由此成立。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "CostEntry".
 */
export interface CostEntry {
  agent: CostAgent;
  at: At;
  cost_id: CostId;
  estimate_ref?: EstimateRef;
  measurements: Measurements;
  phase: Phase;
  schema_version?: SchemaVersion3;
  subject: InputRef;
}
/**
 * 計量單位可插拔（F3）：unit 是登記名（usd／twd／tokens_in／seconds／gpu_seconds…）。
 *
 * 金額用 Decimal 並以字串序列化——錢進浮點數是十年後對不了帳的經典錯誤。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "CostMeasurement".
 */
export interface CostMeasurement {
  amount: Amount;
  unit: Unit;
}
/**
 * 異質參照：帳本之間互相指認的統一形式。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "InputRef".
 */
export interface InputRef {
  id: Id1;
  kind: Kind2;
}
/**
 * 一張圖對一個 Concept 的查核狀態；absence 的唯一權威來源。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "CoverageRecord".
 */
export interface CoverageRecord {
  concept_id: ConceptId3;
  media_hash: MediaHash1;
  reviewer?: Reviewer1;
  schema_version?: SchemaVersion4;
  state?: CoverageState;
  task_id: TaskId3;
  verified_at?: VerifiedAt;
}
/**
 * 一個 Dataset 版本 = 一份清單，不是一份拷貝。回滾 = 以任一舊版為 parent
 * 開新版；歷史版本永不修改、永不刪除（D5）。黃金集項目不得出現在此（D8）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "DatasetVersionManifest".
 */
export interface DatasetVersionManifest {
  created_at: CreatedAt3;
  entries: Entries;
  gate_decision_ref?: GateDecisionRef;
  note?: Note;
  parent_ref?: ParentRef;
  provenance: ProvenanceSummary;
  schema_version?: SchemaVersion5;
  version_id: VersionId;
  version_number: VersionNumber;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "ManifestEntry".
 */
export interface ManifestEntry {
  label_refs?: LabelRefs;
  media_hash: MediaHash2;
  split: Split;
}
/**
 * 血統成分表（防線二）：本版資料的出身統計快照。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "ProvenanceSummary".
 */
export interface ProvenanceSummary {
  human: Human;
  imported: Imported;
  machine_assisted: MachineAssisted;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "DecisionChoice".
 */
export interface DecisionChoice {
  reason_code: ReasonCode;
  target: Target;
}
/**
 * 決策的實際結果——獨立追加記錄（append-only：結果不回寫原決策）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "DecisionOutcome".
 */
export interface DecisionOutcome {
  at: At1;
  decision_ref: DecisionRef;
  detail?: Detail;
  outcome_id: OutcomeId;
  produced_refs?: ProducedRefs;
  schema_version?: SchemaVersion6;
  status: Status1;
}
/**
 * Orchestrator 的不可變決策記錄。五不變量（憲法 §4.4）：
 * 源自政策、附證據、經計量、可重放、可被人覆寫——前四者由本結構承載，
 * 第五者由 kind=human_override 的新記錄實現（不修改原記錄）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "DecisionRecord".
 */
export interface DecisionRecord {
  actor?: Actor1;
  at: At2;
  candidates?: Candidates;
  choice: DecisionChoice;
  decision_id: DecisionId;
  evidence_refs?: EvidenceRefs;
  inputs: Inputs;
  kind: Kind3;
  overrides_ref?: OverridesRef;
  policy: PolicyRef;
  schema_version?: SchemaVersion7;
}
/**
 * 生效政策的快照參照——重放時必須能指認當時的政策（D3）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "PolicyRef".
 */
export interface PolicyRef {
  policy_hash: PolicyHash;
  policy_label: PolicyLabel;
}
/**
 * 黃金集登記：只增與除役，永不刪除；且永不進入任何訓練 manifest（D8）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "GoldenSetEntry".
 */
export interface GoldenSetEntry {
  added_at: AddedAt;
  added_by: AddedBy;
  entry_id: EntryId;
  label_ref: LabelRef;
  media_hash: MediaHash3;
  retired_reason?: RetiredReason;
  schema_version?: SchemaVersion8;
  status?: Status2;
}
/**
 * 一次 Provider 調用的批次紀錄。出處與成本記在 Run，審核以 Claim 為單位。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "InferenceRun".
 */
export interface InferenceRun {
  claims?: Claims;
  cost_ref: CostRef;
  created_at: CreatedAt4;
  decision_ref: DecisionRef1;
  duration_ms: DurationMs;
  producer: Producer;
  run_id: RunId;
  schema_version?: SchemaVersion9;
  subject: MediaSubject;
  task: Task;
}
/**
 * PR6：版本即身分。提示式 Provider 的 prompt_ref 必填由 adapter 層強制。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Producer".
 */
export interface Producer {
  params_hash: ParamsHash;
  prompt_ref?: PromptRef;
  provider_id: ProviderId1;
  provider_version: ProviderVersion1;
}
/**
 * 像素尺寸是 normalized 座標的換算基準——綁在 Run 上，杜絕座標系歧義。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "MediaSubject".
 */
export interface MediaSubject {
  height_px: HeightPx;
  media_hash: MediaHash4;
  width_px: WidthPx;
}
/**
 * 不可變記錄；唯一誕生途徑是審核狀態機（服務層強制，本類記載其產物）。
 *
 * 設計理由（ADR-0003）：Label 與 Claim 分離儲存，Claim 永遠保存 Provider 原始輸出，
 * 兩者對照即可量測 Provider 真實錯誤率——這是盲審與防線五的量測基礎。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Label".
 */
export interface Label {
  assertion: Assertion1;
  claim_ref: ClaimRef;
  final_concept: Concept;
  final_geometry: FinalGeometry;
  label_id: LabelId;
  media_hash: MediaHash5;
  reviewed_at: ReviewedAt1;
  reviewer: Reviewer2;
  run_ref: RunRef;
  schema_version?: SchemaVersion10;
  source_status: SourceStatus;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "MediaAssignment".
 */
export interface MediaAssignment {
  assigned_at: AssignedAt;
  media_hash: MediaHash6;
  schema_version?: SchemaVersion11;
  source_group_id: SourceGroupId;
  task_id: TaskId4;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "MediaRecord".
 */
export interface MediaRecord {
  byte_size: ByteSize;
  exif_normalized: ExifNormalized;
  format: Format1;
  height_px: HeightPx1;
  imported_at: ImportedAt;
  media_hash: MediaHash7;
  schema_version?: SchemaVersion12;
  source: MediaSource;
  width_px: WidthPx1;
}
/**
 * 來源留痕：血統從匯入那一刻開始。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "MediaSource".
 */
export interface MediaSource {
  detail?: Detail1;
  kind: Kind4;
}
/**
 * Provider 機器可讀的能力自我聲明；路由與 UI 組裝的依據。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "ProviderCapability".
 */
export interface ProviderCapability {
  cost_profile: CostProfile;
  locality: Locality;
  promptable_by: PromptableBy;
  provider_id: ProviderId2;
  reproducible: Reproducible;
  role: Role;
  schema_version?: SchemaVersion13;
  tasks: Tasks;
  trainable: Trainable;
  version: Version1;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "Review".
 */
export interface Review1 {
  reviewed_at?: ReviewedAt;
  reviewer?: Reviewer;
  status?: ReviewStatus;
}
/**
 * 一次人為審核動作。Label 記結果，ReviewEvent 記行為——含否決與盲審。
 *
 * context=blind_audit／honeypot 是防線五的量測資料：盲審比對估計漏網錯誤率，
 * 蜜罐量測審核者當下狀態（R1 §9.3）。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "ReviewEvent".
 */
export interface ReviewEvent {
  actor: Actor2;
  at: At3;
  claim_ref: ClaimRef1;
  context?: Context;
  duration_ms?: DurationMs1;
  event_id: EventId;
  from_status: ReviewStatus1;
  label_ref?: LabelRef1;
  schema_version?: SchemaVersion14;
  to_status: ReviewStatus2;
}
/**
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "TaskRecord".
 */
export interface TaskRecord {
  created_at: CreatedAt5;
  kind?: Kind5;
  name: Name;
  schema_version?: SchemaVersion15;
  task_id: TaskId5;
}
/**
 * 專案 Taxonomy 的一個節點；概念的權威身分。
 *
 * This interface was referenced by `VisionForgeContracts`'s JSON-Schema
 * via the `definition` "TaxonomyNode".
 */
export interface TaxonomyNode {
  created_at: CreatedAt6;
  node_id: NodeId;
  raw_text: RawText1;
  schema_version?: SchemaVersion16;
}
