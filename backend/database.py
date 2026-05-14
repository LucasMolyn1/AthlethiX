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
        # ── V1 — tables existantes, non modifiées ──────────────────────────
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

        # ── V2 — nouvelles tables (migration additive) ─────────────────────
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS exercises (
                id          INTEGER PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                category    TEXT NOT NULL CHECK(category IN ('push','pull','legs','core','cardio')),
                is_custom   INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS strength_sessions (
                id              INTEGER PRIMARY KEY,
                date            TEXT NOT NULL,
                duration        INTEGER,
                session_type    TEXT,
                context         TEXT,
                fatigue_score   INTEGER CHECK(fatigue_score BETWEEN 1 AND 10),
                sleep_score     INTEGER CHECK(sleep_score BETWEEN 1 AND 10),
                feeling_score   INTEGER CHECK(feeling_score BETWEEN 1 AND 10),
                notes           TEXT,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at      TEXT
            );

            CREATE TABLE IF NOT EXISTS exercise_sets (
                id          INTEGER PRIMARY KEY,
                session_id  INTEGER NOT NULL REFERENCES strength_sessions(id) ON DELETE CASCADE,
                exercise_id INTEGER NOT NULL REFERENCES exercises(id),
                set_number  INTEGER NOT NULL,
                reps        INTEGER,
                weight_kg   REAL,
                feeling     INTEGER CHECK(feeling BETWEEN 1 AND 5),
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY,
                type        TEXT NOT NULL,
                level       TEXT NOT NULL CHECK(level IN ('danger','warning','info','success')),
                message     TEXT NOT NULL,
                is_read     INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS nutrition_logs (
                id                  INTEGER PRIMARY KEY,
                date                TEXT NOT NULL UNIQUE,
                hydration_liters    REAL,
                nutrition_score     INTEGER CHECK(nutrition_score BETWEEN 1 AND 10),
                pre_workout_meal    TEXT,
                post_workout_meal   TEXT,
                supplements         TEXT,
                notes               TEXT,
                created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at          TEXT
            );
        """)

        # ── V3 — migration Strava ─────────────────────────────────────────
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        conn.commit()
    finally:
        conn.close()

    _seed_exercises()


# Bibliothèque d'exercices par défaut — insérée une seule fois (INSERT OR IGNORE)
_DEFAULT_EXERCISES = [
    ("Squat",                    "legs"),
    ("Deadlift",                 "legs"),
    ("Bench Press",              "push"),
    ("Overhead Press",           "push"),
    ("Pull-up",                  "pull"),
    ("Dips",                     "push"),
    ("Rowing Barre",             "pull"),
    ("Fentes",                   "legs"),
    ("Hip Thrust",               "legs"),
    ("Planche",                  "core"),
    ("Développé Incliné",        "push"),
    ("Curl Biceps",              "pull"),
    ("Triceps Poulie",           "push"),
    ("Leg Press",                "legs"),
    ("Soulevé de Terre Roumain", "legs"),
    ("Kettlebell Swing",         "cardio"),
]


def _seed_exercises() -> None:
    """Insère la bibliothèque d'exercices par défaut si elle est vide. Idempotent."""
    conn = get_connection()
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO exercises (name, category, is_custom) VALUES (?, ?, 0)",
            _DEFAULT_EXERCISES,
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = Path(DATABASE_PATH)
    print(f"Initialisation de la base de données : {db_path.resolve()}")
    init_db()
    print("Tables créées avec succès.")
