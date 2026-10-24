"""Validate uploaded photographs and re-encode them without embedded metadata."""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

SUPPORTED_FORMATS = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png")}
MAX_IMAGE_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class InvalidPhotoError(ValueError):
    """Raised when an uploaded file is not an acceptable photograph."""


@dataclass(frozen=True)
class PreparedPhoto:
    """Validated, metadata-free image bytes ready for durable storage."""

    content: bytes
    content_type: str
    extension: str


def prepare_photo(content: bytes, max_bytes: int) -> PreparedPhoto:
    """Decode a JPEG/PNG and re-encode it with no EXIF or other source metadata."""
    if not content:
        raise InvalidPhotoError("Choose a non-empty JPG or PNG photo.")
    if len(content) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise InvalidPhotoError(f"Each photo must be no larger than {limit_mb} MB.")

    try:
        with Image.open(BytesIO(content)) as source:
            image_format = source.format
            source.verify()
        if image_format not in SUPPORTED_FORMATS:
            raise InvalidPhotoError("Only JPG and PNG photos are accepted.")
        with Image.open(BytesIO(content)) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise InvalidPhotoError("The photo dimensions are too large.")
            source.load()
            mode = "RGBA" if image_format == "PNG" and "A" in source.getbands() else "RGB"
            decoded = source.convert(mode)
            # A new canvas prevents copied image.info/exif data from reaching the output.
            clean = Image.new(mode, decoded.size)
            clean.paste(decoded)
            output = BytesIO()
            clean.save(output, format=image_format, optimize=True)
    except InvalidPhotoError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise InvalidPhotoError("The uploaded file is not a valid JPG or PNG image.") from error

    cleaned_content = output.getvalue()
    if len(cleaned_content) > max_bytes:
        raise InvalidPhotoError("The processed photo exceeds the 5 MB size limit.")
    content_type, extension = SUPPORTED_FORMATS[image_format]
    return PreparedPhoto(cleaned_content, content_type, extension)