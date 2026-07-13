"""本地學生模型訓練：child process 管理與生命週期。"""

from visionforge_app.training.lifecycle import (
    append_training_event,
    create_training_run,
    interrupt_orphaned_runs,
)
from visionforge_app.training.manager import TrainingManager

__all__ = [
    "TrainingManager",
    "append_training_event",
    "create_training_run",
    "interrupt_orphaned_runs",
]
