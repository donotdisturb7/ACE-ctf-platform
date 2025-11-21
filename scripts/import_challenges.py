#!/usr/bin/env python3
"""
Script d'importation automatique des challenges dans CTFd
Lit les fichiers challenge.yml et crée les challenges via l'API CTFd
"""

import os
import sys
import yaml
import requests
from pathlib import Path

# Configuration CTFd
CTFD_URL = os.getenv('CTFD_URL', 'http://localhost:8000')
CTFD_TOKEN = os.getenv('CTFD_TOKEN', '')  # Admin API token

# Headers pour l'API
HEADERS = {
    'Authorization': f'Token {CTFD_TOKEN}',
    'Content-Type': 'application/json'
}


def load_challenge_yaml(yaml_path):
    """Charger un fichier challenge.yml"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_challenge(challenge_data):
    """Créer un challenge via l'API CTFd"""
    print(f"Création du challenge: {challenge_data['name']}")

    # Préparer les données pour l'API
    payload = {
        'name': challenge_data['name'],
        'category': challenge_data['category'],
        'description': challenge_data['description'],
        'value': challenge_data['value'],
        'type': challenge_data.get('type', 'standard'),
        'state': challenge_data.get('state', 'visible'),
        'connection_info': challenge_data.get('connection_info', '')
    }

    # Créer le challenge
    response = requests.post(
        f'{CTFD_URL}/api/v1/challenges',
        json=payload,
        headers=HEADERS
    )

    if response.status_code not in [200, 201]:
        print(f"Erreur lors de la création: {response.text}")
        return None

    challenge_id = response.json()['data']['id']
    print(f"✓ Challenge créé avec l'ID: {challenge_id}")

    # Ajouter les flags
    for flag_text in challenge_data.get('flags', []):
        add_flag(challenge_id, flag_text)

    # Ajouter les hints
    for hint in challenge_data.get('hints', []):
        add_hint(challenge_id, hint)

    # Ajouter les tags
    for tag in challenge_data.get('tags', []):
        add_tag(challenge_id, tag)

    return challenge_id


def add_flag(challenge_id, flag_text):
    """Ajouter un flag à un challenge"""
    payload = {
        'challenge_id': challenge_id,
        'content': flag_text,
        'type': 'static'
    }

    response = requests.post(
        f'{CTFD_URL}/api/v1/flags',
        json=payload,
        headers=HEADERS
    )

    if response.status_code in [200, 201]:
        print(f"  ✓ Flag ajouté: {flag_text}")
    else:
        print(f"  ✗ Erreur flag: {response.text}")


def add_hint(challenge_id, hint_data):
    """Ajouter un hint à un challenge"""
    payload = {
        'challenge_id': challenge_id,
        'content': hint_data['content'],
        'cost': hint_data.get('cost', 0)
    }

    response = requests.post(
        f'{CTFD_URL}/api/v1/hints',
        json=payload,
        headers=HEADERS
    )

    if response.status_code in [200, 201]:
        print(f"  ✓ Hint ajouté (coût: {hint_data.get('cost', 0)})")
    else:
        print(f"  ✗ Erreur hint: {response.text}")


def add_tag(challenge_id, tag_name):
    """Ajouter un tag à un challenge"""
    payload = {
        'challenge_id': challenge_id,
        'value': tag_name
    }

    response = requests.post(
        f'{CTFD_URL}/api/v1/tags',
        json=payload,
        headers=HEADERS
    )

    if response.status_code in [200, 201]:
        print(f"  ✓ Tag ajouté: {tag_name}")


def find_challenge_files(base_path):
    """Trouver tous les fichiers challenge.yml"""
    challenge_files = []

    for root, dirs, files in os.walk(base_path):
        if 'challenge.yml' in files:
            challenge_files.append(os.path.join(root, 'challenge.yml'))

    return sorted(challenge_files)


def main():
    """Fonction principale"""
    if not CTFD_TOKEN:
        print("Erreur: CTFD_TOKEN non défini")
        print("Obtenez un token admin depuis CTFd > Settings > Access Tokens")
        sys.exit(1)

    # Chemin de base des challenges
    base_path = Path(__file__).parent.parent / 'challenges'

    if not base_path.exists():
        print(f"Erreur: Le dossier {base_path} n'existe pas")
        sys.exit(1)

    # Trouver tous les challenges
    challenge_files = find_challenge_files(base_path)

    if not challenge_files:
        print("Aucun challenge trouvé")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"Importation de {len(challenge_files)} challenges")
    print(f"{'='*60}\n")

    success_count = 0
    error_count = 0

    for challenge_file in challenge_files:
        try:
            print(f"\nTraitement: {challenge_file}")
            challenge_data = load_challenge_yaml(challenge_file)

            challenge_id = create_challenge(challenge_data)

            if challenge_id:
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            print(f"✗ Erreur: {e}")
            error_count += 1

    print(f"\n{'='*60}")
    print(f"Résultat: {success_count} réussis, {error_count} erreurs")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
