"""
Router FastAPI — journal de séance.

Routes :
    GET    /api/journal/{activity_id}   — lire l'entrée de journal
    POST   /api/journal/{activity_id}   — créer une entrée
    PUT    /api/journal/{activity_id}   — mettre à jour une entrée
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from database import get_connection

router = APIRouter(prefix="/api/journal", tags=["journal"])


class JournalEntry(BaseModel):
    context: Optional[str] = Field(None, description="Contexte de la séance (astreinte, fatigue accumulée...)")
    feeling_score: Optional[int] = Field(None, ge=1, le=10, description="Ressenti général 1-10")
    fatigue_score: Optional[int] = Field(None, ge=1, le=10, description="Niveau de fatigue 1-10")
    sleep_score: Optional[int] = Field(None, ge=1, le=10, description="Qualité du sommeil la veille 1-10")
    pain_notes: Optional[str] = Field(None, description="Douleurs ou gênes notées")
    free_notes: Optional[str] = Field(None, description="Notes libres")


@router.get("/{activity_id}")
def get_journal(activity_id: int):
    """Retourne l'entrée de journal d'une activité, ou 404 si absente."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM journal_entries WHERE activity_id = ?", (activity_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Aucune entrée de journal pour cette activité")
        return dict(row)
    finally:
        conn.close()


@router.post("/{activity_id}", status_code=201)
def create_journal(activity_id: int, entry: JournalEntry):
    """
    Crée une entrée de journal pour une activité.

    Retourne 409 si une entrée existe déjà (utiliser PUT pour modifier).
    Retourne 404 si l'activité n'existe pas.
    """
    conn = get_connection()
    try:
        activity = conn.execute(
            "SELECT id FROM activities WHERE id = ?", (activity_id,)
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=404, detail="Activité introuvable")

        existing = conn.execute(
            "SELECT id FROM journal_entries WHERE activity_id = ?", (activity_id,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Une entrée de journal existe déjà, utiliser PUT")

        conn.execute(
            """
            INSERT INTO journal_entries
                (activity_id, context, feeling_score, fatigue_score, sleep_score, pain_notes, free_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity_id,
                entry.context,
                entry.feeling_score,
                entry.fatigue_score,
                entry.sleep_score,
                entry.pain_notes,
                entry.free_notes,
            ),
        )
        conn.commit()
        return {"message": "Entrée créée avec succès"}
    finally:
        conn.close()


@router.put("/{activity_id}")
def update_journal(activity_id: int, entry: JournalEntry):
    """
    Met à jour une entrée de journal existante.

    Seuls les champs fournis (non-null) sont mis à jour.
    """
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM journal_entries WHERE activity_id = ?", (activity_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Aucune entrée à mettre à jour, utiliser POST")

        updates = {k: v for k, v in entry.model_dump().items() if v is not None}
        updates["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [activity_id]

        conn.execute(
            f"UPDATE journal_entries SET {set_clause} WHERE activity_id = ?",
            values,
        )
        conn.commit()
        return {"message": "Entrée mise à jour avec succès"}
    finally:
        conn.close()
