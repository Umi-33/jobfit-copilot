import json
from contextlib import closing
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .database import DatabasePath, connect_database


ALLOWED_STATUSES = frozenset(
    {
        "pending_confirmation",
        "not_suitable",
        "preparing_application",
        "applied",
        "preparing_interview",
        "archived",
    }
)
DEFAULT_STATUS = "pending_confirmation"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _detail_from_row(row) -> Dict:
    result = dict(row)
    result["unknown_items"] = json.loads(result.pop("unknown_items_json"))
    result["analysis"] = json.loads(result.pop("analysis_json"))
    result["action_plan"] = json.loads(result.pop("action_plan_json"))
    return result


def create_job_record(
    company_name: str,
    job_title: str,
    city: str,
    profile_snapshot: str,
    jd_text: str,
    analysis: Dict,
    action_plan: Dict,
    status: str = DEFAULT_STATUS,
    database_path: DatabasePath = None,
) -> Dict:
    """Save one analysis snapshot and return its complete record."""
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported job record status: {status}")

    timestamp = _now_iso()
    with closing(connect_database(database_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO job_records (
                    company_name, job_title, city, jd_text, profile_snapshot,
                    rating, decision, risk_level, unknown_items_json,
                    analysis_json, action_plan_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_name,
                    job_title,
                    city,
                    jd_text,
                    profile_snapshot,
                    analysis["rating"],
                    analysis["decision"],
                    analysis["risk_level"],
                    _to_json(analysis.get("unknown_items", [])),
                    _to_json(analysis),
                    _to_json(action_plan),
                    status,
                    timestamp,
                    timestamp,
                ),
            )
            record_id = cursor.lastrowid

    record = get_job_record(record_id, database_path)
    if record is None:
        raise RuntimeError("created job record could not be read back")
    return record


def list_job_records(database_path: DatabasePath = None) -> List[Dict]:
    """Return only fields needed by the job history list."""
    with closing(connect_database(database_path)) as connection:
        rows = connection.execute(
            """
            SELECT id, company_name, job_title, city, rating, decision,
                   risk_level, status, created_at, updated_at
            FROM job_records
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_job_record(record_id: int, database_path: DatabasePath = None) -> Optional[Dict]:
    """Return one complete record with stored JSON restored to Python values."""
    with closing(connect_database(database_path)) as connection:
        row = connection.execute(
            """
            SELECT id, company_name, job_title, city, jd_text, profile_snapshot,
                   rating, decision, risk_level, unknown_items_json,
                   analysis_json, action_plan_json, status, created_at, updated_at
            FROM job_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
    return _detail_from_row(row) if row is not None else None


def update_job_record_status(
    record_id: int,
    status: str,
    database_path: DatabasePath = None,
) -> Optional[Dict]:
    """Update one valid status and return the changed status fields."""
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported job record status: {status}")

    updated_at = _now_iso()
    with closing(connect_database(database_path)) as connection:
        with connection:
            cursor = connection.execute(
                "UPDATE job_records SET status = ?, updated_at = ? WHERE id = ?",
                (status, updated_at, record_id),
            )
            if cursor.rowcount == 0:
                return None
    return {"id": record_id, "status": status, "updated_at": updated_at}
