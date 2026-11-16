import io
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from starlette.datastructures import FormData, UploadFile

from app import models
from app.db import Base
from app.routes import admin_pages
from app.services.material_storage import MaterialStorage


class MaterialBatchUploadTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_storage = admin_pages.material_storage
        admin_pages.material_storage = MaterialStorage(self.temp_dir.name)

    def tearDown(self):
        admin_pages.material_storage = self.original_storage
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def upload(self, filename: str, content: bytes = b"test content") -> UploadFile:
        return UploadFile(io.BytesIO(content), filename=filename)

    async def test_creates_one_material_per_uploaded_file(self):
        form = FormData(
            [
                ("file", self.upload("七上地理期中试卷.pdf")),
                ("file", self.upload("英语复习资料.docx")),
                ("summary", "期中复习资料"),
                ("status", "published"),
            ]
        )

        await admin_pages.create_material(form, self.db)

        materials = self.db.scalars(select(models.Material).order_by(models.Material.title)).all()
        self.assertEqual([item.title for item in materials], ["七上地理期中试卷", "英语复习资料"])
        self.assertTrue(all(item.summary == "期中复习资料" for item in materials))
        self.assertTrue(all(item.status == "published" for item in materials))
        self.assertEqual(len(list(Path(self.temp_dir.name).iterdir())), 2)

    async def test_invalid_file_rolls_back_rows_and_saved_files(self):
        form = FormData(
            [
                ("file", self.upload("有效资料.pdf")),
                ("file", self.upload("不支持.exe")),
                ("status", "published"),
            ]
        )

        with self.assertRaises(HTTPException):
            await admin_pages.create_material(form, self.db)

        self.assertEqual(self.db.scalar(select(func.count(models.Material.id))), 0)
        self.assertEqual(list(Path(self.temp_dir.name).glob("*")), [])


if __name__ == "__main__":
    unittest.main()
