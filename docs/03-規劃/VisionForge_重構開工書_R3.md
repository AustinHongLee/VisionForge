# VisionForge 重構開工書 R3

> **施工狀態（2026-07-13）：** Slice 0～4 的程式垂直路徑已落地；自動化證據、限制與下一步以 [EXECUTION.md](EXECUTION.md) 為準。R3 保持為需求基準，不在此回填測試數字。

| 項目 | 內容 |
|---|---|
| 日期 | 2026-07-13 |
| 性質 | 可直接施工的產品與技術重構基準 |
| 現行效力 | 依 Owner 本次方向立即生效；舊產品規劃與 Agent 分工規則不再阻擋施工，歷史文件整理可平行進行 |
| 取代範圍 | 取代 GoodYolo R1／R2 與舊 AI 分工協議，作為目前產品與 Agent 施工依據；舊憲法僅保留本文重申的資料與安全原則 |
| 不做的事 | 不建立新憲法、不逐項模擬企業流程、不先設計完整平台 |
| 第一成果 | 使用者能教 A、訓練本地模型、用新圖試跑，再安全加入 B |
| First Forge 範圍 | Slice 0～4；Slice 5 工程圖複合能力不屬於本輪交付 |

> **一句話定位：VisionForge 是通用的視覺能力鑄造工具。它讓大型通用模型先提出草稿，使用者透過修正傳授自己的定義，再把確認過的知識訓練成可驗證、可攜、可直接使用的專用視覺模型或能力交付物。**

這裡「通用」的是**鑄造流程**，不是企圖訓練一個什麼都懂的單一模型。

---

## 0. 本次重構的判決

### 0.1 產品沒有改成工程圖工具

VisionForge 仍是通用產品。工程圖、遊戲畫面、工具、零件、缺陷、動物或其他特殊物件，都是它可承載的領域。

工程圖是高難度壓力測試，不是核心資料模型的預設。工程圖特有的 BOM、ISO 區域、Tag、管線與拓撲，未來應住在 Engineering Drawing Domain Pack，不得硬編碼進通用 Core。

### 0.2 訓練不是品牌，但必須成為完整旅程

VisionForge 不以 YOLO 或任何具名模型定義自己；但「把使用者確認過的知識鑄造成能拿走的專用模型」是核心承諾，不可再停在資料匯出。

完整旅程是：

~~~text
定義想教的能力
→ 老師提出草稿
→ 使用者修正
→ VisionForge 檢查資料是否足以訓練
→ 鑄造學生模型
→ 用未見資料驗證
→ 立即試用
→ 匯出可執行能力
→ 實際錯誤回流
~~~

### 0.3 複雜能力可以由多模型組成，但現在不先蓋通用編排平台

- 簡單能力可以是一個多類別偵測模型。
- 複雜能力可以是多個模型、規則與前後處理組成的 Capability Release。
- VisionForge Studio 負責建立、訓練、驗證與封裝能力。
- 第一個 Release 只需附最小 runner；出現第二個真實消費者後，才抽出獨立 VisionForge Runtime。
- 領域特有的分派順序屬於 Domain Pack 或該 Release，不屬於 VisionForge Core。
- 在第一個單模型能力尚未真正匯出使用前，不做獨立 Runtime 平台、Node Editor、通用 DAG 或分散式排程。

### 0.4 使用者不是技術審核者

使用者的角色是 **Direction Setter**：

- 提供想解決的問題、使用情境與不能接受的結果。
- 判斷產品體驗是否符合原意。
- 不負責批准 Schema、ADR、PR 或模型分工。

主責 Agent 對設計、施工、整合與驗證負責；高風險變更由獨立 Reviewer 挑戰，不把技術裁決交還使用者。

---

## 1. 產品承諾與邊界

### 1.1 使用者買到什麼

使用者不是來買一個權重檔，也不是來學機器學習。他想得到：

1. 一個能按照自己定義辨識目標的視覺能力。
2. 一份知道來源、能持續修正的資料資產。
3. 一份看得懂的品質證據。
4. 一個可以在其他程式或設備中直接使用的交付物。

### 1.2 VisionForge 必須隱藏什麼

一般使用者不應被迫理解：

- Provider、backbone、epoch、NMS、mAP 的原始術語。
- Dataset manifest、Schema migration 或模型路由。
- 單模型與多模型的內部部署細節。

這些資訊可以展開查看，但預設介面只回答：

- 現在在教什麼？
- 還缺什麼資料？
- 模型學會了嗎？
- 它在哪些情況會失敗？
- 下一步應該做什麼？
- 要怎麼拿去使用？

### 1.3 近期明確非目標

以下不是錯誤方向，但在第一條完整能力尚未交付前不得進入主線：

- 完整工程圖 BOM／OCR／管線／拓撲判讀。
- 任意節點式 Pipeline Editor。
- 多 Provider 自動表決與成本最佳化。
- Plugin Marketplace。
- 多人協作與權限系統。
- 雲端訓練、多 GPU 叢集。
- 可散布的 VisionForge Studio 桌面 installer；本輪仍用文件化 dev launcher。
- 通用工作流排程平台。
- 預測所有未來 Vision Task 的完美抽象。

### 1.4 First Forge 的固定範圍

First Forge 是本輪完整重構交付，不是其中任一小階段的別名：

| 面向 | 本輪裁定 |
|---|---|
| 輸入 | 本機圖片；不含 PDF、影片與攝影機 |
| Task | object detection |
| Project | 一個 Project 直接代表一個能力 |
| Teacher | 一個真實 Teacher Adapter；fixture 只供明示測試 |
| Student | 一個本地 Trainer Adapter |
| 使用者 | Windows、本機、單人 |
| 完成線 | Slice 0～4 全部驗收：教 A、訓練、驗證、試跑、匯出 Release v1、安全加入 B 並發布 v2 |
| Studio 交付 | 本輪使用文件化 repo／dev launcher；可散布桌面 installer 另立後續交付線 |
| 本輪之外 | Slice 5、多模型 Runtime、工程圖 Domain Pack、通用 DAG |

---

## 2. 使用者視角的核心資料流

~~~mermaid
flowchart TD
    A["建立視覺能力<br/>例如：工具辨識"] --> B["告訴 VisionForge<br/>先學 A：扳手"]
    B --> C["匯入多張圖片"]
    C --> D["老師提出草稿<br/>框、類別或其他結構"]
    D --> E["使用者修正<br/>移動、縮放、刪除、補漏、確認不存在"]
    E --> F["VisionForge 檢查覆蓋與多樣性"]
    F --> G{"足以進入鑄造？"}
    G -->|"否"| H["指出缺少的方向、場景、大小或負樣本"]
    H --> D
    G -->|"是"| I["鎖定 Dataset Version"]
    I --> J["訓練本地學生模型"]
    J --> K["用未參與訓練的資料驗證"]
    K --> L{"使用者接受目前品質？"}
    L -->|"否"| M["顯示漏判、誤判、混淆與框不準案例"]
    M --> E
    L -->|"是"| N["立即用新圖片試跑"]
    N --> O["匯出 CapabilityRelease"]
    O --> P["其他程式、遊戲、工具或領域系統使用"]
    P --> Q["現場錯誤回流"]
    Q --> E
~~~

### 2.1 從 A 增加 B

~~~mermaid
flowchart TD
    A["既有能力已會 A"] --> B["使用者新增 B"]
    B --> C["VisionForge 提出組合建議"]
    C --> D{"B 應放在哪裡？"}
    D -->|"同一輸入、同時辨識、同一輸出型態"| E["加入同一 Task 的多類別模型"]
    D -->|"同一能力、不同模型責任"| F["在同一 Project 建立另一個 Task"]
    D -->|"用途與部署完全不同"| G["建立另一個 Project／能力"]
    E --> H["舊圖片對 B 全部標成未檢查"]
    F --> H
    G --> I["建立獨立資料範圍"]
    H --> J["使用者選定批次<br/>老師重掃舊圖片"]
    I --> J
    J --> K["使用者確認 B 的有、無與漏標"]
    K --> L["建立新 DatasetVersion<br/>與新的 ModelArtifact 候選"]
    L --> M["舊 CapabilityRelease 與資料版本保持可用"]
~~~

VisionForge 可以推薦組合方式，但不得默默替使用者混合任務或資料。

---

## 3. 資料真相：先解決 A／B 污染問題

### 3.1 沒有框，不等於不存在

每張媒體對每個 Task／Concept 必須有明確 Coverage：

| Coverage | 意義 | 可否納入該版本訓練 |
|---|---|---|
| unverified | 尚未檢查，不知道有沒有 | 不可 |
| verified_complete | 已檢查且所有可見實例均完成標註 | 可，作為含正例的完整標註圖 |
| verified_absent | 已檢查並確認不存在 | 可，作為整圖負例 |

例：

| 圖片 | A：扳手 | B：鉗子 |
|---|---|---|
| image-001 | verified_complete | unverified |
| image-002 | verified_absent | verified_complete |
| image-003 | verified_complete | verified_absent |

Coverage 的唯一鍵是 `(task_id, media_hash, concept_id)`。沒有 Coverage row 的唯一語意就是 `unverified`；新增 Task、Concept、Media 或舊資料 migration 都遵守這個預設。新增 B 時，舊圖片對 B 一律從 `unverified` 開始。未檢查的 B 不得因為「沒有 B 的框」而被當成背景。

必須由測試守住：

- `verified_complete` 至少有一個該 Concept 的有效 Label。
- `verified_absent` 不得有該 Concept 的有效 Label。
- 拒絕老師的一個 Claim，不等於確認整張圖不存在該 Concept。
- 批准或新增一個 Label 只證明「至少有一個實例」，不會自動升為 `verified_complete`；只有明示的「完成此圖此概念檢查」操作可以升級。
- 新增、刪除或修改 Label 若使既有確認不再成立，Coverage 必須退回 `unverified`，或要求使用者重新確認。
- 一張圖只有在該 DatasetVersion **選定的 Concept set** 全部已驗證時，才能進入版本；未來新增但未被此版選定的 Concept 不得反向阻擋舊任務。
- v3 的既有 positive Label 只保留標註，不足以證明已找齊全部實例，因此 migration 後 Coverage 仍是 `unverified`。只有無衝突且經人工確認的 legacy whole-image absence 可轉成 `verified_absent`。

### 3.2 老師輸出永遠是建議，人工確認才是訓練事實

保留現有 Claim／Label 的核心精神，但修正一項過度僵化：

- 老師提出的框是 Claim。
- 使用者批准或修改後形成具穩定 `annotation_id` 的 Label revision。
- 老師漏掉的物件，使用者必須能直接補一個 Label。
- Label 的 provenance 應區分 `human_created`、`teacher_approved`、`teacher_edited`、`imported`。
- 邏輯欄位 `source_claim_ref` 可以為空；不能為了滿足舊 Schema 而虛構一個「人工 Provider Claim」。
- 修改會追加 replacement revision，刪除會追加 tombstone／retraction；DatasetVersion 只凍結當下 effective revision ID，不能把舊框和新框一起撈入。
- Claim 與 Label 都必須直接或經 server-owned 關係唯一解析到 `project_id`、`task_id`、`concept_id`；人工新增時由當前 Task／Concept context 寫入並由 server 驗證。

整圖不存在的唯一訓練真相是 Coverage 的 `verified_absent`。新 Label 只表示可定位的正例；Teacher 可以提出 whole-image absence Claim，但人工確認後寫入 Coverage。Legacy absence Label migration 後退出 active label set，避免兩套 absence 真相並存。

這項裁定取代舊 Constitution 對 Label 出生路徑的過度限定。真正不可退讓的規則是「只有經人工確認的資料才能成為訓練事實」，而不是「每個 Label 必須先存在一個機器 Claim」。

### 3.3 最小領域模型

~~~text
Project（第一版一個 Project 就是一個 Capability）
├─ MediaAsset
├─ Task
│  ├─ Concept
│  ├─ Coverage
│  ├─ Claim
│  ├─ Label
│  ├─ DatasetVersion
│  ├─ TrainingRun
│  ├─ ModelArtifact
│  └─ EvaluationReport
├─ CapabilityRelease
└─ ProjectSettings
~~~

#### Project

一個自包含的能力工作空間，保存媒體、教學目標、資料版本、模型與設定。例如「工具辨識」或「ISO 工程圖判讀」。第一版不另加 Workspace → Capability 層；等同一安裝真的需要管理多個能力時，再由多個 Project 組成 Workspace。

#### Task

一個可獨立訓練或執行的目標，例如 detect、classify、ocr、layout、pipe_trace。第一階段只真正實作 detect。

#### Concept

第一版是 Task-scoped class，不做多對多 `TaskConcept`。使用者要教的穩定概念 A、B 各有不可變 ID；顯示名稱可以修改，內部身分不可因改名而變更。

#### DatasetVersion

必須綁定：

- Task。
- Concept set、固定 class map 與版本。
- Media／Label 快照。
- Coverage 完整性。
- train／validation split 與 source group。
- 產生時間與 parent version。

不得再以「專案全部 Label」建立一個沒有 Task 範圍的全域 Dataset。同一來源的切片或變體必須以明示的 source group 一起切分；First Forge 只守內容 hash 與明示分組，不承諾自動找出所有近重複。

DatasetVersion 是不可變快照。Freeze 操作只建立版本；YOLO／COCO Exporter 只能讀取已存在的版本，不得在匯出時偷偷建立另一版。

#### TrainingRun

綁定單一 DatasetVersion、訓練配方、執行環境、seed 與狀態。每次嘗試不可覆寫；失敗、取消與重試都是一等狀態。

#### ModelArtifact

以 `artifact_id`／內容雜湊識別不可變產物，保存模型檔、類別映射、前後處理、來源 Dataset 與 TrainingRun。每次成功訓練產生新 Artifact，不存在可被覆寫的 Model Version。

#### EvaluationReport

保存 frozen validation snapshot 上的結果與錯誤案例。報告必須可回到原圖與對應 Label；它是開發證據，不冒充最終生產品質認證。

#### CapabilityRelease

使用者看見的能力版本，例如 v1、v2。它引用一個或多個 ModelArtifact、固定 manifest 與最小執行範例。第一版只有一個 Artifact；只有真實複合案例出現後，Release 才承載多模型與規則，不為未來先包一層通用 DAG。

版本語意固定如下：TrainingRun 是一次 attempt ID、ModelArtifact 是不可變內容、只有 CapabilityRelease 對使用者呈現 v1／v2。UI 若顯示「模型第 2 版」，也只能是 Task-scoped 顯示別名，不得建立另一套可變版本實體。

### 3.4 Readiness 與品質裁決

「可以開始訓練」拆成兩層，避免先開發一套虛假的資料智慧評分器：

- **硬性阻擋**：幾何與 class 合法、版本選定 Concepts 無 `unverified`、train／validation 都有符合 Trainer 最低要求且來自足夠獨立 source group 的素材、沒有 split 洩漏。
- **軟性警告**：樣本偏少、方向或場景單一、物件尺寸集中、類別失衡。First Forge 只用可解釋規則顯示警告，使用者可選擇繼續。
- **品質是否可用**：VisionForge 顯示 validation 證據、錯誤案例與已知限制，由專案目標或使用者判斷；不得由一個未知門檻替使用者宣稱「已學會」。

若 validation item 被回流成後續訓練資料，下一個 DatasetVersion 必須將它從 validation 除役並補入新的 unseen sample。舊 EvaluationReport 永遠保留為歷史，不得繼續代表目前品質。

---

## 4. 產品與執行邊界

~~~mermaid
flowchart LR
    U["使用者"] --> S["VisionForge Studio"]
    S --> C["資產與版本核心"]
    S --> T["Teacher Adapter"]
    S --> R["Trainer Adapter"]
    T --> C
    R --> M["Model Artifact"]
    C --> R
    M --> E["Evaluation"]
    E --> S
    M --> P["Capability Release"]
    P --> V["最小 Runner<br/>第二個消費者出現後才抽 Runtime"]
    V --> A["使用者應用程式"]
~~~

### 4.1 VisionForge Studio 負責

- 建立／開啟代表一個能力的 Project。
- 管理媒體、Concept、Coverage、Claim 與 Label。
- 呼叫老師產生持久化草稿。
- 提供修框、補框、刪框、改類別與確認不存在的 UI。
- 建立 DatasetVersion。
- 啟動、監看、取消與重試訓練。
- 顯示 Evaluation 與錯誤畫廊。
- 試跑 ModelArtifact。
- 匯出可使用的能力。

### 4.2 Release 執行層負責

- 載入 CapabilityRelease 及其 ModelArtifact。
- 執行前處理、推論與後處理。
- 未來對多模型 Release 依 manifest 執行固定流程。
- 回傳版本化、結構化結果。

第一版只交付能驗證 Release 的最小 runner，不先建立一套 Runtime 產品。當第二個真實消費者證明共用需求後，才抽成 VisionForge Runtime。它不負責訓練、資料治理、企業工作流或領域業務處置。

### 4.3 Domain Pack 負責

工程圖等領域特有內容應由 Pack 持有：

- Editor／Task template、node adapter 與 pipeline blueprint。
- 詞彙與公司／領域 Profile。
- OCR、BOM、管線、關聯等領域節點與 optional base model。
- 領域規則與輸出組合。

精確的 trained ModelArtifact refs 與 release execution manifest 永遠屬於 CapabilityRelease，不屬於 Domain Pack。VisionForge Core 只認識 Task、Artifact、輸入、輸出與版本，不認識 Valve 或 BOM。

---

## 5. 目前程式的誠實盤點

以下以 2026-07-13 main 分支實際程式為準，不採信舊票面狀態。

| 能力 | 現況 | 判決 |
|---|---|---|
| Electron／React 安全殼 | 已存在，含 sidecar 生命週期與基本 CSP | 保留 |
| 圖片匯入、正規化、內容雜湊、縮圖 | 後端與 UI 已接通 | 保留 |
| OpenAI／fixture 老師 | 可產生 BBox Claim | 保留為第一個 Teacher，介面仍 provisional |
| Provider fallback | 設定缺失或無效時可能靜默落到不看圖片的 fixture 假框 | Fixture 限明示 Developer Mode；正式模式顯示 Provider 並清楚失敗 |
| 看懂站 | 呼叫 /infer，只預覽、不持久化 | 必須改為持久化教學流程 |
| /process | 後端可入帳並存 Run／Claim，但 UI 完全沒有呼叫 | 接回使用者主線 |
| 整理站 | 可列出持久化待審 Claim 並批准／否決 | 目前與看懂站斷線 |
| 修正標註 | 後端 approve 可接收修改，但 UI 不能移框、縮放、補框或改類別 | 第一階段必做 |
| 人工新增漏標 | 現有 Label 強制 claim_ref，無自然路徑 | 修改 Schema 與審核服務 |
| Claim 身分 | fixture 與 OpenAI 產生的 claim_id 未納入 media／run，跨圖片或重跑可能碰撞主鍵 | 新資料改由服務層配置 run-scoped ID；舊 ID 原樣保留 |
| 寫入一致性 | Run＋Claims 已同交易；但 Decision→Cost→Run→Outcome、Label→ReviewEvent 仍分次提交，部分 API 又接受 client 傳入關聯鍵 | 只修真正的跨 repository 邊界，並由服務端解析關聯 |
| 終局審核 | 同一 Claim 可重複 approve，可能產生多份有效 Label | 只允許 pending 終局一次；retry idempotent 或回 409 |
| 框座標 | 圖片使用 contain／cover，框卻相對整個容器定位 | 畫布以實際 rendered image rectangle 換算 |
| A／B 教學目標 | 只有自由文字 Concept；沒有 Task 與穩定 Concept membership | 新增最小模型 |
| Coverage | 不存在 | 新增三態 Coverage |
| DatasetVersion | 後端把專案全部 Label 收成全域版本 | 改為 Task／Concept scoped |
| YOLO／COCO 匯出 | 後端存在，UI 沒入口；匯出動作同時建立 DatasetVersion | 拆成「凍結版本」與「由既有版本匯出」兩步 |
| 黃金集／校準 | 目前把全部 review 混作校準材料，血統與統計語意不足以支撐產品宣稱 | 退出主線，保留資料但停止擴建 |
| Decision／Cost 帳本 | 每次 process 建立，但目前未帶來使用者可見價值 | 簡化為 provenance；進階路由前不擴建 |
| 學生模型訓練 | 不存在 | 重構主線 |
| 訓練進度／取消／失敗恢復 | 不存在 | 重構主線 |
| 模型評估與錯誤畫廊 | 不存在 | 重構主線 |
| 應用站 | 只有「施工中」 | 重構主線 |
| CapabilityRelease／runner | 不存在 | 單模型訓練與應用成立後再做 |
| 專案選擇 | 啟動器固定使用 _devproj；沒有正式建立／開啟流程 | 第一階段修正 |
| 雲端同意 | 以本機 JSON 啟用 OpenAI，沒有產品內 per-project 明示同意 | 在正式 Teacher 流程補齊 |
| Studio 桌面打包 | electron-builder 目前只包 UI out 與 package.json，未含 Python sidecar／packages | First Forge 明示使用 dev launcher；可散布 installer 另立後續交付線，不得宣稱已安裝化 |
| 文件 | 總索引、個別票、模組 README 與程式互相漂移 | Phase 0 減重 |

### 5.1 已確認的真實斷點

目前 UI 的看懂站呼叫 `/infer`；整理站只會顯示 `/process` 持久化產生的 Claim。由於 renderer 沒有 `/process` client，使用者在看懂站看到的框不會自然進入整理站。

因此「匯入 → 看懂 → 整理」只在後端整合測試成立，尚不是完整的使用者閉環。

另外，現有資料層有四個開工前必須先處理的正確性風險：Claim 身分可能跨圖碰撞、部分跨 repository 動作可能只寫入一半、同一 Claim 可被重複終局審核、Dataset 匯出會順手建立新的版本。這些不是未來最佳化，而是會直接破壞資料血統與重現性的基礎缺陷。

---

## 6. 重構地圖

### 6.1 保留並重用

- core/contracts/claims.py 中 Claim 是建議、Label 是人工確認結果的分層。
- media content hash、正規化、縮圖與 Project 自包含資料夾。
- SQLite migration 基座與 repository 模式。
- append-only review event 與 provenance 思路。
- OpenAI、fixture provider 的實際接入經驗。
- Electron preload／sidecar／URL policy／CSP 的安全基座。
- FastAPI 可測的 create_app 結構。
- JSON Schema → TypeScript 產物生成機制。
- 現有 Python、API、UI 測試作為回歸資產。

### 6.2 修改或簡化

- Label 允許 `human_created`，不再強制每個 Label 都有 teacher `claim_ref`。
- 新 Claim／Suggestion 由服務層配置 run-scoped ID；舊主鍵與其 Label／Event／Manifest 參照原樣保留，不做危險重寫。
- Decision→Cost→Run→Outcome 與 Label→ReviewEvent 等跨 repository 使用者動作改成單一 transaction；既有已原子的 Run＋Claims 不重做，關聯由 server 端解析。
- 終局 Review 以資料庫／repository 守住單一有效結果，重送必須 idempotent 或回 409。
- DatasetVersion 從全專案改為 Task scoped，並保存 Concept 與 Coverage 快照。
- Dataset freeze 與 YOLO／COCO export 分離；Exporter 只能讀既有不可變 DatasetVersion。
- /infer 與 /process 的重複路徑收斂：產品主線只保留會持久化且回傳可顯示結果的分析操作；純預覽只能作為明示的 Playground 行為。
- Taxonomy 從單一 raw_text 登記擴為穩定 Concept 身分與 Task membership；不在第一版建立完整本體論。
- Decision／Cost／Calibration 保留既有資料相容性，但不再阻斷第一條訓練與應用流程，也不繼續擴建智慧路由。
- 固定三個窄介面：TeacherAdapter 產生草稿、TrainerAdapter 訓練、ModelRunner 執行產物；不再用 Provider 作三者的總稱。
- 專案 UI 從固定 _devproj 改為明確建立／開啟。

### 6.3 新增

- Task、Task-scoped Concept、MediaAssignment／source_group_id 與 Coverage；一個 Project 在第一版直接代表一個能力。
- 可編輯標註畫布。
- Dataset readiness 與未檢查資料防污染守門。
- 本地 Trainer、TrainingRun、ModelArtifact、EvaluationReport。
- 鑄造站與應用站。
- CapabilityRelease 與最小 runner。

### 6.4 暫停擴建

- Orchestrator 智慧路由。
- Provider 投票。
- 成本預測器。
- 複雜校準自動分流。
- 完整 Project Memory 本體。
- 多模型通用 DAG。
- 工程圖專用解析器。

### 6.5 不立即刪除

現有模組先保持可讀與測試通過。只有替代路徑上線、歷史 Project migration 驗證完成後，才移除無消費者的舊 API 或資料表。重構不是以刪除量衡量。

---

## 7. 施工階段

不再沿用「M0 已完成」的敘事。以下每一階段都必須交付一段使用者能親手完成的旅程。

### Slice 0：可信基線與資料護欄

**目標**：讓 repo 對目前狀態說真話，建立可以持續施工的乾淨基線。

工作：

1. 建立可重現的本機開發環境與全套測試基線。
2. 保存 schema v3 Project fixture，補舊 API 與「舊 Project 可無損開啟」characterization tests。
3. 新資料改用 run-scoped Claim ID；補 server-owned references、終局審核唯一性與真正跨 repository 操作的原子交易。
4. 更新 README 與模組 README，移除「目前無內容」與「完整可出貨」等失真文字。
5. 將 R1、舊規格票、交接手冊降為歷史證據，不再作為日常施工流程。
6. 將 AI 分工切換為：一位 Lead 對垂直成果負責，高風險變更獨立審查；不再按模型或目錄永久劃地盤。
7. 保留資料主權、provenance、人工權威、可回滾、可驗證與 Rule of Two；移除全 commit 條文聲明、固定抽審計數與過早 Orchestrator 義務。

第 4～7 項是平行文件整理，不是 WP-00／WP-01 的技術開工前置；不得再次用「尚未修完治理文件」阻擋產品施工。UI 的完整匯入→分析→pending smoke 在 Slice 1 修通後加入，不以紅測試固化目前缺陷。

驗收：

- 全新環境可依一份 README 啟動。
- schema v3 fixture 可由新版無損開啟。
- 兩張圖片同概念、同圖重跑均不發生 Claim ID collision。
- 偽造的 `run_ref`／`media_hash` 被拒絕；任一寫入失敗時整筆操作回滾。
- 同一 Claim 只能有一個有效終局審核；相同 retry 冪等，不同結果重送回 409。
- README 明確列出能做／不能做。
- 沒有任何文件再宣稱鑄造與應用已完成。

### Slice 1：真的教會 A 之前，先讓教學閉環成立

**目標**：使用者能建立一個 detect Task，教單一 Concept A，修正老師結果並安全保存。

工作：

1. 正式的 Project 建立／開啟流程。
2. 新增 Task、Task-scoped Concept、MediaAssignment、Coverage 與 Label revision migration；一個 Project 直接代表一個能力。
3. 看懂站改用持久化分析；看懂與整理收斂成同一個教學工作區，老師草稿可立即編輯。
4. 可移動、縮放、刪除、補畫框與改類別。
5. 支援 `verified_complete`、`verified_absent`、`unverified`。
6. 關閉再開 Project 後，教學目標、框與 Coverage 完整保留。
7. 雲端 Teacher 呼叫前顯示本次會送出的媒體與 per-project 同意。
8. Fixture 只在明示的 Developer Mode／測試環境可用；正式模式不准靜默回退成假框。
9. 標註畫布以圖片實際 rendered rectangle 換算座標，涵蓋 letterbox、縮放與非固定比例圖片。
10. 舊 positive Label 保留但 Coverage 預設 `unverified`；Label edit／delete 以 revision／tombstone 解析出唯一 effective state。

驗收劇本：

~~~text
建立「工具辨識」
→ 新增 detect Task
→ 新增 A「扳手」
→ 匯入多張圖片
→ 老師提出框
→ 使用者移框、刪誤框、補漏框並確認無物件圖片
→ 關閉重開
→ 所有修正與檢查狀態仍在
~~~

本階段不訓練模型。

### Slice 2：鑄造並使用 A

**目標**：從已確認資料訓練第一個本地學生模型，並在應用站對新圖片推論。

工作：

1. Dataset builder 只收本 Task、該版本選定 Concept set 且 Coverage 完整的資料；class map 由該版本固定。
2. detect freeze 遇到不相容的有效幾何必須拒絕並列出問題，不能靜默丟掉後把圖片變成假負例。
3. train／validation 以內容 hash 與明示 `source_group_id` 分組切分；兩邊皆須非空並滿足 Trainer 最低要求。
4. 在接 Trainer 前完成開發、權重使用與 Release 散布的授權路徑裁決；初期可選 Ultralytics，但不把品牌寫入 Core 身分。
5. Trainer 在獨立 child process 執行；TrainingRun 狀態與 log 持久化，支援 queued、running、succeeded、failed、cancelled、interrupted。
6. Sidecar 重啟時把遺留 running 轉為 interrupted 並允許重試；取消、失敗或中斷不得註冊 ModelArtifact。
7. 顯示硬性 readiness、軟性警告、白話進度、失敗原因與技術詳情。
8. 訓練完成建立 ModelArtifact 與綁定 frozen validation snapshot 的 EvaluationReport。
9. 應用站可選 ModelArtifact 並對未入庫的新圖片試跑。
10. 錯誤結果可一鍵送回教學工作區；進入下版訓練後必須從未來 validation 除役。

驗收劇本：

~~~text
從 A 的已確認資料建立 DatasetVersion v1
→ 啟動訓練
→ 看到進度並能取消
→ 訓練完成看到錯誤案例
→ 對新圖片執行本地推論
→ 將一個錯誤送回教學資料
~~~

### Slice 3：把 A 帶走

**目標**：先把單一模型 A 做成真正可攜的 CapabilityRelease v1；使用者不依賴 VisionForge Studio 也能使用它。

CapabilityRelease 至少包含：

- 模型權重。
- Concept／class mapping。
- 輸入尺寸與正規化。
- 後處理與門檻。
- DatasetVersion／TrainingRun／ModelArtifact 摘要。
- 已知弱點與 Evaluation 摘要。
- 最小 Python 使用範例。
- 開放、文件化的 manifest。
- 鎖定依賴與明確 runner 安裝／執行命令。
- 版本化的輸入／輸出 JSON Schema。

驗收：

- 在乾淨 Windows 環境依文件化命令安裝鎖定依賴與最小 runner。
- 載入匯出的 CapabilityRelease。
- 對固定 parity fixture 得到與 Studio 在既定座標與 confidence 誤差內一致的 JSON 結果。
- 不需要專案資料庫或開啟 Studio。
- 授權與再散布清單可被實際交付，沒有做到最後才發現 runner／weights 不能合法散布。

### Slice 4：安全增加 B 並發布 v2

**目標**：證明 VisionForge 能管理變動的教學意圖而不污染 A，並讓舊 Release 真正保持可用。

工作：

1. 在同一 detect Task 新增 Concept B。
2. 舊媒體對 B 自動為 `unverified`。
3. 使用者選定舊資料批次讓老師重掃；智慧排序延後。
4. 未確認 B 的圖片不可作為 B 負樣本。
5. 建立 DatasetVersion v2 與新的 ModelArtifact，驗證後發布 CapabilityRelease v2。
6. DatasetVersion v1、A 的 ModelArtifact 與 CapabilityRelease v1 均可載入與試跑，不被覆寫。
7. 顯示 A、B 各自 Coverage 與弱點。

驗收劇本：

~~~text
既有 CapabilityRelease v1 可用
→ 新增 B「鉗子」
→ 舊圖片顯示 B 尚未檢查
→ 完成 B 的有／無與框修正
→ 訓練 A+B 模型
→ 舊 CapabilityRelease v1 不被覆蓋且仍可試跑
→ 發布含 A+B 的 CapabilityRelease v2
~~~

### Slice 5：第一個複合能力實驗

只有 Slice 4 被真實使用後才開始。

建議以 Engineering Drawing Pack 作為壓力測試，但第一版限定：

- 單一公司／單一圖面家族。
- 使用者可人工指定主圖與 BOM 區域。
- 先驗證一個符號類別，例如 Gate Valve。
- 再逐步加入 layout、OCR、pipe、relation。

此階段才根據兩個以上真實模型流程擴充 CapabilityRelease manifest，並判斷是否真的需要抽出 Runtime；不得先做通用 Node Editor。

---

## 8. 第一批工作包

本節只是從 Slice 0／1 抽出的**一次性首批施工拆解**，不是第二份長期進度真相。完成後以 Slice 驗收為準，後續短期工作進 issue／執行清單，不持續擴寫本節。

### WP-00：先守住資料身分與原子性

成果：

- 服務層配置有 Run scope 的 Claim／Suggestion ID，兩張圖同概念與同圖重跑均不碰撞。
- Decision→Cost→Run→Outcome、Label→ReviewEvent 等真正的跨 repository 動作各自在單一 transaction 內完成；既有 Run＋Claims 原子路徑保留。
- `run_ref`、`media_hash`、`claim_id` 關係由 server 查出，不信任 client 自行拼接。
- schema v3 characterization fixture 可被現行程式無損開啟；不重寫舊 Claim 主鍵。
- 只有 pending Claim 可終局審核；重送冪等或回 409，一個 Claim 只有一份有效終局結果。
- 正式模式不會因 Provider 設定錯誤而靜默顯示 fixture 假框。

### WP-01：把看懂與整理真正接起來

成果：

- Renderer 有持久化分析 client。
- 分析回應包含可立即顯示且已入庫的 Claim。
- 看懂／整理成為同一教學工作區，產生的 Claim 可立即編輯。
- UI 整合測試從匯入／分析一路走到 pending review。

### WP-02：Task／Concept／Coverage migration

成果：

- 一個 Project 可建立 detect Task。
- Concept 有穩定 ID。
- MediaAssignment 保存明示 `source_group_id`。
- Coverage 三態可查詢與更新。
- 未檢查 Concept 絕不進 Dataset negative。
- schema v4 additive migration 與 rollback 測試成立；舊 Project 資料不損失，既有 positive Label 不被誤升為 `verified_complete`。

### WP-03：可編輯標註畫布

成果：

- 移框、縮放、刪除、補框、改類別。
- 每次修改留下不可變 revision／provenance；刪除寫 tombstone，查詢只回 effective revision。
- teacher miss 可以產生 human_created Label。
- 鍵盤與滑鼠操作均有基本可用性。

完成 WP-00～03 後，才開始 Trainer。

---

## 9. Agent 分工與交付規則

### 9.1 角色

#### Direction Setter

使用者只提供方向、情境與底線，不負責技術驗收。

#### Lead Agent

- 對單一垂直成果完整負責。
- 決定方案、切分施工、整合與驗證。
- 可以跨 core、app、ui、providers 修改。
- 必須親自核對所有獨立審查意見，不以投票代替判斷。

#### Builder Agent

- 依明確成果承接可並行的實作。
- 可以反提案，不是只能照票施工。
- 任務按垂直功能或低衝突模組切分，不按模型品牌永久分區。

#### Independent Reviewer

只在下列高風險變更介入：

- 持久化 Schema／migration。
- Dataset split、Coverage 與 frozen validation 隔離。
- 訓練正確性與模型品質宣稱。
- 金鑰、雲端資料、sidecar 與 Release 執行安全。
- 公開 CapabilityRelease 契約。

#### End-to-end QA

使用全新 Project 從 UI 走完整旅程，不接受只以單元測試或後端 API 宣稱產品完成。

### 9.2 只有兩級風險

| 等級 | 例子 | 流程 |
|---|---|---|
| 一般可逆 | UI、文案、一般 API、局部重構 | 主責 Agent＋自動測試 |
| 高風險 | Schema、migration、資料切分、安全、訓練／評估 | 主責 Agent＋獨立 Reviewer＋端到端驗證 |

取消固定 L0／L1／L2 抽查計數與每 commit 憲法條文聲明。

### 9.3 完成的唯一判準

一個 Slice 只有同時滿足以下條件才算完成：

1. 使用者能從 UI 完成該 Slice 的驗收劇本。
2. 重要狀態關閉重開仍存在。
3. 失敗時有可行的人話下一步與技術詳情。
4. 新增資料結構附 migration 與舊 Project 測試。
5. 自動測試綠。
6. README 的能做／不能做同步。

PR 數量、文件數量、測試數量與 commit 數量都不是產品完成指標。

---

## 10. 測試與品質策略

### 10.1 必要測試層

- Core unit：Coverage、Dataset scope、版本與 migration 不變量。
- App integration：持久化分析、審核、Dataset、TrainingRun 與 Artifact。
- UI component：畫布編輯、狀態顯示與錯誤恢復。
- Desktop smoke：Electron 啟動 sidecar，從 Project 建立走到當期 Slice 終點。
- Clean-environment smoke：全新安裝與啟動。
- Artifact parity：匯出模型與 Studio 推論結果在允許誤差內一致。

### 10.2 必須機械守住的資料錯誤

- `unverified` 不可當 negative。
- Frozen validation 不可同時進 train；回流後下一版必須除役並補新 unseen sample。
- 相同內容 hash 或相同明示 source group 不可跨 train 與 validation；First Forge 不承諾自動感知所有近重複。
- TrainingRun 不得讀取會變動的「目前 Dataset」。
- Concept 改名不得重編歷史 class identity。
- ModelArtifact 必須回指 DatasetVersion 與訓練設定。
- 取消或失敗的訓練不得註冊為可用模型。
- 兩張圖片同 Concept 與同圖重跑不得產生 ID collision。
- 偽造或過期的 client 關聯鍵必須被拒絕。
- Label／Event 或 Run／ledger 任一步 fault injection 時，整筆交易不得留下半套狀態。
- 同一 Claim 不可存在兩個有效終局審核或兩份 effective Label。
- detect Dataset 遇到不相容有效幾何必須拒絕 freeze，不可靜默過濾。
- 缺少 Coverage row 與 legacy positive Label 的預設都必須是 `unverified`。
- 非固定比例、letterbox 與縮放後的框座標必須仍對準實際圖片。

### 10.3 每個 Slice 的反過度設計檢查

施工前回答：

1. 這個抽象現在有兩個真實消費者嗎？
2. 不做它，當期使用者旅程是否真的無法完成？
3. 可否先用一個 provisional 實作收集皺褶？
4. 是否正在把領域特例塞進通用 Core？
5. 是否能用端到端測試，而不是再加一條制度？

只要答案顯示需求仍是假設，就延後。

---

## 11. 文件治理減重方案

本開工書暫時作為唯一重構主文件，不立即拆成六份新規格。

重構穩定後只維護：

- README.md：現在能做、如何啟動、現在不能做。
- PRODUCT.md：產品承諾、使用者與非目標。
- ARCHITECTURE.md：現行模組與資料邊界。
- EXECUTION.md：目前 Slice、驗收劇本與下一步。
- ADR：只記真正不可逆且已有現實選項的決策。

舊憲法、R1、R2、規格票與交接手冊應保留為歷史證據，但不得要求每位施工 Agent 全文載入，也不得以舊 Agent 分工阻擋端到端成果。

文件與程式衝突時：

1. 先把實際行為記成事實。
2. 判斷是程式缺陷還是文件過期。
3. 在同一工作包內修正其中一方。
4. 不允許以更新總索引掩蓋個別文件或產品尚未完成。

---

## 12. 開工預設與停止條件

### 12.1 預設

- 第一個完整 Student Task 是本地物件偵測。
- 第一個 Teacher 沿用已存在的 OpenAI adapter，fixture 僅供離線測試。
- 第一個 Student Trainer 可評估 Ultralytics，但必須先確認開發、權重使用與 Release 散布的合法路徑，adapter 保持 provisional。
- 第一個驗收案例先使用容易取得的 A／B 物件；Gate Valve 作為後續專業壓力測試。
- Windows 桌面、本機單人、單機訓練為第一部署環境。
- 不自行發明通用「至少 N 張」品質門檻；只守 Trainer 最低要求、split 非空、獨立 source group 與 Coverage 硬條件，其餘顯示可解釋警告。

### 12.2 必須停止並重新判斷的情況

- 為了接第一個 Trainer，需要先建立通用 Plugin 市場或 DAG。
- Trainer／weights／runner 的授權或再散布路徑尚不清楚。
- 使用者必須理解 Dataset manifest 才能教 A。
- 新增 B 會靜默改寫 A 的舊 DatasetVersion、ModelArtifact 或 CapabilityRelease。
- 訓練完成但無法在應用站立即試跑。
- 只有 API 測試通過，UI 驗收劇本走不完。
- 文件再次使用「完整」「收官」「可出貨」，但仍缺少該階段使用者終點。

---

## 13. 最終北極星

短期北極星不是文件數量，也不是模型指標，而是：

> **一位不懂電腦視覺的使用者，能在 VisionForge 中清楚地教 A、看見老師犯錯、修正它、鑄造本地模型、用新圖驗證，再加入 B 而不污染既有能力，最後把成果帶到 VisionForge 之外使用。**

工程圖、遊戲、工具與未來領域都必須建立在這條已被真實證明的核心旅程上。
