from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema_compatibility()


def _ensure_schema_compatibility(target_engine=engine) -> None:
    """Add nullable columns introduced after the initial database bootstrap."""
    inspector = inspect(target_engine)
    tables = set(inspector.get_table_names())
    with target_engine.begin() as connection:
        if "leads" in tables:
            lead_columns = {column["name"] for column in inspector.get_columns("leads")}
            if "child_school" not in lead_columns:
                connection.execute(text("ALTER TABLE leads ADD COLUMN child_school VARCHAR(120)"))
            if "child_name" not in lead_columns:
                connection.execute(text("ALTER TABLE leads ADD COLUMN child_name VARCHAR(80)"))
            if target_engine.dialect.name == "postgresql":
                connection.execute(text("ALTER TABLE leads ALTER COLUMN child_name DROP NOT NULL"))
                connection.execute(text("ALTER TABLE leads ALTER COLUMN child_age DROP NOT NULL"))
                connection.execute(text("ALTER TABLE leads ALTER COLUMN child_grade DROP NOT NULL"))

        if "campuses" in tables:
            campus_columns = {column["name"] for column in inspector.get_columns("campuses")}
            if "manager_name" not in campus_columns:
                connection.execute(text("ALTER TABLE campuses ADD COLUMN manager_name VARCHAR(80)"))

        if "attendance_records" in tables:
            attendance_columns = {
                column["name"] for column in inspector.get_columns("attendance_records")
            }
            legacy_without_periods = not {
                "morning_present",
                "afternoon_present",
            }.intersection(attendance_columns)
            if "morning_present" not in attendance_columns:
                connection.execute(
                    text(
                        "ALTER TABLE attendance_records "
                        "ADD COLUMN morning_present BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
            if "afternoon_present" not in attendance_columns:
                connection.execute(
                    text(
                        "ALTER TABLE attendance_records "
                        "ADD COLUMN afternoon_present BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
            if legacy_without_periods:
                connection.execute(
                    text(
                        "UPDATE attendance_records "
                        "SET morning_present = TRUE, afternoon_present = TRUE"
                    )
                )
