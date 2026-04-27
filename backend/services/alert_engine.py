"""
Moteur d'alertes — analyse la DB et génère des alertes dans la table `alerts`.

Appeler `run_alert_engine()` après chaque sync Garmin et au démarrage.
Chaque règle est idempotente : elle vérifie si une alerte non lue du même type
existe déjà avant d'en créer une nouvelle.

Règles implémentées :
    - OVERLOAD   : volume hebdomadaire > 150 % de la semaine précédente (danger)
    - REST       : ≥ 5 activités sur 7 jours glissants sans jour de repos (warning)
    - PR         : nouveau record 1RM sur un exercice (success)
    - HYDRATION  : moyenne hydratation 7 jours < 1.5 L (info)
"""

import logging
from datetime import date, timedelta
from database import get_connection

log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _already_open(conn, alert_type: str) -> bool:
    """Retourne True si une alerte non lue de ce type existe déjà."""
    row = conn.execute(
        "SELECT id FROM alerts WHERE type = ? AND is_read = 0", (alert_type,)
    ).fetchone()
    return row is not None


def _create_alert(conn, alert_type: str, level: str, message: str) -> None:
    """Insère une alerte. Ne crée pas de doublon si une alerte non lue existe."""
    if _already_open(conn, alert_type):
        return
    conn.execute(
        "INSERT INTO alerts (type, level, message) VALUES (?, ?, ?)",
        (alert_type, level, message),
    )
    log.info("Alerte créée : [%s] %s — %s", level.upper(), alert_type, message)


def _close_alert(conn, alert_type: str) -> None:
    """Marque les alertes non lues de ce type comme lues (condition résolue)."""
    conn.execute(
        "UPDATE alerts SET is_read = 1 WHERE type = ? AND is_read = 0", (alert_type,)
    )


# ── Règle 1 : Surcharge hebdomadaire ─────────────────────────────────────────

def _check_overload(conn) -> None:
    today = date.today()
    # Semaine courante : lundi → aujourd'hui
    monday_this = today - timedelta(days=today.weekday())
    monday_prev = monday_this - timedelta(weeks=1)
    sunday_prev = monday_this - timedelta(days=1)

    def week_volume(start: date, end: date) -> float:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(duration), 0) AS total
            FROM activities
            WHERE date >= ? AND date <= ?
            """,
            (start.isoformat(), end.isoformat() + "T23:59:59"),
        ).fetchone()
        return row["total"] or 0.0

    vol_this = week_volume(monday_this, today)
    vol_prev = week_volume(monday_prev, sunday_prev)

    if vol_prev > 0 and vol_this > vol_prev * 1.5:
        pct = int((vol_this / vol_prev - 1) * 100)
        _create_alert(
            conn,
            "OVERLOAD",
            "danger",
            f"Charge hebdomadaire en hausse de {pct} % par rapport à la semaine dernière. "
            "Pense à récupérer.",
        )
    else:
        _close_alert(conn, "OVERLOAD")


# ── Règle 2 : Repos insuffisant ───────────────────────────────────────────────

def _check_rest(conn) -> None:
    today = date.today()
    since = (today - timedelta(days=6)).isoformat()

    rows = conn.execute(
        "SELECT DISTINCT substr(date, 1, 10) AS day FROM activities WHERE date >= ? ORDER BY day",
        (since,),
    ).fetchall()

    active_days = {r["day"] for r in rows}

    if len(active_days) >= 5:
        _create_alert(
            conn,
            "REST",
            "warning",
            f"{len(active_days)} jours d'activité sur les 7 derniers jours. "
            "Planifie au moins 2 jours de repos par semaine.",
        )
    else:
        _close_alert(conn, "REST")


# ── Règle 3 : Record personnel (1RM) ─────────────────────────────────────────

def _epley_1rm(weight_kg: float, reps: int) -> float:
    if reps <= 0 or weight_kg <= 0:
        return 0.0
    return round(weight_kg * (1 + reps / 30), 1)


def _check_pr(conn) -> None:
    """Détecte les PR réalisés lors de la dernière séance de musculation."""
    last_session = conn.execute(
        "SELECT id, date FROM strength_sessions ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if not last_session:
        return

    session_id = last_session["id"]

    # Séries de la dernière séance
    last_sets = conn.execute(
        "SELECT exercise_id, reps, weight_kg FROM exercise_sets WHERE session_id = ?",
        (session_id,),
    ).fetchall()

    for s in last_sets:
        if not s["reps"] or not s["weight_kg"]:
            continue
        current_1rm = _epley_1rm(s["weight_kg"], s["reps"])

        # Meilleur 1RM historique sur cet exercice (hors dernière séance)
        prev = conn.execute(
            """
            SELECT es.reps, es.weight_kg
            FROM exercise_sets es
            JOIN strength_sessions ss ON ss.id = es.session_id
            WHERE es.exercise_id = ? AND ss.id != ? AND es.reps > 0 AND es.weight_kg > 0
            """,
            (s["exercise_id"], session_id),
        ).fetchall()

        if not prev:
            continue

        best_prev = max(_epley_1rm(r["weight_kg"], r["reps"]) for r in prev)

        if current_1rm > best_prev:
            ex = conn.execute(
                "SELECT name FROM exercises WHERE id = ?", (s["exercise_id"],)
            ).fetchone()
            ex_name = ex["name"] if ex else f"exercice #{s['exercise_id']}"
            alert_type = f"PR_{s['exercise_id']}"
            _create_alert(
                conn,
                alert_type,
                "success",
                f"Nouveau record sur {ex_name} ! "
                f"1RM estimé : {current_1rm} kg (précédent : {best_prev} kg).",
            )


# ── Règle 4 : Hydratation faible ─────────────────────────────────────────────

def _check_hydration(conn) -> None:
    since = (date.today() - timedelta(days=6)).isoformat()

    rows = conn.execute(
        """
        SELECT hydration_liters FROM nutrition_logs
        WHERE date >= ? AND hydration_liters IS NOT NULL
        """,
        (since,),
    ).fetchall()

    if len(rows) < 3:
        # Pas assez de données pour émettre un avis
        return

    avg = sum(r["hydration_liters"] for r in rows) / len(rows)

    if avg < 1.5:
        _create_alert(
            conn,
            "HYDRATION",
            "info",
            f"Hydratation moyenne sur 7 jours : {avg:.1f} L/jour. "
            "Objectif recommandé : 2 L/jour minimum.",
        )
    else:
        _close_alert(conn, "HYDRATION")


# ── Point d'entrée ────────────────────────────────────────────────────────────

def run_alert_engine() -> None:
    """
    Lance toutes les règles d'alerte. Idempotent — safe à appeler à chaque démarrage
    et à chaque sync Garmin.
    """
    conn = get_connection()
    try:
        _check_overload(conn)
        _check_rest(conn)
        _check_pr(conn)
        _check_hydration(conn)
        conn.commit()
        log.info("Moteur d'alertes exécuté.")
    except Exception as e:
        log.exception("Erreur dans le moteur d'alertes : %s", e)
    finally:
        conn.close()
