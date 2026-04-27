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


@router.get("/extras")
def dashboard_extras():
    """
    Données V2 : nutrition + musculation de la semaine courante.
    Utilisé par les widgets du dashboard.
    """
    monday = datetime.now() - timedelta(days=datetime.now().weekday())
    monday_str = monday.strftime("%Y-%m-%d")
    today_str  = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    try:
        nut_rows = conn.execute(
            "SELECT hydration_liters, nutrition_score FROM nutrition_logs WHERE date >= ? AND date <= ?",
            (monday_str, today_str),
        ).fetchall()

        days_logged  = len(nut_rows)
        hydrations   = [r["hydration_liters"] for r in nut_rows if r["hydration_liters"] is not None]
        scores       = [r["nutrition_score"]  for r in nut_rows if r["nutrition_score"]  is not None]
        avg_hydration = round(sum(hydrations) / len(hydrations), 1) if hydrations else None
        avg_score     = round(sum(scores)     / len(scores),     1) if scores     else None

        str_row = conn.execute(
            """
            SELECT
                COUNT(DISTINCT ss.id)                       AS sessions_count,
                COUNT(s.id)                                 AS total_sets,
                COALESCE(SUM(s.weight_kg * s.reps), 0)     AS total_volume
            FROM strength_sessions ss
            LEFT JOIN exercise_sets s ON s.session_id = ss.id
            WHERE ss.date >= ?
            """,
            (monday_str,),
        ).fetchone()

        return {
            "nutrition": {
                "days_logged":    days_logged,
                "avg_hydration":  avg_hydration,
                "avg_score":      avg_score,
            },
            "strength": {
                "sessions_count": str_row["sessions_count"],
                "total_sets":     str_row["total_sets"],
                "total_volume":   round(str_row["total_volume"]),
            },
        }
    finally:
        conn.close()
