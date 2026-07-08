import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Claim } from "../../../shared/contracts.generated";
import BoxOverlay from "./BoxOverlay";

const bboxClaim: Claim = {
  assertion: "presence",
  claim_id: "00000000000000000000000001",
  concept: { raw_text: "bolt" },
  confidence: { raw: 0.8, reliability: "none" },
  geometry: { type: "bbox", x1: 0.1, x2: 0.5, y1: 0.2, y2: 0.6 },
};

describe("BoxOverlay", () => {
  it("maps normalized BBox coordinates to proportional styles", () => {
    render(<BoxOverlay claims={[bboxClaim]} />);

    const box = screen.getByTestId("claim-box");
    expect(box).toHaveStyle({
      height: "40%",
      left: "10%",
      top: "20%",
      width: "40%",
    });
    expect(box).toHaveClass("reliability-none");
    expect(screen.getByText("bolt")).toBeInTheDocument();
    expect(screen.getByText("未校準")).toBeInTheDocument();
  });
});
