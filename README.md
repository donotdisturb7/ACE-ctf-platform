# ACE CTF Platform 2025

Plateforme CTFd intégrée avec authentification SSO pour la ACE 2025.

## Architecture

```
Site d'inscription (localhost:3000)
           |
           | SSO JWT
           v
      CTFd (localhost:8000)
           |
     +-----+-----+
     |           |
MariaDB       Redis
```

### Services

- **CTFd** : Plateforme CTF (port 8000)
- **MariaDB** : Base de données
- **Redis** : Cache
- **Traefik** : Reverse proxy pour challenges (port 8081)

### Plugins

- `auth_sync` : Authentification SSO avec tokens JWT
- `registration_sync` : Sync équipes avec le site
- `score_sync` : Sync scores vers le site
- `room_display` : Affichage des salles

## Structure

```
ACE-ctf-platform/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── plugins/
│   ├── auth_sync/           # Plugin SSO
│   ├── registration_sync/
│   ├── score_sync/
│   └── room_display/
└── challenges/
    └── test/                # Challenge de test
        ├── README.md
        └── deploy/
            ├── Dockerfile
            └── app.py
```

## Configuration SSO

### Variables d'environnement

Créez `.env` :

```env
# Base de données
MYSQL_ROOT_PASSWORD=changeme_root
MYSQL_PASSWORD=changeme_ctfd

# CTFd
SECRET_KEY=changeme_very_long_random_secret

# SSO (IMPORTANT : doit correspondre au site d'inscription)
JWT_SECRET=changez-moi-en-production
CTFD_PUBLIC_URL=http://localhost:8000

# Integration site
REGISTRATION_SITE_URL=http://ace-website-backend-1:5000/api
```

### Fonctionnement SSO

1. Utilisateur se connecte sur le site d'inscription
2. Backend génère un JWT token
3. Utilisateur clique sur "Accéder au CTFd" dans le dashboard
4. Le navigateur POST le token à CTFd :
   ```
   POST /sso/authenticate
   Content-Type: application/x-www-form-urlencoded

   token=<jwt_token>&email=<user_email>
   ```
5. CTFd valide le token JWT (avec JWT_SECRET)
6. CTFd crée ou trouve l'utilisateur
7. CTFd crée la session (`login_user`)
8. Redirection vers `/challenges` avec cookies de session
9. L'utilisateur est connecté

### Configuration requise

1. **JWT_SECRET identique** : Même valeur dans les deux `.env` (site + CTFd)
2. **Réseau Docker** : CTFd doit être sur `ace-website_ace-network`
3. **CTFD_PUBLIC_URL** : URL accessible par le navigateur (pas l'URL Docker interne)

## Quick Start

### 1. Prérequis

- Docker & Docker Compose
- Site d'inscription ACE lancé
- Réseau `ace-website_ace-network` existant

### 2. Configuration

```bash
cp .env.example .env
# Éditer .env avec les vraies valeurs
```

### 3. Démarrage

```bash
docker compose up -d
```

Attendez ~30 secondes que CTFd démarre.

### 4. Accès

- CTFd : http://localhost:8000
- Challenge test : http://test.challenges.local (ajouter au `/etc/hosts`)
- Traefik : http://localhost:8082

### 5. Première installation

1. Accédez à http://localhost:8000
2. Suivez l'assistant de configuration
3. Créez le compte admin CTFd

## Challenges

### Challenge de test

Un challenge simple pour vérifier l'infrastructure.

**Accès** : `http://test.challenges.local`
**Flag** : `ACE{bienvenue_sur_la_plateforme_ctf}`

Ajoutez au `/etc/hosts` (ou `C:\Windows\System32\drivers\etc\hosts`) :
```
127.0.0.1 test.challenges.local
```

### Créer un challenge

1. Créer le dossier :
```bash
mkdir -p challenges/mon_challenge/deploy
```

2. Créer `Dockerfile` :
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py .
RUN pip install flask
CMD ["python", "app.py"]
```

3. Créer `app.py` :
```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "Flag: ACE{mon_flag}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

4. Ajouter dans `docker-compose.yml` :
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

5. Déployer :
```bash
docker compose up -d --build challenge_mon_challenge
```

## Commandes

```bash
# Aide (liste toutes les commandes)
make help

# Démarrer
make start

# Arrêter
make stop

# Redémarrer
make restart

# Logs CTFd
make logs

# Status
make status

# Rebuild après modification plugin
make rebuild

# Test accès services
make test

# Shell CTFd (debug)
make shell

# Supprimer données (ATTENTION)
make clean
```

## Dépannage

### SSO ne fonctionne pas

1. Vérifier JWT_SECRET identique dans les deux projets
2. Logs backend : `docker logs ace-website-backend-1`
3. Logs CTFd : `docker compose logs ctfd | grep SSO`
4. Test manuel :
```bash
curl -X POST http://localhost:8000/sso/authenticate \
  -d "token=<jwt>&email=<email>"
```

### Plugin ne charge pas

```bash
docker compose up -d --build ctfd
docker compose logs ctfd | grep plugin
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

## Ports

| Service | Port | Description |
|---------|------|-------------|
| CTFd | 8000 | Interface web |
| Traefik | 8081 | Proxy challenges |
| Traefik HTTPS | 8443 | HTTPS |
| Traefik Dashboard | 8082 | Dashboard |

## Sécurité

- Tokens JWT avec expiration
- Validation tokens côté serveur
- Passwords hashés (bcrypt)
- CSRF désactivé uniquement pour SSO
- Base de données sur réseau interne
- Secrets via variables d'environnement

## Documentation

- [CTFd Docs](https://docs.ctfd.io/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Traefik](https://doc.traefik.io/traefik/)

---


