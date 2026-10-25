"""SQLite persistence. Deliberately one connection per request and no global cursor."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  csrf TEXT NOT NULL, expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, offer TEXT NOT NULL DEFAULT '',
  target_industries TEXT NOT NULL DEFAULT '', target_customer TEXT NOT NULL DEFAULT '',
  geography TEXT NOT NULL DEFAULT '', customer_problem TEXT NOT NULL DEFAULT '',
  differentiator TEXT NOT NULL DEFAULT '', price_model TEXT NOT NULL DEFAULT '',
  lead_source TEXT NOT NULL DEFAULT '', contact_strategy TEXT NOT NULL DEFAULT '',
  tone TEXT NOT NULL DEFAULT '', sender_name TEXT NOT NULL DEFAULT '',
  sender_company TEXT NOT NULL DEFAULT '', sender_email TEXT NOT NULL DEFAULT '',
  sender_address TEXT NOT NULL DEFAULT '', sender_site TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  business TEXT NOT NULL, contact_name TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
  phone TEXT NOT NULL DEFAULT '', website TEXT NOT NULL DEFAULT '',
  industry TEXT NOT NULL DEFAULT '', address TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '', evidence TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','qualified','contacted','replied','won','lost')),
  score INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'manual',
  source_ref TEXT NOT NULL DEFAULT '', permission TEXT NOT NULL DEFAULT 'none'
    CHECK(permission IN ('none','consent','existing_customer')),
  permission_evidence TEXT NOT NULL DEFAULT '', permission_date TEXT NOT NULL DEFAULT '',
  last_contact_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_leads_project ON leads(project_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_lead_source ON leads(project_id, source, source_ref) WHERE source_ref != '';
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY, lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  subject TEXT NOT NULL, body TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'draft'
    CHECK(state IN ('draft','approved','sending','sent','failed')),
  error TEXT NOT NULL DEFAULT '', sent_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_messages_lead ON messages(lead_id);
CREATE TABLE IF NOT EXISTS suppression (
  email TEXT PRIMARY KEY, reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS activities (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE, type TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '', at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS discovery_jobs (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  provider TEXT NOT NULL, query TEXT NOT NULL, city TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued', imported INTEGER NOT NULL DEFAULT 0,
  error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT
);
"""


def database_path():
    return Path(os.getenv("VALDRIQ_DB", "./data/valdriq.db")).resolve()


def initialize(path=None):
    destination = Path(path) if path else database_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(destination) as connection:
        connection.executescript(SCHEMA)
    return destination


@contextmanager
def connect(path=None):
    database = Path(path) if path else database_path()
    connection = sqlite3.connect(database, timeout=8)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=8000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]


def one(cursor):
    found = cursor.fetchone()
    return dict(found) if found else None
