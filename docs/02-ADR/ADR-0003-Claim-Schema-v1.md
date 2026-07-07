# ADR-0003：定案 Claim Schema v1.0（含五項開放問題裁決）

| 項目 | 內容 |
|---|---|
| 編號 | ADR-0003 |
| 日期 | 2026-07-07 |
| 狀態 | 🟩 已採納（開放問題由決策者授權 Claude 依草案傾向裁決） |
| 決策者 | 李宗鴻 |

## 背景
Claim Schema 是核心與一切 Provider 的唯一耦合點（PR2），必須先於任何 adapter 與服務程式碼定案。草案（05-討論/20260707，已歸檔）經討論無異議。

## 決策
採納草案 v0.1 全部設計：InferenceRun／Claim 兩層結構、normalized 0–1 座標＋像素基準、型別化開放幾何聯集＋未知型別保留、raw_text 與 taxonomy 映射分離（映射有出處）、raw／calibrated 信心分離＋reliability 分級、Label 為獨立不可變記錄。

五項開放問題裁決：

| # | 問題 | 裁決 |
|---|---|---|
| 1 | mask 格式 | **RLE（COCO 慣例）**，mask 本體為內容雜湊定址檔案；縮圖快取屬 UI 層 |
| 2 | 否定陳述 | **一等公民**：`assertion ∈ {presence, absence}`；absence 必須配 whole_image 幾何（黃金集需要「已驗證的空圖」，健檢負樣本規則依賴它） |
| 3 | keypoints 骨架定義 | **任務模組擁有**，Schema 只存 `skeleton_ref` 登記名 |
| 4 | provider_extra 上限 | **64 KB 硬上限**，超過在邊界拒絕（裁剪是 adapter 正規化層的責任）——確定性優於寬容 |
| 5 | temporal_span | **不預建**（A10）；媒體型別保留擴充點即可 |

**唯一事實來源**：`core/src/visionforge_core/contracts/claims.py`（Pydantic v2）。JSON Schema 與 TS 型別由此生成；文件與程式不一致時，以程式＋本 ADR 為準。

## 理由
見草案（已歸檔）第一～七節論證；裁決 #2、#4 的理由已註記於上表。

## 曾考慮的替代方案
單層結構（每框自帶完整出處）→ 棄：出處重複膨脹；Claim 狀態就地變更為 Label → 棄：摧毀「Provider 原始輸出 vs 人改結果」的對照能力（防線五的量測基礎）。

## 影響範圍
一切 Provider adapter、審核服務、資料庫映射、票-0001 之後的全部 UI 型別。

## 憲法檢核（D19／D20）
觸及 PR2（schema_version＋N/N-1）、PR6（producer 三元組）、F1/F2（開放聯集＋媒體擴充點）、D3（decision_ref／cost_ref 必填——**不存在無帳的 Run**）、D7（Label 獨立記錄，唯一入口為審核狀態機）、A5（Pydantic 邊界驗證）、A10（不預建 temporal_span）。合規。

## 後續行動
- 已完成（Claude）：契約程式碼＋單元測試＋CI 守門（見 repo）。
- 下一步（Claude）：帳本 Schema（Decision／Cost／血統）——B1 的「誠實」本體。
