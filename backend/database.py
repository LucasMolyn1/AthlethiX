"""
Couche base de données — connexion SQLite et initialisation des tables.

SQLite est utilisé comme un simple fichier. Pas de serveur, pas de daemon.
Le chemin est configuré via DATABASE_PATH dans .env.
"""

import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "./athletix.db")


def get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite avec row_factory pour accéder aux colonnes par nom."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Active les foreign keys (désactivées par défaut dans SQLite)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Crée les tables si elles n'existent pas encore. Idempotent."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS activities (
                id          INTEGER PRIMARY KEY,
                garmin_id   TEXT UNIQUE NOT NULL,
                type        TEXT NOT NULL,
                date        TEXT NOT NULL,
                duration    INTEGER,
                distance    REAL,
                elevation_gain REAL,
                avg_hr      INTEGER,
                max_hr      INTEGER,
                calories    INTEGER,
                raw_json    TEXT,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id              INTEGER PRIMARY KEY,
                activity_id     INTEGER REFERENCES activities(id) ON DELETE CASCADE,
                context         TEXT,
                feeling_score   INTEGER CHECK(feeling_score BETWEEN 1 AND 10),
                fatigue_score   INTEGER CHECK(fatigue_score BETWEEN 1 AND 10),
                sleep_score     INTEGER CHECK(sleep_score BETWEEN 1 AND 10),
                pain_notes      TEXT,
                free_notes      TEXT,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at      TEXT
            );

            CREATE TABLE IF NOT EXISTS sync_log (
                id          INTEGER PRIMARY KEY,
                synced_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                status      TEXT NOT NULL,
                activities_added INTEGER DEFAULT 0,
                error_msg   TEXT
            );
        """)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = Path(DATABASE_PATH)
    print(f"Initialisation de la base de données : {db_path.resolve()}")
    init_db()
    print("Tables créées avec succès.")
