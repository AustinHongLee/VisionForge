"""PR 範圍分類器測試（分工協議 §3-2 機械化）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_pr_scope as scope  # noqa: E402


def test_userland_only_is_l0():
    r = scope.classify(["ui/src/App.tsx", "app/tests/test_x.py", "providers/foo.py"])
    assert scope.is_l0(r)
    assert r["level"] == scope.LEVEL_L0


def test_core_triggers_l2():
    r = scope.classify(["core/src/visionforge_core/x.py", "ui/src/App.tsx"])
    assert r["level"] == scope.LEVEL_L2
    assert not scope.is_l0(r)
    assert r["guard"] == ["core/src/visionforge_core/x.py"]


def test_scripts_and_github_trigger_l2():
    assert scope.classify(["scripts/foo.py"])["level"] == scope.LEVEL_L2
    assert scope.classify([".github/workflows/ci.yml"])["level"] == scope.LEVEL_L2


def test_law_paths_trigger_l2_plus_law():
    r = scope.classify(["docs/01-定義/名詞定義表.md", "core/x.py"])
    assert r["level"] == scope.LEVEL_L2_LAW  # 修法優先於守門
    assert r["law"] == ["docs/01-定義/名詞定義表.md"]


def test_plain_docs_are_l0():
    r = scope.classify(["docs/README.md", "docs/06-規格票/票-0007.md"])
    assert scope.is_l0(r)
    assert len(r["other"]) == 2


def test_assert_l0_exit_codes():
    assert scope.main(["--assert-l0", "ui/a.tsx"]) == 0
    assert scope.main(["--assert-l0", "core/a.py"]) == 1
