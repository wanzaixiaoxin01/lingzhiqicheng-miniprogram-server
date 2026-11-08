from dataclasses import dataclass
from pathlib import Path


MAX_MATERIAL_SIZE = 100 * 1024 * 1024

_FILE_TYPES = {
    ".pdf": ("application/pdf", True),
    ".doc": ("application/msword", True),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
    ".xls": ("application/vnd.ms-excel", True),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True),
    ".ppt": ("application/vnd.ms-powerpoint", True),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", True),
    ".txt": ("text/plain", False),
    ".jpg": ("image/jpeg", True),
    ".jpeg": ("image/jpeg", True),
    ".png": ("image/png", True),
    ".gif": ("image/gif", True),
    ".webp": ("image/webp", True),
    ".zip": ("application/zip", False),
}


@dataclass(frozen=True)
class MaterialFileInfo:
    original_name: str
    extension: str
    content_type: str
    can_preview: bool


def _safe_original_name(filename: str) -> str:
    normalized = str(filename or "").replace("\\", "/")
    return Path(normalized).name.strip()


def validate_material_file(filename: str, size: int) -> MaterialFileInfo:
    original_name = _safe_original_name(filename)
    if not original_name:
        raise ValueError("请选择要上传的文件")
    if size < 0:
        raise ValueError("文件大小不正确")
    if size > MAX_MATERIAL_SIZE:
        raise ValueError("文件不能超过 100 MB")

    extension = Path(original_name).suffix.lower()
    file_type = _FILE_TYPES.get(extension)
    if file_type is None:
        raise ValueError("暂不支持该文件格式，请上传 PDF、Word、Excel、PPT、ZIP、TXT 或图片")

    content_type, can_preview = file_type
    return MaterialFileInfo(
        original_name=original_name,
        extension=extension,
        content_type=content_type,
        can_preview=can_preview,
    )


def build_storage_name(material_id: str, filename: str) -> str:
    extension = Path(_safe_original_name(filename)).suffix.lower()
    return f"{material_id}{extension}"
