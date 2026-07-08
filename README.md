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
| 票-0003 匯入管線（import_media，ADR-0006） | ✅ 已合併（4ab83f7，pytest 66 綠） |
| 票-0004 契約 Schema 匯出＋TS codegen（L2） | ✅ 已合併（7ef91be，審查通過 Blocking 0） |
| 票-0005/0006 批次 L0（app 服務＋ui 殼導航/匯入頁） | ✅ 已合併（728f03d／f360caf，票-0006 抽審通過） |
| 試鏡與校準引擎（kernel，統計不外包，R2 9.2） | 🟨 ADR-0007 已提案，待採納後由 Architect 實作於 core |

## 給 AI Agent 的入場須知

1. 先讀 `docs/00-法規/` 全部內容（憲法 D20，無例外），接任 Architect 者再讀 `docs/交接手冊.md`。
2. 任何提交說明必須聲明觸及的憲法條文與合規性。
3. 🟨🟦⬛ 狀態的文件不得作為依據；分工協議的紅線由 CI 強制。
