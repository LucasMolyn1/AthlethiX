"""
Router FastAPI — CRUD activités.

Routes :
    GET /api/activities         — liste paginée avec filtres
    GET /api/activities/{id}    — détail d'une activité
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from database import get_connection
import json

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("")
def list_activities(
    type: Optional[str] = Query(None, description="Filtre par type : run, trail, cycling, swimming, strength"),
    date_from: Optional[str] = Query(None, description="Date début YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Date fin YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Liste les activités avec filtres optionnels.

    Tri par date décroissante (plus récent en premier).
    Supporte la pagination via limit/offset.
    """
    query = "SELECT id, garmin_id, type, date, duration, distance, elevation_gain, avg_hr, max_hr, calories FROM activities WHERE 1=1"
    params: list = []

    if type:
        query += " AND type = ?"
        params.append(type)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to + "T23:59:59")

    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/{activity_id}")
def get_activity(activity_id: int):
    """
    Retourne le détail complet d'une activité, incluant le raw_json Garmin
    et l'entrée de journal associée si elle existe.
    """
    conn = get_connection()
    try:
        activity = conn.execute(
            "SELECT * FROM activities WHERE id = ?", (activity_id,)
        ).fetchone()

        if not activity:
            raise HTTPException(status_code=404, detail="Activité introuvable")

        result = dict(activity)
        if result.get("raw_json"):
            result["raw_json"] = json.loads(result["raw_json"])

        journal = conn.execute(
            "SELECT * FROM journal_entries WHERE activity_id = ?", (activity_id,)
        ).fetchone()
        result["journal"] = dict(journal) if journal else None

        return result
    finally:
        conn.close()
