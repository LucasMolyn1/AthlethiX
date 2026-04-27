# CHANGELOG — AthletiX

## [v2.0.0] - 2026-04-27

### Added

**Étape 7 — Dashboard V2**
- `GET /api/dashboard/extras` : stats nutrition + musculation de la semaine courante
  (avg hydratation, avg score nutrition, sessions_count, total_sets, volume kg)
- `index.html` : deux nouveaux widgets "Nutrition — cette semaine" et "Musculation — cette semaine"
- `dashboard.js` : `loadExtras()` + `renderNutritionWidget()` + `renderStrengthWidget()`
- `alerts.js` : badge rouge dans `.sidebar-logo` affichant le nombre d'alertes non lues ;
  mise à jour dynamique au dismiss, retiré automatiquement quand count = 0

**Étape 6 — Module comparaison**
- `routers/compare.py` : `GET /api/compare/periods` (stats deux périodes) et
  `GET /api/compare/exercises` (comparaison deux exercices côte à côte)
- `compare.html` : deux onglets Périodes / Exercices, sélecteurs de dates et d'exercices
- `compare.js` : tableau comparatif coloré (valeur sup = vert), bar chart périodes,
  line chart 1RM exercices avec union de dates et `spanGaps: true`
- `api.js` : `comparePeriods()` + `compareExercises()`

**Étape 5 — Moteur d'alertes**
- `services/alert_engine.py` : `run_alert_engine()` appelé au démarrage et à chaque sync
  — 4 règles : surcharge cardio (>150% semaine précédente), repos insuffisant (≥5j/7),
  PR 1RM battu (par exercice), hydratation basse (<1.5L moy. 7j)
- `routers/alerts.py` : `GET/PUT/DELETE /api/alerts[/{id}]` + `DELETE /api/alerts` (clear read)
- `js/alerts.js` : bannière partagée toutes pages, dismiss par alerte, badge nav
- `api.js` : `getAlerts()`, `markAlertRead()`, `deleteAlert()`, `clearReadAlerts()`
- `main.py` : `run_alert_engine()` appelé dans `on_startup()`

**Étape 4 — Module nutrition**
- `routers/nutrition.py` : CRUD journal nutritionnel par date
  (`GET/POST/PUT/DELETE /api/nutrition/logs[/{date}]`)
  PUT remplace intégralement tous les champs (sémantique "full replace")
- `nutrition.html` + `nutrition.js` : navigation ←/→ entre les jours,
  formulaire hydratation/score/repas pré-post/compléments/notes,
  historique 10 derniers jours cliquable
- `api.js` : `err.status` propagé sur toutes les erreurs HTTP
  (remplace le parsing de message pour les 404)
- Navigation "🥗 Nutrition" ajoutée dans les 7 pages existantes

**Étape 3 — Frontend musculation**
- `strength.html` + `strength.js` : liste séances paginée, filtres dates,
  bibliothèque exercices avec création custom inline
- `strength_session.html` + `strength_session.js` : formulaire séance complète
  (scores touch-aware, séries dynamiques add/remove par exercice, create/update/delete)
- `exercise.html` + `exercise.js` : fiche exercice, courbe Chart.js 1RM,
  PR box, historique tabulaire
- `css/style.css` : ajout `.btn-danger`
- Navigation "💪 Musculation" ajoutée dans les 4 pages V1

**Étape 2 — Backend musculation**
- `routers/strength.py` : 8 endpoints `/api/strength/*`
  Sessions CRUD + bibliothèque exercices + courbe progression 1RM (Epley)
- `main.py` : enregistrement du router strength

**Étape 1 — Migration DB V2**
- `database.py` : bloc V2 séparé (5 tables : exercises, strength_sessions,
  exercise_sets, alerts, nutrition_logs)
- `_seed_exercises()` : 16 exercices par défaut (INSERT OR IGNORE, idempotent)

---

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
