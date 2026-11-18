from dataclasses import dataclass
from pathlib import Path


MAX_COURSE_IMAGE_SIZE = 10 * 1024 * 1024
SUPPORTED_COURSE_IMAGES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class CourseImageInfo:
    extension: str
    content_type: str


def validate_course_image(filename: str, size: int) -> CourseImageInfo:
    extension = Path(filename or "").suffix.lower()
    content_type = SUPPORTED_COURSE_IMAGES.get(extension)
    if content_type is None:
        raise ValueError("活动封面仅支持 JPG、PNG、WEBP 图片")
    if size < 0 or size > MAX_COURSE_IMAGE_SIZE:
        raise ValueError("活动封面不能超过 10 MB")
    return CourseImageInfo(extension=extension, content_type=content_type)
