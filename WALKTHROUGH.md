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
      ├── /* ──────────────────► /var/www/athletix/   (HTML/CSS/JS)
      │                           index.html, history.html,
      │                           activity.html, journal.html
      │
      └── /api/* ──────────────► 127.0.0.1:8000       (FastAPI)
                                       │
                          ┌────────────┼────────────┐
                          ▼            ▼            ▼
                     garmin.py   activities.py  dashboard.py
                     journal.py
                          │
                          ▼
                      SQLite (athletix.db)
                   ┌──────────────────────┐
                   │ activities           │
                   │ journal_entries      │
                   │ sync_log             │
                   └──────────────────────┘
                          │
                    garmin_sync.py
                          │
                          ▼
                  [Garmin Connect API]
                  sso.garmin.com (OAuth)
```

### Pourquoi deux serveurs web (OpenResty + Apache2) ?

- **OpenResty** est déjà en place sur ton infra et gère le SSL pour tous tes services.
  Il "termine" la connexion HTTPS et passe la requête en HTTP simple à la VM.
- **Apache2** tourne sur la VM et fait deux choses : servir les fichiers statiques
  (HTML/CSS/JS) et rediriger les appels `/api/*` vers FastAPI. C'est ce qu'on appelle
  un "reverse proxy".

---

## Le frontend — `frontend/`

Quatre pages HTML en JavaScript vanilla (pas de React, pas de framework).
Toutes les données viennent de l'API FastAPI, jamais directement de la base.

| Page | Fichier | Rôle |
|------|---------|------|
| Dashboard | `index.html` + `dashboard.js` | Résumé semaine, courbe de forme 30j, dernières activités, bouton sync |
| Historique | `history.html` + `history.js` | Liste paginée avec filtres sport/date |
| Détail activité | `activity.html` + `activity.js` | Métriques complètes + formulaire journal |
| Journal | `journal.html` + `journal.js` | Vue des activités avec indicateur journal rempli/vide |

`js/api.js` centralise tous les appels `fetch()` vers le backend. Chaque page importe
ce fichier plutôt que de faire ses propres requêtes HTTP en dur.

`js/vendor/chart.min.js` — Chart.js 4.4.4 embarqué localement. Pas de CDN externe,
l'app fonctionne sans accès internet côté navigateur.

---

## Le backend FastAPI — `backend/`

### `main.py`
Le point d'entrée. Il démarre le serveur, configure les autorisations CORS
(qui peut appeler l'API), et branche tous les "routers". Initialise aussi
la DB au démarrage si les tables n'existent pas encore.

### `database.py`
Configure la connexion à SQLite et crée les tables au premier démarrage.
SQLite = un fichier `.db` sur le disque. Pas de serveur, pas de service,
juste un fichier qu'on peut sauvegarder avec `cp`.

### `services/garmin_sync.py`
Le cœur de la synchronisation. Il :
1. Ouvre une session Garmin Connect avec email/mot de passe (depuis `.env`)
2. Récupère les activités des N derniers jours
3. Mappe les types Garmin (`trail_running`, `road_biking`…) vers nos types internes (`trail`, `cycling`…)
4. Insère en base uniquement les activités absentes (le champ `garmin_id` est unique)
5. Enregistre le résultat dans `sync_log` (date, nb ajoutés, erreur éventuelle)

**Gestion des tokens** : la lib `garth` (utilisée par `garminconnect`) stocke des
tokens OAuth dans `~/.garminconnect` sur la VM. Après la première authentification
réussie, ces tokens sont réutilisés — Garmin SSO n'est plus sollicité à chaque sync.

### `routers/`
Chaque fichier est une "famille" d'endpoints :
- `garmin.py` → `GET /api/garmin/test`, `POST /api/garmin/sync`
- `activities.py` → `GET /api/activities`, `GET /api/activities/{id}`
- `journal.py` → `GET/POST/PUT /api/journal/{activity_id}`
- `dashboard.py` → `GET /api/dashboard/week`, `/fitness`, `/recent`, `/sync-status`

La documentation interactive de l'API est accessible à `http://192.168.1.26/api/docs`
(générée automatiquement par FastAPI).

---

## La base de données — 3 tables

### `activities`
Toutes les activités Garmin synchronisées. Le champ `raw_json` stocke
la réponse complète de Garmin en JSON, au cas où on aurait besoin d'un champ
qui n'a pas été extrait explicitement.

### `journal_entries`
Les notes personnelles liées à chaque activité. Une activité peut avoir
0 ou 1 entrée de journal. La relation est assurée par `activity_id` (clé étrangère).
`ON DELETE CASCADE` : si on supprime une activité, son journal est supprimé aussi.

### `sync_log`
Historique de toutes les synchronisations (date, statut, nombre d'activités
ajoutées, message d'erreur éventuel). Alimenté par `garmin_sync.py` et lu
par `GET /api/dashboard/sync-status` pour afficher le badge dans le dashboard.

---

## Le fichier `.env` — les secrets

Jamais commité dans Git (listé dans `.gitignore`). Contient les informations sensibles :
- `GARMIN_EMAIL` / `GARMIN_PASSWORD` : tes credentials Garmin
- `DATABASE_PATH` : chemin vers le fichier SQLite (`/opt/athletix/backend/athletix.db`)
- `API_HOST` / `API_PORT` : écoute sur `127.0.0.1:8000` (jamais exposé directement)

---

## Déploiement — ce qui tourne sur la VM (192.168.1.26)

```
/opt/athletix/                    ← code source de l'application
├── backend/
│   ├── athletix.db               ← base de données SQLite
│   ├── main.py, database.py…
│   ├── routers/
│   └── services/
├── venv/                         ← environnement Python 3.13 isolé
└── .env                          ← secrets (pas dans Git)

/var/www/athletix/                ← fichiers HTML/CSS/JS servis par Apache2

/etc/apache2/sites-enabled/athletix.conf  ← vhost Apache2
/etc/systemd/system/athletix.service      ← service systemd (démarrage auto)
/etc/cron.d/athletix                      ← sync automatique toutes les heures
/var/log/athletix_sync.log                ← logs des syncs cron
```

### Commandes utiles sur la VM

```bash
# État du service
sudo systemctl status athletix

# Logs en temps réel
sudo journalctl -u athletix -f

# Redémarrer après une modification de code
sudo systemctl restart athletix

# Tester l'API localement
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:8000/api/garmin/sync -H "Content-Type: application/json" -d '{"days": 30}'

# Voir les logs de sync cron
tail -f /var/log/athletix_sync.log
```

---

## Garmin Connect et le rate limiting

### Comment fonctionne l'authentification
La lib Python `garminconnect` utilise la lib `garth` pour s'authentifier via
l'endpoint SSO de Garmin (`sso.garmin.com/mobile/api/login`). C'est l'API
qu'utilisent les apps mobiles tierces. Ce n'est pas l'API officielle Garmin
(qui nécessite une inscription développeur).

### Tokens OAuth — fonctionnement après la première sync
À la première authentification réussie, `garth` sauvegarde des tokens OAuth
dans `~/.garminconnect` sur la VM. Les syncs suivantes **réutilisent ces tokens**
sans rappeler Garmin SSO. Les tokens durent plusieurs semaines.

En cas d'expiration, `garth` tente un refresh automatique. Seulement si le refresh
échoue, il ré-authentifie avec email/mot de passe.

### Rate limit (erreur 429)
Garmin bloque temporairement l'IP qui fait trop de tentatives de login en peu
de temps. Cette situation est arrivée lors du déploiement initial (nombreuses
tentatives de test en rafale).

**À retenir :**
- Ne jamais appuyer plusieurs fois sur "Synchroniser" rapidement
- Le cron toutes les heures est une fréquence raisonnable pour Garmin
- Si le 429 revient : attendre sans retenter, les tokens se rafraîchiront seuls

**Le dashboard affiche un message d'erreur explicite** (toast rouge) en cas de
rate limit — plus de HTTP 500 silencieux.

---

## Sauvegarder l'application

Un seul fichier contient toutes tes données : `/opt/athletix/backend/athletix.db`

```bash
# Sauvegarder manuellement
cp /opt/athletix/backend/athletix.db ~/athletix_backup_$(date +%Y%m%d).db

# Ou via rsync depuis ta machine
rsync debian@192.168.1.26:/opt/athletix/backend/athletix.db ./athletix_backup.db
```
