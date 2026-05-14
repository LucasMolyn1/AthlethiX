"""
Router Strava — OAuth2 + synchronisation des activités.

Flow d'autorisation (une seule fois) :
  1. Visiter GET /api/strava/auth  → redirigé vers Strava
  2. Strava redirige vers GET /api/strava/callback?code=xxx
  3. Les tokens sont sauvegardés en DB → syncs automatiques possibles
"""

import os
import logging
import requests as http
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from database import get_connection
from services.strava_sync import run_sync
from services.alert_engine import run_alert_engine

router = APIRouter(prefix="/api/strava", tags=["strava"])
logger = logging.getLogger(__name__)

STRAVA_AUTH_URL  = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


class SyncRequest(BaseModel):
    days: int = 30


# ── Statut de connexion ────────────────────────────────────────────────────────

@router.get("/status")
def strava_status(db=Depends(get_db)):
    """Indique si un refresh_token Strava est enregistré."""
    token = db.execute(
        "SELECT value FROM settings WHERE key='strava_refresh_token'"
    ).fetchone()
    return {"connected": token is not None}


# ── OAuth2 — autorisation initiale ────────────────────────────────────────────

@router.get("/auth")
def strava_auth():
    """Redirige vers la page d'autorisation Strava."""
    client_id    = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri = os.getenv(
        "STRAVA_REDIRECT_URI",
        "http://192.168.1.27/api/strava/callback",
    )
    if not client_id:
        raise HTTPException(400, "STRAVA_CLIENT_ID manquant dans .env")

    url = (
        f"{STRAVA_AUTH_URL}"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&approval_prompt=force"
        f"&scope=read,activity:read_all"
    )
    return RedirectResponse(url)


@router.get("/callback")
def strava_callback(code: str = None, error: str = None, db=Depends(get_db)):
    """Reçoit le code OAuth2 de Strava, échange contre des tokens, redirige."""
    if error or not code:
        return RedirectResponse("/?strava=error")

    client_id     = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    resp = http.post(STRAVA_TOKEN_URL, data={
        "client_id":     client_id,
        "client_secret": client_secret,
        "code":          code,
        "grant_type":    "authorization_code",
    }, timeout=10)

    if not resp.ok:
        logger.error("Échange token Strava échoué : %s", resp.text)
        return RedirectResponse("/?strava=error")

    _save_tokens(db, resp.json())
    return RedirectResponse("/?strava=connected")


# ── Synchronisation ───────────────────────────────────────────────────────────

@router.post("/sync")
def sync_strava(body: SyncRequest, db=Depends(get_db)):
    """Importe les activités Strava des N derniers jours."""
    try:
        added = run_sync(db, body.days)
        db.execute(
            "INSERT INTO sync_log (status, activities_added) VALUES (?,?)",
            ("ok", added),
        )
        db.commit()
        run_alert_engine()
        return {"status": "ok", "added": added}
    except Exception as exc:
        db.execute(
            "INSERT INTO sync_log (status, activities_added, error_msg) VALUES (?,?,?)",
            ("error", 0, str(exc)),
        )
        db.commit()
        logger.exception("Sync Strava échouée")
        raise HTTPException(500, str(exc))


# ── Utilitaire interne ────────────────────────────────────────────────────────

def _save_tokens(db, data: dict):
    for key, value in [
        ("strava_access_token",    data.get("access_token", "")),
        ("strava_refresh_token",   data.get("refresh_token", "")),
        ("strava_token_expires_at", str(data.get("expires_at", 0))),
    ]:
        db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
            (key, value),
        )
    db.commit()
