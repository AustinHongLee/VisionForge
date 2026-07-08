import { useState } from "react";

const DropZone = (): React.JSX.Element => {
  const [isDragging, setIsDragging] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<string[]>([]);

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
          setPendingFiles(Array.from(event.dataTransfer.files, (file) => file.name));
        }}
      >
        <p className="eyebrow">Understand</p>
        <h2 id="drop-zone-title">拖放影像</h2>
        <p>拖放影像到這裡，先排成待匯入清單。</p>
      </div>

      <div className="pending-panel" aria-live="polite">
        <h3>待匯入（尚未接後端）</h3>
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
