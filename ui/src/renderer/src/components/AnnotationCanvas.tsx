import { useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type {
  AnnotationRevision,
  BBox,
  Claim,
  ConceptDefinition,
  MediaRecord,
} from "../../../shared/contracts.generated";

type DragState =
  | { kind: "draw"; startX: number; startY: number; current: BBox }
  | {
      kind: "move" | "resize";
      annotation: AnnotationRevision;
      startX: number;
      startY: number;
      original: BBox;
      current: BBox;
    };

interface AnnotationCanvasProps {
  annotations: AnnotationRevision[];
  concepts: ConceptDefinition[];
  imageUrl: string;
  media: MediaRecord;
  teacherClaims: Claim[];
  busy: boolean;
  onAdd(conceptId: string, bbox: BBox): void;
  onDelete(annotationId: string): void;
  onEdit(annotationId: string, conceptId: string, bbox: BBox): void;
}

const clamp = (value: number): number => Math.max(0, Math.min(1, value));

const claimBBox = (claim: Claim): BBox | null => {
  const geometry = claim.geometry;
  return geometry.type === "bbox" && "x1" in geometry ? (geometry as BBox) : null;
};

const styleFor = (bbox: BBox): React.CSSProperties => ({
  height: `${(bbox.y2 - bbox.y1) * 100}%`,
  left: `${bbox.x1 * 100}%`,
  top: `${bbox.y1 * 100}%`,
  width: `${(bbox.x2 - bbox.x1) * 100}%`,
});

const AnnotationCanvas = ({
  annotations,
  busy,
  concepts,
  imageUrl,
  media,
  onAdd,
  onDelete,
  onEdit,
  teacherClaims,
}: AnnotationCanvasProps): React.JSX.Element => {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [drawing, setDrawing] = useState(false);
  const [drag, setDrag] = useState<DragState | null>(null);
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(null);
  const [selectedConceptId, setSelectedConceptId] = useState(concepts[0]?.concept_id ?? "");
  const conceptNames = useMemo(
    () => new Map(concepts.map((concept) => [concept.concept_id, concept.display_name])),
    [concepts],
  );
  const selected = annotations.find(
    (annotation) => annotation.annotation_id === selectedAnnotationId,
  );

  const point = (event: ReactPointerEvent): { x: number; y: number } => {
    const rect = overlayRef.current?.getBoundingClientRect();
    if (rect === undefined || rect.width === 0 || rect.height === 0) {
      return { x: 0, y: 0 };
    }
    return {
      x: clamp((event.clientX - rect.left) / rect.width),
      y: clamp((event.clientY - rect.top) / rect.height),
    };
  };

  const startDrawing = (event: ReactPointerEvent<HTMLDivElement>): void => {
    if (!drawing || busy || event.target !== event.currentTarget || selectedConceptId === "") {
      return;
    }
    const start = point(event);
    event.currentTarget.setPointerCapture(event.pointerId);
    setDrag({
      current: { type: "bbox", x1: start.x, x2: start.x, y1: start.y, y2: start.y },
      kind: "draw",
      startX: start.x,
      startY: start.y,
    });
  };

  const startExisting = (
    event: ReactPointerEvent,
    annotation: AnnotationRevision,
    kind: "move" | "resize",
  ): void => {
    if (busy || annotation.bbox === null) {
      return;
    }
    event.stopPropagation();
    const start = point(event);
    overlayRef.current?.setPointerCapture(event.pointerId);
    setSelectedAnnotationId(annotation.annotation_id);
    setSelectedConceptId(annotation.concept_id);
    setDrag({
      annotation,
      current: annotation.bbox,
      kind,
      original: annotation.bbox,
      startX: start.x,
      startY: start.y,
    });
  };

  const movePointer = (event: ReactPointerEvent<HTMLDivElement>): void => {
    if (drag === null) {
      return;
    }
    const current = point(event);
    if (drag.kind === "draw") {
      setDrag({
        ...drag,
        current: {
          type: "bbox",
          x1: Math.min(drag.startX, current.x),
          x2: Math.max(drag.startX, current.x),
          y1: Math.min(drag.startY, current.y),
          y2: Math.max(drag.startY, current.y),
        },
      });
      return;
    }
    const dx = current.x - drag.startX;
    const dy = current.y - drag.startY;
    if (drag.kind === "move") {
      const width = drag.original.x2 - drag.original.x1;
      const height = drag.original.y2 - drag.original.y1;
      const x1 = clamp(Math.min(1 - width, drag.original.x1 + dx));
      const y1 = clamp(Math.min(1 - height, drag.original.y1 + dy));
      setDrag({
        ...drag,
        current: { type: "bbox", x1, x2: x1 + width, y1, y2: y1 + height },
      });
      return;
    }
    setDrag({
      ...drag,
      current: {
        type: "bbox",
        x1: drag.original.x1,
        x2: Math.max(drag.original.x1 + 0.005, clamp(drag.original.x2 + dx)),
        y1: drag.original.y1,
        y2: Math.max(drag.original.y1 + 0.005, clamp(drag.original.y2 + dy)),
      },
    });
  };

  const finishPointer = (event: ReactPointerEvent<HTMLDivElement>): void => {
    if (drag === null) {
      return;
    }
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    const finished = drag;
    setDrag(null);
    if (finished.current.x2 - finished.current.x1 < 0.005) {
      return;
    }
    if (finished.current.y2 - finished.current.y1 < 0.005) {
      return;
    }
    if (finished.kind === "draw") {
      onAdd(selectedConceptId, finished.current);
      setDrawing(false);
      return;
    }
    onEdit(finished.annotation.annotation_id, finished.annotation.concept_id, finished.current);
  };

  return (
    <div className="annotation-canvas">
      <div className="annotation-toolbar">
        <label htmlFor="annotation-concept">目前類別</label>
        <select
          id="annotation-concept"
          disabled={concepts.length === 0 || busy}
          value={selectedConceptId}
          onChange={(event) => {
            const next = event.target.value;
            setSelectedConceptId(next);
            if (selected?.bbox !== null && selected?.bbox !== undefined) {
              onEdit(selected.annotation_id, next, selected.bbox);
            }
          }}
        >
          {concepts.map((concept) => (
            <option key={concept.concept_id} value={concept.concept_id}>
              {concept.display_name}
            </option>
          ))}
        </select>
        <button
          className={drawing ? "primary-action" : "secondary-action"}
          disabled={concepts.length === 0 || busy}
          type="button"
          onClick={() => setDrawing((value) => !value)}
        >
          {drawing ? "拖曳圖片畫框" : "新增框"}
        </button>
        <button
          className="secondary-action danger"
          disabled={selected === undefined || busy}
          type="button"
          onClick={() => selected && onDelete(selected.annotation_id)}
        >
          刪除所選框
        </button>
      </div>

      <div
        className={`annotation-stage ${drawing ? "is-drawing" : ""}`}
        style={{ aspectRatio: `${media.width_px} / ${media.height_px}` }}
      >
        <img alt={media.source.detail ?? media.media_hash} src={imageUrl} />
        <div
          ref={overlayRef}
          className="annotation-overlay"
          onPointerDown={startDrawing}
          onPointerMove={movePointer}
          onPointerUp={finishPointer}
        >
          {teacherClaims.map((claim) => {
            const bbox = claimBBox(claim);
            return bbox === null ? null : (
              <div className="teacher-box" key={claim.claim_id} style={styleFor(bbox)}>
                <span>{claim.concept.raw_text} · 教師建議</span>
              </div>
            );
          })}
          {annotations.map((annotation) => {
            const bbox =
              drag !== null && drag.kind !== "draw" &&
              drag.annotation.annotation_id === annotation.annotation_id
                ? drag.current
                : annotation.bbox;
            if (bbox === null) {
              return null;
            }
            return (
              <div
                className={`annotation-box ${
                  selectedAnnotationId === annotation.annotation_id ? "is-selected" : ""
                }`}
                data-testid="annotation-box"
                key={annotation.annotation_id}
                style={styleFor(bbox)}
                onPointerDown={(event) => startExisting(event, annotation, "move")}
              >
                <span>{conceptNames.get(annotation.concept_id) ?? "未知類別"}</span>
                <button
                  aria-label="調整框大小"
                  className="resize-handle"
                  type="button"
                  onPointerDown={(event) => startExisting(event, annotation, "resize")}
                />
              </div>
            );
          })}
          {drag?.kind === "draw" ? (
            <div className="annotation-box is-draft" style={styleFor(drag.current)} />
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default AnnotationCanvas;
