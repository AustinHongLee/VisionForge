import { useEffect, useMemo, useState } from "react";
import type {
  BBox,
  Claim,
  ConceptDefinition,
  CoverageState,
  MediaRecord,
  TaskRecord,
} from "../../../shared/contracts.generated";
import {
  ApiError,
  addAnnotation,
  assignMedia,
  createConcept,
  createTask,
  deleteAnnotation,
  editAnnotation,
  listConcepts,
  listTasks,
  teach,
  teachingState,
  updateCoverage,
} from "../api/client";
import type { TeachingState } from "../api/client";
import AnnotationCanvas from "./AnnotationCanvas";

interface TeachingViewProps {
  imageUrl: string | undefined;
  media: MediaRecord | null;
  onError(message: string | null): void;
}

const messageOf = (error: unknown): string => (error instanceof Error ? error.message : String(error));

const TeachingView = ({ imageUrl, media, onError }: TeachingViewProps): React.JSX.Element => {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [activeTaskId, setActiveTaskId] = useState("");
  const [concepts, setConcepts] = useState<ConceptDefinition[]>([]);
  const [state, setState] = useState<TeachingState | null>(null);
  const [newTaskName, setNewTaskName] = useState("");
  const [newConceptName, setNewConceptName] = useState("");
  const [busy, setBusy] = useState(false);

  const activeTask = tasks.find((task) => task.task_id === activeTaskId);

  const refreshTasks = async (): Promise<void> => {
    const next = await listTasks();
    setTasks(next);
    setActiveTaskId((current) => current || next[0]?.task_id || "");
  };

  useEffect(() => {
    refreshTasks().catch((error: unknown) => onError(messageOf(error)));
  }, []);

  const refreshScope = async (): Promise<void> => {
    if (activeTaskId === "") {
      setConcepts([]);
      setState(null);
      return;
    }
    const nextConcepts = await listConcepts(activeTaskId);
    setConcepts(nextConcepts);
    if (media === null) {
      setState(null);
      return;
    }
    try {
      setState(await teachingState(activeTaskId, media.media_hash));
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setState(null);
        return;
      }
      throw error;
    }
  };

  useEffect(() => {
    refreshScope().catch((error: unknown) => onError(messageOf(error)));
  }, [activeTaskId, media?.media_hash]);

  const perform = async (work: () => Promise<void>): Promise<void> => {
    setBusy(true);
    onError(null);
    try {
      await work();
    } catch (error) {
      onError(messageOf(error));
    } finally {
      setBusy(false);
    }
  };

  const createTaskNow = (): void => {
    const name = newTaskName.trim();
    if (name === "") return;
    void perform(async () => {
      const created = await createTask(name);
      setNewTaskName("");
      await refreshTasks();
      setActiveTaskId(created.task_id);
    });
  };

  const createConceptNow = (): void => {
    const name = newConceptName.trim();
    if (name === "" || activeTaskId === "") return;
    void perform(async () => {
      await createConcept(activeTaskId, name);
      setNewConceptName("");
      await refreshScope();
    });
  };

  const ensureAssigned = (): void => {
    if (media === null || activeTaskId === "") return;
    void perform(async () => {
      await assignMedia(activeTaskId, media.media_hash);
      await refreshScope();
    });
  };

  const runTeacher = (): void => {
    if (media === null || activeTaskId === "") return;
    void perform(async () => {
      await teach(
        activeTaskId,
        media.media_hash,
        concepts.map((concept) => concept.concept_id),
      );
      await refreshScope();
    });
  };

  const claimConcept = (claim: Claim): ConceptDefinition | undefined => {
    const raw = claim.concept.raw_text.toLocaleLowerCase();
    return concepts.find(
      (concept) =>
        concept.display_name.toLocaleLowerCase() === raw ||
        (concept.aliases ?? []).some((alias) => alias.toLocaleLowerCase() === raw),
    );
  };

  const acceptedClaimRefs = useMemo(
    () => new Set((state?.annotations ?? []).flatMap((item) => item.source_claim_ref ?? [])),
    [state],
  );
  const pendingSuggestions = (state?.teacher_claims ?? []).filter(
    (claim) => !acceptedClaimRefs.has(claim.claim_id) && claimConcept(claim) !== undefined,
  );

  const saveAdd = (conceptId: string, bbox: BBox): void => {
    if (media === null) return;
    void perform(async () => {
      await addAnnotation({
        bbox,
        concept_id: conceptId,
        media_hash: media.media_hash,
        task_id: activeTaskId,
      });
      await refreshScope();
    });
  };

  const acceptClaim = (claim: Claim): void => {
    if (media === null) return;
    const concept = claimConcept(claim);
    if (concept === undefined) return;
    void perform(async () => {
      await addAnnotation({
        concept_id: concept.concept_id,
        media_hash: media.media_hash,
        source_claim_ref: claim.claim_id,
        task_id: activeTaskId,
      });
      await refreshScope();
    });
  };

  const saveEdit = (annotationId: string, conceptId: string, bbox: BBox): void => {
    void perform(async () => {
      await editAnnotation(annotationId, conceptId, bbox);
      await refreshScope();
    });
  };

  const saveDelete = (annotationId: string): void => {
    void perform(async () => {
      await deleteAnnotation(annotationId);
      await refreshScope();
    });
  };

  const verify = (conceptId: string, coverageState: CoverageState): void => {
    if (media === null) return;
    void perform(async () => {
      await updateCoverage({
        concept_id: conceptId,
        media_hash: media.media_hash,
        state: coverageState,
        task_id: activeTaskId,
      });
      await refreshScope();
    });
  };

  return (
    <section className="teaching-panel" aria-label="教學工作區">
      <div className="forge-setup">
        <div className="setup-block">
          <label htmlFor="task-select">能力任務</label>
          <div className="inline-controls">
            <select
              id="task-select"
              value={activeTaskId}
              onChange={(event) => setActiveTaskId(event.target.value)}
            >
              <option value="">選擇任務</option>
              {tasks.map((task) => (
                <option key={task.task_id} value={task.task_id}>
                  {task.name}
                </option>
              ))}
            </select>
            <input
              aria-label="新任務名稱"
              placeholder="例如：閥件偵測"
              value={newTaskName}
              onChange={(event) => setNewTaskName(event.target.value)}
            />
            <button className="secondary-action" disabled={busy} type="button" onClick={createTaskNow}>
              建立任務
            </button>
          </div>
        </div>
        <div className="setup-block">
          <label htmlFor="new-concept">要教的物件</label>
          <div className="inline-controls">
            <input
              id="new-concept"
              placeholder="例如：Gate Valve"
              value={newConceptName}
              onChange={(event) => setNewConceptName(event.target.value)}
            />
            <button
              className="secondary-action"
              disabled={activeTask === undefined || busy}
              type="button"
              onClick={createConceptNow}
            >
              新增物件
            </button>
          </div>
          <div className="concept-chips" aria-label="任務物件">
            {concepts.map((concept) => (
              <span key={concept.concept_id}>{concept.display_name}</span>
            ))}
          </div>
        </div>
      </div>

      {media === null ? (
        <div className="empty-panel">
          <h3>先選一張圖片</h3>
          <p className="muted">圖片、任務與物件三者會明確綁定，不會把 A 的資料混進 B。</p>
        </div>
      ) : activeTask === undefined ? (
        <div className="empty-panel">
          <h3>先建立一個能力任務</h3>
          <p className="muted">一個專案是一項能力；Task 是其中輸出形狀一致的一條學習工作。</p>
        </div>
      ) : state === null ? (
        <div className="empty-panel">
          <h3>把這張圖加入「{activeTask.name}」</h3>
          <p className="muted">加入後每個物件一律從「尚未查核」開始，不會偷當成負例。</p>
          <button className="primary-action" disabled={busy} type="button" onClick={ensureAssigned}>
            加入任務
          </button>
        </div>
      ) : imageUrl === undefined ? (
        <div className="empty-panel">圖片載入中</div>
      ) : (
        <div className="teaching-workspace">
          <div className="teaching-main">
            <div className="teaching-actions">
              <div>
                <p className="eyebrow">Teacher</p>
                <h3>{media.source.detail ?? media.media_hash.slice(0, 12)}</h3>
              </div>
              <button
                className="primary-action"
                disabled={concepts.length === 0 || busy}
                type="button"
                onClick={runTeacher}
              >
                {busy ? "處理中" : "請教師框選"}
              </button>
            </div>
            <AnnotationCanvas
              annotations={state.annotations}
              busy={busy}
              concepts={concepts}
              imageUrl={imageUrl}
              media={media}
              teacherClaims={pendingSuggestions}
              onAdd={saveAdd}
              onDelete={saveDelete}
              onEdit={saveEdit}
            />
          </div>

          <aside className="teaching-sidebar">
            <section>
              <p className="eyebrow">Suggestions</p>
              <h3>教師建議</h3>
              {pendingSuggestions.length === 0 ? (
                <p className="muted">沒有待接受的建議；也可以直接畫框。</p>
              ) : (
                <ul className="suggestion-list">
                  {pendingSuggestions.map((claim) => (
                    <li key={claim.claim_id}>
                      <span>{claim.concept.raw_text}</span>
                      <button
                        className="secondary-action"
                        disabled={busy}
                        type="button"
                        onClick={() => acceptClaim(claim)}
                      >
                        接受這個框
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section>
              <p className="eyebrow">Coverage</p>
              <h3>這張圖查完了嗎？</h3>
              <div className="coverage-list">
                {concepts.map((concept) => {
                  const coverage = state.coverage.find(
                    (item) => item.concept_id === concept.concept_id,
                  );
                  const current = coverage?.state ?? "unverified";
                  return (
                    <div className="coverage-card" key={concept.concept_id}>
                      <strong>{concept.display_name}</strong>
                      <span className={`coverage-state state-${current}`}>{current}</span>
                      <div>
                        <button
                          className="secondary-action"
                          disabled={busy}
                          type="button"
                          onClick={() => verify(concept.concept_id, "verified_complete")}
                        >
                          框完了
                        </button>
                        <button
                          className="secondary-action"
                          disabled={busy}
                          type="button"
                          onClick={() => verify(concept.concept_id, "verified_absent")}
                        >
                          圖中沒有
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </aside>
        </div>
      )}
    </section>
  );
};

export default TeachingView;
