import { useState } from "react";

interface DropZoneProps {
  isUploading: boolean;
  onFiles(files: File[]): void;
  pendingFiles: string[];
}

const DropZone = ({ isUploading, onFiles, pendingFiles }: DropZoneProps): React.JSX.Element => {
  const [isDragging, setIsDragging] = useState(false);

  const stopDrag = (): void => {
    setIsDragging(false);
  };

  return (
    <section className="drop-zone-panel" aria-labelledby="drop-zone-title">
      <div
        data-testid="drop-zone"
        className={`drop-zone${isDragging ? " is-dragging" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={stopDrag}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          onFiles(Array.from(event.dataTransfer.files));
        }}
      >
        <p className="eyebrow">Understand</p>
        <h2 id="drop-zone-title">拖放影像</h2>
        <p>{isUploading ? "匯入中，請稍候。" : "拖放影像到這裡，匯入後會出現在縮圖網格。"}</p>
      </div>

      <div className="pending-panel" aria-live="polite">
        <h3>最近匯入</h3>
        {pendingFiles.length > 0 ? (
          <ul>
            {pendingFiles.map((name, index) => (
              <li key={`${name}-${index}`}>{name}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">尚無待匯入檔案</p>
        )}
      </div>
    </section>
  );
};

export default DropZone;
