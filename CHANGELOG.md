# CHANGELOG — AthletiX

## [v0.2.0] - 2026-04-27

### Added
- Frontend complet : `index.html` (dashboard), `history.html`, `activity.html`, `journal.html`
- `css/style.css` : design sombre responsive, palette bleue/verte
- `js/api.js` : couche fetch centralisée vers FastAPI
- `js/dashboard.js` : résumé semaine, courbe de forme Chart.js, sync manuelle
- `js/history.js` : liste paginée avec filtres sport/date
- `js/activity.js` : détail activité + formulaire journal (create/update)
- `js/journal.js` : vue journal avec indicateur de complétion
- Chart.js 4.4.4 embarqué localement (`frontend/js/vendor/chart.min.js`)
- Cron toutes les heures (`/etc/cron.d/athletix`)
- Service systemd `athletix.service` (démarrage automatique)

### Changed
- `garmin_sync.py` : gestion explicite du 429 rate limit Garmin

### Deployment
- Déployé sur VM `192.168.1.26` via SCP
- Frontend servi depuis `/var/www/athletix` par Apache2
- Backend FastAPI sur `127.0.0.1:8000` (service systemd)
- Proxy Apache2 `/api/*` → `127.0.0.1:8000` opérationnel

## [v0.1.0] - 2026-04-27

### Added
- Structure complète du projet (backend, frontend, config, scripts)
- `database.py` : configuration SQLite, création des tables `activities` et `journal_entries`
- `services/garmin_sync.py` : connexion Garmin Connect, récupération et mapping des activités
- `routers/garmin.py` : endpoints `/api/garmin/test` et `/api/garmin/sync`
- `main.py` : point d'entrée FastAPI avec CORS et inclusion des routers
- `requirements.txt` : dépendances Python épinglées
- `.env.example` : template des variables d'environnement
- `.gitignore` : exclusion des fichiers sensibles et artefacts
- `IMPLEMENTATION_PLAN.md` : plan d'implémentation complet avec statuts
- `WALKTHROUGH.md` : documentation technique accessible
