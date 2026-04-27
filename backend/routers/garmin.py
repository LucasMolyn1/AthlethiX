"""
Router FastAPI — endpoints Garmin Connect.

Routes :
    GET  /api/garmin/test   — vérifie la connexion Garmin
    POST /api/garmin/sync   — déclenche une synchronisation manuelle
"""

from fastapi import APIRouter
from pydantic import BaseModel
from services.garmin_sync import test_connection, sync_activities

router = APIRouter(prefix="/api/garmin", tags=["garmin"])


class SyncRequest(BaseModel):
    days: int = 30


@router.get("/test")
def garmin_test():
    """
    Teste la connexion à Garmin Connect.

    Retourne le nom d'affichage du compte si la connexion réussit,
    ou un message d'erreur explicite sinon.
    """
    return test_connection()


@router.post("/sync")
def garmin_sync(req: SyncRequest = SyncRequest()):
    """
    Lance une synchronisation manuelle des activités Garmin.

    Body (optionnel) :
        days (int) : nombre de jours à récupérer (défaut 30, max conseillé 90)

    Retourne le nombre d'activités ajoutées et ignorées (déjà en base).
    """
    result = sync_activities(days=req.days)
    return result
