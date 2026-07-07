# providers/ — Vision Provider adapters（Codex 地盤）

每個 Provider 一個子套件，實作核心契約（`visionforge_core.contracts`）並通過 Conformance Suite（PR5）後才可註冊。

規則：可以 import `visionforge_core`（實作契約），**core 永不 import 這裡**（D1，CI 強制）。Provider 之間不得互相 import（PR8）。

目前無內容——等規格票。
