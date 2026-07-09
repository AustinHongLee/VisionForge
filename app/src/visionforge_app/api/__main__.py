"""Sidecar 執行入口。

Electron 之後會 spawn 這個模組；本入口只綁 127.0.0.1，符合 ADR-0009 離線優先。
"""

from __future__ import annotations

import ctypes
import os
import threading
import time
from pathlib import Path

import uvicorn
from visionforge_core.storage import Project, create_project, open_project

from visionforge_app.api import create_app

_MARKER = "project.json"
_DEFAULT_PROJECT_ID = "00000000000000000000000009"
_DEFAULT_PORT = 8765
_PARENT_PID_ENV = "VISIONFORGE_PARENT_PID"


def _open_or_create_project(root: Path) -> Project:
    if (root / _MARKER).is_file():
        return open_project(root)
    return create_project(root, root.name or "VisionForge", _DEFAULT_PROJECT_ID)


def _start_parent_watchdog() -> None:
    parent_pid = _parent_pid()
    if parent_pid is None:
        return

    thread = threading.Thread(target=_wait_for_parent_exit, args=(parent_pid,), daemon=True)
    thread.start()


def _parent_pid() -> int | None:
    value = os.environ.get(_PARENT_PID_ENV)
    if not value:
        return None
    try:
        pid = int(value)
    except ValueError:
        return None
    return pid if pid > 0 else None


def _wait_for_parent_exit(parent_pid: int) -> None:
    if os.name == "nt":
        _wait_for_windows_process_exit(parent_pid)
    else:
        _wait_for_posix_process_exit(parent_pid)
    os._exit(0)


def _wait_for_windows_process_exit(parent_pid: int) -> None:
    synchronize = 0x00100000
    infinite = 0xFFFFFFFF
    handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, parent_pid)
    if not handle:
        return
    try:
        ctypes.windll.kernel32.WaitForSingleObject(handle, infinite)
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _wait_for_posix_process_exit(parent_pid: int) -> None:
    while True:
        try:
            os.kill(parent_pid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            pass
        time.sleep(1)


def main() -> None:
    _start_parent_watchdog()
    project_env = os.environ.get("VISIONFORGE_PROJECT")
    if not project_env:
        raise SystemExit("VISIONFORGE_PROJECT is required")
    project = _open_or_create_project(Path(project_env))
    port = int(os.environ.get("VISIONFORGE_API_PORT", str(_DEFAULT_PORT)))
    uvicorn.run(create_app(project), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
