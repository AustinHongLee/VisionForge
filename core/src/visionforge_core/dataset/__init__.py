"""Dataset 版本化（ADR-0010 收尾，D5）：版本＝清單。"""

from visionforge_core.dataset.teaching import (
    DatasetNotReadyError,
    freeze_dataset,
    inspect_readiness,
)
from visionforge_core.dataset.versions import build_version

__all__ = ["DatasetNotReadyError", "build_version", "freeze_dataset", "inspect_readiness"]
