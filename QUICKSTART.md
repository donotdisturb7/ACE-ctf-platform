# Démarrage Rapide - CTFd ACE 2025



### 1. Prérequis

```bash
# Vérifier Docker
docker --version
docker compose --version

# Vérifier que le site d'inscription est lancé
curl http://localhost:5000/api
```

### 2. Configuration

```bash
cd escape-game-ctfd

# Copier le fichier d'environnement
cp .env.example .env

# Éditer avec vos vraies valeurs
nano .env  # ou vim, code, etc.
```

**Minimum à modifier dans `.env` :**
```env
SECRET_KEY=generer_une_cle_aleatoire_ici
MYSQL_ROOT_PASSWORD=votre_mot_de_passe
MYSQL_PASSWORD=votre_mot_de_passe_ctfd
REGISTRATION_SITE_ADMIN_PASSWORD=le_vrai_mot_de_passe_admin
```

### 3. Créer le réseau (si nécessaire)

```bash
docker network create ace-network
```

### 4. Démarrer

```bash
docker compose up -d
```

### 5. Vérifier

```bash
# Attendre 30 secondes puis tester
python scripts/test_sync.py
```

### 6. Accéder

- **CTFd** : http://localhost:8000
- **Traefik** : http://localhost:8080

## Commandes utiles

```bash
# Voir les logs
docker compose logs -f ctfd

# Redémarrer
docker compose restart

# Arrêter
docker compose down

# Tout supprimer (ATTENTION: perte de données)
docker compose down -v
```

## Tester la synchronisation

```bash
# Test complet
python scripts/test_sync.py

# Voir les équipes synchronisées
curl http://localhost:8000/api/v1/teams | jq
```

## Importer les challenges

```bash
# 1. Créer un token API dans CTFd
#    Settings > Access Tokens > Create

# 2. Exporter le token
export CTFD_TOKEN="votre_token_ici"

# 3. Importer
python scripts/import_challenges.py
```

## Problèmes courants

### Erreur "network ace-network not found"

```bash
docker network create ace-network
docker compose up -d
```

### Erreur "authentication failed"

Vérifiez votre `.env` :
```bash
cat .env | grep REGISTRATION_SITE
```

### Les équipes ne se créent pas

```bash
# Vérifier les logs
docker compose logs ctfd | grep registration_sync

# Synchronisation manuelle
docker compose exec ctfd curl -X POST http://localhost:8000/admin/registration-sync/manual-sync
```

## Prochaines étapes

1. Vérifier que les équipes du site apparaissent dans CTFd
2. Importer les challenges
3. Tester la résolution d'un challenge
4. Vérifier que les scores remontent au site
5. fix create team in ctfd even tho already in a team from the register website
6. fix sync 

## Architecture réseau

```
┌─────────────────────────────────────┐
│   Réseau ace-network (externe)      │
│                                     │
│   ┌──────────┐      ┌──────────┐   │
│   │ backend  │◄────►│  ctfd    │   │
│   │  :5000   │      │  :8000   │   │
│   └──────────┘      └──────────┘   │
│                                     │
└─────────────────────────────────────┘
```

Le réseau `ace-network` permet la communication entre le site d'inscription (backend) et CTFd.

---

** Consultez le [README.md](README.md) complet.
