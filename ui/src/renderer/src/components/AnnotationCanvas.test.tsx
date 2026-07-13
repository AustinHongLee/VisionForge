import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type {
  AnnotationRevision,
  ConceptDefinition,
  MediaRecord,
} from "../../../shared/contracts.generated";
import AnnotationCanvas from "./AnnotationCanvas";

const media: MediaRecord = {
  byte_size: 100,
  exif_normalized: true,
  format: "jpeg",
  height_px: 100,
  imported_at: "2026-07-13T00:00:00Z",
  media_hash: "1".repeat(64),
  source: { detail: "keyboard.jpg", kind: "file" },
  width_px: 200,
};

const concept: ConceptDefinition = {
  aliases: [],
  concept_id: "0000000000000000000000000A",
  created_at: "2026-07-13T00:00:00Z",
  display_name: "Gate Valve",
  task_id: "0000000000000000000000000B",
};

const annotation: AnnotationRevision = {
  annotation_id: "0000000000000000000000000C",
  bbox: { type: "bbox", x1: 0.1, x2: 0.4, y1: 0.2, y2: 0.5 },
  concept_id: concept.concept_id,
  created_at: "2026-07-13T00:00:00Z",
  created_by: "local-user",
  media_hash: media.media_hash,
  revision_id: "0000000000000000000000000D",
  source: "manual",
  status: "active",
  task_id: concept.task_id,
};

describe("AnnotationCanvas keyboard controls", () => {
  it("adds, moves, and deletes boxes without pointer input", () => {
    const onAdd = vi.fn();
    const onDelete = vi.fn();
    const onEdit = vi.fn();
    render(
      <AnnotationCanvas
        annotations={[annotation]}
        busy={false}
        concepts={[concept]}
        imageUrl="blob:image"
        media={media}
        teacherClaims={[]}
        onAdd={onAdd}
        onDelete={onDelete}
        onEdit={onEdit}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "鍵盤新增置中框" }));
    expect(onAdd).toHaveBeenCalledWith(
      concept.concept_id,
      expect.objectContaining({ x1: 0.35, x2: 0.65 }),
    );

    const box = screen.getByRole("button", { name: /Gate Valve 標註框/ });
    fireEvent.keyDown(box, { key: "ArrowRight" });
    expect(onEdit).toHaveBeenCalledOnce();
    const [annotationId, conceptId, moved] = onEdit.mock.calls[0];
    expect(annotationId).toBe(annotation.annotation_id);
    expect(conceptId).toBe(concept.concept_id);
    expect(moved.x1).toBeCloseTo(0.105);
    expect(moved.x2).toBeCloseTo(0.405);

    fireEvent.keyDown(box, { key: "Delete" });
    expect(onDelete).toHaveBeenCalledWith(annotation.annotation_id);
  });
});
