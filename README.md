# ACE CTF Platform 2025

Plateforme CTFd avec authentification SSO pour l'ACE 2025.

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

## Services

- **CTFd**: Plateforme CTF (port 8000)
- **MariaDB**: Base de données
- **Redis**: Cache
- **Traefik**: Reverse proxy pour challenges (port 8081)

## Plugins

- `auth_sync`: Authentification SSO avec tokens JWT
- `initial_setup`: Configuration automatique au premier démarrage (sécurité)
- `disable_setup`: Désactive la route /setup (sécurité)
- `registration_sync`: Synchronisation équipes avec le site
- `score_sync`: Synchronisation scores vers le site
- `room_display`: Affichage des salles

## Démarrage Rapide

### Prérequis

- Docker & Docker Compose
- Site d'inscription ACE lancé
- Réseau `ace-website_ace-network` existant

### Installation

```bash
# Copier et configurer .env
cp .env.example .env
nano .env

# Démarrer
docker compose up -d
```

### Accès

- CTFd: http://localhost:8000
- Traefik Dashboard: http://localhost:8082

## Configuration SSO

### Variables d'environnement critiques

```env
# Doit être identique au site d'inscription
JWT_SECRET=changez-moi-en-production

# URL publique accessible par le navigateur
CTFD_PUBLIC_URL=http://localhost:8000

# URL interne Docker du backend
REGISTRATION_SITE_URL=http://ace-website-backend-1:5000/api

# Mot de passe admin CTFd
CTFD_ADMIN_PASSWORD=changeme
```

### Fonctionnement SSO

1. Utilisateur se connecte sur le site d'inscription
2. Backend génère un JWT token
3. Utilisateur clique sur "Accéder au CTFd" dans le dashboard
4. Le navigateur POST le token à CTFd `/sso/authenticate`
5. CTFd valide le token JWT avec `JWT_SECRET`
6. CTFd crée ou trouve l'utilisateur et crée la session
7. Redirection vers `/challenges` avec cookies de session

## Challenges

### Challenge de test

Un challenge simple pour vérifier l'infrastructure.

**Accès**: http://test.challenges.local
**Flag**: `ACE{bienvenue_sur_la_plateforme_ctf}`

Ajoutez au `/etc/hosts`:
```
127.0.0.1 test.challenges.local
```

### Créer un challenge

1. Créer le dossier:
```bash
mkdir -p challenges/mon_challenge/deploy
```

2. Créer `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py .
RUN pip install flask
CMD ["python", "app.py"]
```

3. Créer `app.py`:
```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "Flag: ACE{mon_flag}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

4. Ajouter dans `docker-compose.yml`:
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

5. Déployer:
```bash
docker compose up -d --build challenge_mon_challenge
```

## Commandes

```bash
# Aide
make help

# Démarrer
make start

# Arrêter
make stop

# Logs CTFd
make logs

# Rebuild après modification plugin
make rebuild

# Fresh start (supprime tout)
make fresh
```

## Sécurité

- Tokens JWT avec expiration
- Validation tokens côté serveur
- Passwords hashés (bcrypt)
- CSRF désactivé uniquement pour SSO
- Page /setup bloquée après installation
- Configuration automatique au démarrage

## Documentation

- [QUICKSTART.md](./QUICKSTART.md) - Démarrage rapide
- [CTFd Docs](https://docs.ctfd.io/)
