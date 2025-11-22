# ACE CTF Platform 2025

Plateforme CTF basée sur CTFd 3.8.1 avec authentification SSO et synchronisation temps réel pour l'événement ACE 2025 Escape Game Cybersécurité.

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Fonctionnalités](#fonctionnalités)
- [Démarrage rapide](#démarrage-rapide)
- [Configuration](#configuration)
- [Plugins](#plugins)
- [Développement](#développement)
- [Documentation](#documentation)

## Vue d'ensemble

Cette plateforme CTF intègre :
- **Authentification SSO** : Connexion unique avec le site d'inscription ACE
- **Synchronisation temps réel** : Équipes et scores synchronisés automatiquement via webhooks
- **Gestion centralisée** : Toutes les inscriptions gérées depuis le site principal
- **Infrastructure challenges** : Traefik pour le routing des challenges dynamiques

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Site d'inscription ACE                      │
│                    (localhost:3000)                          │
│                                                              │
│  ┌──────────────┐              ┌──────────────┐            │
│  │   Frontend   │              │   Backend    │            │
│  │   Next.js    │─────────────▶│   Express    │            │
│  └──────────────┘              └──────┬───────┘            │
│                                        │                     │
└────────────────────────────────────────┼─────────────────────┘
                                         │
                    JWT Token + Webhooks │
                                         │
┌────────────────────────────────────────▼─────────────────────┐
│                    Plateforme CTFd                            │
│                    (localhost:8000)                           │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │    CTFd      │───▶│   MariaDB    │    │    Redis     │  │
│  │   (Flask)    │    │              │    │   (Cache)    │  │
│  └──────┬───────┘    └──────────────┘    └──────────────┘  │
│         │                                                    │
│         │ Plugins:                                          │
│         │ • auth_sync (SSO)                                 │
│         │ • registration_sync (Webhooks)                    │
│         │ • score_sync                                      │
│         │ • disable_team_creation                           │
│         │                                                    │
│  ┌──────▼───────────────────────────────────────────────┐  │
│  │              Traefik (Reverse Proxy)                  │  │
│  │                  (localhost:8081)                     │  │
│  └──────┬───────────────────────────────────────────────┘  │
│         │                                                    │
│         │ Routes challenges:                                │
│         │ • test.challenges.local                           │
│         │ • web1.challenges.local                           │
│         │ • ...                                             │
└─────────┼────────────────────────────────────────────────────┘
          │
          ▼
    Challenges Docker
```

## Fonctionnalités

### Authentification SSO
- Connexion unique depuis le site d'inscription
- Validation JWT avec signature partagée
- Création automatique des comptes utilisateurs
- Sessions sécurisées avec cookies

### Synchronisation temps réel
- **Webhooks** : Notifications instantanées des changements d'équipes
- **Création équipe** : Équipe créée automatiquement dans CTFd
- **Ajout membre** : Membre ajouté instantanément à l'équipe CTFd
- **Retrait membre** : Membre retiré immédiatement de l'équipe CTFd
- **Suppression équipe** : Équipe supprimée quand le capitaine quitte
- **Fallback** : Synchronisation périodique (1 minute) en cas d'échec webhook

### Sécurité
- Tokens JWT avec expiration
- Webhooks signés avec HMAC SHA256
- Passwords hashés avec bcrypt
- Page `/setup` désactivée après installation
- Création d'équipes bloquée (gestion centralisée uniquement)
- CSRF protection (sauf endpoints SSO/webhooks)

### Gestion des challenges
- Routing automatique via Traefik
- Isolation réseau des challenges
- Déploiement simple avec Docker Compose
- Support multi-challenges simultanés

## Démarrage rapide

Voir [QUICKSTART.md](./QUICKSTART.md) pour un guide détaillé.

### Prérequis

- Docker et Docker Compose installés
- Site d'inscription ACE démarré
- Réseau Docker `ace-website_ace-network` créé

### Installation en 3 étapes

```bash
# 1. Copier et configurer les variables d'environnement
cp .env.example .env
nano .env  # Configurer les variables

# 2. Démarrer tous les services
docker compose up -d

# 3. Accéder à CTFd
# http://localhost:8000
```

### Accès aux services

| Service | URL | Description |
|---------|-----|-------------|
| CTFd | http://localhost:8000 | Plateforme CTF principale |
| Traefik Dashboard | http://localhost:8082 | Monitoring des challenges |
| Challenge Test | http://test.challenges.local | Challenge de démonstration |

## Configuration

### Variables d'environnement essentielles

Toutes les variables sont définies dans le fichier `.env` :

```env
# Sécurité
SECRET_KEY=votre-secret-key-aleatoire
JWT_SECRET=meme-secret-que-site-inscription

# Base de données
MYSQL_ROOT_PASSWORD=root-password
MYSQL_PASSWORD=ctfd-password

# Intégration site d'inscription
REGISTRATION_SITE_URL=http://ace-website-backend-1:5000/api
REGISTRATION_SITE_ADMIN_EMAIL=admin@ace-escapegame.com
REGISTRATION_SITE_ADMIN_PASSWORD=Admin123Pass

# Webhooks
WEBHOOK_SECRET=secret-partage-avec-backend

# Admin CTFd
CTFD_ADMIN_USER=admin
CTFD_ADMIN_EMAIL=admin@ctfd.local
CTFD_ADMIN_PASSWORD=votre-mot-de-passe-admin

# URLs publiques
CTFD_PUBLIC_URL=http://localhost:8000
```

### Configuration réseau

Le projet utilise 3 réseaux Docker :

1. **ctfd-internal** : Communication interne (DB, Redis) - pas d'accès internet
2. **ctfd-challenges** : Réseau des challenges avec Traefik
3. **ace-website_ace-network** : Réseau partagé avec le site d'inscription (externe)

## Plugins

### auth_sync
Gère l'authentification SSO avec tokens JWT.

**Fonctionnalités** :
- Validation des tokens JWT
- Création/mise à jour utilisateurs
- Attribution automatique des équipes
- Gestion des capitaines d'équipe

### registration_sync
Synchronise les équipes via webhooks et polling.

**Fonctionnalités** :
- Réception webhooks signés HMAC
- Synchronisation temps réel des équipes
- Fallback avec polling (1 minute)
- Gestion membres et capitaines

**Événements webhook supportés** :
- `team.created` : Création d'équipe
- `team.deleted` : Suppression d'équipe
- `team.member_added` : Ajout de membre
- `team.member_removed` : Retrait de membre

### score_sync
Synchronise les scores CTFd vers le site d'inscription.

### disable_team_creation
Bloque la création manuelle d'équipes dans CTFd.

**Raison** : Toutes les équipes doivent être créées via le site d'inscription pour garantir la cohérence des données.

### disable_setup
Désactive la route `/setup` après la configuration initiale.

**Sécurité** : Empêche la reconfiguration non autorisée de CTFd.

### initial_setup
Configure automatiquement CTFd au premier démarrage.

**Actions** :
- Création de l'admin
- Configuration du CTF
- Mode équipes activé

## Développement

### Structure du projet

```
ACE-ctf-platform/
├── challenges/              # Challenges CTF
│   └── test/               # Challenge de test
│       ├── deploy/         # Fichiers de déploiement
│       └── solution/       # Solution et writeup
├── plugins/                # Plugins CTFd personnalisés
│   ├── auth_sync/         # Authentification SSO
│   ├── registration_sync/ # Synchronisation équipes
│   ├── score_sync/        # Synchronisation scores
│   ├── disable_team_creation/
│   ├── disable_setup/
│   └── initial_setup/
├── scripts/               # Scripts utilitaires
├── docker-compose.yml     # Configuration services
├── .env.example          # Template variables d'environnement
├── Makefile              # Commandes make
├── README.md             # Ce fichier
└── QUICKSTART.md         # Guide de démarrage rapide
```

### Commandes Make

```bash
make help      # Afficher l'aide
make start     # Démarrer tous les services
make stop      # Arrêter tous les services
make restart   # Redémarrer tous les services
make logs      # Voir les logs CTFd
make rebuild   # Rebuild après modification plugin
make fresh     # Fresh start (supprime volumes)
make shell     # Shell dans le conteneur CTFd
```

### Développement de plugins

Les plugins sont montés en volumes, les modifications sont prises en compte après redémarrage :

```bash
# Modifier le plugin
nano plugins/mon_plugin/__init__.py

# Redémarrer CTFd
docker restart ace-ctf-platform-ctfd-1
```

### Logs et debugging

```bash
# Logs CTFd en temps réel
docker logs -f ace-ctf-platform-ctfd-1

# Logs d'un plugin spécifique
docker logs ace-ctf-platform-ctfd-1 2>&1 | grep "registration_sync"

# Logs webhooks
docker logs ace-ctf-platform-ctfd-1 2>&1 | grep "Webhook"

# Shell dans le conteneur
docker exec -it ace-ctf-platform-ctfd-1 bash
```

### Création d'un challenge

Voir [QUICKSTART.md](./QUICKSTART.md#créer-un-challenge) pour un guide détaillé.

## Documentation

- [QUICKSTART.md](./QUICKSTART.md) - Guide de démarrage rapide et tutoriels
- [CTFd Documentation](https://docs.ctfd.io/) - Documentation officielle CTFd
- [Docker Compose](https://docs.docker.com/compose/) - Documentation Docker Compose
- [Traefik](https://doc.traefik.io/traefik/) - Documentation Traefik

## Support

Pour toute question ou problème :
1. Consulter [QUICKSTART.md](./QUICKSTART.md) pour les problèmes courants
2. Vérifier les logs : `docker logs ace-ctf-platform-ctfd-1`
3. Vérifier la configuration réseau : `docker network ls`
4. Vérifier les variables d'environnement dans `.env`

## Licence

Projet ACE 2025 - Rénald DESIRE - Vizyon Dijital
