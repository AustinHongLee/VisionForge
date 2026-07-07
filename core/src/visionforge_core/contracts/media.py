"""媒體記錄契約（ADR-0005）。

媒體本體＝內容雜湊定址檔案（R1 §5.4）；本記錄是它的戶籍資料。
exif_normalized 對應 R1 §7.1：匯入時像素已轉正、方向標記已剝除——
標註框整批錯位的經典災難從源頭消滅。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from visionforge_core.contracts.claims import (
    SCHEMA_VERSION,
    Sha256,
    StrictModel,
    _require_tz,
)

# 封閉集合：新格式＝修訂本型別（確定性優於寬容，A5）。
MediaFormat = Literal["jpeg", "png", "webp", "bmp", "tiff"]

SourceKind = Literal[
    "file",
    "folder",
    "clipboard",
    "video_frame",
    "pdf_page",
    "camera",
    "screen",
    "url",
]


class MediaSource(StrictModel):
    """來源留痕：血統從匯入那一刻開始。"""

    kind: SourceKind
    detail: str = Field(default="", max_length=1024)  # 原路徑／影片時間點／頁碼…


class MediaRecord(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    media_hash: Sha256
    width_px: int = Field(gt=0, le=1_000_000)
    height_px: int = Field(gt=0, le=1_000_000)
    format: MediaFormat
    byte_size: int = Field(gt=0)
    imported_at: datetime
    source: MediaSource
    exif_normalized: bool

    _tz = field_validator("imported_at")(_require_tz)
