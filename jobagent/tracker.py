"""Capability 3: track applications in a local SQLite database.

No server, no account — a single file (default: data/applications.db). Includes
CSV export so you can pull everything into a spreadsheet or share progress.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .models import Application, Job

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    job_id     TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    company    TEXT NOT NULL,
    url        TEXT,
    status     TEXT NOT NULL DEFAULT 'saved',
    notes      TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Tracker:
    def __init__(self, db_path: str | Path = "data/applications.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def save_job(self, job: Job, status: str = "saved", notes: str = "") -> Application:
        app = Application(
            job_id=job.id, title=job.title, company=job.company, url=job.url,
            status=status, notes=notes,
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO applications "
            "(job_id, title, company, url, status, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (app.job_id, app.title, app.company, app.url, app.status, app.notes,
             app.created_at, app.updated_at),
        )
        self.conn.commit()
        return app

    def set_status(self, job_id: str, status: str) -> bool:
        if status not in Application.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Use one of: {', '.join(Application.VALID_STATUSES)}"
            )
        from .models import _now

        cur = self.conn.execute(
            "UPDATE applications SET status = ?, updated_at = ? WHERE job_id = ?",
            (status, _now(), job_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def add_note(self, job_id: str, note: str) -> bool:
        from .models import _now

        cur = self.conn.execute(
            "UPDATE applications SET notes = ?, updated_at = ? WHERE job_id = ?",
            (note, _now(), job_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def list(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM applications ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def export_csv(self, path: str | Path) -> Path:
        path = Path(path)
        rows = self.list()
        fields = ["job_id", "title", "company", "url", "status", "notes",
                  "created_at", "updated_at"]
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path
