"""內容雜湊定址的媒體檔案庫（R1 §5.4）。

同一張圖不論匯入幾次只存一份——去重不是功能，是儲存格式的物理性質。
寫入採 temp+rename 原子操作：不存在「寫到一半的 blob」這種狀態。
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

_EXT: dict[str, str] = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "bmp": ".bmp",
    "tiff": ".tif",
}


class MediaBlobStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, media_format: str) -> str:
        """寫入位元組，回傳 sha256。同內容重複寫入是 no-op（天然去重）。"""
        if media_format not in _EXT:
            raise ValueError(f"未支援的媒體格式「{media_format}」（MediaFormat 封閉集合）")
        digest = hashlib.sha256(data).hexdigest()
        subdir = self._root / digest[:2]
        final = subdir / f"{digest}{_EXT[media_format]}"
        if final.exists():
            return digest
        subdir.mkdir(parents=True, exist_ok=True)
        tmp = subdir / f"{digest}.{os.getpid()}.tmp"
        tmp.write_bytes(data)
        os.replace(tmp, final)  # 原子：blob 只有「不存在」與「完整」兩種狀態
        return digest

    def find(self, media_hash: str) -> Path | None:
        subdir = self._root / media_hash[:2]
        if not subdir.is_dir():
            return None
        for path in subdir.glob(f"{media_hash}.*"):
            if not path.name.endswith(".tmp"):
                return path
        return None

    def exists(self, media_hash: str) -> bool:
        return self.find(media_hash) is not None
