# IMPLEMENTATION PLAN — AthletiX

## Statut global

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
| Phase 10 | Tests + documentation finale | ➡️ Reporté V2 |

> **V1 validée fonctionnellement le 2026-04-27.**
> Sync Garmin en attente de levée du rate limit (IP de la VM temporairement bannie
> suite aux tentatives répétées lors du déploiement). Toutes les fonctionnalités
> sont implémentées et le code est correct — le problème est opérationnel, pas technique.

---

## Fonctionnalités détaillées

### 1. Authentification Garmin
- [x] Connexion via `garminconnect` (email/password dans .env)
- [x] Gestion des tokens (stockage local `~/.garminconnect`, auto-refresh)
- [x] Endpoint de test de connexion `GET /api/garmin/test`
- [x] Gestion rate limit 429 (`GarthHTTPError` → JSON 200 avec message d'erreur)
- [x] Gestion erreur réseau (`GarminConnectConnectionError` catchée)
- [x] Gestion credentials invalides (`GarminConnectAuthenticationError` catchée)
- [ ] **MFA (2FA)** — non géré. Si le compte Garmin a la double authentification
      activée, la connexion échoue sans message explicite. Nécessite un setup
      manuel des tokens via script interactif séparé (V2).

### 2. Synchronisation des activités
- [x] Service `garmin_sync.py` — récupération des activités par plage de dates
- [x] Mapping types Garmin → types internes (run/trail/cycling/swimming/strength)
- [x] Endpoint sync manuelle `POST /api/garmin/sync` (param `days`, défaut 30)
- [x] Cron toutes les heures `/etc/cron.d/athletix` (installé sur VM)
- [x] Gestion du rate limit Garmin (429 → message clair, pas de retry immédiat)
- [x] Indicateur "dernière sync" stocké dans table `sync_log` + `GET /api/dashboard/sync-status`

### 3. Dashboard API
- [x] `GET /api/dashboard/week` — résumé semaine courante agrégé par sport
- [x] `GET /api/dashboard/fitness` — courbe de charge d'entraînement 30 jours
      ⚠️ Note : le plan initial disait `/fitness-curve`, l'implémentation
      utilise `/fitness`. `api.js` est cohérent avec le code, pas de bug.
- [x] `GET /api/dashboard/recent` — 5 dernières activités
- [x] `GET /api/dashboard/sync-status` — date et statut de la dernière sync

### 4. Journal de séance
- [x] `POST /api/journal/{activity_id}` — créer une entrée (409 si déjà existante)
- [x] `PUT /api/journal/{activity_id}` — mettre à jour (champs partiels supportés)
- [x] `GET /api/journal/{activity_id}` — lire (404 si absente)

### 5. Historique
- [x] `GET /api/activities` — liste paginée avec filtres `type`, `date_from`,
      `date_to`, `limit`, `offset`. Tri date décroissante.
- [x] `GET /api/activities/{id}` — détail complet + journal associé dans la réponse

### 6. Frontend
- [x] `index.html` — Dashboard : résumé semaine, courbe Chart.js, activités récentes,
      bouton sync manuelle, badge statut sync
- [x] `history.html` — Historique avec filtres sport/date, pagination 20/page
- [x] `activity.html` — Métriques détaillées + formulaire journal (create/update)
- [x] `journal.html` — Vue journal : liste activités avec indicateur rempli/vide
- [x] `css/style.css` — Design sombre responsive, breakpoint 768px
- [x] `js/api.js` — Couche fetch centralisée, tous les endpoints couverts
- [x] `js/vendor/chart.min.js` — Chart.js 4.4.4 embarqué localement (pas de CDN)

### Phase 10 — Tests et documentation
- [x] `WALKTHROUGH.md` — documentation complète à jour
- [x] `CHANGELOG.md` — tenu à jour à chaque version
- [x] `IMPLEMENTATION_PLAN.md` — ce fichier
- [ ] **Tests automatisés** — aucun test unitaire ni d'intégration n'existe.
      L'API a été validée manuellement (curl, dashboard). (V2)
- [ ] **Première sync Garmin validée** — en attente de la levée du rate limit
      sur la VM (conséquence des tentatives répétées lors du déploiement).

---

## Ce qui manque réellement en V1

| Item | Impact | Priorité |
|------|--------|----------|
| Première sync Garmin (rate limit levé) | Bloquant pour valider l'app | Immédiat |
| Gestion MFA Garmin | Bloquant si 2FA activé sur le compte | Faible (compte sans 2FA) |
| Tests automatisés | Aucun filet de sécurité pour les évolutions | V2 |

---

## Architecture technique

```
Internet
    │
    ▼
[OpenResty] ← HTTPS/443, certificat SSL, domaine OVH
    │ HTTP proxy_pass
    ▼
[Apache2 :80] ← VM Debian LXC (192.168.1.26)
    │
    ├─ /* ──────────────────────► /var/www/athletix/ (fichiers statiques)
    │                               index.html, history.html,
    │                               activity.html, journal.html
    │                               css/style.css, js/*.js
    │
    └─ /api/* ──────────────────► 127.0.0.1:8000 (FastAPI / Uvicorn)
                                    │
                                    ├── routers/garmin.py
                                    ├── routers/activities.py
                                    ├── routers/journal.py
                                    └── routers/dashboard.py
                                              │
                                              ▼
                                    SQLite : /opt/athletix/backend/athletix.db
                                    ├── activities
                                    ├── journal_entries
                                    └── sync_log
                                              │
                                    services/garmin_sync.py
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
garth==0.8.0          ← dépendance de garminconnect, SSO OAuth
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
