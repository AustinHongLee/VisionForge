import { useState } from "react";
import type { Claim, MediaRecord } from "../../../shared/contracts.generated";
import BoxOverlay from "./BoxOverlay";

interface DetailViewProps {
  claims: Claim[];
  error: string | null;
  imageUrl: string | undefined;
  isInferring: boolean;
  media: MediaRecord | null;
  onDetect(concepts: string[]): void;
}

const parseConcepts = (value: string): string[] =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

const DetailView = ({
  claims,
  error,
  imageUrl,
  isInferring,
  media,
  onDetect,
}: DetailViewProps): React.JSX.Element => {
  const [conceptText, setConceptText] = useState("bolt");

  if (media === null) {
    return (
      <section className="detail-panel empty-panel" aria-label="媒體詳情">
        <p className="eyebrow">Detect</p>
        <h3>選一張圖開始偵測</h3>
        <p className="muted">匯入後點縮圖，輸入概念，框會疊在這裡。</p>
      </section>
    );
  }

  const concepts = parseConcepts(conceptText);

  return (
    <section className="detail-panel" aria-label="媒體詳情">
      <div className="detail-toolbar">
        <div>
          <p className="eyebrow">Detect</p>
          <h3>{media.source.detail ?? media.media_hash.slice(0, 10)}</h3>
        </div>
        <code>{media.media_hash.slice(0, 12)}</code>
      </div>

      <div className="concept-controls">
        <label htmlFor="concept-input">概念</label>
        <input
          id="concept-input"
          value={conceptText}
          onChange={(event) => setConceptText(event.target.value)}
          placeholder="bolt, crack"
        />
        <button
          type="button"
          className="primary-action"
          disabled={concepts.length === 0 || isInferring}
          onClick={() => onDetect(concepts)}
        >
          {isInferring ? "偵測中" : "偵測"}
        </button>
      </div>

      {error !== null ? <p className="error-message">{error}</p> : null}

      <div className="detail-image-frame">
        {imageUrl === undefined ? (
          <div className="image-placeholder">縮圖載入中</div>
        ) : (
          <>
            <img src={imageUrl} alt={media.source.detail ?? media.media_hash} />
            <BoxOverlay claims={claims} />
          </>
        )}
      </div>
    </section>
  );
};

export default DetailView;
