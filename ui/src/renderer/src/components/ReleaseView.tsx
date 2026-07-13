import { useEffect, useState } from "react";
import type {
  CapabilityRelease,
  ModelArtifact,
  TaskRecord,
} from "../../../shared/contracts.generated";
import {
  createRelease,
  listArtifacts,
  listReleases,
  listTasks,
  releaseArchiveUrl,
} from "../api/client";

interface ReleaseViewProps {
  onError(message: string | null): void;
}

const messageOf = (error: unknown): string => (error instanceof Error ? error.message : String(error));

const ReleaseView = ({ onError }: ReleaseViewProps): React.JSX.Element => {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [taskId, setTaskId] = useState("");
  const [artifacts, setArtifacts] = useState<ModelArtifact[]>([]);
  const [artifactId, setArtifactId] = useState("");
  const [releases, setReleases] = useState<CapabilityRelease[]>([]);
  const [archiveUrls, setArchiveUrls] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listTasks()
      .then((items) => {
        setTasks(items);
        setTaskId(items[0]?.task_id ?? "");
      })
      .catch((error: unknown) => onError(messageOf(error)));
  }, []);

  const refresh = async (): Promise<void> => {
    if (taskId === "") return;
    const [nextArtifacts, nextReleases] = await Promise.all([
      listArtifacts(taskId),
      listReleases(taskId),
    ]);
    setArtifacts(nextArtifacts);
    setArtifactId((current) => current || nextArtifacts.at(-1)?.artifact_id || "");
    setReleases(nextReleases);
    const pairs = await Promise.all(
      nextReleases.map(async (release) => [
        release.release_id,
        await releaseArchiveUrl(release.release_id),
      ] as const),
    );
    setArchiveUrls(Object.fromEntries(pairs));
  };

  useEffect(() => {
    refresh().catch((error: unknown) => onError(messageOf(error)));
  }, [taskId]);

  const publish = async (): Promise<void> => {
    if (artifactId === "") return;
    setBusy(true);
    onError(null);
    try {
      await createRelease(artifactId);
      await refresh();
    } catch (error) {
      onError(messageOf(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="release-panel" aria-label="能力版本">
      <div className="release-toolbar">
        <div>
          <p className="eyebrow">Capability Release</p>
          <h3>把能力帶走，不依賴 Studio</h3>
        </div>
        <label htmlFor="release-task">能力任務</label>
        <select id="release-task" value={taskId} onChange={(event) => setTaskId(event.target.value)}>
          <option value="">選擇任務</option>
          {tasks.map((task) => (
            <option key={task.task_id} value={task.task_id}>
              {task.name}
            </option>
          ))}
        </select>
      </div>

      {artifacts.length === 0 ? (
        <div className="empty-panel">
          <h3>還沒有能發布的 Artifact</h3>
          <p className="muted">完成鑄造與 frozen validation 後，這裡才會允許發布。</p>
        </div>
      ) : (
        <section className="publish-panel">
          <div>
            <label htmlFor="release-artifact">選擇模型產物</label>
            <select
              id="release-artifact"
              value={artifactId}
              onChange={(event) => setArtifactId(event.target.value)}
            >
              {artifacts.map((artifact) => (
                <option key={artifact.artifact_id} value={artifact.artifact_id}>
                  {artifact.artifact_id.slice(0, 10)} · {artifact.class_map.map((item) => item.display_name).join("、")}
                </option>
              ))}
            </select>
          </div>
          <button
            className="primary-action"
            disabled={artifactId === "" || busy}
            type="button"
            onClick={() => void publish()}
          >
            {busy ? "封裝與 parity 驗證中" : "發布下一個能力版本"}
          </button>
          <p className="muted">
            zip 會包含權重、class map、前後處理、Evaluation 摘要、runner、鎖定依賴、
            I/O Schema、parity fixture 與授權清單。
          </p>
        </section>
      )}

      <section className="release-history">
        <p className="eyebrow">Immutable history</p>
        <h3>已發布版本</h3>
        {releases.length === 0 ? (
          <p className="muted">尚未發布。</p>
        ) : (
          <div className="release-card-grid">
            {[...releases].reverse().map((release) => (
              <article className="release-card" key={release.release_id}>
                <strong>CapabilityRelease v{release.version_number}</strong>
                <code>{release.archive_hash.slice(0, 16)}</code>
                <span>{release.artifact_ids.length} 個不可變 Artifact</span>
                <a className="primary-action" href={archiveUrls[release.release_id]}>
                  儲存 zip
                </a>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
};

export default ReleaseView;
