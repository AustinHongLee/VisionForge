"""VisionForge 核心套件（確定性保留區）。

憲法約束（節錄，全文見 docs/00-法規/）：
- D1  ：本套件不得 import 任何 Provider SDK（CI 以 scripts/check_forbidden_imports.py 強制）。
- D11 ：LLM 與一切機率性元件不得進入本套件。
- A3  ：依賴方向 介面層→服務→Orchestrator→Provider；core 位於底層，不得反向依賴。
"""

__version__ = "0.1.0"
