# Structure du projet CTFd ACE 2025

## Vue d'ensemble

```
ACE-ctf-platform/
├── plugins/                    # Plugins CTFd
│   ├── auth_sync/             # SSO avec JWT
│   │   └── __init__.py
│   ├── registration_sync/     # Sync équipes
│   │   └── __init__.py
│   ├── score_sync/            # Sync scores
│   │   └── __init__.py
│   └── room_display/          # Affichage salles
│       └── __init__.py
│
├── challenges/                # Challenges CTF
│   └── test/                  # Challenge de test
│       ├── README.md
│       └── deploy/
│           ├── Dockerfile
│           └── app.py
│
├── docker-compose.yml         # Configuration services
├── Dockerfile                 # Image CTFd personnalisée
├── .env.example              # Template config
├── Makefile                  # Commandes simplifiées
├── README.md                 # Documentation principale
└── STRUCTURE.md              # Ce fichier
```

## Fichiers essentiels

### Configuration

| Fichier | Description |
|---------|-------------|
| `docker-compose.yml` | Services Docker (CTFd, MariaDB, Redis, Traefik, challenges) |
| `Dockerfile` | Image CTFd avec plugins et dépendances (requests, APScheduler, PyJWT) |
| `.env.example` | Variables d'environnement (JWT_SECRET, passwords, URLs) |
| `Makefile` | Commandes simplifiées (start, stop, logs, etc.) |

### Plugins

| Plugin | Rôle |
|--------|------|
| `auth_sync` | Authentification SSO avec JWT entre site et CTFd |
| `registration_sync` | Synchronisation équipes depuis le site (2 min) |
| `score_sync` | Envoi des scores vers le site (30 sec) |
| `room_display` | Affichage des salles dans l'interface |

### Challenges

| Challenge | Type | Difficulté | Flag |
|-----------|------|------------|------|
| `test` | Misc | Facile | `ACE{bienvenue_sur_la_plateforme_ctf}` |

## Services Docker

| Service | Port | Description |
|---------|------|-------------|
| `ctfd` | 8000 | Application CTFd |
| `db` | - (interne) | Base de données MariaDB |
| `cache` | - (interne) | Cache Redis |
| `traefik` | 8081, 8082, 8443 | Reverse proxy pour challenges |
| `challenge_test` | - (interne) | Challenge de test |

## Réseaux Docker

| Réseau | Type | Usage |
|--------|------|-------|
| `ctfd-internal` | bridge (internal) | Communication DB/Redis (pas d'accès internet) |
| `ctfd-challenges` | bridge | Réseau des challenges avec Traefik |
| `ace-network` | external | Réseau partagé avec le site d'inscription |

## Volumes persistants

| Volume | Contenu |
|--------|---------|
| `ctfd_db` | Base de données MariaDB |
| `ctfd_redis` | Cache Redis |
| `ctfd_uploads` | Fichiers uploadés sur CTFd |
| `ctfd_logs` | Logs de l'application |

## Variables d'environnement

### Essentielles

```env
# Base de données
MYSQL_ROOT_PASSWORD=changeme_root
MYSQL_PASSWORD=changeme_ctfd

# CTFd
SECRET_KEY=changeme_very_long_random_secret

# SSO (doit être identique au site)
JWT_SECRET=changez-moi-en-production
CTFD_PUBLIC_URL=http://localhost:8000

# Site d'inscription
REGISTRATION_SITE_URL=http://ace-website-backend-1:5000/api
REGISTRATION_SITE_ADMIN_EMAIL=admin@ace-escapegame.com
REGISTRATION_SITE_ADMIN_PASSWORD=Admin123!ChangeMoi
```

### Optionnelles

```env
# Mail (géré par le site d'inscription)
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAILFROM_ADDR=noreply@ace.com
MAIL_USERNAME=user
MAIL_PASSWORD=pass
```

## Flux SSO

```
Site d'inscription (localhost:3000)
          │
          │ 1. User clique "Accéder au CTFd"
          │ 2. Frontend POST token JWT + email
          ▼
  POST /sso/authenticate
          │
          │ 3. CTFd valide JWT avec JWT_SECRET
          │ 4. Crée/trouve l'utilisateur
          │ 5. login_user() + cookies session
          ▼
    CTFd /challenges
    (utilisateur connecté)
```

## Flux de synchronisation

### Équipes (toutes les 2 min)

```
Site backend:5000/api/admin/teams
          │
          ▼
[registration_sync plugin]
          │
          ▼
    CTFd Teams
```

### Scores (toutes les 30 sec)

```
    CTFd Scoreboard
          │
          ▼
[score_sync plugin]
          │
          ▼
Site backend:5000/api/admin/ctfd/sync-scores
```

## Commandes Makefile

```bash
make help      # Liste des commandes
make setup     # Créer .env
make start     # Démarrer services
make stop      # Arrêter services
make restart   # Redémarrer
make logs      # Logs CTFd
make status    # État des services
make build     # Rebuild image CTFd
make rebuild   # Rebuild + restart
make shell     # Shell dans CTFd
make test      # Test accès services
make clean     # Supprimer tout (avec confirmation)
```

## Créer un nouveau challenge

### 1. Structure

```
challenges/mon_challenge/
├── README.md
└── deploy/
    ├── Dockerfile
    └── app.py
```

### 2. Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py .
RUN pip install flask
CMD ["python", "app.py"]
```

### 3. Application

```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "Flag: ACE{mon_flag}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### 4. Docker Compose

Ajouter dans `docker-compose.yml` :

```yaml
  challenge_mon_challenge:
    build: ./challenges/mon_challenge/deploy
    restart: always
    networks:
      - ctfd-challenges
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mon.rule=Host(`mon.challenges.local`)"
      - "traefik.http.services.mon.loadbalancer.server.port=5000"
```

### 5. Déployer

```bash
docker compose up -d --build challenge_mon_challenge
```

## Vérifications

### Avant l'événement

- [ ] Site d'inscription lancé sur réseau `ace-website_ace-network`
- [ ] `.env` configuré avec JWT_SECRET identique au site
- [ ] `make start` réussit
- [ ] `make test` : CTFd et Traefik accessibles
- [ ] SSO fonctionne (test avec user et admin)
- [ ] Challenge test accessible sur http://test.challenges.local
- [ ] Synchronisation équipes/scores active

### Pendant l'événement

- [ ] `make status` : tous les services UP
- [ ] `make logs` : pas d'erreurs
- [ ] Scoreboard mis à jour
- [ ] Challenges accessibles

## Dépannage

### SSO ne fonctionne pas

1. Vérifier `JWT_SECRET` identique dans les deux `.env`
2. Vérifier réseau Docker : `docker network ls | grep ace`
3. Logs : `make logs | grep SSO`
4. Test manuel :
   ```bash
   curl -X POST http://localhost:8000/sso/authenticate \
     -d "token=<jwt>&email=<email>"
   ```

### Plugin ne charge pas

```bash
make rebuild
make logs | grep plugin
```

### Challenge inaccessible

```bash
# Vérifier Traefik
curl http://localhost:8082/api/http/routers

# Logs challenge
docker compose logs challenge_test

# Redémarrer
docker compose restart challenge_test
```

### Synchronisation échoue

```bash
# Vérifier site accessible depuis CTFd
docker compose exec ctfd curl -s http://ace-website-backend-1:5000/api/health

# Logs sync
make logs | grep -E "(registration_sync|score_sync)"
```

---


