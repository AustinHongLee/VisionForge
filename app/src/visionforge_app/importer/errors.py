"""匯入錯誤分類（凍結介面，票-0003）。

面向使用者的錯誤最終需雙層訊息（憲法 D14：人話＋技術詳情），該格式化
在 API/UI 邊界完成；本層只界定可被上層攔截的結構化例外型別。
"""

from __future__ import annotations


class MediaImportError(Exception):
    """匯入失敗基類。所有匯入錯誤皆繼承此類，供上層統一攔截。"""


class UnsupportedMediaFormatError(MediaImportError):
    """格式不在 MediaFormat 封閉集（jpeg/png/webp/bmp/tiff）。"""


class MultiFrameMediaError(MediaImportError):
    """多幀輸入（影片／動圖）——本票範圍外（F2 模態擴充留門，A10 不預建）。"""


class MediaDecodeError(MediaImportError):
    """位元組無法解碼為有效影像。"""
