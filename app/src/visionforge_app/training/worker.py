"""獨立訓練程序入口；成功才原子註冊 Artifact、Evaluation 與 succeeded。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from visionforge_core.contracts import (
    EvaluationMetric,
    EvaluationReport,
    ModelArtifact,
)
from visionforge_core.storage import open_project
from visionforge_core.storage.errors import ConflictError

from visionforge_app.training.lifecycle import append_training_event
from visionforge_app.training.tiny_detector import train_and_evaluate

_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _new_ulid() -> str:
    timestamp_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    value = (timestamp_ms << 80) | secrets.randbits(80)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD32[value & 0b11111])
        value >>= 5
    return "".join(reversed(chars))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parent_watchdog(project_root: Path, run_id: str, parent_pid: int) -> None:
    _wait_for_parent_exit(parent_pid)
    try:
        with open_project(project_root) as project:
            append_training_event(
                project,
                training_run_id=run_id,
                event_id=_new_ulid(),
                status="interrupted",
                at=_now(),
                message="API sidecar 已結束，訓練程序同步中斷",
            )
    except ConflictError:
        pass
    os._exit(2)


def _wait_for_parent_exit(parent_pid: int) -> None:
    if os.name == "nt":
        import ctypes

        synchronize = 0x00100000
        infinite = 0xFFFFFFFF
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, parent_pid)
        if not handle:
            return
        try:
            ctypes.windll.kernel32.WaitForSingleObject(handle, infinite)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
        return
    while True:
        try:
            os.kill(parent_pid, 0)
        except (OSError, ProcessLookupError):
            return
        time.sleep(1)


def run_worker(project_root: Path, run_id: str, parent_pid: int | None = None) -> None:
    if parent_pid is not None:
        threading.Thread(
            target=_parent_watchdog,
            args=(project_root, run_id, parent_pid),
            daemon=True,
        ).start()
    with open_project(project_root) as project:
        run = project.training_runs.get(run_id)
        append_training_event(
            project,
            training_run_id=run_id,
            event_id=_new_ulid(),
            status="running",
            at=_now(),
            progress=0,
            message="正在準備本地學生模型",
        )
        artifact_id = _new_ulid()
        artifact_dir = project.root / "artifacts" / artifact_id
        fixture = os.environ.get("VISIONFORGE_TRAINER_FIXTURE") == "1"
        artifact_path = artifact_dir / ("model.fixture.json" if fixture else "model.pt")
        try:
            if fixture:
                artifact_dir.mkdir(parents=True, exist_ok=False)
                artifact_path.write_text(
                    json.dumps({"fixture": True, "run_id": run_id}, sort_keys=True),
                    encoding="utf-8",
                )
                result_metrics = (
                    EvaluationMetric(name="precision", value=1),
                    EvaluationMetric(name="recall", value=1),
                    EvaluationMetric(name="mean_iou", value=1),
                )
                result_errors = ()
            else:

                def progress(epoch: int, epochs: int, loss: float) -> None:
                    append_training_event(
                        project,
                        training_run_id=run_id,
                        event_id=_new_ulid(),
                        status="running",
                        at=_now(),
                        progress=epoch / epochs,
                        message=f"第 {epoch}/{epochs} 輪，loss {loss:.4f}",
                    )

                result = train_and_evaluate(
                    project, run, artifact_path, progress=progress
                )
                result_metrics = result.metrics
                result_errors = result.errors

            artifact_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            dataset = project.dataset_versions.get(run.dataset_version_id)
            created_at = _now()
            artifact = ModelArtifact(
                artifact_id=artifact_id,
                artifact_hash=artifact_hash,
                task_id=run.task_id,
                dataset_version_id=run.dataset_version_id,
                training_run_id=run_id,
                relative_path=artifact_path.relative_to(project.root).as_posix(),
                class_map=dataset.class_map,
                input_size=run.recipe.input_size,
                created_at=created_at,
            )
            validation_hashes = tuple(
                item.media_hash for item in dataset.items if item.split == "validation"
            )
            report = EvaluationReport(
                evaluation_id=_new_ulid(),
                artifact_id=artifact_id,
                dataset_version_id=dataset.dataset_version_id,
                validation_media_hashes=validation_hashes,
                metrics=result_metrics,
                errors=result_errors,
                created_at=created_at,
            )
            with project.db.transaction():
                project.model_artifacts.append(artifact)
                project.evaluations.append(report)
                append_training_event(
                    project,
                    training_run_id=run_id,
                    event_id=_new_ulid(),
                    status="succeeded",
                    at=created_at,
                    progress=1,
                    message="訓練完成，模型與驗證報告已封存",
                )
        except BaseException as exc:
            try:
                append_training_event(
                    project,
                    training_run_id=run_id,
                    event_id=_new_ulid(),
                    status="failed",
                    at=_now(),
                    message="本地訓練失敗",
                    technical_detail="".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )[-4096:],
                )
            except ConflictError:
                pass
            raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--parent-pid", type=int)
    args = parser.parse_args()
    run_worker(args.project, args.run, args.parent_pid)


if __name__ == "__main__":
    main()
