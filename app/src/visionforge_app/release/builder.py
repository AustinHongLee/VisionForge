"""把單一 ModelArtifact 封裝為不依賴 Studio／project.db 的可攜 Release。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from visionforge_core.contracts import CapabilityRelease
from visionforge_core.storage import Project

from visionforge_app.training.tiny_detector import load_and_predict


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def build_release(
    project: Project,
    *,
    artifact_id: str,
    release_id: str,
    created_at: datetime,
) -> CapabilityRelease:
    artifact = project.model_artifacts.get(artifact_id)
    artifact_path = (project.root / artifact.relative_path).resolve()
    if not artifact_path.is_relative_to(project.root.resolve()) or not artifact_path.is_file():
        raise ValueError("ModelArtifact 檔案不在專案內或已遺失")
    artifact_bytes = artifact_path.read_bytes()
    if _sha(artifact_bytes) != artifact.artifact_hash:
        raise ValueError("ModelArtifact 內容雜湊不符，拒絕發布")
    evaluation = project.evaluations.latest_for_artifact(artifact_id)
    if evaluation is None:
        raise ValueError("ModelArtifact 尚無 frozen validation EvaluationReport")
    dataset = project.dataset_versions.get(artifact.dataset_version_id)
    run = project.training_runs.get(artifact.training_run_id)
    task = project.tasks.get(artifact.task_id)
    latest = project.capability_releases.latest(artifact.task_id)
    version_number = 1 if latest is None else latest.version_number + 1

    release_root = project.root / "releases"
    release_root.mkdir(parents=True, exist_ok=True)
    archive_name = f"capability-v{version_number}-{release_id}.zip"
    final_archive = release_root / archive_name
    if final_archive.exists():
        raise ValueError(f"Release archive 已存在：{final_archive}")

    with tempfile.TemporaryDirectory(prefix=".release-", dir=release_root) as temp_name:
        staging = Path(temp_name) / "bundle"
        staging.mkdir()
        bundled_artifact = staging / "model" / artifact_path.name
        bundled_artifact.parent.mkdir()
        shutil.copyfile(artifact_path, bundled_artifact)

        validation_item = next(
            item for item in dataset.items if item.split == "validation"
        )
        validation_record = project.media.get(validation_item.media_hash)
        validation_blob = project.blobs.find(validation_item.media_hash)
        if validation_blob is None:
            raise ValueError("parity fixture 的 validation media blob 已遺失")
        extension = {
            "jpeg": ".jpg",
            "png": ".png",
            "webp": ".webp",
            "bmp": ".bmp",
            "tiff": ".tif",
        }[validation_record.format]
        parity_input = staging / "parity" / f"input{extension}"
        parity_input.parent.mkdir()
        shutil.copyfile(validation_blob, parity_input)

        if artifact_path.name.endswith(".fixture.json"):
            prediction_payload: list[dict] = []
        else:
            prediction_payload = [
                prediction.model_dump(mode="json")
                for prediction in load_and_predict(
                    artifact_path,
                    validation_blob.read_bytes(),
                    threshold=artifact.confidence_threshold,
                )
            ]
        parity_expected = {
            "schema_version": "1.0",
            "release_version": version_number,
            "predictions": prediction_payload,
        }
        _write_json(staging / "parity" / "expected.json", parity_expected)

        input_schema = _input_schema()
        output_schema = _output_schema()
        _write_json(staging / "schemas" / "input.schema.json", input_schema)
        _write_json(staging / "schemas" / "output.schema.json", output_schema)

        manifest = {
            "schema_version": "1.0",
            "release": {
                "release_id": release_id,
                "version_number": version_number,
                "name": task.name,
                "created_at": created_at.isoformat(),
            },
            "execution": {
                "artifact_path": bundled_artifact.relative_to(staging).as_posix(),
                "artifact_hash": artifact.artifact_hash,
                "input_size": artifact.input_size,
                "normalization": "RGB float32 / 255",
                "confidence_threshold": artifact.confidence_threshold,
                "nms_iou_threshold": 0.45,
                "input_schema": "schemas/input.schema.json",
                "output_schema": "schemas/output.schema.json",
            },
            "class_map": [entry.model_dump(mode="json") for entry in artifact.class_map],
            "provenance": {
                "dataset_version_id": dataset.dataset_version_id,
                "dataset_version_number": dataset.version_number,
                "training_run_id": run.training_run_id,
                "trainer_id": run.trainer_id,
                "trainer_version": run.trainer_version,
                "artifact_id": artifact.artifact_id,
                "evaluation_id": evaluation.evaluation_id,
            },
            "evaluation": {
                "metrics": [metric.model_dump(mode="json") for metric in evaluation.metrics],
                "validation_media_count": len(evaluation.validation_media_hashes),
                "recorded_error_count": len(evaluation.errors),
                "scope": "development evidence on a frozen validation snapshot",
            },
            "known_limitations": [
                "模型從使用者資料由零開始訓練，沒有外部預訓練知識。",
                "目前是 8x8 grid、每格最多 3 個物件的 First Forge detector。",
                "Evaluation 是開發證據，不是未知場景的品質保證。",
            ],
            "runtime": {
                "python": ">=3.12,<3.15",
                "requirements": "runner/requirements.lock",
                "runner": "runner/visionforge_runner.py",
            },
            "parity": {
                "input": parity_input.relative_to(staging).as_posix(),
                "expected": "parity/expected.json",
            },
        }
        manifest_bytes = _json_bytes(manifest)
        (staging / "manifest.json").write_bytes(manifest_bytes)
        (staging / "runner").mkdir()
        shutil.copyfile(
            Path(__file__).with_name("standalone_runner.py"),
            staging / "runner" / "visionforge_runner.py",
        )
        (staging / "runner" / "requirements.lock").write_text(
            _requirements_lock(), encoding="utf-8"
        )
        (staging / "README.md").write_text(
            _readme(parity_input.name), encoding="utf-8"
        )
        (staging / "THIRD_PARTY_LICENSES.md").write_text(
            _license_inventory(), encoding="utf-8"
        )

        temp_archive = Path(temp_name) / archive_name
        with zipfile.ZipFile(temp_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(staging).as_posix())
        os.replace(temp_archive, final_archive)

    archive_hash = _sha(final_archive.read_bytes())
    release = CapabilityRelease(
        release_id=release_id,
        version_number=version_number,
        task_id=artifact.task_id,
        artifact_ids=(artifact_id,),
        archive_hash=archive_hash,
        manifest_hash=_sha(manifest_bytes),
        relative_path=final_archive.relative_to(project.root).as_posix(),
        created_at=created_at,
        parent_ref=None if latest is None else latest.release_id,
    )
    try:
        project.capability_releases.append(release)
    except BaseException:
        final_archive.unlink(missing_ok=True)
        raise
    return release


def _requirements_lock() -> str:
    return (
        "--extra-index-url https://download.pytorch.org/whl/cpu\n"
        "numpy==2.3.5\n"
        "Pillow==12.2.0\n"
        "torch==2.9.1\n"
    )


def _readme(parity_name: str) -> str:
    return f"""# VisionForge CapabilityRelease

此資料夾不需要 VisionForge Studio 或 project.db。

```powershell
py -3.12 -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r runner\\requirements.lock
.venv\\Scripts\\python.exe runner\\visionforge_runner.py --release . --verify-parity
```

Parity 使用 `parity\\{parity_name}`。對自己的圖片執行時改用 `--input`；
輸出契約見 `schemas/output.schema.json`。
"""


def _license_inventory() -> str:
    return """# Third-party runtime inventory

- PyTorch 2.9.1 — BSD-3-Clause — https://github.com/pytorch/pytorch/blob/main/LICENSE
- NumPy — BSD-3-Clause — https://github.com/numpy/numpy/blob/main/LICENSE.txt
- Pillow — HPND — https://github.com/python-pillow/Pillow/blob/main/LICENSE

VisionForge Tiny Detector 沒有使用或散布任何第三方預訓練權重。
Release 內只含使用者資料訓練出的權重；runtime 套件由 requirements.lock 指示安裝，
不內嵌於此 zip。
"""


def _input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "VisionForge Capability Input",
        "type": "object",
        "additionalProperties": False,
        "required": ["image_path"],
        "properties": {"image_path": {"type": "string", "minLength": 1}},
    }


def _output_schema() -> dict:
    bbox = {
        "type": "object",
        "additionalProperties": False,
        "required": ["type", "x1", "y1", "x2", "y2"],
        "properties": {
            "type": {"const": "bbox"},
            "x1": {"type": "number", "minimum": 0, "maximum": 1},
            "y1": {"type": "number", "minimum": 0, "maximum": 1},
            "x2": {"type": "number", "minimum": 0, "maximum": 1},
            "y2": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "VisionForge Capability Output",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "release_version", "predictions"],
        "properties": {
            "schema_version": {"const": "1.0"},
            "release_version": {"type": "integer", "minimum": 1},
            "predictions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["concept_id", "display_name", "bbox", "confidence"],
                    "properties": {
                        "concept_id": {"type": "string"},
                        "display_name": {"type": "string"},
                        "bbox": bbox,
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
        },
    }
