import { useEffect, useState } from "react";
import type {
  DatasetVersion,
  ModelArtifact,
  ReadinessReport,
  TaskRecord,
} from "../../../shared/contracts.generated";
import {
  cancelTraining,
  freezeDataset,
  getReadiness,
  listArtifacts,
  listDatasets,
  listTasks,
  listTrainingRuns,
  sendEvaluationFeedback,
  startTraining,
} from "../api/client";
import type { TrainingStatusResult } from "../api/client";

const terminal = new Set(["succeeded", "failed", "cancelled", "interrupted"]);
const messageOf = (error: unknown): string => (error instanceof Error ? error.message : String(error));

interface DistillViewProps {
  onError(message: string | null): void;
}

const DistillView = ({ onError }: DistillViewProps): React.JSX.Element => {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [taskId, setTaskId] = useState("");
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [datasets, setDatasets] = useState<DatasetVersion[]>([]);
  const [runs, setRuns] = useState<TrainingStatusResult[]>([]);
  const [artifacts, setArtifacts] = useState<ModelArtifact[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listTasks()
      .then((items) => {
        setTasks(items);
        setTaskId((current) => current || items[0]?.task_id || "");
      })
      .catch((error: unknown) => onError(messageOf(error)));
  }, []);

  const refresh = async (): Promise<void> => {
    if (taskId === "") return;
    const [nextReadiness, nextDatasets, nextRuns, nextArtifacts] = await Promise.all([
      getReadiness(taskId),
      listDatasets(taskId),
      listTrainingRuns(taskId),
      listArtifacts(taskId),
    ]);
    setReadiness(nextReadiness);
    setDatasets(nextDatasets);
    setRuns(nextRuns);
    setArtifacts(nextArtifacts);
  };

  useEffect(() => {
    refresh().catch((error: unknown) => onError(messageOf(error)));
  }, [taskId]);

  useEffect(() => {
    if (!runs.some((item) => !terminal.has(item.latest_event.status))) return;
    const timer = window.setInterval(() => {
      refresh().catch((error: unknown) => onError(messageOf(error)));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [taskId, runs]);

  const perform = async (work: () => Promise<void>): Promise<void> => {
    setBusy(true);
    onError(null);
    try {
      await work();
      await refresh();
    } catch (error) {
      onError(messageOf(error));
    } finally {
      setBusy(false);
    }
  };

  const blockers = readiness?.blockers ?? [];
  const warnings = readiness?.warnings ?? [];

  return (
    <section className="distill-panel" aria-label="鑄造工作區">
      <div className="distill-toolbar">
        <div>
          <p className="eyebrow">Distill</p>
          <h3>把已確認資料鑄成自己的本地模型</h3>
        </div>
        <label htmlFor="distill-task">能力任務</label>
        <select id="distill-task" value={taskId} onChange={(event) => setTaskId(event.target.value)}>
          <option value="">選擇任務</option>
          {tasks.map((task) => (
            <option key={task.task_id} value={task.task_id}>
              {task.name}
            </option>
          ))}
        </select>
      </div>

      {taskId === "" ? (
        <div className="empty-panel">
          <h3>還沒有可鑄造的任務</h3>
          <p className="muted">先到教學站建立物件並完成至少兩個獨立來源群組。</p>
        </div>
      ) : (
        <>
          <section className="readiness-panel">
            <div className="panel-heading-row">
              <div>
                <p className="eyebrow">Readiness</p>
                <h3>{blockers.length === 0 ? "可以建立資料版本" : "還有硬性阻擋"}</h3>
              </div>
              <button
                className="primary-action"
                disabled={blockers.length > 0 || busy}
                type="button"
                onClick={() => void perform(async () => void (await freezeDataset(taskId)))}
              >
                凍結新資料版本
              </button>
            </div>
            {blockers.length > 0 ? (
              <ul className="issue-list blockers">
                {blockers.map((issue, index) => (
                  <li key={`${issue.code}-${index}`}>{issue.message}</li>
                ))}
              </ul>
            ) : null}
            {warnings.length > 0 ? (
              <ul className="issue-list warnings">
                {warnings.map((issue, index) => (
                  <li key={`${issue.code}-${index}`}>{issue.message}</li>
                ))}
              </ul>
            ) : null}
          </section>

          <section className="dataset-panel">
            <p className="eyebrow">Frozen datasets</p>
            <h3>不可變資料版本</h3>
            {datasets.length === 0 ? (
              <p className="muted">尚未凍結版本。</p>
            ) : (
              <div className="version-card-grid">
                {[...datasets].reverse().map((dataset) => {
                  const trainCount = dataset.items.filter((item) => item.split === "train").length;
                  const validationCount = dataset.items.length - trainCount;
                  return (
                    <article className="version-card" key={dataset.dataset_version_id}>
                      <strong>Dataset v{dataset.version_number}</strong>
                      <span>{dataset.class_map.map((item) => item.display_name).join("、")}</span>
                      <small>
                        train {trainCount} · validation {validationCount}
                      </small>
                      <button
                        className="primary-action"
                        disabled={busy}
                        type="button"
                        onClick={() =>
                          void perform(async () => void (await startTraining(dataset.dataset_version_id)))
                        }
                      >
                        開始鑄造
                      </button>
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <section className="runs-panel">
            <p className="eyebrow">Training attempts</p>
            <h3>訓練紀錄</h3>
            {runs.length === 0 ? (
              <p className="muted">尚無訓練嘗試。</p>
            ) : (
              <div className="run-list">
                {[...runs].reverse().map((item) => (
                  <article className="run-card" key={item.run.training_run_id}>
                    <div className="panel-heading-row">
                      <div>
                        <strong>{item.latest_event.status}</strong>
                        <p>{item.latest_event.message || "等待狀態"}</p>
                      </div>
                      {!terminal.has(item.latest_event.status) ? (
                        <button
                          className="secondary-action danger"
                          disabled={busy}
                          type="button"
                          onClick={() =>
                            void perform(async () =>
                              void (await cancelTraining(item.run.training_run_id)),
                            )
                          }
                        >
                          取消
                        </button>
                      ) : null}
                    </div>
                    <progress max={1} value={item.latest_event.progress ?? 0} />
                    {item.latest_event.technical_detail ? (
                      <details>
                        <summary>技術詳情</summary>
                        <pre>{item.latest_event.technical_detail}</pre>
                      </details>
                    ) : null}
                    {item.evaluation !== null ? (
                      <div className="evaluation-panel">
                        <div className="metric-row">
                          {item.evaluation.metrics.map((metric) => (
                            <span key={metric.name}>
                              {metric.name} {(metric.value * 100).toFixed(1)}%
                            </span>
                          ))}
                        </div>
                        {(item.evaluation.errors ?? []).length === 0 ? (
                          <p className="success-message">此 validation snapshot 沒有記錄到錯誤案例。</p>
                        ) : (
                          <ul className="error-gallery">
                            {(item.evaluation.errors ?? []).map((error, index) => (
                              <li key={`${error.media_hash}-${index}`}>
                                <span>{error.kind} · {error.media_hash.slice(0, 10)}</span>
                                <button
                                  className="secondary-action"
                                  disabled={busy}
                                  type="button"
                                  onClick={() =>
                                    void perform(async () =>
                                      void (await sendEvaluationFeedback(
                                        item.evaluation!.evaluation_id,
                                        index,
                                      )),
                                    )
                                  }
                                >
                                  送回教學修正
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            )}
          </section>

          <p className="muted">已封存 ModelArtifact：{artifacts.length}</p>
        </>
      )}
    </section>
  );
};

export default DistillView;
