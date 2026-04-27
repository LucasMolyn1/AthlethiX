"""
Router FastAPI — module musculation.

Routes :
    GET    /api/strength/sessions               — liste des séances
    POST   /api/strength/sessions               — créer une séance (avec séries)
    GET    /api/strength/sessions/{id}          — détail séance + toutes les séries
    PUT    /api/strength/sessions/{id}          — mettre à jour séance (remplace les séries)
    DELETE /api/strength/sessions/{id}          — supprimer séance (cascade sur séries)
    GET    /api/strength/exercises              — bibliothèque d'exercices
    POST   /api/strength/exercises              — ajouter un exercice personnalisé
    GET    /api/strength/exercises/{id}/progress — progression dans le temps (courbes)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from database import get_connection

router = APIRouter(prefix="/api/strength", tags=["strength"])


# ── Modèles Pydantic ──────────────────────────────────────────────────────────

class ExerciseSetIn(BaseModel):
    exercise_id: int
    set_number:  int
    reps:        Optional[int]   = None
    weight_kg:   Optional[float] = None
    feeling:     Optional[int]   = Field(None, ge=1, le=5)
    notes:       Optional[str]   = None


class SessionCreate(BaseModel):
    date:          str
    duration:      Optional[int]   = Field(None, description="Durée en secondes")
    session_type:  Optional[str]   = Field(None, description="full_body / push / pull / legs / upper / lower / cardio / other")
    context:       Optional[str]   = None
    fatigue_score: Optional[int]   = Field(None, ge=1, le=10)
    sleep_score:   Optional[int]   = Field(None, ge=1, le=10)
    feeling_score: Optional[int]   = Field(None, ge=1, le=10)
    notes:         Optional[str]   = None
    sets:          list[ExerciseSetIn] = Field(default_factory=list)


class SessionUpdate(BaseModel):
    date:          Optional[str]   = None
    duration:      Optional[int]   = None
    session_type:  Optional[str]   = None
    context:       Optional[str]   = None
    fatigue_score: Optional[int]   = Field(None, ge=1, le=10)
    sleep_score:   Optional[int]   = Field(None, ge=1, le=10)
    feeling_score: Optional[int]   = Field(None, ge=1, le=10)
    notes:         Optional[str]   = None
    sets:          Optional[list[ExerciseSetIn]] = None


class ExerciseCreate(BaseModel):
    name:     str
    category: str = Field(..., description="push / pull / legs / core / cardio")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _epley_1rm(weight_kg: float, reps: int) -> float:
    """Formule Epley : 1RM estimé = poids × (1 + reps/30). Fiable jusqu'à ~12 reps."""
    if reps <= 0 or weight_kg <= 0:
        return 0.0
    return round(weight_kg * (1 + reps / 30), 1)


def _insert_sets(conn, session_id: int, sets: list[ExerciseSetIn]) -> None:
    """Insère les séries d'une séance. Vérifie que chaque exercise_id existe."""
    for s in sets:
        ex = conn.execute("SELECT id FROM exercises WHERE id = ?", (s.exercise_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=422, detail=f"exercise_id {s.exercise_id} introuvable")
        conn.execute(
            """
            INSERT INTO exercise_sets
                (session_id, exercise_id, set_number, reps, weight_kg, feeling, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, s.exercise_id, s.set_number, s.reps, s.weight_kg, s.feeling, s.notes),
        )


def _sets_for_session(conn, session_id: int) -> list[dict]:
    """Retourne toutes les séries d'une séance avec le nom de l'exercice."""
    rows = conn.execute(
        """
        SELECT es.*, e.name AS exercise_name, e.category AS exercise_category
        FROM exercise_sets es
        JOIN exercises e ON e.id = es.exercise_id
        WHERE es.session_id = ?
        ORDER BY es.set_number
        """,
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions(
    date_from: Optional[str] = Query(None, description="Date début YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="Date fin YYYY-MM-DD"),
    limit:     int           = Query(50, ge=1, le=200),
    offset:    int           = Query(0, ge=0),
):
    """
    Liste les séances de musculation, triées par date décroissante.

    Retourne les métadonnées + nombre de séries par séance (sans le détail).
    """
    q = """
        SELECT s.*, COUNT(es.id) AS sets_count
        FROM strength_sessions s
        LEFT JOIN exercise_sets es ON es.session_id = s.id
        WHERE 1=1
    """
    params: list = []

    if date_from:
        q += " AND s.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND s.date <= ?"
        params.append(date_to + "T23:59:59")

    q += " GROUP BY s.id ORDER BY s.date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()


@router.post("/sessions", status_code=201)
def create_session(body: SessionCreate):
    """
    Crée une séance avec ses séries.

    Les séries sont optionnelles (séance sans charge, cardio seul…).
    Retourne l'id de la séance créée.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO strength_sessions
                (date, duration, session_type, context,
                 fatigue_score, sleep_score, feeling_score, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (body.date, body.duration, body.session_type, body.context,
             body.fatigue_score, body.sleep_score, body.feeling_score, body.notes),
        )
        session_id = cur.lastrowid
        _insert_sets(conn, session_id, body.sets)
        conn.commit()
        return {"id": session_id, "message": "Séance créée"}
    finally:
        conn.close()


@router.get("/sessions/{session_id}")
def get_session(session_id: int):
    """
    Retourne le détail complet d'une séance : métadonnées + toutes les séries
    avec le nom et la catégorie de chaque exercice.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM strength_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Séance introuvable")
        result = dict(row)
        result["sets"] = _sets_for_session(conn, session_id)
        return result
    finally:
        conn.close()


@router.put("/sessions/{session_id}")
def update_session(session_id: int, body: SessionUpdate):
    """
    Met à jour une séance.

    Si `sets` est fourni, les séries existantes sont remplacées intégralement.
    Si `sets` est absent, les séries ne sont pas touchées.
    Les champs de métadonnées non fournis (null) ne sont pas modifiés.
    """
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM strength_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Séance introuvable")

        # Mise à jour partielle des métadonnées
        meta_fields = {k: v for k, v in body.model_dump(exclude={"sets"}).items() if v is not None}
        if meta_fields:
            meta_fields["updated_at"] = datetime.now().isoformat()
            set_clause = ", ".join(f"{k} = ?" for k in meta_fields)
            conn.execute(
                f"UPDATE strength_sessions SET {set_clause} WHERE id = ?",
                list(meta_fields.values()) + [session_id],
            )

        # Remplacement des séries si fournies
        if body.sets is not None:
            conn.execute("DELETE FROM exercise_sets WHERE session_id = ?", (session_id,))
            _insert_sets(conn, session_id, body.sets)

        conn.commit()
        return {"message": "Séance mise à jour"}
    finally:
        conn.close()


@router.delete("/sessions/{session_id}", status_code=200)
def delete_session(session_id: int):
    """
    Supprime une séance et toutes ses séries (CASCADE).
    Retourne 404 si la séance n'existe pas.
    """
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM strength_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Séance introuvable")
        conn.execute("DELETE FROM strength_sessions WHERE id = ?", (session_id,))
        conn.commit()
        return {"message": "Séance supprimée"}
    finally:
        conn.close()


# ── Exercices ─────────────────────────────────────────────────────────────────

@router.get("/exercises")
def list_exercises(category: Optional[str] = Query(None)):
    """
    Retourne la bibliothèque d'exercices.

    Filtre optionnel par catégorie (push/pull/legs/core/cardio).
    Tri : exercices de bibliothèque d'abord, puis personnalisés, par nom.
    """
    q = "SELECT * FROM exercises WHERE 1=1"
    params: list = []
    if category:
        q += " AND category = ?"
        params.append(category)
    q += " ORDER BY is_custom ASC, name ASC"

    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()


@router.post("/exercises", status_code=201)
def create_exercise(body: ExerciseCreate):
    """
    Ajoute un exercice personnalisé à la bibliothèque.

    Retourne 409 si un exercice avec ce nom existe déjà.
    """
    if body.category not in ("push", "pull", "legs", "core", "cardio"):
        raise HTTPException(status_code=422, detail="Catégorie invalide (push/pull/legs/core/cardio)")

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM exercises WHERE LOWER(name) = LOWER(?)", (body.name,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Un exercice avec ce nom existe déjà")

        cur = conn.execute(
            "INSERT INTO exercises (name, category, is_custom) VALUES (?, ?, 1)",
            (body.name, body.category),
        )
        conn.commit()
        return {"id": cur.lastrowid, "message": "Exercice créé"}
    finally:
        conn.close()


@router.get("/exercises/{exercise_id}/progress")
def get_exercise_progress(exercise_id: int):
    """
    Progression d'un exercice dans le temps.

    Pour chaque séance contenant cet exercice, retourne :
    - date, session_id
    - meilleur 1RM estimé du jour (Epley : poids × (1 + reps/30))
    - volume total (somme des reps × poids sur toutes les séries du jour)
    - poids maximal soulevé

    Retourne aussi le record personnel (meilleur 1RM toutes séances confondues).
    """
    conn = get_connection()
    try:
        exercise = conn.execute(
            "SELECT * FROM exercises WHERE id = ?", (exercise_id,)
        ).fetchone()
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercice introuvable")

        rows = conn.execute(
            """
            SELECT
                substr(s.date, 1, 10)   AS day,
                s.id                    AS session_id,
                es.reps,
                es.weight_kg
            FROM exercise_sets es
            JOIN strength_sessions s ON s.id = es.session_id
            WHERE es.exercise_id = ?
            ORDER BY s.date ASC
            """,
            (exercise_id,),
        ).fetchall()

        # Agrégation par jour
        days: dict = {}
        for r in rows:
            day = r["day"]
            if day not in days:
                days[day] = {
                    "date":        day,
                    "session_id":  r["session_id"],
                    "max_weight":  0.0,
                    "best_1rm":    0.0,
                    "total_volume": 0.0,
                    "sets_count":  0,
                }
            d = days[day]
            d["sets_count"] += 1

            w = r["weight_kg"] or 0.0
            reps = r["reps"] or 0

            if w > d["max_weight"]:
                d["max_weight"] = w

            volume = w * reps
            d["total_volume"] = round(d["total_volume"] + volume, 1)

            orm = _epley_1rm(w, reps)
            if orm > d["best_1rm"]:
                d["best_1rm"] = orm

        history = list(days.values())

        # Record personnel
        pr = max(history, key=lambda x: x["best_1rm"], default=None)

        return {
            "exercise": dict(exercise),
            "history":  history,
            "pr":       pr,
        }
    finally:
        conn.close()
