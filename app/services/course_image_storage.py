import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.domain.course_images import MAX_COURSE_IMAGE_SIZE, CourseImageInfo, validate_course_image


class CourseImageStorage:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or settings.upload_dir).expanduser().resolve() / "courses"

    async def save_upload(self, upload: UploadFile) -> tuple[CourseImageInfo, str, int]:
        info = validate_course_image(upload.filename or "", 0)
        self.root.mkdir(parents=True, exist_ok=True)
        storage_name = f"course-{uuid.uuid4().hex}{info.extension}"
        temporary = self.root / f".{storage_name}.upload"
        total = 0
        try:
            with temporary.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_COURSE_IMAGE_SIZE:
                        raise ValueError("活动封面不能超过 10 MB")
                    destination.write(chunk)
            info = validate_course_image(upload.filename or "", total)
            temporary.replace(self.path_for(storage_name))
            return info, storage_name, total
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    def path_for(self, storage_name: str) -> Path:
        candidate = (self.root / storage_name).resolve()
        if self.root not in candidate.parents:
            raise ValueError("文件路径不安全")
        return candidate

    def url_for(self, storage_name: str) -> str:
        return f"/uploads/courses/{storage_name}"

    def remove(self, storage_name: str) -> None:
        self.path_for(storage_name).unlink(missing_ok=True)


course_image_storage = CourseImageStorage()
