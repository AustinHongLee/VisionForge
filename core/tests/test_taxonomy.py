"""最小 Taxonomy 儲存測試（ADR-0010）：get-or-create、查詢、列舉、遷移相容。"""

from datetime import datetime, timezone

from visionforge_core.contracts import TaxonomyNode
from visionforge_core.storage import create_project

NOW = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def node(n: int, text: str) -> TaxonomyNode:
    return TaxonomyNode(node_id=f"{n:026d}", raw_text=text, created_at=NOW)


def test_ensure_creates_then_returns_existing(tmp_path):
    proj = create_project(tmp_path / "p", "q", "0" * 26)
    try:
        created = proj.taxonomy.ensure(node(1, "bolt"))
        assert created.node_id == f"{1:026d}"
        # 同 raw_text 再 ensure（帶不同 node_id）→ 回既有、不新增
        again = proj.taxonomy.ensure(node(2, "bolt"))
        assert again.node_id == f"{1:026d}"  # 既有的，不是 2
        assert len(proj.taxonomy.list()) == 1
    finally:
        proj.close()


def test_get_and_get_by_text(tmp_path):
    proj = create_project(tmp_path / "p", "q", "0" * 26)
    try:
        proj.taxonomy.ensure(node(1, "crack"))
        assert proj.taxonomy.get(f"{1:026d}").raw_text == "crack"
        assert proj.taxonomy.get_by_text("crack").node_id == f"{1:026d}"
        assert proj.taxonomy.get_by_text("missing") is None
    finally:
        proj.close()


def test_list_is_deterministic(tmp_path):
    proj = create_project(tmp_path / "p", "q", "0" * 26)
    try:
        for i, t in enumerate(["a", "b", "c"], start=1):
            proj.taxonomy.ensure(node(i, t))
        assert [n.raw_text for n in proj.taxonomy.list()] == ["a", "b", "c"]
    finally:
        proj.close()


def test_reopen_after_migration_v2(tmp_path):
    from visionforge_core.storage import open_project
    root = tmp_path / "p"
    proj = create_project(root, "q", "0" * 26)
    proj.taxonomy.ensure(node(1, "bolt"))
    proj.close()
    reopened = open_project(root)  # 遷移冪等：v2 表在，資料還在
    try:
        assert reopened.taxonomy.get_by_text("bolt") is not None
    finally:
        reopened.close()
