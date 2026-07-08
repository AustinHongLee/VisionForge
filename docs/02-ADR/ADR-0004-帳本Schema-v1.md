# ADR-0004：定案帳本 Schema v1.0（Decision／Cost／ReviewEvent／版本 Manifest／黃金集登記）

| 項目 | 內容 |
|---|---|
| 編號 | ADR-0004 |
| 日期 | 2026-07-07 |
| 狀態 | 🟩 已採納（含本 ADR 的 commit b862c71 已合併進 main，依授權「合併即視同採納」生效） |
| 決策者 | 李宗鴻（Claude 起草） |

## 背景
憲法 B1：路由邏輯可以極簡，但 Decision／成本／血統／版本的記錄格式必須第一天完整——缺頁的帳本永遠補不回來。Claim/Label（ADR-0003）已覆蓋血統的實例層，本 ADR 補齊其餘帳本。

## 決策
新增 `core/src/visionforge_core/contracts/ledgers.py`（唯一事實來源），五組記錄：

| 記錄 | 職責 | 關鍵設計 |
|---|---|---|
| DecisionRecord | Orchestrator 決策（D3） | 政策快照參照、候選證據列、**理由碼封閉登記表**（拒絕自由文字）；human_override 是一種決策而非修改（A12） |
| DecisionOutcome | 決策結果 | **獨立追加記錄**，不回寫原決策（append-only） |
| CostEntry | 一切消耗（D4/C1） | 金額用 **Decimal 字串序列化**（錢不進浮點數）；estimate/actual 兩筆分錄以 estimate_ref 配對（C6 預測可證偽）；**人的審核時間同樣入帳**（C5）；計量單位開放登記（F3） |
| ReviewEvent | 人審行為留痕（P4） | 含否決；批准必回指 Label（D7）；**context=blind_audit／honeypot** 是防線五的量測資料來源 |
| DatasetVersionManifest ＋ GoldenSetEntry | 版本與黃金集（D5/D8） | 版本＝清單非拷貝，回滾＝開新版指向舊 parent；同版媒體去重強制；黃金集只增與除役（除役須留理由），永不出現在訓練 manifest |

儲存層可將大型 Manifest 正規化為關聯表；本契約定義邏輯與交換格式。

## 曾考慮的替代方案
- 決策結果就地回寫 DecisionRecord → 棄：破壞不可變性，崩潰時無法區分「沒結果」與「被改過」。
- 理由碼用自由文字 → 棄：A5 確定性內核，自由文字無法統計與稽核。
- 金額用 float → 棄：十年後對不了帳的經典錯誤。
- Project Memory schema 一併定案 → 棄：R2 9.6 教訓——記憶本體論必須從真實審核行為長出，先驗設計必錯（A10）。

## 影響範圍
Orchestrator v1、Cost Engine、審核服務、儲存層的全部實作都以此為契約。

## 憲法檢核（D19／D20）
觸及 B1、D3、D4、D5、D7、D8、C1、C5、C6、F3、A6、A12、A5。合規：全部條文直接落為欄位不變量（見 ledgers.py 註解與 test_ledgers.py）。

## 後續行動
- 下一步（Claude）：儲存層（project.db 映射＋repository 介面）→ 解鎖匯入管線票（Codex）。
- 待辦（Claude）：Budget 為政策設定非帳本，隨 Cost Engine 服務實作時定義。
