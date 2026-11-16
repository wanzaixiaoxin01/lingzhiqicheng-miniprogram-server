"""Copy the current Lingzhi data from SQLite into an empty PostgreSQL database."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import create_engine, func, select

from app import models  # noqa: F401
from app.config import settings
from app.db import Base


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="path to the SQLite database")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = args.source.expanduser().resolve()
    if not source_path.is_file():
        raise SystemExit(f"SQLite database does not exist: {source_path}")
    if not settings.database_url.startswith("postgresql"):
        raise SystemExit("DATABASE_URL must point to PostgreSQL")

    source = create_engine(f"sqlite+pysqlite:///{source_path}")
    target = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(target)

    with target.connect() as connection:
        populated = [
            table.name
            for table in Base.metadata.sorted_tables
            if connection.execute(select(func.count()).select_from(table)).scalar_one()
        ]
    if populated:
        raise SystemExit(f"target database is not empty: {', '.join(populated)}")

    copied: list[tuple[str, int]] = []
    with source.connect() as source_connection, target.begin() as target_connection:
        for table in Base.metadata.sorted_tables:
            rows = source_connection.execute(select(table)).mappings().all()
            if rows:
                target_connection.execute(table.insert(), [dict(row) for row in rows])
            copied.append((table.name, len(rows)))

    for table_name, count in copied:
        print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
