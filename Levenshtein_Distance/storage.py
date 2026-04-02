from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .engine import default_field_configs


APP_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = APP_ROOT / "prototype.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def open_connection():
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database() -> None:
    with open_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS field_configs (
                key TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                comparator TEXT NOT NULL,
                weight REAL NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS comparison_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_a_filename TEXT NOT NULL,
                dataset_b_filename TEXT NOT NULL,
                dataset_a_mapping_json TEXT NOT NULL,
                dataset_b_mapping_json TEXT NOT NULL,
                matched_count INTEGER NOT NULL,
                issue_count INTEGER NOT NULL,
                high_count INTEGER NOT NULL,
                medium_count INTEGER NOT NULL,
                low_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS comparison_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                phone_key TEXT NOT NULL,
                overall_score REAL NOT NULL,
                band TEXT NOT NULL,
                reviewer_status TEXT NOT NULL DEFAULT 'Pending',
                reviewer_note TEXT NOT NULL DEFAULT '',
                breakdown_json TEXT NOT NULL,
                dataset_a_record_json TEXT NOT NULL,
                dataset_b_record_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES comparison_runs(id)
            );

            CREATE TABLE IF NOT EXISTS comparison_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                phone_key TEXT,
                issue_type TEXT NOT NULL,
                source_context TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES comparison_runs(id)
            );
            """
        )

        existing_count = connection.execute("SELECT COUNT(*) FROM field_configs").fetchone()[0]
        if existing_count == 0:
            created_at = datetime.now(UTC).isoformat()
            for position, field_config in enumerate(default_field_configs()):
                connection.execute(
                    """
                    INSERT INTO field_configs (key, label, comparator, weight, active, position, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        field_config["key"],
                        field_config["label"],
                        field_config["comparator"],
                        field_config["weight"],
                        1 if field_config["active"] else 0,
                        position,
                        created_at,
                    ),
                )


def load_field_configs() -> list[dict[str, Any]]:
    with open_connection() as connection:
        rows = connection.execute(
            """
            SELECT key, label, comparator, weight, active
            FROM field_configs
            ORDER BY position ASC, created_at ASC
            """
        ).fetchall()
    return [
        {
            "key": row["key"],
            "label": row["label"],
            "comparator": row["comparator"],
            "weight": float(row["weight"]),
            "active": bool(row["active"]),
        }
        for row in rows
    ]


def save_field_configs(field_configs: list[dict[str, Any]]) -> None:
    with open_connection() as connection:
        connection.execute("DELETE FROM field_configs")
        created_at = datetime.now(UTC).isoformat()
        for position, field_config in enumerate(field_configs):
            connection.execute(
                """
                INSERT INTO field_configs (key, label, comparator, weight, active, position, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    field_config["key"],
                    field_config["label"],
                    field_config["comparator"],
                    float(field_config["weight"]),
                    1 if field_config.get("active", True) else 0,
                    position,
                    created_at,
                ),
            )


def create_run(
    dataset_a_filename: str,
    dataset_b_filename: str,
    dataset_a_mapping: dict[str, str],
    dataset_b_mapping: dict[str, str],
    results: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    summary: dict[str, int],
) -> int:
    created_at = datetime.now(UTC).isoformat()
    with open_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO comparison_runs (
                dataset_a_filename,
                dataset_b_filename,
                dataset_a_mapping_json,
                dataset_b_mapping_json,
                matched_count,
                issue_count,
                high_count,
                medium_count,
                low_count,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_a_filename,
                dataset_b_filename,
                json.dumps(dataset_a_mapping),
                json.dumps(dataset_b_mapping),
                summary["matched_count"],
                summary["issue_count"],
                summary["high_count"],
                summary["medium_count"],
                summary["low_count"],
                created_at,
            ),
        )
        run_id = int(cursor.lastrowid)

        for result in results:
            connection.execute(
                """
                INSERT INTO comparison_results (
                    run_id,
                    phone_key,
                    overall_score,
                    band,
                    reviewer_status,
                    reviewer_note,
                    breakdown_json,
                    dataset_a_record_json,
                    dataset_b_record_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    result["phone_key"],
                    result["overall_score"],
                    result["band"],
                    "Pending",
                    "",
                    json.dumps(result["breakdowns"]),
                    json.dumps(result["dataset_a_record"]),
                    json.dumps(result["dataset_b_record"]),
                    created_at,
                ),
            )

        for issue in issues:
            connection.execute(
                """
                INSERT INTO comparison_issues (
                    run_id,
                    phone_key,
                    issue_type,
                    source_context,
                    details_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    issue.get("phone_key", ""),
                    issue["issue_type"],
                    issue["source_context"],
                    json.dumps(issue["details"]),
                    created_at,
                ),
            )

    return run_id


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    with open_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM comparison_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    with open_connection() as connection:
        row = connection.execute(
            "SELECT * FROM comparison_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    return dict(row) if row else None


def get_run_results(
    run_id: int,
    band: str = "",
    reviewer_status: str = "",
    phone_query: str = "",
    limit: int = 250,
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM comparison_results
        WHERE run_id = ?
    """
    params: list[Any] = [run_id]

    if band:
        query += " AND band = ?"
        params.append(band)
    if reviewer_status:
        query += " AND reviewer_status = ?"
        params.append(reviewer_status)
    if phone_query:
        query += " AND phone_key LIKE ?"
        params.append(f"%{phone_query}%")

    query += " ORDER BY overall_score DESC, id ASC LIMIT ?"
    params.append(limit)

    with open_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    results = []
    for row in rows:
        result = dict(row)
        result["breakdowns"] = json.loads(result["breakdown_json"])
        result["dataset_a_record"] = json.loads(result["dataset_a_record_json"])
        result["dataset_b_record"] = json.loads(result["dataset_b_record_json"])
        results.append(result)
    return results


def get_result(result_id: int) -> dict[str, Any] | None:
    with open_connection() as connection:
        row = connection.execute(
            "SELECT * FROM comparison_results WHERE id = ?",
            (result_id,),
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["breakdowns"] = json.loads(result["breakdown_json"])
    result["dataset_a_record"] = json.loads(result["dataset_a_record_json"])
    result["dataset_b_record"] = json.loads(result["dataset_b_record_json"])
    return result


def get_run_issues(run_id: int, limit: int = 250) -> list[dict[str, Any]]:
    with open_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM comparison_issues
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (run_id, limit),
        ).fetchall()
    issues = []
    for row in rows:
        issue = dict(row)
        issue["details"] = json.loads(issue["details_json"])
        issues.append(issue)
    return issues


def update_result_review(result_id: int, reviewer_status: str, reviewer_note: str) -> None:
    with open_connection() as connection:
        connection.execute(
            """
            UPDATE comparison_results
            SET reviewer_status = ?, reviewer_note = ?
            WHERE id = ?
            """,
            (reviewer_status, reviewer_note.strip(), result_id),
        )


initialize_database()
