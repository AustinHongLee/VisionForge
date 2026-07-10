# VisionForge（開發代號：GoodYolo）

> **把大模型的理解力，鑄造成你自己的視覺能力。**
> 老師模型先看懂（zero-shot 草稿）→ 人審治理（血統／黃金集／閘門）→ 蒸餾成可部署的學生模型（YOLO 等）→ 接上應用。

## 文件

**一切從 [docs/README.md](docs/README.md) 開始**——那裡有效力層級、狀態板與全部文件的登記表。

最高效力文件：[VisionForge Constitution v1.0](docs/00-法規/VisionForge_Constitution_v1.0.md)（79 條）。
協作規範：[AI 分工協議](docs/00-法規/VisionForge_AI分工協議_v1.md)（Architect × Builder）。
接任者必讀：[交接手冊](docs/交接手冊.md)。

## 目前狀態

| 階段 | 狀態 |
|---|---|
| 文件工程（R1 → R2 → 憲法 → 分工協議 → 文件治理） | ✅ 完成 |
| 契約層：Claim Schema（ADR-0003）＋帳本 Schema（ADR-0004） | ✅ 完成 |
| 儲存層（ADR-0005，core 49 測試綠、ruff 乾淨） | ✅ 完成 |
| UI 殼＋安全加固（票-0001/0002，已合併） | ✅ 完成 |
| 架構代理交接（Fable 5 → Opus 4.8，見交接手冊） | ✅ 完成 |
| **M0 資料工房核心迴圈**（匯入→看懂→整理審核→校準→匯出 YOLO/COCO） | ✅ 完整可出貨（票-0003~0016，ADR-0006~0010；core 89/app 59+/ui 25 測試綠） |
| 契約→JSON Schema→TS 生成＋雙向漂移守門（票-0004） | ✅ 已合併 |
| 試鏡與校準引擎（kernel，統計不外包，R2 9.2） | ✅ 已合併（ad3914c，PR #4） |
| **第一個真實老師**（OpenAI 雲端 VLM，ADR-0008） | ✅ 已合併（2f52b2e，PR #24）；實機對真圖畫框成功 |
| 一鍵啟動器 `start-visionforge.bat` | ✅ 已納管（6efd815，PR #25） |

## 給 AI Agent 的入場須知

1. 先讀 `docs/00-法規/` 全部內容（憲法 D20，無例外），接任 Architect 者再讀 `docs/交接手冊.md`。
2. 任何提交說明必須聲明觸及的憲法條文與合規性。
3. 🟨🟦⬛ 狀態的文件不得作為依據；分工協議的紅線由 CI 強制。
