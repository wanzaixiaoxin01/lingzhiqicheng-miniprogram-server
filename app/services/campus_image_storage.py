import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.domain.campus_images import (
    MAX_CAMPUS_IMAGE_SIZE,
    CampusImageInfo,
    build_campus_storage_name,
    validate_campus_image,
)


class CampusImageStorage:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or settings.upload_dir).expanduser().resolve() / "campuses"

    async def save_upload(self, upload: UploadFile, campus_id: str) -> tuple[CampusImageInfo, str, int]:
        filename = upload.filename or ""
        validate_campus_image(filename, 0)
        self.root.mkdir(parents=True, exist_ok=True)

        temporary = self.root / f".{campus_id}.upload"
        total = 0
        try:
            with temporary.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_CAMPUS_IMAGE_SIZE:
                        raise ValueError("服务点封面不能超过 10 MB")
                    destination.write(chunk)
            info = validate_campus_image(filename, total)
            storage_name = build_campus_storage_name(campus_id, info.extension, uuid.uuid4().hex)
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
        return f"/uploads/campuses/{storage_name}"

    def remove(self, storage_name: str) -> None:
        self.path_for(storage_name).unlink(missing_ok=True)


campus_image_storage = CampusImageStorage()
