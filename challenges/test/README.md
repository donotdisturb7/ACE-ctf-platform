# Challenge de Test - ACE 2025

## Description

Challenge simple pour vérifier que l'infrastructure CTFd fonctionne correctement.

## Catégorie

Misc / Test

## Difficulté

Facile

## Points

10 points

## Flag

```
ACE{bienvenue_sur_la_plateforme_ctf}
```

## Solution

Le flag est directement visible sur la page d'accueil du challenge. Il suffit de :
1. Accéder au challenge via l'URL : `http://test.challenges.local`
2. Copier le flag affiché
3. Le soumettre sur CTFd

## Déploiement

Le challenge est automatiquement déployé via Docker Compose :

```bash
docker compose up -d challenge_test
```

L'application est accessible via Traefik sur : `http://test.challenges.local`

## Structure

```
test/
├── README.md          # Ce fichier
└── deploy/
    ├── Dockerfile     # Image Docker
    └── app.py         # Application Flask
```

## Technologies

- Python 3.11
- Flask
- Docker

## Notes

Ce challenge sert uniquement de test pour valider :
- Le déploiement des challenges
- La configuration Traefik
- L'accès via le réseau Docker
- La soumission de flags sur CTFd
