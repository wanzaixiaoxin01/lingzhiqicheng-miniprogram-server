from pathlib import Path
from fastapi import UploadFile

from app.config import settings
from app.domain.materials import MaterialFileInfo, build_storage_name, validate_material_file


class MaterialStorage:
    def __init__(self, root: str | Path | None = None, max_size: int | None = None):
        self.root = Path(root or settings.upload_dir).expanduser().resolve()
        self.max_size = max_size or settings.max_material_size

    async def save_upload(self, upload: UploadFile, material_id: str) -> tuple[MaterialFileInfo, str, int]:
        filename = upload.filename or ""
        validate_material_file(filename, 0)
        self.root.mkdir(parents=True, exist_ok=True)

        temporary = self.root / f".{material_id}.upload"
        total = 0
        try:
            with temporary.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > self.max_size:
                        raise ValueError("文件不能超过 100 MB")
                    destination.write(chunk)
            info = validate_material_file(filename, total)
            storage_name = build_storage_name(material_id, info.original_name)
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

    def remove(self, storage_name: str) -> None:
        self.path_for(storage_name).unlink(missing_ok=True)

    def exists(self, storage_name: str) -> bool:
        return self.path_for(storage_name).is_file()


material_storage = MaterialStorage()
