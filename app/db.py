"""Conexiones cortas y transacciones para SQLite."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


@contextmanager
def connection():
    path = Path(os.environ.get("DATABASE_PATH", "data/courtflow.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 15000")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    with connection() as db:
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if not db.execute("SELECT 1 FROM courts LIMIT 1").fetchone():
            courts = [
                ("Loza Central", "Sede Centro", "Fútbol", 14, 6000),
                ("Loza Las Palmeras", "Sede Norte", "Vóley", 12, 4000),
                ("Loza El Mirador", "Sede Sur", "Básquet", 10, 4500),
            ]
            db.executemany(
                "INSERT INTO courts(name,venue,sport,capacity,hourly_rate) VALUES(?,?,?,?,?)",
                courts,
            )
            db.executemany(
                "INSERT INTO schedules(court_id,weekday,opens,closes) VALUES(?,?,480,1380)",
                [(court_id, day) for court_id in (1, 2, 3) for day in range(7)],
            )
