"""
Service de synchronisation Strava.
Gère le refresh automatique des tokens OAuth2 et l'import des activités.
"""

import os
import json
import time
import requests

STRAVA_TOKEN_URL     = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

# Mapping types Strava → types internes
TYPE_MAP = {
    "Run":              "run",
    "TrailRun":         "trail",
    "Hike":             "trail",
    "Ride":             "cycling",
    "VirtualRide":      "cycling",
    "GravelRide":       "cycling",
    "MountainBikeRide": "cycling",
    "EBikeRide":        "cycling",
    "Swim":             "swimming",
    "WeightTraining":   "strength",
    "Crossfit":         "strength",
    "Workout":          "other",
    "Walk":             "other",
    "Yoga":             "other",
    "Rowing":           "other",
}


def _get_setting(db, key: str):
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def _set_setting(db, key: str, value):
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
        (key, str(value)),
    )


def _ensure_valid_token(db) -> str:
    """Retourne un access_token valide, le rafraîchit si nécessaire."""
    expires_at = int(_get_setting(db, "strava_token_expires_at") or 0)
    if time.time() < expires_at - 300:
        return _get_setting(db, "strava_access_token")

    client_id     = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    refresh_token = _get_setting(db, "strava_refresh_token")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Strava non connecté. Visitez /api/strava/auth pour autoriser l'application."
        )

    resp = requests.post(STRAVA_TOKEN_URL, data={
        "client_id":     client_id,
        "client_secret": client_secret,
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    _set_setting(db, "strava_access_token",    data["access_token"])
    _set_setting(db, "strava_refresh_token",   data.get("refresh_token", refresh_token))
    _set_setting(db, "strava_token_expires_at", data["expires_at"])
    db.commit()

    return data["access_token"]


def run_sync(db, days: int = 30) -> int:
    """Importe les activités Strava des N derniers jours. Retourne le nombre ajouté."""
    access_token = _ensure_valid_token(db)
    headers = {"Authorization": f"Bearer {access_token}"}
    after   = int(time.time()) - days * 86400
    added   = 0
    page    = 1

    while True:
        resp = requests.get(STRAVA_ACTIVITIES_URL, headers=headers, params={
            "after": after, "per_page": 100, "page": page,
        }, timeout=15)
        resp.raise_for_status()
        activities = resp.json()

        if not activities:
            break

        for act in activities:
            strava_id = str(act["id"])
            if db.execute(
                "SELECT id FROM activities WHERE garmin_id=?", (strava_id,)
            ).fetchone():
                continue

            activity_type = TYPE_MAP.get(act.get("sport_type") or act.get("type", ""), "other")
            date = act["start_date_local"][:10]

            db.execute("""
                INSERT INTO activities
                    (garmin_id, type, date, duration, distance, elevation_gain,
                     avg_hr, max_hr, calories, raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                strava_id,
                activity_type,
                date,
                act.get("moving_time"),
                act.get("distance"),
                act.get("total_elevation_gain"),
                act.get("average_heartrate"),
                act.get("max_heartrate"),
                act.get("calories") or None,
                json.dumps(act),
            ))
            added += 1

        page += 1

    db.commit()
    return added
