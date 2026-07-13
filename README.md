# VisionForge（開發代號：GoodYolo）

> **把大模型的理解力，鑄造成你自己的視覺能力。**
> 老師模型先看懂（zero-shot 草稿）→ 人審治理（血統／黃金集／閘門）→ 蒸餾成可部署的學生模型（YOLO 等）→ 接上應用。

> **2026-07-13 現況校正：**媒體、Teacher、儲存與桌面殼已有基座，但 UI 教學迴圈尚未接通，Student 訓練、評估、應用與可安裝交付尚未完成。現行施工入口是 [VisionForge 重構開工書 R3](docs/03-規劃/VisionForge_重構開工書_R3.md)。

## 文件

**一切從 [docs/README.md](docs/README.md) 開始**——那裡有效力層級、狀態板與全部文件的登記表。

現行產品與施工基準：[VisionForge 重構開工書 R3](docs/03-規劃/VisionForge_重構開工書_R3.md)。

歷史資料與安全原則參考：[VisionForge Constitution v1.0](docs/00-法規/VisionForge_Constitution_v1.0.md)（部分由 R3 延續）。
已歸檔協作方式：[AI 分工協議](docs/00-法規/VisionForge_AI分工協議_v1.md)（已由 R3 §9 取代）。

## 目前狀態

| 階段 | 狀態 |
|---|---|
| 文件工程（R1 → R2 → 憲法 → 分工協議 → 文件治理） | ✅ 完成 |
| 契約層：Claim Schema（ADR-0003）＋帳本 Schema（ADR-0004） | ✅ 完成 |
| 儲存層（ADR-0005，core 49 測試綠、ruff 乾淨） | ✅ 完成 |
| UI 殼＋安全加固（票-0001/0002，已合併） | ✅ 完成 |
| 架構代理交接（Fable 5 → Opus 4.8，見交接手冊） | ✅ 完成 |
| **既有 M0 後端零件**（匯入、Teacher、審核 API、Dataset 匯出） | ⚠️ 有基座，但 UI 的看懂使用 `/infer`、整理依賴 `/process`，主迴圈未接通；不可宣稱可出貨 |
| 契約→JSON Schema→TS 生成＋雙向漂移守門（票-0004） | ✅ 已合併 |
| 試鏡與校準引擎（kernel，統計不外包，R2 9.2） | ✅ 已合併（ad3914c，PR #4） |
| **第一個真實老師**（OpenAI 雲端 VLM，ADR-0008） | ✅ 已合併（2f52b2e，PR #24）；實機對真圖畫框成功 |
| 開發啟動器 `start-visionforge.bat` | ✅ 已納管（6efd815，PR #25）；不是可散布桌面 installer |
| **Student 訓練、評估、新圖應用、CapabilityRelease** | ❌ 尚未實作；依重構開工書 Slice 2～4 施工 |

## 給 AI Agent 的入場須知

1. 先讀 [VisionForge 重構開工書 R3](docs/03-規劃/VisionForge_重構開工書_R3.md)、README 與當期相關程式。
2. 以一位 Lead 負責垂直成果；Builders 可跨模組，高風險變更才做獨立審查。
3. 使用者提供方向與底線，不擔任 Schema、ADR、PR 或 Agent 分工的技術審核者。
