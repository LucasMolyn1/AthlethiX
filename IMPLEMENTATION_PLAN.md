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
| Phase 10 | Tests + documentation finale | TODO |

---

## Fonctionnalités détaillées

### 1. Authentification Garmin
- [x] Connexion via `garminconnect` (email/password dans .env)
- [x] Gestion des tokens (stockage local, auto-refresh)
- [x] Endpoint de test de connexion `/api/garmin/test`
- [ ] Gestion d'erreur : token expiré, réseau, MFA

### 2. Synchronisation des activités
- [x] Service `garmin_sync.py` — récupération des activités
- [x] Mapping types Garmin → types internes (run/trail/cycling/swimming/strength)
- [x] Endpoint sync manuelle `/api/garmin/sync`
- [ ] Cron toutes les heures via script shell
- [ ] Gestion du rate limit Garmin
- [ ] Indicateur "dernière sync" stocké en DB

### 3. Dashboard API
- [ ] GET `/api/dashboard/week` — résumé semaine courante par sport
- [ ] GET `/api/dashboard/fitness-curve` — courbe de forme 30 jours
- [ ] GET `/api/dashboard/recent` — 5 dernières activités

### 4. Journal de séance
- [ ] POST `/api/journal/{activity_id}` — créer une entrée
- [ ] PUT `/api/journal/{activity_id}` — modifier
- [ ] GET `/api/journal/{activity_id}` — lire

### 5. Historique
- [ ] GET `/api/activities` — liste paginée avec filtres (type, date_from, date_to)
- [ ] GET `/api/activities/{id}` — détail complet

### 6. Frontend
- [ ] `index.html` — Dashboard avec Chart.js
- [ ] `history.html` — Historique avec filtres
- [ ] `activity.html` — Détail + journal
- [ ] `journal.html` — Vue journal seule
- [ ] CSS responsive
- [ ] `api.js` — couche d'appels fetch centralisée

---

## Architecture technique

```
Internet
    │
    ▼
[OpenResty] ← HTTPS/443, certificat SSL, domaine OVH
    │ HTTP proxy_pass
    ▼
[Apache2 :80] ← VM Debian LXC
    │
    ├─ /* ──────────────────────► /var/www/athletix/ (fichiers statiques)
    │                               index.html, css/, js/
    │
    └─ /api/* ──────────────────► 127.0.0.1:8000 (FastAPI / Uvicorn)
                                    │
                                    ├── routers/garmin.py
                                    ├── routers/activities.py
                                    ├── routers/journal.py
                                    └── routers/dashboard.py
                                              │
                                              ▼
                                    SQLite : athletix.db
                                    ├── activities
                                    └── journal_entries
                                              │
                                    services/garmin_sync.py
                                              │
                                              ▼
                                    [Garmin Connect API]
                                    (garminconnect lib)
```

---

## Dépendances et versions

### Backend Python
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
garminconnect==0.2.19
python-dotenv==1.0.1
```

### Frontend (libs locales, pas de CDN)
```
Chart.js 4.4.x  → frontend/js/vendor/chart.min.js
```

---

## Variables d'environnement (voir .env.example)

| Variable | Description | Exemple |
|----------|-------------|---------|
| `GARMIN_EMAIL` | Email compte Garmin Connect | user@example.com |
| `GARMIN_PASSWORD` | Mot de passe Garmin Connect | *** |
| `DATABASE_PATH` | Chemin du fichier SQLite | ./athletix.db |
| `API_HOST` | Hôte d'écoute Uvicorn | 127.0.0.1 |
| `API_PORT` | Port Uvicorn | 8000 |

---

## Notes d'architecture

### Pourquoi SQLite ?
Application mono-utilisateur, auto-hébergée, faible charge.
SQLite est sans serveur, un seul fichier à sauvegarder, 
performances largement suffisantes pour un usage personnel.

### Pourquoi FastAPI ?
Documentation auto-générée (Swagger), typage fort avec Pydantic,
performances ASGI, syntaxe concise. Idéal pour une API REST simple.

### Pourquoi vanilla JS ?
Pas de build toolchain, pas de dépendances npm à maintenir,
déploiement = copie de fichiers. Cohérent avec l'approche
auto-hébergée minimaliste.
