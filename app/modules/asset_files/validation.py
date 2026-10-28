from pathlib import PurePath

from app.modules.asset_files.constants import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
)


def validate_file(
    filename: str,
    content_type: str,
    file_size: int,
) -> None:
    if not filename or filename != filename.strip():
        raise ValueError("Filename must not be empty or padded with spaces")

    if len(filename) > 255:
        raise ValueError("Filename must not exceed 255 characters")

    if PurePath(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError("Filename must not contain a path")

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported file types")

    extension = PurePath(filename).suffix.lower()
    expected_content_type = ALLOWED_EXTENSIONS.get(extension)

    if expected_content_type != content_type:
        raise ValueError("File extension does not match the content type")

    if isinstance(file_size, bool) or not isinstance(file_size, int):
        raise ValueError("File size must be an integer")

    if file_size <= 0:
        raise ValueError("File size must be greater than zero")

    if file_size > MAX_FILE_SIZE:
        raise ValueError("File size must not exceed 5 MB")
