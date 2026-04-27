"""
Router FastAPI — module alertes.

Routes :
    GET    /api/alerts          — liste des alertes (non lues par défaut)
    PUT    /api/alerts/{id}/read — marquer une alerte comme lue
    DELETE /api/alerts/{id}     — supprimer une alerte
    DELETE /api/alerts          — supprimer toutes les alertes lues
"""

from fastapi import APIRouter, HTTPException, Query
from database import get_connection

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    unread_only: bool = Query(True, description="True = seulement les non lues"),
    limit:       int  = Query(50, ge=1, le=200),
):
    """Liste les alertes, triées par date décroissante."""
    q = "SELECT * FROM alerts"
    params: list = []
    if unread_only:
        q += " WHERE is_read = 0"
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()


@router.put("/{alert_id}/read")
def mark_read(alert_id: int):
    """Marque une alerte comme lue."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Alerte introuvable")
        conn.execute("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,))
        conn.commit()
        return {"message": "Alerte marquée comme lue"}
    finally:
        conn.close()


@router.delete("/{alert_id}", status_code=200)
def delete_alert(alert_id: int):
    """Supprime une alerte."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Alerte introuvable")
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        return {"message": "Alerte supprimée"}
    finally:
        conn.close()


@router.delete("", status_code=200)
def clear_read_alerts():
    """Supprime toutes les alertes déjà lues."""
    conn = get_connection()
    try:
        result = conn.execute("DELETE FROM alerts WHERE is_read = 1")
        conn.commit()
        return {"deleted": result.rowcount, "message": f"{result.rowcount} alertes supprimées"}
    finally:
        conn.close()
