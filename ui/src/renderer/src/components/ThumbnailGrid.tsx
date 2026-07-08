import type { MediaRecord } from "../../../shared/contracts.generated";

interface ThumbnailGridProps {
  media: MediaRecord[];
  onSelect(media: MediaRecord): void;
  selectedHash: string | null;
  thumbnailUrls: Record<string, string>;
}

const ThumbnailGrid = ({
  media,
  onSelect,
  selectedHash,
  thumbnailUrls,
}: ThumbnailGridProps): React.JSX.Element => (
  <section className="media-panel" aria-labelledby="media-grid-title">
    <div className="section-heading">
      <p className="eyebrow">Imported media</p>
      <h2 id="media-grid-title">縮圖網格</h2>
    </div>

    <ul className="thumbnail-grid" aria-label="媒體縮圖網格">
      {media.length === 0 ? <li className="empty-media">尚無匯入影像</li> : null}
      {media.map((item) => (
        <li className="media-card" key={item.media_hash}>
          <button
            type="button"
            className={item.media_hash === selectedHash ? "media-button is-selected" : "media-button"}
            onClick={() => onSelect(item)}
          >
            {thumbnailUrls[item.media_hash] !== undefined ? (
              <img
                className="thumb-image"
                src={thumbnailUrls[item.media_hash]}
                alt={item.source.detail ?? item.media_hash}
              />
            ) : (
              <div className={`thumb-placeholder thumb-${item.format}`} aria-hidden="true">
                {item.format.toUpperCase()}
              </div>
            )}
          </button>
          <div className="media-meta">
            <strong>{item.format}</strong>
            <span>
              {item.width_px}×{item.height_px}
            </span>
            <code>{item.media_hash.slice(0, 8)}</code>
          </div>
        </li>
      ))}
    </ul>
  </section>
);

export default ThumbnailGrid;
