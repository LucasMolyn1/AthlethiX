"""
Router FastAPI — module comparaison.

Routes :
    GET /api/compare/periods   — compare deux plages de dates (cardio + musculation)
    GET /api/compare/exercises — compare la progression de deux exercices (1RM Epley)
"""

from fastapi import APIRouter, HTTPException, Query
from database import get_connection

router = APIRouter(prefix="/api/compare", tags=["compare"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _epley_1rm(weight_kg: float, reps: int) -> float:
    if reps <= 0 or weight_kg <= 0:
        return 0.0
    return round(weight_kg * (1 + reps / 30), 1)


def _period_stats(conn, date_from: str, date_to: str) -> dict:
    """Agrège les métriques d'entraînement sur une plage de dates."""
    date_to_full = date_to + "T23:59:59"

    # Activités Garmin par type
    act_rows = conn.execute(
        """
        SELECT type,
               COUNT(*)                    AS cnt,
               COALESCE(SUM(duration), 0)  AS total_dur,
               COALESCE(SUM(distance), 0)  AS total_dist
        FROM activities
        WHERE date >= ? AND date <= ?
        GROUP BY type
        """,
        (date_from, date_to_full),
    ).fetchall()

    by_type: dict = {}
    total_count    = 0
    total_duration = 0
    total_distance = 0.0
    for r in act_rows:
        by_type[r["type"]] = {
            "count":       r["cnt"],
            "duration_s":  r["total_dur"],
            "distance_km": round(r["total_dist"] / 1000, 1) if r["total_dist"] else 0.0,
        }
        total_count    += r["cnt"]
        total_duration += r["total_dur"]
        total_distance += r["total_dist"] or 0.0

    # Séances de musculation par type
    str_rows = conn.execute(
        """
        SELECT s.session_type,
               COUNT(DISTINCT s.id) AS sessions,
               COUNT(es.id)         AS sets_total
        FROM strength_sessions s
        LEFT JOIN exercise_sets es ON es.session_id = s.id
        WHERE s.date >= ? AND s.date <= ?
        GROUP BY s.session_type
        """,
        (date_from, date_to_full),
    ).fetchall()

    str_by_type: dict = {}
    str_sessions = 0
    str_sets     = 0
    for r in str_rows:
        key = r["session_type"] or "other"
        str_by_type[key]  = r["sessions"]
        str_sessions     += r["sessions"]
        str_sets         += r["sets_total"]

    # Jours actifs : union des jours activities + strength_sessions
    active_days: set = set()
    for r in conn.execute(
        "SELECT DISTINCT substr(date,1,10) AS d FROM activities WHERE date >= ? AND date <= ?",
        (date_from, date_to_full),
    ).fetchall():
        active_days.add(r["d"])
    for r in conn.execute(
        "SELECT DISTINCT substr(date,1,10) AS d FROM strength_sessions WHERE date >= ? AND date <= ?",
        (date_from, date_to_full),
    ).fetchall():
        active_days.add(r["d"])

    return {
        "from": date_from,
        "to":   date_to,
        "activities": {
            "total_count":       total_count,
            "total_duration_s":  total_duration,
            "total_distance_km": round(total_distance / 1000, 1),
            "by_type":           by_type,
        },
        "strength": {
            "sessions_count": str_sessions,
            "total_sets":     str_sets,
            "by_type":        str_by_type,
        },
        "active_days": len(active_days),
    }


def _exercise_stats(conn, exercise_id: int) -> dict:
    """Retourne la progression complète d'un exercice (même logique que strength.py)."""
    exercise = conn.execute(
        "SELECT * FROM exercises WHERE id = ?", (exercise_id,)
    ).fetchone()
    if not exercise:
        raise HTTPException(status_code=404, detail=f"Exercice {exercise_id} introuvable")

    rows = conn.execute(
        """
        SELECT substr(s.date, 1, 10) AS day,
               s.id                  AS session_id,
               es.reps,
               es.weight_kg
        FROM exercise_sets es
        JOIN strength_sessions s ON s.id = es.session_id
        WHERE es.exercise_id = ?
        ORDER BY s.date ASC
        """,
        (exercise_id,),
    ).fetchall()

    days: dict = {}
    for r in rows:
        day = r["day"]
        if day not in days:
            days[day] = {
                "date":         day,
                "session_id":   r["session_id"],
                "max_weight":   0.0,
                "best_1rm":     0.0,
                "total_volume": 0.0,
                "sets_count":   0,
            }
        d    = days[day]
        d["sets_count"] += 1
        w    = r["weight_kg"] or 0.0
        reps = r["reps"]      or 0
        if w > d["max_weight"]:
            d["max_weight"] = w
        d["total_volume"] = round(d["total_volume"] + w * reps, 1)
        orm = _epley_1rm(w, reps)
        if orm > d["best_1rm"]:
            d["best_1rm"] = orm

    history = list(days.values())
    pr = max(history, key=lambda x: x["best_1rm"], default=None)

    return {
        "exercise": dict(exercise),
        "history":  history,
        "pr":       pr,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/periods")
def compare_periods(
    a_from: str = Query(..., description="Période A — début YYYY-MM-DD"),
    a_to:   str = Query(..., description="Période A — fin YYYY-MM-DD"),
    b_from: str = Query(..., description="Période B — début YYYY-MM-DD"),
    b_to:   str = Query(..., description="Période B — fin YYYY-MM-DD"),
):
    """Compare deux périodes : activités cardio, séances muscu, jours actifs."""
    conn = get_connection()
    try:
        return {
            "period_a": _period_stats(conn, a_from, a_to),
            "period_b": _period_stats(conn, b_from, b_to),
        }
    finally:
        conn.close()


@router.get("/exercises")
def compare_exercises(
    exercise_a_id: int = Query(..., description="ID exercice A"),
    exercise_b_id: int = Query(..., description="ID exercice B"),
):
    """Compare la progression de deux exercices (1RM Epley, volume, PR)."""
    conn = get_connection()
    try:
        return {
            "exercise_a": _exercise_stats(conn, exercise_a_id),
            "exercise_b": _exercise_stats(conn, exercise_b_id),
        }
    finally:
        conn.close()
