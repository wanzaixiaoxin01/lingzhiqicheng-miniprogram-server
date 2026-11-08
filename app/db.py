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


def _ensure_schema_compatibility() -> None:
    """Add nullable columns introduced after the initial database bootstrap."""
    columns = {column["name"] for column in inspect(engine).get_columns("campuses")}
    if "manager_name" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE campuses ADD COLUMN manager_name VARCHAR(80)"))
