# Démarrage Rapide - CTFd ACE 2025

## Prérequis

```bash
docker --version
docker compose --version

# Vérifier que le site d'inscription est lancé
curl http://localhost:5000/health
```

## Installation

```bash
cd ACE-ctf-platform

# Copier le fichier d'environnement
cp .env.example .env

# Éditer avec vos vraies valeurs
nano .env
```

### Variables critiques dans `.env`

```env
SECRET_KEY=generer_une_cle_aleatoire_ici
MYSQL_ROOT_PASSWORD=changeme
MYSQL_PASSWORD=changeme
JWT_SECRET=doit_correspondre_au_site_inscription
CTFD_ADMIN_PASSWORD=mot_de_passe_admin
```

## Démarrage

```bash
# Démarrer tous les services
docker compose up -d

# Vérifier les logs
docker compose logs -f ctfd
```

## Accès

- CTFd: http://localhost:8000
- Traefik Dashboard: http://localhost:8082

## Commandes Utiles

```bash
# Aide (liste toutes les commandes)
make help

# Logs CTFd
make logs

# Redémarrer
make restart

# Rebuild après modification plugin
make rebuild

# Fresh start (supprime tout)
make fresh
```

## Test SSO

1. Se connecter sur le site d'inscription (http://localhost:3000)
2. Cliquer sur "Accéder au CTFd" dans le dashboard
3. Vérifier la connexion automatique sur CTFd

## Problèmes Courants

### Erreur "network not found"

```bash
# Le réseau est créé automatiquement par le site d'inscription
cd ../ACE-website && docker compose up -d
```

### SSO ne fonctionne pas

Vérifier que `JWT_SECRET` est identique dans les deux projets:

```bash
# Site d'inscription
grep JWT_SECRET ../ACE-website/.env

# CTFd
grep JWT_SECRET .env
```

### Plugin ne charge pas

```bash
docker compose up -d --build ctfd
docker compose logs ctfd | grep plugin
```

## Documentation

- [README.md](./README.md) - Documentation complète
