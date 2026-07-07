from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from visionforge_app.importer import import_media
from visionforge_app.importer.errors import (
    MediaDecodeError,
    MultiFrameMediaError,
    UnsupportedMediaFormatError,
)
from visionforge_core.contracts.media import MediaSource
from visionforge_core.storage import create_project

GOLDEN_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
    "CAAFAAcDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAA"
    "AgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkK"
    "FhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWG"
    "h4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl"
    "5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREA"
    "AgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYk"
    "NOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOE"
    "hYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk"
    "5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDx2iiiu04z/9k="
)
GOLDEN_JPEG_HASH = "49ab860f370463b727f21321f4149d9a1cced7ea27dd0b116bd73824aaa18495"
GOLDEN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAECAIAAADJUWIXAAAAFElEQVR4nGOMEuFiQAJMDKi"
    "AEB8AHqAAgInSKCsAAAAASUVORK5CYII="
)
GOLDEN_PNG_HASH = "308459369f46f29cb2c17ecf1a9ddec5db0252a2165978004ec72fe065fc6104"


@pytest.fixture()
def project(tmp_path: Path):
    proj = create_project(tmp_path / "project", "import-test", "0" * 26)
    try:
        yield proj
    finally:
        proj.close()


@pytest.fixture()
def source() -> MediaSource:
    return MediaSource(kind="file", detail="fixture")


def _save_image(
    image: Image.Image,
    image_format: str,
    *,
    exif_orientation: int | None = None,
) -> bytes:
    output = BytesIO()
    if exif_orientation is None:
        image.save(output, format=image_format)
    else:
        exif = Image.Exif()
        exif[274] = exif_orientation
        image.save(output, format=image_format, exif=exif)
    return output.getvalue()


def _image_bytes(image_format: str, size: tuple[int, int] = (12, 8)) -> bytes:
    return _save_image(Image.new("RGB", size, (20, 80, 140)), image_format)


def _blob_files(project) -> list[Path]:
    return [
        path
        for path in (project.root / "media" / "blobs").rglob("*")
        if path.is_file() and not path.name.endswith(".tmp")
    ]


def _thumbs(project) -> list[Path]:
    return list((project.root / "media" / "thumbs").glob("*.jpg"))


def _assert_zero_writes(project) -> None:
    assert project.media.count() == 0
    assert _blob_files(project) == []
    assert _thumbs(project) == []


def test_orientation_one_jpeg_preserves_original_bytes(project, source) -> None:
    outcome = import_media(project, GOLDEN_JPEG, source)

    assert outcome.media_hash == GOLDEN_JPEG_HASH
    assert outcome.deduplicated is False
    assert outcome.record.media_hash == GOLDEN_JPEG_HASH
    assert outcome.record.width_px == 7
    assert outcome.record.height_px == 5
    assert outcome.record.format == "jpeg"
    assert outcome.record.byte_size == len(GOLDEN_JPEG)
    assert outcome.record.exif_normalized is True
    assert outcome.record.imported_at.tzinfo is not None
    assert project.media.get(GOLDEN_JPEG_HASH) == outcome.record
    assert project.blobs.find(GOLDEN_JPEG_HASH).read_bytes() == GOLDEN_JPEG
    assert (project.root / "media" / "thumbs" / f"{GOLDEN_JPEG_HASH}.jpg").is_file()


def test_orientation_six_jpeg_is_transposed_before_storage(project, source) -> None:
    original = _save_image(Image.new("RGB", (12, 8), (200, 40, 20)), "JPEG", exif_orientation=6)

    outcome = import_media(project, original, source)
    stored = project.blobs.find(outcome.media_hash).read_bytes()

    assert stored != original
    with Image.open(BytesIO(stored)) as stored_image:
        assert stored_image.size == (8, 12)
        assert stored_image.getexif().get(274, 1) == 1
    assert outcome.record.width_px == 8
    assert outcome.record.height_px == 12


def test_import_is_idempotent_and_skips_thumbnail_regeneration(project, source) -> None:
    first = import_media(project, GOLDEN_JPEG, source)
    thumb = project.root / "media" / "thumbs" / f"{first.media_hash}.jpg"
    thumb.write_bytes(b"sentinel")

    second = import_media(project, GOLDEN_JPEG, source)

    assert second.media_hash == first.media_hash
    assert second.record == first.record
    assert second.deduplicated is True
    assert project.media.count() == 1
    assert thumb.read_bytes() == b"sentinel"


@pytest.mark.parametrize(
    ("image_format", "media_format", "suffix"),
    [
        ("PNG", "png", ".png"),
        ("WEBP", "webp", ".webp"),
        ("BMP", "bmp", ".bmp"),
        ("TIFF", "tiff", ".tif"),
    ],
)
def test_supported_formats_roundtrip(project, source, image_format, media_format, suffix) -> None:
    data = _image_bytes(image_format)

    outcome = import_media(project, data, source)
    blob = project.blobs.find(outcome.media_hash)

    assert outcome.record.format == media_format
    assert blob is not None and blob.suffix == suffix
    assert blob.read_bytes() == data


@pytest.mark.parametrize(
    ("data", "expected_hash"),
    [
        (GOLDEN_JPEG, GOLDEN_JPEG_HASH),
        (GOLDEN_PNG, GOLDEN_PNG_HASH),
    ],
)
def test_golden_hashes_for_orientation_one_inputs(project, source, data, expected_hash) -> None:
    assert hashlib.sha256(data).hexdigest() == expected_hash
    assert import_media(project, data, source).media_hash == expected_hash


@pytest.mark.parametrize("data", [_image_bytes("GIF"), b"not an image"])
def test_unsupported_formats_have_no_side_effects(project, source, data) -> None:
    with pytest.raises(UnsupportedMediaFormatError):
        import_media(project, data, source)

    _assert_zero_writes(project)


def test_multiframe_tiff_has_no_side_effects(project, source) -> None:
    output = BytesIO()
    Image.new("RGB", (8, 5), (1, 2, 3)).save(
        output,
        format="TIFF",
        save_all=True,
        append_images=[Image.new("RGB", (8, 5), (4, 5, 6))],
    )

    with pytest.raises(MultiFrameMediaError):
        import_media(project, output.getvalue(), source)

    _assert_zero_writes(project)


def test_corrupt_image_has_no_side_effects(project, source) -> None:
    with pytest.raises(MediaDecodeError):
        import_media(project, GOLDEN_JPEG[:30], source)

    _assert_zero_writes(project)


def test_thumbnail_respects_max_edge_and_aspect_ratio(project, source) -> None:
    data = _image_bytes("JPEG", size=(400, 200))
    outcome = import_media(project, data, source, thumbnail_max_edge=50)
    thumb = project.root / "media" / "thumbs" / f"{outcome.media_hash}.jpg"

    with Image.open(thumb) as thumb_image:
        assert thumb_image.size == (50, 25)
        assert max(thumb_image.size) <= 50
