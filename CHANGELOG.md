# CHANGELOG — AthletiX

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
