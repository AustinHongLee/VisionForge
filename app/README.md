# app/ — 本機服務與 Worker（FastAPI + 獨立程序，ADR-0002）

服務層：HTTP＋WebSocket 事件流；Worker：獨立 Python process（PR4 崩潰隔離）。

規則：可以 import `visionforge_core`；不得被 core import（D13）。

目前無內容——等規格票。
