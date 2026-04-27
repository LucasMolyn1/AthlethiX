"""
Router FastAPI — module nutrition.

Routes :
    GET    /api/nutrition/logs          — liste des journaux (filtres date)
    GET    /api/nutrition/logs/{date}   — journal d'un jour (YYYY-MM-DD)
    POST   /api/nutrition/logs          — créer un journal
    PUT    /api/nutrition/logs/{date}   — mettre à jour (remplace tous les champs)
    DELETE /api/nutrition/logs/{date}   — supprimer
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from database import get_connection

router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])


# ── Modèles Pydantic ──────────────────────────────────────────────────────────

class NutritionLogIn(BaseModel):
    date:               str
    hydration_liters:   Optional[float] = None
    nutrition_score:    Optional[int]   = Field(None, ge=1, le=10)
    pre_workout_meal:   Optional[str]   = None
    post_workout_meal:  Optional[str]   = None
    supplements:        Optional[str]   = None
    notes:              Optional[str]   = None


class NutritionLogUpdate(BaseModel):
    hydration_liters:   Optional[float] = None
    nutrition_score:    Optional[int]   = Field(None, ge=1, le=10)
    pre_workout_meal:   Optional[str]   = None
    post_workout_meal:  Optional[str]   = None
    supplements:        Optional[str]   = None
    notes:              Optional[str]   = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/logs")
def list_logs(
    date_from: Optional[str] = Query(None, description="Date début YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="Date fin YYYY-MM-DD"),
    limit:     int           = Query(30, ge=1, le=200),
    offset:    int           = Query(0, ge=0),
):
    """Liste les journaux nutritionnels, triés par date décroissante."""
    q = "SELECT * FROM nutrition_logs WHERE 1=1"
    params: list = []
    if date_from:
        q += " AND date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND date <= ?"
        params.append(date_to)
    q += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()


@router.get("/logs/{date}")
def get_log(date: str):
    """Retourne le journal nutritionnel d'un jour précis (YYYY-MM-DD)."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM nutrition_logs WHERE date = ?", (date,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Journal introuvable pour cette date")
        return dict(row)
    finally:
        conn.close()


@router.post("/logs", status_code=201)
def create_log(body: NutritionLogIn):
    """Crée un journal pour une date. Retourne 409 si un journal existe déjà ce jour."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM nutrition_logs WHERE date = ?", (body.date,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Un journal existe déjà pour cette date")
        cur = conn.execute(
            """
            INSERT INTO nutrition_logs
                (date, hydration_liters, nutrition_score,
                 pre_workout_meal, post_workout_meal, supplements, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (body.date, body.hydration_liters, body.nutrition_score,
             body.pre_workout_meal, body.post_workout_meal, body.supplements, body.notes),
        )
        conn.commit()
        return {"id": cur.lastrowid, "message": "Journal créé"}
    finally:
        conn.close()


@router.put("/logs/{date}")
def update_log(date: str, body: NutritionLogUpdate):
    """Met à jour tous les champs du journal (remplace intégralement)."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM nutrition_logs WHERE date = ?", (date,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Journal introuvable pour cette date")
        conn.execute(
            """
            UPDATE nutrition_logs
            SET hydration_liters=?, nutrition_score=?,
                pre_workout_meal=?, post_workout_meal=?,
                supplements=?, notes=?, updated_at=?
            WHERE date=?
            """,
            (body.hydration_liters, body.nutrition_score,
             body.pre_workout_meal, body.post_workout_meal,
             body.supplements, body.notes,
             datetime.now().isoformat(), date),
        )
        conn.commit()
        return {"message": "Journal mis à jour"}
    finally:
        conn.close()


@router.delete("/logs/{date}", status_code=200)
def delete_log(date: str):
    """Supprime le journal d'une date. Retourne 404 si absent."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM nutrition_logs WHERE date = ?", (date,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Journal introuvable pour cette date")
        conn.execute("DELETE FROM nutrition_logs WHERE date = ?", (date,))
        conn.commit()
        return {"message": "Journal supprimé"}
    finally:
        conn.close()
