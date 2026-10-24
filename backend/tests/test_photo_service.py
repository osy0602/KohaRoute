"""Tests for decoded image validation and metadata removal."""

from io import BytesIO

import pytest
from PIL import Image

from app.services.photo_service import InvalidPhotoError, prepare_photo


def make_image(image_format="PNG", **save_options):
    """Create a tiny real image in memory for upload validation tests."""
    output = BytesIO()
    Image.new("RGB", (8, 8), "red").save(output, format=image_format, **save_options)
    return output.getvalue()


@pytest.mark.parametrize(
    ("image_format", "expected_type"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png")],
)
def test_valid_photo_is_decoded_and_reencoded(image_format, expected_type):
    """Real JPEG and PNG images are accepted and have the right stored MIME type."""
    prepared = prepare_photo(make_image(image_format), 1024 * 1024)
    assert prepared.content_type == expected_type
    with Image.open(BytesIO(prepared.content)) as decoded:
        assert decoded.format == image_format
        assert decoded.size == (8, 8)
        assert not decoded.info.get("exif")


def test_extension_or_mime_cannot_make_non_image_bytes_valid():
    """Unrecognized bytes are rejected regardless of a client-supplied MIME type."""
    with pytest.raises(InvalidPhotoError, match="not a valid"):
        prepare_photo(b"not actually an image", 1024)


def test_photo_size_is_checked_before_decoding():
    """Oversized request bodies fail before image decoding."""
    with pytest.raises(InvalidPhotoError, match="no larger"):
        prepare_photo(make_image(), 1)


def test_svg_and_other_formats_are_rejected():
    """Only decoded JPEG and PNG content is accepted."""
    with pytest.raises(InvalidPhotoError, match="Only JPG and PNG"):
        prepare_photo(make_image("GIF"), 1024 * 1024)


def test_exif_metadata_is_not_preserved():
    """Re-encoding drops source EXIF payloads."""
    source = Image.new("RGB", (8, 8), "blue")
    exif = Image.Exif()
    exif[270] = "private camera notes"
    original = BytesIO()
    source.save(original, format="JPEG", exif=exif)

    prepared = prepare_photo(original.getvalue(), 1024 * 1024)
    with Image.open(BytesIO(prepared.content)) as decoded:
        assert not decoded.getexif()