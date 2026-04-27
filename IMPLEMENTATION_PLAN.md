# IMPLEMENTATION PLAN — AthletiX

## Statut global

### V1 — Tracking Garmin (complète)

| Phase | Description | Statut |
|-------|-------------|--------|
| Phase 0 | Structure projet + initialisation Git | ✅ DONE |
| Phase 1 | Base de données SQLite + modèles | ✅ DONE |
| Phase 2 | Sync Garmin (service + router) | ✅ DONE |
| Phase 3 | CRUD activités + journal | ✅ DONE |
| Phase 4 | Dashboard API | ✅ DONE |
| Phase 5 | Frontend — Dashboard | ✅ DONE |
| Phase 6 | Frontend — Historique | ✅ DONE |
| Phase 7 | Frontend — Détail activité + Journal | ✅ DONE |
| Phase 8 | Configuration Apache2 + déploiement | ✅ DONE |
| Phase 9 | Script install.sh + cron | ✅ DONE |
| Phase 10 | Tests + documentation finale | ➡️ Reporté V3 |

> **V1 validée et taggée v1.0.0 le 2026-04-27.**
> Sync Garmin opérationnelle dès levée du rate limit IP (conséquence des
> tentatives répétées lors du déploiement initial).

---

### V2 — Modules avancés (complète)

| Étape | Description | Statut |
|-------|-------------|--------|
| Étape 1 | Migration DB V2 — 5 nouvelles tables + seed exercices | ✅ DONE |
| Étape 2 | Backend musculation — `routers/strength.py` (8 endpoints) | ✅ DONE |
| Étape 3 | Frontend musculation — 3 pages + nav mise à jour | ✅ DONE |
| Étape 4 | Module nutrition — backend + frontend | ✅ DONE |
| Étape 5 | Moteur d'alertes — `services/alert_engine.py` + `routers/alerts.py` | ✅ DONE |
| Étape 6 | Module comparaison — `routers/compare.py` + `compare.html` | ✅ DONE |
| Étape 7 | Dashboard V2 — widgets nutrition/muscu + badge alertes nav | ✅ DONE |
| Étape 8 | Clôture V2 — docs, CHANGELOG, tag git v2.0.0 | ✅ DONE |

> **V2 validée et taggée v2.0.0 le 2026-04-27.**

---

## Fonctionnalités détaillées — V2

### Étape 1 — Migration DB V2 ✅

Bloc `executescript` séparé dans `database.py` (V1 intouché, migration additive) :

| Table | Rôle |
|-------|------|
| `exercises` | Bibliothèque d'exercices (16 par défaut + custom). UNIQUE sur `name`. |
| `strength_sessions` | Séances de musculation avec scores fatigue/sommeil/ressenti (1–10). |
| `exercise_sets` | Séries d'une séance. FK sur `strength_sessions` (CASCADE). FK sur `exercises`. |
| `alerts` | Alertes générées par le moteur (danger / warning / info / success). |
| `nutrition_logs` | Journal nutritionnel quotidien. UNIQUE sur `date`. |

`_seed_exercises()` insère 16 exercices par défaut (INSERT OR IGNORE). Idempotent.

---

### Étape 2 — Backend musculation ✅

`routers/strength.py` — prefix `/api/strength`

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/sessions` | Liste paginée, filtres `date_from`/`date_to`, agrège `sets_count` |
| POST | `/sessions` | Crée séance + séries atomiquement (transaction) |
| GET | `/sessions/{id}` | Détail complet : métadonnées + séries avec noms exercices |
| PUT | `/sessions/{id}` | Mise à jour partielle métadonnées + remplacement optionnel séries |
| DELETE | `/sessions/{id}` | Supprime séance + séries (CASCADE FK) |
| GET | `/exercises` | Bibliothèque, filtre optionnel par catégorie |
| POST | `/exercises` | Crée exercice personnalisé (`is_custom=1`), 409 si doublon nom |
| GET | `/exercises/{id}/progress` | Courbe 1RM Epley, volume, PR historique |

Formule Epley : `1RM = poids × (1 + reps/30)`, fiable jusqu'à ~12 reps.
Le PR est le meilleur 1RM toutes séances confondues pour un exercice donné.

---

### Étape 3 — Frontend musculation ✅

| Page | JS | Description |
|------|----|-------------|
| `strength.html` | `strength.js` | Liste séances paginée, filtres dates, bibliothèque exercices avec création custom |
| `strength_session.html` | `strength_session.js` | Formulaire séance complète : scores touch-aware, séries dynamiques (add/remove), create/update/delete |
| `exercise.html` | `exercise.js` | Fiche exercice : PR box, courbe Chart.js 1RM, historique tabulaire cliquable |

Navigation "💪 Musculation" ajoutée dans les 4 pages V1 (index, history, journal, activity).

---

### Étape 4 — Module nutrition ✅

`routers/nutrition.py` — prefix `/api/nutrition`

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/logs` | Liste paginée, filtres `date_from`/`date_to` |
| GET | `/logs/{date}` | Journal d'un jour (404 si absent) |
| POST | `/logs` | Crée journal (409 si date déjà existante) |
| PUT | `/logs/{date}` | Remplace intégralement tous les champs du journal |
| DELETE | `/logs/{date}` | Supprime le journal |

`nutrition.html` + `nutrition.js` :
- Navigation ←/→ entre les jours, date picker
- Formulaire : hydratation (litres), score alimentation (slider 1–10 touch-aware),
  repas pré/post-entraînement, compléments, notes libres
- Historique des 10 derniers jours en bas de page (cliquables pour navigation)
- `err.status` propagé sur toutes les erreurs HTTP dans `api.js`

Navigation "🥗 Nutrition" ajoutée dans les 7 pages existantes.

---

### Étape 5 — Moteur d'alertes ✅

**Backend** : `services/alert_engine.py`
- `run_alert_engine()` : analyse la DB et génère des alertes dans la table `alerts`
- Règles implémentées :
  - Surcharge hebdomadaire (volume cardio > 150% semaine précédente) → `danger`
  - Repos insuffisant (≥ 5 jours actifs sur 7 glissants) → `warning`
  - Record personnel 1RM battu (Epley, par exercice) → `success`
  - Rappel hydratation (moyenne 7j < 1.5L, ≥ 3 points de données) → `info`
- `_already_open()` : idempotent, évite les doublons
- `_close_alert()` : résout automatiquement les alertes dont la condition cesse
- Appelé au démarrage + à chaque sync Garmin

`routers/alerts.py` — prefix `/api/alerts`

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/alerts` | Liste alertes (param `unread_only`, défaut `true`) |
| PUT | `/alerts/{id}/read` | Marquer comme lue |
| DELETE | `/alerts/{id}` | Supprimer une alerte |
| DELETE | `/alerts` | Supprimer toutes les alertes lues |

**Frontend** : `js/alerts.js` partagé entre toutes les pages
- Bannière colorée en haut du `<main>` selon niveau (danger/warning/info/success)
- Bouton ✕ par alerte → `dismissAlert(id)` → `markAlertRead` puis suppression DOM
- Badge rouge dans `.sidebar-logo` avec le nombre d'alertes non lues
- Badge mis à jour dynamiquement au dismiss, retiré quand count = 0

---

### Étape 6 — Module comparaison ✅

`routers/compare.py` — prefix `/api/compare`

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/periods` | Stats deux périodes : activités, durée, distance, séances muscu, séries |
| GET | `/exercises` | Comparaison deux exercices : PR, best 1RM, historique |

`_period_stats()` : calcule `active_days` comme union des jours avec activité OU séance muscu.
Distance convertie mètres → km.

`compare.html` + `compare.js` :
- Deux onglets (Périodes / Exercices) avec `showTab()`
- Périodes : sélecteurs de dates A (bleue) et B (verte), tableau comparatif avec couleur
  sur la meilleure valeur, bar chart Chart.js groupé (4 métriques × 2 périodes)
- Exercices : deux selects (remplis depuis `/api/strength/exercises`), cards PR + stats,
  line chart comparatif 1RM (union de dates, `spanGaps: true`, `null` pour dates manquantes)

---

### Étape 7 — Dashboard V2 ✅

`GET /api/dashboard/extras` (ajout dans `dashboard.py`) :
- Nutrition semaine : `days_logged`, `avg_hydration`, `avg_score`
- Musculation semaine : `sessions_count`, `total_sets`, `total_volume` (kg)

`index.html` : nouvelle ligne `grid-2` sous les graphiques existants :
- Widget **Nutrition** — hydratation moyenne (L) + score moyen / 10
- Widget **Musculation** — séances + volume soulevé (kg ou tonnes si ≥ 1000 kg)

`dashboard.js` : `loadExtras()` appelé dans `DOMContentLoaded`, `renderNutritionWidget()` +
`renderStrengthWidget()` injectent dans `#widget-nutrition` et `#widget-strength`.

---

### Étape 8 — Clôture V2 ✅

- `WALKTHROUGH.md` : mis à jour avec toute la V2
- `IMPLEMENTATION_PLAN.md` : audit final, tous les statuts à ✅ DONE
- `CHANGELOG.md` : entrée `[v2.0.0]` complète
- Tag git `v2.0.0`

---

## Ce qui manque réellement

| Item | Impact | Priorité |
|------|--------|----------|
| Sync Garmin (levée du rate limit) | Bloquant pour valider les données réelles | Immédiat (opérationnel) |
| Première sync Garmin validée end-to-end | Dépend du rate limit | Dès levée |
| Tests automatisés | Aucun filet de sécurité | V3 |
| Gestion MFA Garmin | Bloquant si 2FA activé (compte sans 2FA actuel) | V3 |

---

## Architecture technique — V2

```
Internet
    │
    ▼
[OpenResty] ← HTTPS/443, certificat SSL, domaine OVH
    │ HTTP proxy_pass
    ▼
[Apache2 :80] ← VM Debian LXC (192.168.1.26)
    │
    ├─ /* ────────────────────────► /var/www/athletix/
    │                               index.html      history.html
    │                               activity.html   journal.html
    │                               strength.html   strength_session.html
    │                               exercise.html   nutrition.html
    │                               compare.html
    │                               css/style.css
    │                               js/api.js       js/dashboard.js
    │                               js/history.js   js/activity.js
    │                               js/journal.js   js/strength.js
    │                               js/strength_session.js
    │                               js/exercise.js  js/nutrition.js
    │                               js/compare.js   js/alerts.js
    │
    └─ /api/* ────────────────────► 127.0.0.1:8000 (FastAPI / Uvicorn)
                                        │
                                        ├── routers/garmin.py
                                        ├── routers/activities.py
                                        ├── routers/journal.py
                                        ├── routers/dashboard.py
                                        ├── routers/strength.py     ← V2
                                        ├── routers/nutrition.py    ← V2
                                        ├── routers/alerts.py       ← V2
                                        └── routers/compare.py      ← V2
                                                    │
                                                    ▼
                                        SQLite : athletix.db
                                        ── V1 ──────────────────
                                        │ activities             │
                                        │ journal_entries        │
                                        │ sync_log               │
                                        ── V2 ──────────────────
                                        │ exercises              │
                                        │ strength_sessions      │
                                        │ exercise_sets          │
                                        │ alerts                 │
                                        │ nutrition_logs         │
                                        ─────────────────────────
                                                    │
                                        services/garmin_sync.py
                                        services/alert_engine.py  ← V2
                                                    │
                                                    ▼
                                        [Garmin Connect API]
                                        garth 0.8.0 / garminconnect 0.2.19
```

---

## Dépendances et versions

### Backend Python (VM)
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
garminconnect==0.2.19
garth==0.8.0
python-dotenv==1.0.1
```

### Frontend (libs locales, pas de CDN)
```
Chart.js 4.4.4  → frontend/js/vendor/chart.min.js
```

### Environnement VM
```
OS      : Debian GNU/Linux (trixie)
Python  : 3.13.5
Apache2 : 2.4.66
```

---

## Variables d'environnement (voir .env.example)

| Variable | Description | Valeur sur VM |
|----------|-------------|---------------|
| `GARMIN_EMAIL` | Email compte Garmin Connect | configuré |
| `GARMIN_PASSWORD` | Mot de passe Garmin Connect | configuré |
| `DATABASE_PATH` | Chemin du fichier SQLite | `/opt/athletix/backend/athletix.db` |
| `API_HOST` | Hôte d'écoute Uvicorn | `127.0.0.1` |
| `API_PORT` | Port Uvicorn | `8000` |

---

## Notes d'architecture

### Pourquoi SQLite ?
Application mono-utilisateur, auto-hébergée, faible charge.
SQLite est sans serveur, un seul fichier à sauvegarder,
performances largement suffisantes pour un usage personnel.

### Pourquoi FastAPI ?
Documentation auto-générée (Swagger à `/api/docs`), typage fort avec Pydantic,
performances ASGI, syntaxe concise. Idéal pour une API REST simple.

### Pourquoi vanilla JS ?
Pas de build toolchain, pas de dépendances npm à maintenir,
déploiement = copie de fichiers. Cohérent avec l'approche
auto-hébergée minimaliste.

### Migrations DB — approche additive
La stratégie est de toujours ajouter des tables (IF NOT EXISTS) sans jamais
modifier les tables existantes. Les blocs V1 et V2 dans `database.py` restent
visiblement séparés. L'`init_db()` est idempotent : relancer ne casse rien.
