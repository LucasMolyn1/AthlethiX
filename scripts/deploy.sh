#!/usr/bin/env bash
# deploy.sh — Mise à jour AthletiX depuis GitHub
# Usage : sudo bash /opt/athletix/scripts/deploy.sh

set -euo pipefail

GREEN='\033[0;32m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC}  $*"; }

INSTALL_DIR="/opt/athletix"
WWW_DIR="/var/www/athletix"

info "Pull depuis GitHub..."
git -C "$INSTALL_DIR" pull origin main

info "Mise à jour du frontend..."
cp -r "$INSTALL_DIR/frontend/." "$WWW_DIR/"

info "Redémarrage de l'API..."
systemctl restart athletix

info "Déployé. Statut :"
systemctl status athletix --no-pager -l
