# Guide de démarrage rapide

## Installation

### Prérequis
- Docker et Docker Compose
- Site d'inscription ACE démarré
- Ports 8000, 8081, 8082 disponibles

### Étapes

```bash
# 1. Cloner le projet
git clone https://github.com/donotdisturb7/ACE-ctf-platform.git
cd ACE-ctf-platform

# 2. Configurer l'environnement
cp .env.example .env
nano .env  # Configurer JWT_SECRET, WEBHOOK_SECRET, passwords

# 3. Démarrer
docker compose up -d

# 4. Vérifier
docker compose ps
docker logs ace-ctf-platform-ctfd-1
```

### Variables essentielles (.env)

```env
# Doit être IDENTIQUE au site d'inscription
JWT_SECRET=meme-secret-que-site-inscription
WEBHOOK_SECRET=secret-partage-avec-backend

# Sécurité
SECRET_KEY=cle-aleatoire-32-caracteres-minimum
MYSQL_ROOT_PASSWORD=password-securise
MYSQL_PASSWORD=password-securise

# Admin site d'inscription
REGISTRATION_SITE_ADMIN_EMAIL=admin@ace-escapegame.com
REGISTRATION_SITE_ADMIN_PASSWORD=Admin123Pass

# Admin CTFd
CTFD_ADMIN_PASSWORD=votre-password-admin
```

## Accès

| Service | URL |
|---------|-----|
| CTFd | http://localhost:8000 |
| Traefik | http://localhost:8082 |
| Challenge Test | http://test.challenges.local |

**Connexion admin** : `admin` / votre `CTFD_ADMIN_PASSWORD`

## Créer un challenge

### 1. Structure

```bash
mkdir -p challenges/mon_challenge/deploy
cd challenges/mon_challenge/deploy
```

### 2. Application (app.py)

```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "Flag: ACE{mon_flag}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### 3. Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py .
RUN pip install flask
CMD ["python", "app.py"]
```

### 4. Ajouter au docker-compose.yml

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

### 6. Tester

Ajouter dans `/etc/hosts` : `127.0.0.1 mon.challenges.local`

Ouvrir http://mon.challenges.local

## Commandes utiles

```bash
# Démarrer
docker compose up -d

# Arrêter
docker compose down

# Logs
docker logs -f ace-ctf-platform-ctfd-1

# Redémarrer après modification plugin
docker restart ace-ctf-platform-ctfd-1

# Fresh start (supprime tout)
docker compose down -v && docker compose up -d

# Shell
docker exec -it ace-ctf-platform-ctfd-1 bash
```

## Dépannage

### SSO ne fonctionne pas
```bash
# Vérifier JWT_SECRET identique
grep JWT_SECRET .env
grep JWT_SECRET ../ACE-website/backend/.env

# Vérifier logs
docker logs ace-ctf-platform-ctfd-1 2>&1 | grep "SSO\|JWT"
```

### Équipes ne se synchronisent pas
```bash
# Vérifier WEBHOOK_SECRET identique
grep WEBHOOK_SECRET .env
grep WEBHOOK_SECRET ../ACE-website/backend/.env

# Vérifier webhooks
docker logs ace-ctf-platform-ctfd-1 2>&1 | grep "Webhook"
docker logs ace-website-backend-1 2>&1 | grep "webhook"

# Forcer sync
docker restart ace-ctf-platform-ctfd-1
```

### Réseau introuvable
```bash
# Démarrer le site d'inscription d'abord
cd ../ACE-website
docker compose up -d

# Vérifier le réseau
docker network ls | grep ace-website_ace-network
```

### Port déjà utilisé
```bash
# Trouver le processus
sudo lsof -i :8000

# Ou changer le port dans docker-compose.yml
# "8001:8000" au lieu de "8000:8000"
```

## Documentation complète

Voir [README.md](./README.md) pour plus de détails sur l'architecture, les plugins et la configuration avancée.
