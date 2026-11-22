import unittest

from sqlalchemy import create_engine, inspect, text

from app.db import _ensure_schema_compatibility
from app.domain.leads import validate_lead_input


class ChildNameTest(unittest.TestCase):
    def payload(self):
        return dict(name="家长", phone="13800138000", child_age=10,
                    child_grade="四年级", source="trial", campus_id="campus-1",
                    appointment_at="2099-01-01T14:30:00+08:00")

    def test_child_name_is_optional(self):
        self.assertTrue(validate_lead_input(self.payload()).ok)
        for name in [123, "名" * 81]:
            with self.subTest(name=name):
                result = validate_lead_input({**self.payload(), "child_name": name})
                self.assertIn("child_name", result.errors)
        result = validate_lead_input({**self.payload(), "child_name": " 小明 "})
        self.assertTrue(result.ok)
        self.assertEqual(result.value["child_name"], "小明")

    def test_migration_on_empty_test_table_is_repeatable(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE leads (id VARCHAR(32) PRIMARY KEY, name VARCHAR(80))"))
        _ensure_schema_compatibility(engine)
        _ensure_schema_compatibility(engine)
        columns = {column["name"]: column for column in inspect(engine).get_columns("leads")}
        self.assertTrue(columns["child_name"]["nullable"])
        with engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT count(*) FROM leads")).scalar_one(), 0)
        engine.dispose()

    def test_school_is_optional_trimmed_and_length_limited(self):
        payload = {**self.payload(), "child_name": "小明"}
        for school in [None, "", "  "]:
            result = validate_lead_input({**payload, "child_school": school})
            self.assertTrue(result.ok)
            self.assertIsNone(result.value["child_school"])
        self.assertTrue(validate_lead_input(payload).ok)
        self.assertEqual(validate_lead_input({**payload, "child_school": " 实验小学 "}).value["child_school"], "实验小学")
        for school in [123, "校" * 121]:
            self.assertIn("child_school", validate_lead_input({**payload, "child_school": school}).errors)

    def test_school_migration_keeps_existing_appointments(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE leads (id VARCHAR(32), child_name VARCHAR(80) NOT NULL)"))
            connection.execute(text("INSERT INTO leads VALUES ('existing', '小明')"))
        _ensure_schema_compatibility(engine)
        _ensure_schema_compatibility(engine)
        with engine.connect() as connection:
            self.assertEqual(tuple(connection.execute(text("SELECT id, child_name, child_school FROM leads")).one()), ("existing", "小明", None))
        engine.dispose()
