"""
Router FastAPI — données dashboard.

Routes :
    GET /api/dashboard/week         — résumé de la semaine courante par sport
    GET /api/dashboard/fitness      — courbe de forme sur 30 jours
    GET /api/dashboard/recent       — 5 dernières activités
    GET /api/dashboard/sync-status  — statut de la dernière synchronisation
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
from database import get_connection

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/week")
def week_summary():
    """
    Résumé de la semaine en cours, agrégé par type de sport.

    Retourne pour chaque sport : nombre de séances, distance totale (m),
    durée totale (s), dénivelé total (m).
    """
    monday = datetime.now() - timedelta(days=datetime.now().weekday())
    monday_str = monday.strftime("%Y-%m-%d")

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                type,
                COUNT(*)        AS sessions,
                SUM(distance)   AS total_distance,
                SUM(duration)   AS total_duration,
                SUM(elevation_gain) AS total_elevation
            FROM activities
            WHERE date >= ?
            GROUP BY type
            """,
            (monday_str,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/fitness")
def fitness_curve():
    """
    Courbe de forme sur les 30 derniers jours.

    Charge d'entraînement journalière = somme des (durée_min * FC_moyenne / 100)
    pour chaque activité du jour. Approximation simple de la charge TRIMP.
    Retourne une liste de {date, load} triée chronologiquement.
    """
    since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                substr(date, 1, 10) AS day,
                SUM(
                    CASE
                        WHEN avg_hr IS NOT NULL AND avg_hr > 0
                        THEN (duration / 60.0) * (avg_hr / 100.0)
                        ELSE duration / 60.0 * 0.5
                    END
                ) AS load
            FROM activities
            WHERE date >= ?
            GROUP BY day
            ORDER BY day ASC
            """,
            (since,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/recent")
def recent_activities():
    """Retourne les 5 dernières activités (id, type, date, durée, distance)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, type, date, duration, distance, elevation_gain, avg_hr
            FROM activities
            ORDER BY date DESC
            LIMIT 5
            """,
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/sync-status")
def sync_status():
    """Retourne le statut et la date de la dernière synchronisation."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT synced_at, status, activities_added, error_msg FROM sync_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return {"last_sync": None, "status": "never"}
        return dict(row)
    finally:
        conn.close()
