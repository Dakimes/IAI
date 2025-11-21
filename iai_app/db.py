import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "iai.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
            created_at DATETIME NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_companies():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT slug, name, iai FROM companies ORDER BY iai DESC, created_at DESC"
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


def insert_company(slug: str, name: str, iai: float, subindices: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO companies (slug, name, iai, subindices_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (slug, name, iai, json.dumps(subindices, ensure_ascii=False), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
