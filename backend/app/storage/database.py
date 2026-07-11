import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Optional, Union


DATABASE_ENV_VAR = "JOBFIT_DATABASE_PATH"
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "jobfit_copilot.sqlite3"
DatabasePath = Optional[Union[str, Path]]


def resolve_database_path(database_path: DatabasePath = None) -> Path:
    """Resolve an explicit, environment, or default SQLite database path."""
    if database_path is not None:
        return Path(database_path)
    configured_path = os.getenv(DATABASE_ENV_VAR)
    return Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH


def connect_database(database_path: DatabasePath = None) -> sqlite3.Connection:
    """Create a configured SQLite connection for one repository operation."""
    connection = sqlite3.connect(resolve_database_path(database_path), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: DatabasePath = None) -> None:
    """Create the database directory and the V1.5 job records table."""
    resolved_path = resolve_database_path(database_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(connect_database(resolved_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS job_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    city TEXT NOT NULL,
                    jd_text TEXT NOT NULL,
                    profile_snapshot TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    unknown_items_json TEXT NOT NULL,
                    analysis_json TEXT NOT NULL,
                    action_plan_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
