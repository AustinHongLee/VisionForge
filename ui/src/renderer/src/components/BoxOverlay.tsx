import type { BBox, Claim } from "../../../shared/contracts.generated";

const RELIABILITY_LABEL = {
  high: "高",
  low: "低",
  none: "未校準",
} as const;

const isBBox = (claim: Claim): claim is Claim & { geometry: BBox } =>
  claim.geometry.type === "bbox";

interface BoxOverlayProps {
  claims: Claim[];
}

const BoxOverlay = ({ claims }: BoxOverlayProps): React.JSX.Element => (
  <div className="box-overlay" aria-label="偵測框">
    {claims.filter(isBBox).map((claim) => {
      const reliability = claim.confidence.reliability ?? "none";
      const style = {
        height: `${(claim.geometry.y2 - claim.geometry.y1) * 100}%`,
        left: `${claim.geometry.x1 * 100}%`,
        top: `${claim.geometry.y1 * 100}%`,
        width: `${(claim.geometry.x2 - claim.geometry.x1) * 100}%`,
      };

      return (
        <div
          aria-label={`偵測框 ${claim.concept.raw_text}`}
          className={`claim-box reliability-${reliability}`}
          data-testid="claim-box"
          key={claim.claim_id}
          style={style}
        >
          <span className="claim-label">
            {claim.concept.raw_text}
            <small>{RELIABILITY_LABEL[reliability]}</small>
          </span>
        </div>
      );
    })}
  </div>
);

export default BoxOverlay;
