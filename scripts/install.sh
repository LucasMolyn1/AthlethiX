#!/usr/bin/env bash
# install.sh — Script d'installation AthletiX
# Usage : sudo bash install.sh

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

REPO_URL="https://github.com/VOTRE_USERNAME/athletix.git"  # à adapter
INSTALL_DIR="/opt/athletix"
WWW_DIR="/var/www/athletix"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_USER="www-data"

echo "========================================="
echo "  Installation AthletiX"
echo "========================================="

# --- 1. Prérequis ---
info "Vérification des prérequis..."

command -v python3 >/dev/null 2>&1 || error "Python3 introuvable. Installer : apt install python3"
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
[[ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 1 ]] || error "Python 3.11+ requis (détecté : $PYTHON_VERSION)"
info "Python $PYTHON_VERSION détecté."

command -v pip3 >/dev/null 2>&1 || error "pip3 introuvable. Installer : apt install python3-pip"
command -v git  >/dev/null 2>&1 || error "git introuvable. Installer : apt install git"
command -v apache2ctl >/dev/null 2>&1 || warn "Apache2 introuvable. Configurer manuellement."

# --- 2. Clone du repo ---
info "Clonage du dépôt dans $INSTALL_DIR..."
if [[ -d "$INSTALL_DIR" ]]; then
    warn "$INSTALL_DIR existe déjà. Mise à jour (git pull)..."
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# --- 3. Virtualenv Python ---
info "Création du virtualenv Python..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

info "Installation des dépendances Python..."
pip install --upgrade pip -q
pip install -r "$INSTALL_DIR/backend/requirements.txt" -q
deactivate

# --- 4. Fichier .env ---
info "Configuration de l'environnement..."
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    warn "Fichier .env créé depuis .env.example"
    warn "IMPORTANT : éditez $INSTALL_DIR/.env avec vos credentials Garmin !"
else
    info ".env déjà présent, ignoré."
fi

# --- 5. Initialisation base de données ---
info "Initialisation de la base SQLite..."
cd "$INSTALL_DIR/backend"
source "$VENV_DIR/bin/activate"
python3 database.py
deactivate

# --- 6. Frontend ---
info "Déploiement du frontend dans $WWW_DIR..."
mkdir -p "$WWW_DIR"
cp -r "$INSTALL_DIR/frontend/." "$WWW_DIR/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$WWW_DIR"

# --- 7. Apache2 ---
if command -v apache2ctl >/dev/null 2>&1; then
    info "Configuration Apache2..."
    cp "$INSTALL_DIR/config/apache2.conf" /etc/apache2/sites-available/athletix.conf
    a2ensite athletix
    a2enmod proxy proxy_http
    apache2ctl configtest && systemctl reload apache2
    info "Apache2 configuré et rechargé."
else
    warn "Apache2 non trouvé. Copier manuellement config/apache2.conf."
fi

# --- 8. Service systemd ---
info "Création du service systemd..."
cat > /etc/systemd/system/athletix.service << EOF
[Unit]
Description=AthletiX FastAPI Backend
After=network.target

[Service]
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/backend
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable athletix
systemctl start athletix
info "Service athletix démarré."

# --- 9. Cron de synchronisation ---
info "Installation du cron de synchronisation Garmin (toutes les heures)..."
CRON_JOB="0 * * * * $SERVICE_USER bash $INSTALL_DIR/scripts/sync_garmin.sh >> /var/log/athletix_sync.log 2>&1"
CRON_FILE="/etc/cron.d/athletix"
echo "$CRON_JOB" > "$CRON_FILE"
chmod 644 "$CRON_FILE"
info "Cron installé dans $CRON_FILE."

# --- Récapitulatif ---
echo ""
echo "========================================="
echo -e "${GREEN}  Installation terminée !${NC}"
echo "========================================="
echo ""
echo "Prochaines étapes :"
echo "  1. Éditer $INSTALL_DIR/.env avec vos credentials Garmin"
echo "  2. Relancer l'API : systemctl restart athletix"
echo "  3. Tester la connexion : curl http://localhost/api/garmin/test"
echo "  4. Lancer une sync manuelle : curl -X POST http://localhost/api/garmin/sync"
echo ""
echo "Logs :"
echo "  API     : journalctl -u athletix -f"
echo "  Apache2 : tail -f /var/log/apache2/athletix_error.log"
echo "  Sync    : tail -f /var/log/athletix_sync.log"
