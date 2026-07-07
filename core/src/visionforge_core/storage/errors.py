"""儲存層錯誤（D14：服務層負責把這些翻譯成人話＋技術詳情雙層）。"""

from __future__ import annotations


class StorageError(Exception):
    """儲存層錯誤基底。"""


class ConflictError(StorageError):
    """append-only 帳本拒絕重複身分（同 ID 再寫入＝程式缺陷，不是可重試情況）。"""


class NotFoundError(StorageError):
    """指名讀取查無記錄。"""


class NotAProjectError(StorageError):
    """目標資料夾不是 VisionForge 專案（缺 project.json 標記）。"""


class ProjectSchemaTooNewError(StorageError):
    """專案由較新版本的應用程式建立（D9：舊程式必須明確拒絕，不得靜默損毀）。"""
