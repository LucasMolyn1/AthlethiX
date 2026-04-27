"""
Point d'entrée FastAPI — AthletiX backend.

Lance avec : uvicorn main:app --host 127.0.0.1 --port 8000
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db
from routers import garmin, activities, journal, dashboard, strength, nutrition, alerts, compare
from services.alert_engine import run_alert_engine

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="AthletiX API",
    description="API de suivi sportif personnel — synchronisation Garmin Connect",
    version="0.1.0",
)

# CORS : Apache2 et le frontend sont sur le même domaine,
# mais on autorise localhost pour le développement local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(garmin.router)
app.include_router(activities.router)
app.include_router(journal.router)
app.include_router(dashboard.router)
app.include_router(strength.router)
app.include_router(nutrition.router)
app.include_router(alerts.router)
app.include_router(compare.router)


@app.on_event("startup")
def on_startup():
    """Initialise la DB au démarrage si les tables n'existent pas."""
    init_db()
    logging.getLogger(__name__).info("Base de données initialisée.")
    run_alert_engine()


@app.get("/api/health")
def health():
    """Endpoint de santé — vérifie que l'API répond."""
    return {"status": "ok", "version": "0.1.0"}
