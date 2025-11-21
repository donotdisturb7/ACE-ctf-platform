"""
Plugin de synchronisation des scores vers le site d'inscription ACE 2025
Envoie automatiquement les scores CTFd au site toutes les 30 secondes
"""

import os
import requests
import logging
from flask import Blueprint
from apscheduler.schedulers.background import BackgroundScheduler
from CTFd.models import Teams
from CTFd.utils.scores import get_standings
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REGISTRATION_SITE_URL = os.getenv('REGISTRATION_SITE_URL', 'http://backend:5000/api')
ADMIN_EMAIL = os.getenv('REGISTRATION_SITE_ADMIN_EMAIL', 'admin@ace-escapegame.com')
ADMIN_PASSWORD = os.getenv('REGISTRATION_SITE_ADMIN_PASSWORD', '')

# Scheduler global
scheduler = None
flask_app = None


class ScoreSyncAPI:
    """Client pour synchroniser les scores avec le site d'inscription"""

    def __init__(self):
        self.base_url = REGISTRATION_SITE_URL
        self.token = None

    def authenticate(self):
        """Se connecter à l'API"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD
                },
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if data.get('success'):
                self.token = data['data']['token']
                return True
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur d'authentification pour score_sync: {e}")
            return False

    def send_scores(self, scores_data):
        """Envoyer les scores au site d'inscription"""
        if not self.token:
            if not self.authenticate():
                return False

        try:
            response = requests.post(
                f"{self.base_url}/admin/ctfd/sync-scores",
                json={"scores": scores_data},
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Scores synchronisés: {len(scores_data)} équipes")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'envoi des scores: {e}")
            # Retry with new token
            if self.authenticate():
                return self.send_scores(scores_data)
            return False


# Instance globale
score_api = ScoreSyncAPI()


def get_ctfd_scoreboard(app=None):
    """
    Récupérer le scoreboard complet de CTFd avec les scores actuels
    """
    from flask import current_app

    try:
        # Utiliser le contexte Flask si fourni, sinon utiliser current_app
        app_context = app or current_app

        with app_context.app_context():
            # Utiliser la fonction get_standings de CTFd
            standings = get_standings()

            scoreboard = []
            for position, team in enumerate(standings, start=1):
                scoreboard.append({
                    'ctfd_team_id': team.id,
                    'team_name': team.name,
                    'score': team.score,
                    'rank': position
                })

            return scoreboard

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du scoreboard: {e}")
        return []


def find_website_team_id(team_name):
    """
    Récupérer l'ID du site d'inscription depuis la base CTFd
    On peut stocker cet ID dans un champ custom ou utiliser le nom
    """
    # Pour l'instant, on va chercher l'équipe par nom sur le site
    # Dans une version avancée, on stockerait website_id dans la table Teams
    try:
        if not score_api.token:
            score_api.authenticate()

        response = requests.get(
            f"{score_api.base_url}/admin/teams",
            headers={"Authorization": f"Bearer {score_api.token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            teams = data.get('data', {}).get('teams', [])

            for team in teams:
                if team['name'] == team_name:
                    return team['id']

        return None

    except Exception as e:
        logger.error(f"Erreur lors de la recherche de l'équipe {team_name}: {e}")
        return None


def sync_scores_to_registration_site():
    """
    Fonction principale de synchronisation des scores
    Appelée toutes les 30 secondes par le scheduler
    """
    global flask_app

    try:
        # Récupérer le scoreboard CTFd avec le contexte Flask
        scoreboard = get_ctfd_scoreboard(flask_app)

        if not scoreboard:
            logger.debug("Pas de scores à synchroniser")
            return

        # Préparer les données pour l'API du site
        scores_to_send = []

        for entry in scoreboard:
            # Trouver l'ID de l'équipe sur le site d'inscription
            website_team_id = find_website_team_id(entry['team_name'])

            if website_team_id:
                scores_to_send.append({
                    'teamId': website_team_id,
                    'ctfdTeamId': entry['ctfd_team_id'],
                    'score': entry['score'],
                    'rank': entry['rank']
                })
            else:
                logger.debug(f"Équipe {entry['team_name']} non trouvée sur le site")

        if scores_to_send:
            # Envoyer au site d'inscription
            success = score_api.send_scores(scores_to_send)

            if success:
                logger.debug(f"Synchronisation réussie: {len(scores_to_send)} équipes")
            else:
                logger.warning("Échec de la synchronisation des scores")
        else:
            logger.debug("Aucune équipe à synchroniser")

    except Exception as e:
        logger.error(f"Erreur critique lors de la synchronisation des scores: {e}")


def load(app):
    """Charger le plugin dans CTFd"""
    global scheduler, flask_app

    # Stocker l'app pour utilisation dans le scheduler
    flask_app = app

    logger.info("Chargement du plugin score_sync")

    # Créer un blueprint
    blueprint = Blueprint(
        'score_sync',
        __name__,
        url_prefix='/admin/score-sync'
    )

    @blueprint.route('/manual-sync', methods=['POST'])
    def manual_score_sync():
        """Endpoint pour déclencher une synchronisation manuelle"""
        from CTFd.utils.decorators import admins_only

        @admins_only
        def sync():
            sync_scores_to_registration_site()
            return {'success': True, 'message': 'Synchronisation des scores lancée'}

        return sync()

    @blueprint.route('/test', methods=['GET'])
    def test_score_sync():
        """Tester la connexion et afficher le scoreboard"""
        from CTFd.utils.decorators import admins_only

        @admins_only
        def test():
            scoreboard = get_ctfd_scoreboard()
            return {
                'success': True,
                'scoreboard': scoreboard,
                'count': len(scoreboard)
            }

        return test()

    # Enregistrer le blueprint
    app.register_blueprint(blueprint)

    # Configurer le scheduler
    if not scheduler or not scheduler.running:
        scheduler = BackgroundScheduler()

        # Synchronisation toutes les 30 secondes
        scheduler.add_job(
            func=sync_scores_to_registration_site,
            trigger='interval',
            seconds=30,
            id='sync_scores',
            name='Sync scores to registration site',
            replace_existing=True
        )

        # Première synchronisation après 20 secondes (laisser le temps aux équipes de se créer)
        scheduler.add_job(
            func=sync_scores_to_registration_site,
            trigger='date',
            run_date=datetime.now(),
            id='sync_scores_startup',
            name='Initial score sync'
        )

        scheduler.start()
        logger.info("Scheduler de synchronisation des scores démarré (toutes les 30 secondes)")

    logger.info("Plugin score_sync chargé avec succès")
