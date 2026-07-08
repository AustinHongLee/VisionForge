#!/usr/bin/env python3
"""PR 範圍分類（分工協議 §3-2 機械化預告的落地）。

依變更檔路徑判定 PR 應走的審查層級，讓「L0 自併 vs L2 必審」不靠人肉判斷：
- 觸及 docs/00-法規、docs/01-定義 → 修法/修憲，需人明示同意。
- 觸及 core/、scripts/、.github/ → 守門路徑，L2 必審。
- 只動 app/、ui/、providers/（＋一般文件）→ L0 可自併。

預設為「資訊性」：印出層級供合併決策，不阻擋合法 L2/修法 PR。
`--assert-l0` 供宣稱 L0 的 PR 自我把關：一旦觸及守門/修法路徑即 exit 1。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence

LAW_PATHS = ("docs/00-法規/", "docs/01-定義/")  # 修憲/修法：需人
GUARD_PATHS = (
    "core/",
    "scripts/",
    ".github/",
    "ui/src/main/",  # Electron 主行程＝安全殼
    "ui/src/preload/",  # 特權橋接面
    "ui/src/renderer/index.html",  # CSP 所在
)  # 守門路徑：L2 必審（含 UI 安全殼，票-0010 教訓）
USERLAND_PATHS = ("app/", "ui/", "providers/")  # userland：L0 可自併

LEVEL_L0 = "L0（可自併）"
LEVEL_L2 = "L2（必審）"
LEVEL_L2_LAW = "L2＋修法（需人確認）"


def _match(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(p) for p in prefixes)


def classify(paths: Sequence[str]) -> dict:
    """依變更檔路徑回傳審查層級與分桶。修法優先於守門，守門優先於 userland。"""
    law = sorted(p for p in paths if _match(p, LAW_PATHS))
    guard = sorted(p for p in paths if _match(p, GUARD_PATHS))
    userland = sorted(p for p in paths if _match(p, USERLAND_PATHS))
    known = set(law) | set(guard) | set(userland)
    other = sorted(p for p in paths if p not in known)
    if law:
        level = LEVEL_L2_LAW
    elif guard:
        level = LEVEL_L2
    else:
        level = LEVEL_L0
    return {"level": level, "law": law, "guard": guard, "userland": userland, "other": other}


def is_l0(result: dict) -> bool:
    return result["level"] == LEVEL_L0


def changed_files(base: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def render(result: dict) -> str:
    lines = [f"審查層級：{result['level']}"]
    if result["law"]:
        lines.append("　修法路徑（需人確認）：" + ", ".join(result["law"]))
    if result["guard"]:
        lines.append("　守門路徑（L2 必審）：" + ", ".join(result["guard"]))
    if result["userland"]:
        lines.append(f"　userland：{len(result['userland'])} 檔")
    if result["other"]:
        lines.append(f"　其他（一般文件等）：{len(result['other'])} 檔")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR 範圍分類（§3-2）")
    parser.add_argument("--base", default="origin/main", help="比較基準（預設 origin/main）")
    parser.add_argument(
        "--assert-l0", action="store_true", help="若非 L0（觸及守門/修法路徑）則 exit 1"
    )
    parser.add_argument("files", nargs="*", help="變更檔清單；省略則以 git diff 推算")
    args = parser.parse_args(argv)

    paths = list(args.files) if args.files else changed_files(args.base)
    result = classify(paths)
    print(render(result))
    if args.assert_l0 and not is_l0(result):
        print(
            "::error::此 PR 觸及守門/修法路徑，非 L0——需 Architect 必審，不得走 L0 自併。",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
