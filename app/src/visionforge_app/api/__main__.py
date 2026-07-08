"""Sidecar 執行入口。

Electron 之後會 spawn 這個模組；本入口只綁 127.0.0.1，符合 ADR-0009 離線優先。
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from visionforge_core.storage import Project, create_project, open_project

from visionforge_app.api import create_app

_MARKER = "project.json"
_DEFAULT_PROJECT_ID = "00000000000000000000000009"
_DEFAULT_PORT = 8765


def _open_or_create_project(root: Path) -> Project:
    if (root / _MARKER).is_file():
        return open_project(root)
    return create_project(root, root.name or "VisionForge", _DEFAULT_PROJECT_ID)


def main() -> None:
    project_env = os.environ.get("VISIONFORGE_PROJECT")
    if not project_env:
        raise SystemExit("VISIONFORGE_PROJECT is required")
    project = _open_or_create_project(Path(project_env))
    port = int(os.environ.get("VISIONFORGE_API_PORT", str(_DEFAULT_PORT)))
    uvicorn.run(create_app(project), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
