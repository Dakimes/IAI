import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

DB_PATH = Path(__file__).resolve().parent / "iai.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(current_revision: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            iai REAL NOT NULL,
            subindices_json TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            revision TEXT NOT NULL DEFAULT ''
        )
        """
    )
    _ensure_revision_column(cur)
    cur.execute("UPDATE companies SET revision = COALESCE(revision, '') WHERE revision IS NULL")
    conn.commit()
    conn.close()


def _ensure_revision_column(cur: sqlite3.Cursor):
    cur.execute("PRAGMA table_info(companies)")
    cols = {row[1] for row in cur.fetchall()}
    if "revision" not in cols:
        cur.execute("ALTER TABLE companies ADD COLUMN revision TEXT NOT NULL DEFAULT ''")


def fetch_companies():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT slug, name, iai, revision FROM companies ORDER BY iai DESC, created_at DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_company(slug: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM companies WHERE slug = ?", (slug,))
    row = cur.fetchone()
    conn.close()
    return row


def fetch_outdated_companies(revision: str) -> Iterable[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM companies WHERE revision != ? OR revision IS NULL", (revision,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def insert_company(slug: str, name: str, iai: float, subindices: dict, revision: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO companies (slug, name, iai, subindices_json, created_at, revision) VALUES (?, ?, ?, ?, ?, ?)",
        (
            slug,
            name,
            iai,
            json.dumps(subindices, ensure_ascii=False),
            datetime.utcnow().isoformat(),
            revision,
        ),
    )
    conn.commit()
    conn.close()


def update_company(slug: str, name: str, iai: float, subindices: dict, revision: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE companies SET name = ?, iai = ?, subindices_json = ?, revision = ?, created_at = ? WHERE slug = ?",
        (
            name,
            iai,
            json.dumps(subindices, ensure_ascii=False),
            revision,
            datetime.utcnow().isoformat(),
            slug,
        ),
    )
    conn.commit()
    conn.close()
