#!/usr/bin/env python3
"""紅線守門：core 不得 import 任何 Provider SDK 或上層模組（憲法 D1／D13）。

分工協議 §4：此檢查由 CI 強制，對 Claude 與 Codex 一視同仁（D20）。
守備範圍會隨套件增加而擴充；本腳本零依賴、確定性、可獨立執行。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_SRC = REPO_ROOT / "core" / "src"

# D1：Provider SDK 與重型 ML/CV 庫——它們屬於 providers/ 與 worker，永不屬於 core。
# D13：上層模組（app/ui/providers）——依賴方向單向，core 位於底層。
FORBIDDEN_ROOTS = {
    # 上層模組（D13）
    "visionforge_app",
    "visionforge_ui",
    "visionforge_providers",
    "providers",
    "app",
    "ui",
    # Provider SDK 與 ML/CV 重庫（D1／A5／D11）
    "ultralytics",
    "torch",
    "torchvision",
    "transformers",
    "openai",
    "anthropic",
    "google",
    "cv2",
    "PIL",
    "onnxruntime",
    "tensorflow",
    "langchain",
}

IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_.]*)")


def main() -> int:
    if not CORE_SRC.exists():
        print(f"找不到 {CORE_SRC}，略過（尚未建立 core）")
        return 0

    violations: list[str] = []
    for py in sorted(CORE_SRC.rglob("*.py")):
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            m = IMPORT_RE.match(line)
            if not m:
                continue
            root = m.group(1).split(".")[0]
            if root in FORBIDDEN_ROOTS:
                rel = py.relative_to(REPO_ROOT)
                violations.append(f"{rel}:{lineno}: 禁止的 import「{root}」 → {line.strip()}")

    if violations:
        print("❌ 違反憲法 D1／D13（core 不識 Provider、依賴方向單向）：\n")
        print("\n".join(violations))
        print("\n處置：把這段邏輯移到 providers/ 或 app/，或提出修憲案（D19）。不得繞過。")
        return 1

    print("✅ D1／D13 守門通過：core 乾淨。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
