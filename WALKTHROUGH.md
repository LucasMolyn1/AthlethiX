# WALKTHROUGH — AthletiX

Guide technique expliqué simplement. Pour comprendre ce qui a été construit,
comment ça fonctionne, et pourquoi ces choix.

---

## Vue d'ensemble

AthletiX est une application web auto-hébergée qui :
1. Se connecte à ton compte Garmin Connect et récupère tes activités sportives
2. Les stocke dans une base de données locale (SQLite)
3. Te permet de les consulter via un tableau de bord dans ton navigateur
4. Te permet d'ajouter un journal personnel à chaque séance
5. Suit tes séances de musculation avec progression 1RM (formule Epley)
6. Journal nutritionnel quotidien : hydratation, repas, compléments, score
7. Génère des alertes intelligentes sur ta charge d'entraînement
8. Compare deux périodes ou deux exercices côte à côte avec graphiques

L'application tourne entièrement sur ta VM Debian. Aucune donnée ne sort
vers un service cloud externe (hors Garmin Connect qui est la source).

---

## Architecture : comment les pièces s'assemblent

```
Ton navigateur
      │  HTTPS
      ▼
[OpenResty]  ← Le "portier" : gère le certificat SSL et ton domaine OVH
      │  HTTP
      ▼
[Apache2 :80]  ← Le "serveur web" sur la VM Debian (192.168.1.26)
      │
      ├── /* ──────────────────────► /var/www/athletix/
      │       index.html      history.html    activity.html
      │       journal.html    strength.html   strength_session.html
      │       exercise.html   nutrition.html  compare.html
      │       css/style.css
      │       js/api.js       js/alerts.js    js/dashboard.js
      │       js/history.js   js/activity.js  js/journal.js
      │       js/strength.js  js/strength_session.js
      │       js/exercise.js  js/nutrition.js js/compare.js
      │
      └── /api/* ──────────────────► 127.0.0.1:8000 (FastAPI/Uvicorn)
                     │
                     ├── garmin.py       → sync Garmin Connect
                     ├── activities.py   → CRUD activités
                     ├── journal.py      → journal de séance
                     ├── dashboard.py    → agrégats dashboard
                     ├── strength.py     → séances musculation (V2)
                     ├── nutrition.py    → journal nutritionnel (V2)
                     ├── alerts.py       → alertes entraînement (V2)
                     └── compare.py      → module comparaison (V2)
                                  │
                             SQLite (athletix.db)
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
                    services/alert_engine.py (V2)
                                  │
                          [Garmin Connect API]
```

### Pourquoi deux serveurs web (OpenResty + Apache2) ?

- **OpenResty** est déjà en place sur ton infra et gère le SSL pour tous tes services.
  Il "termine" la connexion HTTPS et passe la requête en HTTP simple à la VM.
- **Apache2** tourne sur la VM et fait deux choses : servir les fichiers statiques
  (HTML/CSS/JS) et rediriger les appels `/api/*` vers FastAPI.

---

## Le frontend — `frontend/`

Pages HTML en JavaScript vanilla (pas de React, pas de framework).
Toutes les données viennent de l'API FastAPI, jamais directement de la base.

### Pages V1

| Page | Fichier JS | Rôle |
|------|-----------|------|
| Dashboard | `dashboard.js` | Résumé semaine, courbe de forme 30j, dernières activités, sync |
| Historique | `history.js` | Liste paginée avec filtres sport/date |
| Détail activité | `activity.js` | Métriques complètes + formulaire journal |
| Journal | `journal.js` | Vue activités avec indicateur journal rempli/vide |

### Pages V2

| Page | Fichier JS | Rôle |
|------|-----------|------|
| Musculation | `strength.js` | Liste séances, filtres, bibliothèque exercices + création custom |
| Séance | `strength_session.js` | Formulaire séance (métadonnées + séries dynamiques), create/update/delete |
| Exercice | `exercise.js` | Fiche exercice : courbe 1RM Chart.js, PR, historique |
| Nutrition | `nutrition.js` | Journal quotidien : navigation ←/→, formulaire, historique récent |
| Comparaison | `compare.js` | Deux onglets : comparaison périodes (bar chart) + exercices (line chart) |

### Fichiers JS partagés

`js/api.js` — centralise tous les appels `fetch()` vers le backend. Les erreurs HTTP
exposent `err.status` pour distinguer 404 des vraies erreurs réseau.

`js/alerts.js` — chargé sur toutes les pages. Injecte la bannière d'alertes non lues
en haut du `<main>`, et un badge rouge dans le logo sidebar avec le compteur.

`js/vendor/chart.min.js` — Chart.js 4.4.4 embarqué localement (pas de CDN).

---

## Le backend FastAPI — `backend/`

### `main.py`
Point d'entrée. Démarre le serveur, configure CORS, branche tous les routers,
initialise la DB au démarrage (idempotent).

### `database.py`
Configure SQLite et crée les tables. Deux blocs `executescript` distincts :
- Bloc V1 (activities, journal_entries, sync_log) — jamais modifié
- Bloc V2 (exercises, strength_sessions, exercise_sets, alerts, nutrition_logs)

`_seed_exercises()` insère 16 exercices par défaut à chaque démarrage (INSERT OR IGNORE).

### `services/garmin_sync.py`
1. Ouvre une session Garmin Connect avec email/mot de passe (`.env`)
2. Récupère les activités des N derniers jours
3. Mappe les types Garmin vers les types internes (run/trail/cycling/swimming/strength)
4. Insère uniquement les activités absentes (`garmin_id` UNIQUE)
5. Enregistre le résultat dans `sync_log`

### `services/alert_engine.py` (V2)
Analyse la DB et génère des alertes dans la table `alerts`. Appelé au démarrage
et à chaque sync Garmin. 4 règles : surcharge cardio, repos insuffisant, PR 1RM, hydratation basse.
Idempotent : `_already_open()` évite les doublons, `_close_alert()` résout les conditions passées.

### `routers/` — détail des endpoints

**V1 : `garmin.py`**
- `GET /api/garmin/test` — vérifie les credentials Garmin
- `POST /api/garmin/sync` — déclenche une sync manuelle

**V1 : `activities.py`**
- `GET /api/activities` — liste paginée, filtres type/date
- `GET /api/activities/{id}` — détail + journal associé

**V1 : `journal.py`**
- `GET /api/journal/{activity_id}`
- `POST /api/journal/{activity_id}`
- `PUT /api/journal/{activity_id}`

**V1 : `dashboard.py`**
- `GET /api/dashboard/week` — résumé semaine en cours
- `GET /api/dashboard/fitness` — courbe de charge 30 jours
- `GET /api/dashboard/recent` — 5 dernières activités
- `GET /api/dashboard/sync-status` — date et statut de la dernière sync
- `GET /api/dashboard/extras` — (V2) avg hydratation + score nutrition, séances + volume muscu semaine

**V2 : `strength.py`**
- `GET /api/strength/sessions` — liste paginée, filtres dates, `sets_count` agrégé
- `POST /api/strength/sessions` — crée séance + séries (atomique)
- `GET /api/strength/sessions/{id}` — détail + séries avec noms exercices
- `PUT /api/strength/sessions/{id}` — mise à jour partielle + remplacement optionnel séries
- `DELETE /api/strength/sessions/{id}` — supprime (CASCADE sur séries)
- `GET /api/strength/exercises` — bibliothèque, filtre catégorie optionnel
- `POST /api/strength/exercises` — crée exercice custom (409 si doublon nom)
- `GET /api/strength/exercises/{id}/progress` — courbe 1RM Epley, PR, historique

**V2 : `nutrition.py`**
- `GET /api/nutrition/logs` — liste paginée, filtres dates
- `GET /api/nutrition/logs/{date}` — journal d'un jour (404 si absent)
- `POST /api/nutrition/logs` — crée (409 si date déjà existante)
- `PUT /api/nutrition/logs/{date}` — remplace intégralement
- `DELETE /api/nutrition/logs/{date}` — supprime

**V2 : `alerts.py`**
- `GET /api/alerts` — alertes non lues (param `unread_only`, défaut `true`)
- `PUT /api/alerts/{id}/read` — marquer lue
- `DELETE /api/alerts/{id}` — supprimer une alerte
- `DELETE /api/alerts` — supprimer toutes les alertes déjà lues

**V2 : `compare.py`**
- `GET /api/compare/periods` — stats deux périodes (activités, durée, distance, séances muscu)
- `GET /api/compare/exercises` — comparaison deux exercices (PR, best 1RM, historique sessions)

La documentation interactive est accessible à `http://192.168.1.26/api/docs`.

---

## La base de données

### Tables V1

**`activities`** — activités Garmin synchronisées.
- `garmin_id TEXT UNIQUE` : évite les doublons lors des syncs
- `raw_json TEXT` : réponse complète de Garmin, au cas où

**`journal_entries`** — notes personnelles liées à une activité.
- 0 ou 1 entrée par activité
- `ON DELETE CASCADE` sur `activity_id`

**`sync_log`** — historique de toutes les synchronisations.
- Date, statut, nombre d'activités ajoutées, message d'erreur éventuel

### Tables V2

**`exercises`** — bibliothèque d'exercices.
- `name TEXT UNIQUE` : pas de doublons
- `category` : push / pull / legs / core / cardio
- `is_custom INTEGER` : 0 = bibliothèque par défaut, 1 = exercice personnalisé
- 16 exercices pré-chargés au démarrage

**`strength_sessions`** — séances de musculation.
- Scores fatigue/sommeil/ressenti : INTEGER 1–10 (optionnels)
- `session_type` : full_body / push / pull / legs / upper / lower / cardio / other
- `duration` : durée en secondes

**`exercise_sets`** — séries d'une séance.
- FK `session_id` → `strength_sessions` (CASCADE)
- FK `exercise_id` → `exercises`
- `set_number` : numéro de série par exercice (calculé côté JS au moment de la sauvegarde)
- `feeling INTEGER 1–5` : ressenti de la série spécifiquement

**`alerts`** — alertes générées par le moteur d'analyse.
- `level` : danger / warning / info / success
- `is_read INTEGER DEFAULT 0` : badge dans la nav

**`nutrition_logs`** — journal nutritionnel.
- `date TEXT UNIQUE` : un seul enregistrement par jour
- Champs : hydration_liters, nutrition_score (1–10), pre/post_workout_meal, supplements, notes

---

## Formule Epley (1RM estimé)

Utilisée dans le module musculation pour estimer le 1RM (record sur une répétition)
à partir d'une série avec plusieurs répétitions :

```
1RM = poids_kg × (1 + reps / 30)
```

Fiable jusqu'à environ 12 répétitions. Au-delà, sous-estime le 1RM réel.
Implémentée dans `_epley_1rm()` dans `strength.py`.

---

## Scores touch-aware dans les formulaires

Les sliders de scores (fatigue, sommeil, ressenti, nutrition) utilisent
un attribut `data-touched="0"`. Le score n'est envoyé à l'API (valeur non-null)
que si l'utilisateur a effectivement bougé le slider. Cela évite d'enregistrer
une valeur par défaut (5/10) quand l'utilisateur n'a pas renseigné le score.

Au chargement d'une entrée existante avec un score, `data-touched` est mis à `"1"`
et le slider est positionné sur la valeur existante.

---

## Le fichier `.env` — les secrets

Jamais commité dans Git (listé dans `.gitignore`). Contient :
- `GARMIN_EMAIL` / `GARMIN_PASSWORD` : credentials Garmin
- `DATABASE_PATH` : chemin vers le fichier SQLite
- `API_HOST` / `API_PORT` : écoute sur `127.0.0.1:8000`

---

## Déploiement — ce qui tourne sur la VM (192.168.1.26)

```
/opt/athletix/
├── backend/
│   ├── athletix.db               ← base de données SQLite (toutes les données)
│   ├── main.py
│   ├── database.py
│   ├── routers/
│   │   ├── garmin.py    activities.py  journal.py  dashboard.py
│   │   ├── strength.py  nutrition.py  alerts.py   compare.py   ← V2
│   ├── services/
│   │   ├── garmin_sync.py
│   │   └── alert_engine.py                                      ← V2
│   └── .env
├── venv/                         ← environnement Python 3.13
└── requirements.txt

/var/www/athletix/                ← fichiers HTML/CSS/JS

/etc/systemd/system/athletix.service
/etc/cron.d/athletix              ← sync automatique toutes les heures
/var/log/athletix_sync.log
```

### Commandes utiles sur la VM

```bash
# État du service
sudo systemctl status athletix

# Logs en temps réel
journalctl -u athletix -f

# Redémarrer après modification de code backend
sudo systemctl restart athletix

# Tester l'API
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/strength/exercises
curl http://127.0.0.1:8000/api/nutrition/logs
curl http://127.0.0.1:8000/api/alerts
curl http://127.0.0.1:8000/api/dashboard/extras

# Comparaison de périodes
curl "http://127.0.0.1:8000/api/compare/periods?a_from=2026-04-20&a_to=2026-04-27&b_from=2026-04-13&b_to=2026-04-19"

# Déclencher une sync Garmin manuellement
curl -X POST http://127.0.0.1:8000/api/garmin/sync \
     -H "Content-Type: application/json" \
     -d '{"days": 30}'

# Logs cron
tail -f /var/log/athletix_sync.log
```

---

## Garmin Connect et le rate limiting

### Fonctionnement des tokens OAuth
La lib `garth` sauvegarde des tokens OAuth dans `~/.garminconnect` à la
première authentification. Les syncs suivantes réutilisent ces tokens.
En cas d'expiration, `garth` tente un refresh automatique.

### Rate limit (429)
Garmin bloque l'IP après trop de tentatives de login rapprochées.
- Ne jamais appuyer plusieurs fois sur "Synchroniser" rapidement
- Le cron toutes les heures est raisonnable
- En cas de 429 : attendre, les tokens se rafraîchiront seuls
- Le dashboard affiche un message d'erreur explicite (toast rouge)

---

## Sauvegarder l'application

Un seul fichier contient toutes tes données : `/opt/athletix/backend/athletix.db`

```bash
# Depuis la VM
cp /opt/athletix/backend/athletix.db ~/athletix_backup_$(date +%Y%m%d).db

# Depuis ta machine (Mac)
rsync debian@192.168.1.26:/opt/athletix/backend/athletix.db ./athletix_backup.db
```
