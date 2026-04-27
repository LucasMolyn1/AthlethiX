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
[Apache2]    ← Le "serveur web" : sert les fichiers HTML/CSS/JS
      │
      ├── Si l'URL est /api/* → redirige vers FastAPI
      │                              │
      │                              ▼
      │                         [FastAPI]  ← L'"API" : cerveau de l'application
      │                              │
      │                              ▼
      │                         [SQLite]   ← La base de données (un seul fichier)
      │
      └── Sinon → envoie directement le fichier HTML/CSS/JS
```

### Pourquoi deux serveurs web (OpenResty + Apache2) ?

- **OpenResty** est déjà en place sur ton infra et gère le SSL pour tous tes services.
  Il "termine" la connexion HTTPS et passe la requête en HTTP simple à la VM.
- **Apache2** tourne sur la VM et fait deux choses : servir les fichiers statiques
  (HTML/CSS/JS) et rediriger les appels API vers FastAPI. C'est ce qu'on appelle
  un "reverse proxy".

---

## Le backend FastAPI — `backend/`

### `main.py`
Le point d'entrée. Il démarre le serveur, configure les autorisations CORS
(qui peut appeler l'API), et branche tous les "routers".

### `database.py`
Configure la connexion à SQLite et crée les tables au premier démarrage.
SQLite = un fichier `.db` sur le disque. Pas de serveur, pas de service,
juste un fichier qu'on peut sauvegarder avec `cp`.

### `services/garmin_sync.py`
Le cœur de la synchronisation. Il :
1. Se connecte à Garmin Connect avec ton email/mot de passe (depuis `.env`)
2. Récupère les activités des N derniers jours
3. "Mappe" les types Garmin (ex: `trail_running`) vers nos types internes (`trail`)
4. Insère en base uniquement les activités qui n'y sont pas déjà

**Gestion des tokens Garmin** : la lib `garminconnect` stocke automatiquement
des tokens de session dans un fichier local (`.garminconnect`). Elle les réutilise
à chaque démarrage. Si les tokens expirent, elle se ré-authentifie automatiquement.

### `routers/`
Chaque fichier correspond à une "famille" d'endpoints API :
- `garmin.py` → `/api/garmin/test`, `/api/garmin/sync`
- `activities.py` → `/api/activities`, `/api/activities/{id}`
- `journal.py` → `/api/journal/{activity_id}`
- `dashboard.py` → `/api/dashboard/*`

---

## La base de données — 3 tables

### `activities`
Toutes les activités Garmin synchronisées. Le champ `raw_json` stocke
la réponse complète de Garmin en JSON, au cas où on aurait besoin d'un champ
qui n'a pas été extrait explicitement.

### `journal_entries`
Les notes personnelles liées à chaque activité. Une activité peut avoir
0 ou 1 entrée de journal. La relation est assurée par `activity_id` (clé étrangère).

### `sync_log`
Historique de toutes les synchronisations (date, statut, nombre d'activités
ajoutées, message d'erreur éventuel). Permet de voir quand la dernière sync
a eu lieu et si elle a réussi.

---

## Le fichier `.env` — les secrets

Jamais commité dans Git. Contient les informations sensibles :
- `GARMIN_EMAIL` / `GARMIN_PASSWORD` : tes credentials Garmin
- `DATABASE_PATH` : chemin vers le fichier SQLite
- `API_HOST` / `API_PORT` : configuration du serveur

---

## Déploiement — ce qui tourne sur la VM

```
/opt/athletix/          ← code source de l'application
├── backend/
│   └── athletix.db     ← base de données SQLite (créée au 1er démarrage)
├── venv/               ← environnement Python isolé
└── .env                ← tes secrets (pas dans Git)

/var/www/athletix/      ← fichiers HTML/CSS/JS servis par Apache2

/etc/systemd/system/athletix.service  ← le service qui garde FastAPI actif
/etc/cron.d/athletix                  ← la sync automatique toutes les heures
```

### Démarrer / arrêter l'application
```bash
systemctl start athletix    # démarrer
systemctl stop athletix     # arrêter
systemctl restart athletix  # redémarrer
systemctl status athletix   # voir l'état
journalctl -u athletix -f   # voir les logs en temps réel
```

---

## Points d'attention

### La sync Garmin peut échouer si :
- Ton mot de passe Garmin a changé → mettre à jour `.env` et redémarrer
- Garmin a une panne → la sync réessaiera à l'heure suivante (cron)
- Garmin impose un rate limit → espacer les syncs (le cron toutes les heures est raisonnable)

### Sauvegarder l'application
Un seul fichier à sauvegarder : `/opt/athletix/backend/athletix.db`
C'est toute ta base de données. Un simple `cp` ou `rsync` suffit.
