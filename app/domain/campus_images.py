from dataclasses import dataclass
from pathlib import Path


MAX_CAMPUS_IMAGE_SIZE = 10 * 1024 * 1024

_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class CampusImageInfo:
    original_name: str
    extension: str
    content_type: str


def _safe_original_name(filename: str) -> str:
    normalized = str(filename or "").replace("\\", "/")
    return Path(normalized).name.strip()


def validate_campus_image(filename: str, size: int) -> CampusImageInfo:
    original_name = _safe_original_name(filename)
    if not original_name:
        raise ValueError("请选择服务点封面图片")
    if size < 0:
        raise ValueError("图片大小不正确")
    if size > MAX_CAMPUS_IMAGE_SIZE:
        raise ValueError("服务点封面不能超过 10 MB")

    extension = Path(original_name).suffix.lower()
    content_type = _IMAGE_TYPES.get(extension)
    if content_type is None:
        raise ValueError("服务点封面仅支持 JPG、PNG、GIF 或 WEBP 图片")
    return CampusImageInfo(original_name, extension, content_type)


def build_campus_storage_name(campus_id: str, extension: str, suffix: str | None = None) -> str:
    normalized_extension = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    extra = f"-{suffix}" if suffix else ""
    return f"campus-{campus_id}{extra}{normalized_extension}"
