# VisionForge（開發代號：GoodYolo）

> **把大模型的理解力，鑄造成你自己的視覺能力。**
> 老師模型先看懂（zero-shot 草稿）→ 人審治理（血統／黃金集／閘門）→ 蒸餾成可部署的學生模型（YOLO 等）→ 接上應用。

## 文件

**一切從 [docs/README.md](docs/README.md) 開始**——那裡有效力層級、狀態板與全部文件的登記表。

最高效力文件：[VisionForge Constitution v1.0](docs/00-法規/VisionForge_Constitution_v1.0.md)（79 條）。
協作規範：[AI 分工協議](docs/00-法規/VisionForge_AI分工協議_v1.md)（Claude × Codex）。

## 目前狀態

| 階段 | 狀態 |
|---|---|
| 文件工程（R1 規劃 → R2 評審 → 憲法 → 分工協議 → 文件治理） | ✅ 完成 |
| ADR-0002 技術棧確認、Claim Schema 草案 | ⬜ 下一步（Claude） |
| repo 骨架、CI 守門（依賴方向 lint、core 禁 import） | ⬜ 排隊中（Claude） |
| 第一張 Codex 規格票（Provider adapter／匯入管線／GUI 殼） | ⬜ 等前兩項完成 |

## 給 AI Agent 的入場須知

1. 先讀 `docs/00-法規/` 全部內容（憲法 D20，無例外）。
2. 任何提交說明必須聲明觸及的憲法條文與合規性。
3. 🟨🟦⬛ 狀態的文件不得作為依據；分工協議的紅線由 CI 強制。
