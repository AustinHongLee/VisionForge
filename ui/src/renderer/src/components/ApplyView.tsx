import { useEffect, useState } from "react";
import type { ModelArtifact, ModelPrediction, TaskRecord } from "../../../shared/contracts.generated";
import { applyArtifact, listArtifacts, listTasks } from "../api/client";

interface ApplyViewProps {
  onError(message: string | null): void;
}

const messageOf = (error: unknown): string => (error instanceof Error ? error.message : String(error));

const ApplyView = ({ onError }: ApplyViewProps): React.JSX.Element => {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [taskId, setTaskId] = useState("");
  const [artifacts, setArtifacts] = useState<ModelArtifact[]>([]);
  const [artifactId, setArtifactId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState({ width: 4, height: 3 });
  const [predictions, setPredictions] = useState<ModelPrediction[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listTasks()
      .then((items) => {
        setTasks(items);
        setTaskId(items[0]?.task_id ?? "");
      })
      .catch((error: unknown) => onError(messageOf(error)));
  }, []);

  useEffect(() => {
    if (taskId === "") {
      setArtifacts([]);
      setArtifactId("");
      return;
    }
    listArtifacts(taskId)
      .then((items) => {
        setArtifacts(items);
        setArtifactId(items.at(-1)?.artifact_id ?? "");
      })
      .catch((error: unknown) => onError(messageOf(error)));
  }, [taskId]);

  useEffect(
    () => () => {
      if (previewUrl !== null) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl],
  );

  const selectFile = (next: File | null): void => {
    if (previewUrl !== null) URL.revokeObjectURL(previewUrl);
    setFile(next);
    setPredictions([]);
    setPreviewUrl(next === null ? null : URL.createObjectURL(next));
  };

  const run = async (): Promise<void> => {
    if (file === null || artifactId === "") return;
    setBusy(true);
    onError(null);
    try {
      const result = await applyArtifact(artifactId, file);
      setPredictions(result.predictions);
    } catch (error) {
      onError(messageOf(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="apply-panel" aria-label="模型試跑">
      <div className="apply-toolbar">
        <div>
          <p className="eyebrow">Apply</p>
          <h3>拿未入庫的新圖片試跑 ModelArtifact</h3>
        </div>
        <label htmlFor="apply-task">能力任務</label>
        <select id="apply-task" value={taskId} onChange={(event) => setTaskId(event.target.value)}>
          <option value="">選擇任務</option>
          {tasks.map((task) => (
            <option key={task.task_id} value={task.task_id}>
              {task.name}
            </option>
          ))}
        </select>
        <label htmlFor="apply-artifact">模型產物</label>
        <select
          id="apply-artifact"
          value={artifactId}
          onChange={(event) => setArtifactId(event.target.value)}
        >
          <option value="">選擇 Artifact</option>
          {artifacts.map((artifact) => (
            <option key={artifact.artifact_id} value={artifact.artifact_id}>
              {artifact.artifact_id.slice(0, 10)} · {artifact.class_map.map((item) => item.display_name).join("、")}
            </option>
          ))}
        </select>
      </div>

      {artifacts.length === 0 ? (
        <div className="empty-panel">
          <h3>尚無本地模型</h3>
          <p className="muted">先到鑄造站凍結資料版本並完成一次訓練。</p>
        </div>
      ) : (
        <>
          <div className="apply-file-row">
            <label className="secondary-action" htmlFor="apply-file">選擇新圖片</label>
            <input
              accept="image/*"
              id="apply-file"
              type="file"
              onChange={(event) => selectFile(event.target.files?.[0] ?? null)}
            />
            <button
              className="primary-action"
              disabled={file === null || artifactId === "" || busy}
              type="button"
              onClick={() => void run()}
            >
              {busy ? "本地推論中" : "執行本地模型"}
            </button>
          </div>
          {previewUrl === null ? (
            <div className="empty-panel">選一張未入庫的圖片開始試跑。</div>
          ) : (
            <div
              className="apply-stage"
              style={{ aspectRatio: `${imageSize.width} / ${imageSize.height}` }}
            >
              <img
                alt="試跑圖片"
                src={previewUrl}
                onLoad={(event) =>
                  setImageSize({
                    height: event.currentTarget.naturalHeight,
                    width: event.currentTarget.naturalWidth,
                  })
                }
              />
              <div className="prediction-overlay">
                {predictions.map((prediction, index) => (
                  <div
                    className="prediction-box"
                    key={`${prediction.concept_id}-${index}`}
                    style={{
                      height: `${(prediction.bbox.y2 - prediction.bbox.y1) * 100}%`,
                      left: `${prediction.bbox.x1 * 100}%`,
                      top: `${prediction.bbox.y1 * 100}%`,
                      width: `${(prediction.bbox.x2 - prediction.bbox.x1) * 100}%`,
                    }}
                  >
                    <span>{prediction.display_name} {(prediction.confidence * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
};

export default ApplyView;
