# Disable Team Editing Plugin

## Description
Ce plugin désactive la possibilité pour les équipes de modifier leurs informations dans CTFd.

## Fonctionnalités
- Bloque les requêtes PATCH/PUT/DELETE vers `/api/v1/teams/`
- Les utilisateurs normaux ne peuvent pas modifier les informations d'équipe
- Les admins peuvent toujours modifier les équipes
- Les utilisateurs peuvent toujours consulter les informations d'équipe (GET)

## Pourquoi ?
Dans le système ACE Escape Game, le site d'inscription (Next.js/Express) est la source unique de vérité pour :
- Nom d'équipe
- Membres d'équipe
- Affiliation
- Autres informations

Permettre les modifications dans CTFd créerait des conflits de synchronisation.

## Synchronisation
Les modifications doivent être faites sur le site d'inscription :
- `http://localhost:3000` (développement)

Le plugin `registration_sync` se charge de synchroniser automatiquement les changements vers CTFd via webhook.

## Installation
Le plugin est automatiquement chargé au démarrage de CTFd si présent dans `/opt/CTFd/CTFd/plugins/disable_team_editing`.

## Configuration
Aucune configuration nécessaire - le plugin fonctionne automatiquement une fois chargé.
