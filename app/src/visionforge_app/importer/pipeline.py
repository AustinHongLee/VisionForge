"""匯入管線：解碼 → EXIF 正規化 → 內容雜湊 → 縮圖 → 落庫。

**本檔的簽名、型別與例外契約已由 Architect 凍結（票-0003【介面】）；
Builder 只實作本體，不得更動簽名。** 政策定案於 ADR-0006。
"""

from __future__ import annotations

from dataclasses import dataclass

from visionforge_core.contracts.media import MediaRecord, MediaSource
from visionforge_core.storage.project import Project

DEFAULT_THUMBNAIL_MAX_EDGE = 256


@dataclass(frozen=True)
class ImportOutcome:
    """匯入結果（非持久化的傳輸型別，屬服務層）。

    media_hash：入庫位元組的 SHA-256（＝ MediaRecord.media_hash，ADR-0006）。
    record：對應的媒體戶籍（既有或新建）。
    deduplicated：True 表示該內容早已在庫，本次為冪等命中、無新寫入。
    """

    media_hash: str
    record: MediaRecord
    deduplicated: bool


def import_media(
    project: Project,
    data: bytes,
    source: MediaSource,
    *,
    thumbnail_max_edge: int = DEFAULT_THUMBNAIL_MAX_EDGE,
) -> ImportOutcome:
    """把一份影像位元組匯入專案。政策凍結於 ADR-0006，重點：

    1. media_hash = sha256(實際入庫位元組) = project.blobs.put(...) 之回傳值。
    2. EXIF 正規化（Policy B）：Orientation 缺失或 =1 → 原始位元組原封入庫；
       Orientation 2..8 → Pillow ImageOps.exif_transpose 轉正、重編碼為同格式後
       入庫。兩者 exif_normalized 皆為 True。
    3. 影像庫釘 Pillow；格式限 MediaFormat 封閉集，其餘與多幀輸入結構化拒絕。
    4. 冪等：project.media 已含該 hash → 回傳既有 record（deduplicated=True），
       不重複 add、不重生縮圖。
    5. 失敗無副作用：解碼與格式驗證先行，通過後才寫 blob＋縮圖＋record。

    參數：
        project：目標專案（提供 .blobs／.media／.root，見 storage.project.Project）。
        data：原始影像位元組。
        source：血統來源，由呼叫端提供（見 contracts.media.MediaSource）。
        thumbnail_max_edge：縮圖最長邊像素（預設 256）。

    回傳：ImportOutcome(media_hash, record, deduplicated)。

    例外：
        UnsupportedMediaFormatError：格式不在封閉集。
        MultiFrameMediaError：多幀輸入。
        MediaDecodeError：無法解碼。
    """
    raise NotImplementedError("票-0003：由 Builder 實作；簽名與型別已凍結，不得更動")
