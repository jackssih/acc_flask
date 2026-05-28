import sqlite3
from pathlib import Path

DB_PATH = Path("choir_data.db")


def connect_db(row_factory: bool = False):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS choir_data (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            identification_no TEXT    UNIQUE NOT NULL,
            name              TEXT,
            choir             TEXT,
            gender            TEXT,
            status            TEXT DEFAULT 'alive',
            comment           TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS graduation_data (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            identification_no  TEXT NOT NULL,
            institute          TEXT,
            course_name        TEXT,
            duration           TEXT,
            year_of_graduation INTEGER,
            FOREIGN KEY (identification_no)
                REFERENCES choir_data(identification_no)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT DEFAULT 'viewer'
        );
    """)
    conn.commit()
    conn.close()
