from dataclasses import dataclass
from pathlib import Path


MAX_POSTER_IMAGE_SIZE = 10 * 1024 * 1024
SUPPORTED_POSTER_IMAGES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class PosterImageInfo:
    extension: str
    content_type: str


def validate_poster_image(filename: str, size: int) -> PosterImageInfo:
    extension = Path(filename).suffix.lower()
    content_type = SUPPORTED_POSTER_IMAGES.get(extension)
    if content_type is None:
        raise ValueError("学习机海报仅支持 JPG、PNG、WEBP 图片")
    if size > MAX_POSTER_IMAGE_SIZE:
        raise ValueError("单张学习机海报不能超过 10 MB")
    return PosterImageInfo(extension=extension, content_type=content_type)
