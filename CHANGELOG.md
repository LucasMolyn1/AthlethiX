# CHANGELOG — AthletiX

## [v1.0.0] - 2026-04-27

### Release
- V1 complète : toutes les fonctionnalités planifiées implémentées et déployées
- Backend FastAPI opérationnel sur VM Debian (192.168.1.26), service systemd actif
- Frontend vanilla JS/CSS déployé dans `/var/www/athletix`
- Sync Garmin Connect en attente de levée du rate limit (opérationnel dès résolution)

### Added
- `routers/activities.py` : liste paginée avec filtres, détail activité + journal intégré
- `routers/journal.py` : CRUD complet journal de séance (GET/POST/PUT)
- `routers/dashboard.py` : résumé semaine, courbe de forme, activités récentes, sync-status
- Table `sync_log` : historique de toutes les synchronisations
- `GarthHTTPError` importée explicitement — plus de HTTP 500 sur erreur Garmin

### Fixed
- `garmin_sync.py` : `_get_client()` ne relance plus `login()` sur 429 (aggravait le rate limit)
- `sync_activities()` attrape désormais `GarthHTTPError` → retourne JSON 200 avec message d'erreur

### Docs
- `WALKTHROUGH.md` entièrement réécrit : architecture détaillée, tokens Garmin, commandes VM
- `IMPLEMENTATION_PLAN.md` : audit V1 complet, statuts réels vérifiés dans le code

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
