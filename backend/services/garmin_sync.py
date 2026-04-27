"""
Service de synchronisation Garmin Connect.

Responsabilités :
- Authentification et maintien de la session garminconnect
- Récupération des activités récentes
- Mapping des types d'activité Garmin → types internes
- Persistance en SQLite

La lib garminconnect stocke ses tokens dans un fichier local (.garminconnect).
Ce fichier est ignoré par git (.gitignore) car il contient des credentials.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError
from dotenv import load_dotenv

from database import get_connection

load_dotenv()

logger = logging.getLogger(__name__)

# Mapping des noms d'activité Garmin vers les types internes
GARMIN_TYPE_MAP: dict[str, str] = {
    "running":          "run",
    "trail_running":    "trail",
    "cycling":          "cycling",
    "road_biking":      "cycling",
    "mountain_biking":  "cycling",
    "swimming":         "swimming",
    "lap_swimming":     "swimming",
    "open_water_swimming": "swimming",
    "strength_training": "strength",
    "fitness_equipment": "strength",
    "indoor_cycling":   "cycling",
    "treadmill_running": "run",
    "virtual_ride":     "cycling",
    "hiking":           "trail",
    "walking":          "run",
}


def _map_activity_type(garmin_type: str) -> str:
    """Convertit un type Garmin en type interne. Retourne 'other' si inconnu."""
    return GARMIN_TYPE_MAP.get(garmin_type.lower(), "other")


def _get_client() -> Garmin:
    """
    Instancie et authentifie le client Garmin.

    Tente d'abord un login avec les tokens mis en cache.
    Si les tokens sont expirés ou absents, ré-authentifie avec email/password.

    Raises:
        GarminConnectAuthenticationError: credentials invalides
        GarminConnectConnectionError: réseau inaccessible
        ValueError: variables d'environnement manquantes
    """
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        raise ValueError("GARMIN_EMAIL et GARMIN_PASSWORD doivent être définis dans .env")

    client = Garmin(email, password)
    try:
        client.login()
        logger.info("Connexion Garmin réussie (tokens mis en cache)")
    except Exception:
        # Tokens absents ou expirés → ré-authentification complète
        logger.warning("Tokens expirés ou absents, ré-authentification...")
        client.login()
        logger.info("Ré-authentification Garmin réussie")

    return client


def test_connection() -> dict:
    """
    Vérifie que la connexion à Garmin Connect fonctionne.

    Returns:
        dict avec 'success' (bool), 'display_name' (str), et éventuellement 'error' (str)
    """
    try:
        client = _get_client()
        profile = client.get_full_name()
        return {"success": True, "display_name": profile}
    except GarminConnectAuthenticationError as e:
        logger.error("Erreur d'authentification Garmin : %s", e)
        return {"success": False, "error": f"Authentification échouée : {e}"}
    except GarminConnectConnectionError as e:
        logger.error("Erreur réseau Garmin : %s", e)
        return {"success": False, "error": f"Connexion impossible : {e}"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        msg = str(e)
        if "429" in msg:
            logger.warning("Rate limit Garmin (429) — réessayer dans 15 minutes")
            return {"success": False, "error": "Rate limit Garmin : trop de tentatives. Réessayer dans 15 minutes."}
        logger.error("Erreur inattendue : %s", e)
        return {"success": False, "error": f"Erreur inattendue : {e}"}


def sync_activities(days: int = 30) -> dict:
    """
    Synchronise les activités des N derniers jours depuis Garmin Connect.

    Seules les activités absentes de la DB (garmin_id UNIQUE) sont insérées.

    Args:
        days: nombre de jours à récupérer (défaut 30)

    Returns:
        dict avec 'added' (int), 'skipped' (int), 'error' (str|None)
    """
    try:
        client = _get_client()
    except (GarminConnectAuthenticationError, GarminConnectConnectionError, ValueError) as e:
        _log_sync(status="error", error_msg=str(e))
        return {"added": 0, "skipped": 0, "error": str(e)}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        raw_activities = client.get_activities_by_date(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )
    except GarminConnectConnectionError as e:
        _log_sync(status="error", error_msg=str(e))
        return {"added": 0, "skipped": 0, "error": f"Erreur réseau lors de la récupération : {e}"}
    except Exception as e:
        _log_sync(status="error", error_msg=str(e))
        return {"added": 0, "skipped": 0, "error": f"Erreur inattendue : {e}"}

    added = 0
    skipped = 0
    conn = get_connection()

    try:
        for activity in raw_activities:
            garmin_id = str(activity.get("activityId", ""))
            if not garmin_id:
                continue

            # Vérifie si déjà en base
            existing = conn.execute(
                "SELECT id FROM activities WHERE garmin_id = ?", (garmin_id,)
            ).fetchone()

            if existing:
                skipped += 1
                continue

            activity_type_raw = activity.get("activityType", {}).get("typeKey", "unknown")
            activity_type = _map_activity_type(activity_type_raw)

            # Extraction des métriques principales
            date_str = activity.get("startTimeLocal", "")[:19]  # format YYYY-MM-DDTHH:MM:SS
            duration = int(activity.get("duration", 0))
            distance = float(activity.get("distance", 0) or 0)
            elevation_gain = float(activity.get("elevationGain", 0) or 0)
            avg_hr = activity.get("averageHR")
            max_hr = activity.get("maxHR")
            calories = activity.get("calories")

            conn.execute(
                """
                INSERT INTO activities
                    (garmin_id, type, date, duration, distance, elevation_gain,
                     avg_hr, max_hr, calories, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    garmin_id,
                    activity_type,
                    date_str,
                    duration,
                    distance,
                    elevation_gain,
                    avg_hr,
                    max_hr,
                    calories,
                    json.dumps(activity),
                ),
            )
            added += 1

        conn.commit()
    finally:
        conn.close()

    _log_sync(status="ok", activities_added=added)
    logger.info("Sync terminée : %d ajoutées, %d ignorées", added, skipped)
    return {"added": added, "skipped": skipped, "error": None}


def _log_sync(status: str, activities_added: int = 0, error_msg: Optional[str] = None) -> None:
    """Enregistre le résultat d'une sync dans sync_log."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO sync_log (status, activities_added, error_msg) VALUES (?, ?, ?)",
            (status, activities_added, error_msg),
        )
        conn.commit()
    finally:
        conn.close()
