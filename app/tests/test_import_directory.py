from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from visionforge_app.importer import import_directory
from visionforge_core.storage import create_project


@pytest.fixture()
def project(tmp_path: Path):
    proj = create_project(tmp_path / "project", "batch-import-test", "1" * 26)
    try:
        yield proj
    finally:
        proj.close()


def _image_bytes(image_format: str, color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (16, 10), color).save(output, format=image_format)
    return output.getvalue()


def _write_fixture_tree(root: Path) -> dict[str, bytes]:
    images = {
        "a.jpg": _image_bytes("JPEG", (220, 30, 30)),
        "b.png": _image_bytes("PNG", (20, 120, 220)),
    }
    (root / "a.jpg").write_bytes(images["a.jpg"])
    (root / "b.png").write_bytes(images["b.png"])
    (root / "c-copy.jpeg").write_bytes(images["a.jpg"])
    (root / "notes.txt").write_text("not a candidate", encoding="utf-8")
    (root / "z-broken.jpg").write_bytes(images["a.jpg"][:30])
    return images


def _source_names(outcomes) -> list[str]:
    return [Path(outcome.record.source.detail).name for outcome in outcomes]


def test_mixed_directory_buckets_candidates_and_failures(project, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    _write_fixture_tree(source_dir)

    outcome = import_directory(project, source_dir)

    assert _source_names(outcome.imported) == ["a.jpg", "b.png"]
    assert len(outcome.duplicated) == 1
    assert outcome.duplicated[0].media_hash == outcome.imported[0].media_hash
    assert [failure.path.name for failure in outcome.failed] == ["z-broken.jpg"]
    assert outcome.failed[0].error == "MediaDecodeError"
    assert "notes.txt" not in _source_names(outcome.imported + outcome.duplicated)
    assert outcome.total_seen == 4
    assert project.media.count() == 2


def test_import_directory_is_idempotent(project, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "a.jpg").write_bytes(_image_bytes("JPEG", (30, 40, 50)))
    (source_dir / "b.png").write_bytes(_image_bytes("PNG", (90, 80, 70)))

    first = import_directory(project, source_dir)
    second = import_directory(project, source_dir)

    assert len(first.imported) == 2
    assert first.duplicated == ()
    assert second.imported == ()
    assert _source_names(second.duplicated) == ["a.jpg", "b.png"]
    assert project.media.count() == 2


def test_recursive_flag_controls_child_directories(project, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    child_dir = source_dir / "child"
    child_dir.mkdir(parents=True)
    (source_dir / "top.jpg").write_bytes(_image_bytes("JPEG", (1, 2, 3)))
    (child_dir / "nested.png").write_bytes(_image_bytes("PNG", (4, 5, 6)))

    top_only = import_directory(project, source_dir, recursive=False)
    recursive = import_directory(project, source_dir, recursive=True)

    assert _source_names(top_only.imported) == ["top.jpg"]
    assert _source_names(recursive.imported) == ["nested.png"]
    assert _source_names(recursive.duplicated) == ["top.jpg"]


def test_import_directory_order_is_deterministic(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "b.png").write_bytes(_image_bytes("PNG", (8, 8, 8)))
    (source_dir / "a.jpg").write_bytes(_image_bytes("JPEG", (9, 9, 9)))
    (source_dir / "c.bmp").write_bytes(_image_bytes("BMP", (10, 10, 10)))

    project_a = create_project(tmp_path / "project-a", "a", "2" * 26)
    project_b = create_project(tmp_path / "project-b", "b", "3" * 26)
    try:
        first = import_directory(project_a, source_dir)
        second = import_directory(project_b, source_dir)
    finally:
        project_a.close()
        project_b.close()

    assert _source_names(first.imported) == ["a.jpg", "b.png", "c.bmp"]
    assert _source_names(second.imported) == _source_names(first.imported)


def test_empty_directory_has_empty_buckets(project, tmp_path: Path) -> None:
    source_dir = tmp_path / "empty"
    source_dir.mkdir()

    outcome = import_directory(project, source_dir)

    assert outcome.imported == ()
    assert outcome.duplicated == ()
    assert outcome.failed == ()
    assert outcome.total_seen == 0


def test_import_directory_rejects_missing_or_file(project, tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-directory.jpg"
    file_path.write_bytes(_image_bytes("JPEG", (1, 1, 1)))

    with pytest.raises(NotADirectoryError):
        import_directory(project, tmp_path / "missing")

    with pytest.raises(NotADirectoryError):
        import_directory(project, file_path)
