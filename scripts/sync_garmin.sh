#!/usr/bin/env bash
# sync_garmin.sh — Synchronisation Garmin via cron
# Appelé toutes les heures par /etc/cron.d/athletix

INSTALL_DIR="/opt/athletix"
VENV_DIR="$INSTALL_DIR/venv"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Démarrage de la sync Garmin..."

curl -s -X POST "http://127.0.0.1:8000/api/garmin/sync" \
     -H "Content-Type: application/json" \
     -d '{"days": 7}' \
     && echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync terminée." \
     || echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERREUR : sync échouée."
