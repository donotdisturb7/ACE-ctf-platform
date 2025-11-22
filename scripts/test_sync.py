import os
import sys
import requests
from datetime import datetime

# Configuration
REGISTRATION_SITE_URL = os.getenv('REGISTRATION_SITE_URL', 'http://localhost:5000/api')
ADMIN_EMAIL = os.getenv('REGISTRATION_SITE_ADMIN_EMAIL', 'admin@ace-escapegame.com')
ADMIN_PASSWORD = os.getenv('REGISTRATION_SITE_ADMIN_PASSWORD', '')

CTFD_URL = os.getenv('CTFD_URL', 'http://localhost:8000')


def test_connection(url):
    """Tester la connexion à une URL"""
    print(f"Test de connexion à {url}...")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✓ Connexion réussie à {url}")
            return True
        else:
            print(f"✗ Connexion échouée: Status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Erreur de connexion: {e}")
        return False


def test_authentication():
    """Tester l'authentification au site d'inscription"""
    print(f"\nTest d'authentification au site d'inscription...")
    print(f"Email: {ADMIN_EMAIL}")

    try:
        response = requests.post(
            f"{REGISTRATION_SITE_URL}/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                token = data['data']['token']
                print(f"✓ Authentification réussie")
                print(f"  Token: {token[:50]}...")
                return token
            else:
                print(f"✗ Authentification échouée: {data}")
                return None
        else:
            print(f"✗ Erreur HTTP {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ Erreur de connexion: {e}")
        return None


def test_get_teams(token):
    """Tester la récupération des équipes"""
    print(f"\nTest de récupération des équipes...")

    try:
        response = requests.get(
            f"{REGISTRATION_SITE_URL}/admin/teams",
            headers={"Authorization": f"Bearer {token}"},
            params={"complete": "true"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                teams = data['data']['teams']
                print(f"✓ Récupéré {len(teams)} équipes")

                # Afficher quelques détails
                for i, team in enumerate(teams[:5], 1):
                    print(f"\n  Équipe {i}:")
                    print(f"    - Nom: {team['name']}")
                    print(f"    - Code: {team['inviteCode']}")
                    print(f"    - Membres: {team['memberCount']}")
                    print(f"    - Salle: {team.get('roomNumber', 'Non assignée')}")
                    print(f"    - CTFd ID: {team.get('ctfdTeamId', 'Non créée')}")

                if len(teams) > 5:
                    print(f"\n  ... et {len(teams) - 5} autres équipes")

                return teams
            else:
                print(f"✗ Échec: {data}")
                return []
        else:
            print(f"✗ Erreur HTTP {response.status_code}: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"✗ Erreur de connexion: {e}")
        return []


def test_sync_scores(token):
    """Tester l'envoi de scores de test"""
    print(f"\nTest d'envoi de scores...")

    test_scores = [
        {
            "teamId": "test-team-uuid-1",
            "ctfdTeamId": 1,
            "score": 450,
            "rank": 5
        }
    ]

    try:
        response = requests.post(
            f"{REGISTRATION_SITE_URL}/admin/ctfd/sync-scores",
            json={"scores": test_scores},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        if response.status_code == 200:
            print(f"✓ Scores envoyés avec succès")
            return True
        else:
            print(f"✗ Erreur HTTP {response.status_code}: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"✗ Erreur de connexion: {e}")
        return False


def test_ctfd_connection():
    """Tester la connexion à CTFd"""
    print(f"\nTest de connexion à CTFd...")

    return test_connection(CTFD_URL)


def main():
    """Fonction principale"""
    print("=" * 70)
    print("TEST DE SYNCHRONISATION CTFd <-> Site d'inscription ACE 2025")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Vérifier les variables d'environnement
    if not ADMIN_PASSWORD:
        print("⚠️  ATTENTION: REGISTRATION_SITE_ADMIN_PASSWORD non défini")
        print("   Définissez cette variable dans votre fichier .env\n")

    # Tests
    results = {
        'Site d\'inscription accessible': False,
        'CTFd accessible': False,
        'Authentification': False,
        'Récupération équipes': False,
        'Envoi scores': False
    }

    # Test 1: Connexion au site d'inscription
    results['Site d\'inscription accessible'] = test_connection(REGISTRATION_SITE_URL)

    # Test 2: Connexion à CTFd
    results['CTFd accessible'] = test_ctfd_connection()

    # Test 3: Authentification
    token = test_authentication()
    results['Authentification'] = token is not None

    if token:
        # Test 4: Récupération des équipes
        teams = test_get_teams(token)
        results['Récupération équipes'] = len(teams) > 0

        # Test 5: Envoi de scores (optionnel si pas d'équipes)
        # results['Envoi scores'] = test_sync_scores(token)

    # Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ DES TESTS")
    print("=" * 70)

    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:10} {test_name}")

    all_passed = all(results.values())

    print("=" * 70)
    if all_passed:
        print("✓ Tous les tests sont passés !")
        print("  La synchronisation devrait fonctionner correctement.")
    else:
        print("✗ Certains tests ont échoué")
        print("  Vérifiez la configuration et la connexion réseau.")

    print("=" * 70 + "\n")

    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
