import { useEffect, useMemo, useState } from "react";
import type { Claim } from "../../../shared/contracts.generated";
import {
  approveClaim,
  recalibrate,
  rejectClaim,
  reviewPending,
  thumbnailUrl,
  type PendingItem,
} from "../api/client";
import BoxOverlay from "./BoxOverlay";

const REVIEWER = "local-user";

const hasBBox = (claim: Claim): boolean => claim.geometry.type === "bbox";

const formatRaw = (raw: number): string => `${Math.round(raw * 100)}%`;

const groupPending = (items: PendingItem[]): Map<string, PendingItem[]> => {
  const groups = new Map<string, PendingItem[]>();
  for (const item of items) {
    const key = item.claim.concept.raw_text;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return groups;
};

const decisionBody = (item: PendingItem) => ({
  claim_id: item.claim.claim_id,
  reviewer: REVIEWER,
});

const CurateView = (): React.JSX.Element => {
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRecalibrating, setIsRecalibrating] = useState(false);
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [thumbnailUrls, setThumbnailUrls] = useState<Record<string, string>>({});
  const groups = useMemo(() => groupPending(pending.filter((item) => hasBBox(item.claim))), [pending]);

  const loadPending = async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const items = await reviewPending();
      setPending(items);
      const uniqueHashes = Array.from(new Set(items.map((item) => item.media_hash)));
      const entries = await Promise.all(
        uniqueHashes.map(async (mediaHash) => [mediaHash, await thumbnailUrl(mediaHash)] as const),
      );
      setThumbnailUrls(Object.fromEntries(entries));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadPending();
  }, []);

  const handleApprove = async (item: PendingItem): Promise<void> => {
    setError(null);
    setStatus(null);
    try {
      await approveClaim(decisionBody(item));
      await loadPending();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  };

  const handleReject = async (item: PendingItem): Promise<void> => {
    setError(null);
    setStatus(null);
    try {
      await rejectClaim(decisionBody(item));
      await loadPending();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  };

  const handleRecalibrate = async (): Promise<void> => {
    setIsRecalibrating(true);
    setError(null);
    setStatus(null);
    try {
      const snapshot = await recalibrate();
      setStatus(
        snapshot === null
          ? "尚無已審結果"
          : `已用已審結果重新校準：${snapshot.calibration_id.slice(0, 8)}`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setIsRecalibrating(false);
    }
  };

  return (
    <section className="curate-panel" aria-label="審核中心">
      <div className="curate-toolbar">
        <div>
          <p className="eyebrow">Review</p>
          <h3>待審 Claim</h3>
        </div>
        <button
          type="button"
          className="primary-action"
          disabled={isRecalibrating}
          onClick={() => {
            void handleRecalibrate();
          }}
        >
          {isRecalibrating ? "校準中" : "重新校準"}
        </button>
      </div>

      {status !== null ? <p className="success-message">{status}</p> : null}
      {error !== null ? (
        <p className="error-message" role="alert">
          {error}
        </p>
      ) : null}
      {isLoading ? <p className="muted">載入待審佇列中</p> : null}

      {!isLoading && groups.size === 0 ? (
        <div className="empty-panel">
          <p className="eyebrow">Review</p>
          <h3>尚無待審 Claim</h3>
          <p className="muted">看懂站產生 run 後，待審框會出現在這裡。</p>
        </div>
      ) : null}

      <div className="review-groups">
        {Array.from(groups.entries()).map(([concept, items]) => (
          <section className="review-group" key={concept} aria-label={`概念 ${concept}`}>
            <div className="review-group-heading">
              <h3>{concept}</h3>
              <span>{items.length} 筆</span>
            </div>
            <div className="review-card-grid">
              {items.map((item) => {
                const imageUrl = thumbnailUrls[item.media_hash];
                return (
                  <article className="review-card" key={item.claim.claim_id}>
                    <div className="review-image-frame">
                      {imageUrl === undefined ? (
                        <div className="image-placeholder">縮圖載入中</div>
                      ) : (
                        <>
                          <img src={imageUrl} alt={`${concept} 待審縮圖`} />
                          <BoxOverlay claims={[item.claim]} />
                        </>
                      )}
                    </div>
                    <div className="review-card-body">
                      <div>
                        <p className="eyebrow">Raw confidence</p>
                        <strong>{formatRaw(item.claim.confidence.raw)}</strong>
                      </div>
                      <code>{item.claim.claim_id.slice(0, 10)}</code>
                    </div>
                    <div className="review-actions">
                      <button
                        type="button"
                        className="secondary-action danger"
                        onClick={() => {
                          void handleReject(item);
                        }}
                      >
                        否決
                      </button>
                      <button
                        type="button"
                        className="primary-action"
                        onClick={() => {
                          void handleApprove(item);
                        }}
                      >
                        批准
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
};

export default CurateView;
