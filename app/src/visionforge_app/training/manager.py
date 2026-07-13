"""訓練 child process 管理；模型運算不在 API sidecar 主程序內執行。"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from visionforge_core.contracts import TrainingRecipe, TrainingRun
from visionforge_core.storage import open_project
from visionforge_core.storage.errors import ConflictError

from visionforge_app.training.lifecycle import append_training_event, create_training_run


class TrainingManager:
    def __init__(
        self,
        project_root: Path,
        *,
        id_factory: Callable[[], str],
        spawn: Callable[..., subprocess.Popen] = subprocess.Popen,
    ) -> None:
        self._project_root = project_root
        self._id_factory = id_factory
        self._spawn = spawn
        self._processes: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def start(
        self,
        dataset_version_id: str,
        *,
        recipe: TrainingRecipe,
        retry_of: str | None = None,
    ) -> TrainingRun:
        run_id = self._id_factory()
        with open_project(self._project_root) as project:
            run = create_training_run(
                project,
                training_run_id=run_id,
                dataset_version_id=dataset_version_id,
                trainer_version="1.0.0",
                recipe=recipe,
                created_at=datetime.now(timezone.utc),
                queued_event_id=self._id_factory(),
                retry_of=retry_of,
            )
        command = [
            sys.executable,
            "-m",
            "visionforge_app.training.worker",
            "--project",
            str(self._project_root),
            "--run",
            run_id,
            "--parent-pid",
            str(os.getpid()),
        ]
        try:
            process = self._spawn(
                command,
                env=os.environ.copy(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except OSError as exc:
            with open_project(self._project_root) as project:
                append_training_event(
                    project,
                    training_run_id=run_id,
                    event_id=self._id_factory(),
                    status="failed",
                    at=datetime.now(timezone.utc),
                    message="無法啟動訓練程序",
                    technical_detail=str(exc),
                )
            raise
        with self._lock:
            self._processes[run_id] = process
        threading.Thread(target=self._reap, args=(run_id, process), daemon=True).start()
        return run

    def cancel(self, training_run_id: str) -> None:
        with self._lock:
            process = self._processes.get(training_run_id)
        with open_project(self._project_root) as project:
            latest = project.training_runs.latest_event(training_run_id)
            if latest.status not in {"queued", "running"}:
                raise ConflictError(f"TrainingRun 已終止於 {latest.status}")
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            append_training_event(
                project,
                training_run_id=training_run_id,
                event_id=self._id_factory(),
                status="cancelled",
                at=datetime.now(timezone.utc),
                progress=latest.progress,
                message="使用者已取消訓練",
            )

    def _reap(self, training_run_id: str, process: subprocess.Popen) -> None:
        process.wait()
        with self._lock:
            self._processes.pop(training_run_id, None)
