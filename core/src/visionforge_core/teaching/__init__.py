"""R3 教學工作區：Task、Concept、Coverage 與 Annotation Revision。"""

from visionforge_core.teaching.service import (
    add_annotation,
    add_concept,
    add_task,
    assign_media,
    edit_annotation,
    get_coverage,
    retract_annotation,
    set_coverage,
)

__all__ = [
    "add_annotation",
    "add_concept",
    "add_task",
    "assign_media",
    "edit_annotation",
    "get_coverage",
    "retract_annotation",
    "set_coverage",
]
