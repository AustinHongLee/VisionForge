import type { MediaRecord } from "../../../shared/contracts.generated";

interface ThumbnailGridProps {
  media: MediaRecord[];
}

const ThumbnailGrid = ({ media }: ThumbnailGridProps): React.JSX.Element => (
  <section className="media-panel" aria-labelledby="media-grid-title">
    <div className="section-heading">
      <p className="eyebrow">Imported media</p>
      <h2 id="media-grid-title">縮圖網格</h2>
    </div>

    <ul className="thumbnail-grid" aria-label="媒體縮圖網格">
      {media.map((item) => (
        <li className="media-card" key={item.media_hash}>
          <div className={`thumb-placeholder thumb-${item.format}`} aria-hidden="true">
            {item.format.toUpperCase()}
          </div>
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
