# providers

目前包含兩個 Teacher adapter：確定性的本機 fixture，以及 OpenAI 雲端 vision adapter。兩者只實作 core 的窄 VisionProvider 契約，Provider 之間不互相依賴。

Fixture 只允許明示 Developer Mode／測試。正式設定缺失或錯誤時 API 失敗，不會悄悄回假框；雲端 Teacher 在 Project 尚未同意前也會被 API 拒絕。
