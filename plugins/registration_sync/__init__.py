"""
Plugin de synchronisation avec le site d'inscription ACE 2025
Synchronise automatiquement les équipes depuis le site Next.js/Express existant
"""

import os
import requests
import logging
from flask import Blueprint
from apscheduler.schedulers.background import BackgroundScheduler
from CTFd.models import db, Teams, Users
from CTFd.utils.security.auth import generate_user_token
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


class RegistrationSiteAPI:
    """Client pour communiquer avec l'API du site d'inscription"""

    def __init__(self):
        self.base_url = REGISTRATION_SITE_URL
        self.token = None
        self.token_expires = None

    def authenticate(self):
        """Se connecter à l'API et obtenir un token JWT"""
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
                logger.info("Authentification réussie avec le site d'inscription")
                return True
            else:
                logger.error(f"Échec d'authentification: {data}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de connexion au site d'inscription: {e}")
            return False

    def get_teams(self):
        """Récupérer toutes les équipes depuis le site"""
        if not self.token:
            if not self.authenticate():
                return []

        try:
            # Récupérer toutes les équipes (pas seulement les complètes)
            # pour permettre la synchronisation même si l'équipe n'est pas encore complète
            response = requests.get(
                f"{self.base_url}/admin/teams",
                headers={"Authorization": f"Bearer {self.token}"},
                # Ne pas filtrer par complete pour synchroniser toutes les équipes
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if data.get('success'):
                teams = data['data']['teams']
                logger.info(f"Récupéré {len(teams)} équipes depuis le site")
                return teams
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération des équipes: {e}")
            # Retry with new token
            if self.authenticate():
                return self.get_teams()
            return []

    def update_team_ctfd_id(self, team_id, ctfd_team_id):
        """Mettre à jour le ctfdTeamId sur le site d'inscription"""
        if not self.token:
            if not self.authenticate():
                return False

        try:
            response = requests.patch(
                f"{self.base_url}/admin/teams/{team_id}",
                json={"ctfdTeamId": ctfd_team_id},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Mis à jour ctfdTeamId={ctfd_team_id} pour l'équipe {team_id}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la mise à jour de l'équipe {team_id}: {e}")
            return False


# Instance globale de l'API
api_client = RegistrationSiteAPI()

# Variable globale pour stocker l'application Flask
flask_app = None


def sync_teams_from_registration_site():
    """
    Fonction principale de synchronisation
    Appelée toutes les 2 minutes par le scheduler
    """
    global flask_app
    
    logger.info("=== Début de la synchronisation des équipes ===")

    # Utiliser le contexte de l'application Flask pour accéder à la base de données
    if flask_app is None:
        logger.error("Application Flask non disponible pour la synchronisation")
        return
    
    with flask_app.app_context():
        try:
            # Récupérer les équipes du site d'inscription
            teams_data = api_client.get_teams()

            if not teams_data:
                logger.warning("Aucune équipe récupérée")
                return

            created_count = 0
            updated_count = 0
            error_count = 0

            for team_data in teams_data:
                try:
                    # Vérifier si l'équipe existe déjà dans CTFd
                    existing_team = Teams.query.filter_by(
                        name=team_data['name']
                    ).first()

                    # Si l'équipe a déjà un ctfdTeamId, vérifier qu'elle existe
                    if team_data.get('ctfdTeamId'):
                        existing_team = Teams.query.filter_by(
                            id=team_data['ctfdTeamId']
                        ).first()

                    if existing_team:
                        # Équipe existe déjà, vérifier et ajouter les nouveaux membres
                        new_members_count = 0
                        for member in team_data.get('members', []):
                            # Vérifier si l'utilisateur existe déjà
                            existing_user = Users.query.filter_by(
                                email=member['email']
                            ).first()

                            # Ne pas créer de comptes utilisateurs individuels
                            # Les utilisateurs n'utilisent pas CTFd directement
                            new_members_count += 1
                            logger.info(f"  Nouveau membre détecté: {member.get('firstName')} {member.get('lastName')} ({member.get('email')})")
                        
                        if new_members_count > 0:
                            db.session.commit()
                            logger.info(f"Équipe mise à jour: {existing_team.name} (+{new_members_count} membre(s))")
                        
                        updated_count += 1
                        continue

                    # Créer la nouvelle équipe dans CTFd
                    new_team = Teams(
                        name=team_data['name'],
                        email=f"{team_data['inviteCode']}@ace-ctf.local",
                        password=team_data['inviteCode'],  # Utiliser le code d'invitation comme mot de passe
                        banned=False,
                        hidden=False
                    )

                    db.session.add(new_team)
                    db.session.flush()  # Pour obtenir l'ID

                    logger.info(f"Équipe créée: {new_team.name} (ID: {new_team.id})")

                    # Ne pas créer de comptes utilisateurs individuels
                    # Les utilisateurs n'utilisent pas CTFd directement - ils font les épreuves sur le site d'inscription
                    # CTFd sert uniquement à calculer les scores en arrière-plan et les envoyer au site

                    db.session.commit()

                    # Informer le site d'inscription du ctfdTeamId
                    api_client.update_team_ctfd_id(team_data['id'], new_team.id)

                    created_count += 1

                except Exception as e:
                    logger.error(f"Erreur lors du traitement de l'équipe {team_data.get('name')}: {e}")
                    db.session.rollback()
                    error_count += 1
                    continue

            logger.info(f"=== Synchronisation terminée: {created_count} créées, {updated_count} existantes, {error_count} erreurs ===")

        except Exception as e:
            logger.error(f"Erreur critique lors de la synchronisation: {e}")
            db.session.rollback()


def generate_random_password(length=12):
    """Générer un mot de passe aléatoire sécurisé"""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def load(app):
    """Charger le plugin dans CTFd"""
    global scheduler, flask_app
    
    # Stocker l'application Flask pour l'utiliser dans le scheduler
    flask_app = app

    logger.info("Chargement du plugin registration_sync")

    # Créer un blueprint pour les routes admin
    blueprint = Blueprint(
        'registration_sync',
        __name__,
        template_folder='templates',
        url_prefix='/admin/registration-sync'
    )

    @blueprint.route('/manual-sync', methods=['POST'])
    def manual_sync():
        """Endpoint pour déclencher une synchronisation manuelle"""
        from CTFd.utils.decorators import admins_only

        @admins_only
        def sync():
            sync_teams_from_registration_site()
            return {'success': True, 'message': 'Synchronisation lancée'}

        return sync()

    @blueprint.route('/status', methods=['GET'])
    def sync_status():
        """Vérifier l'état de la connexion avec le site"""
        from CTFd.utils.decorators import admins_only

        @admins_only
        def status():
            try:
                if api_client.authenticate():
                    teams_count = len(api_client.get_teams())
                    return {
                        'success': True,
                        'connected': True,
                        'teams_available': teams_count,
                        'site_url': REGISTRATION_SITE_URL
                    }
                else:
                    return {
                        'success': False,
                        'connected': False,
                        'error': 'Impossible de se connecter au site'
                    }
            except Exception as e:
                return {
                    'success': False,
                    'connected': False,
                    'error': str(e)
                }

        return status()

    # Enregistrer le blueprint
    app.register_blueprint(blueprint)

    # Configurer le scheduler pour la synchronisation automatique
    if not scheduler or not scheduler.running:
        scheduler = BackgroundScheduler()

        # Synchronisation toutes les minutes pour un rafraîchissement plus rapide
        # (évite le rate limiting tout en restant réactif)
        scheduler.add_job(
            func=sync_teams_from_registration_site,
            trigger='interval',
            minutes=1,
            id='sync_teams',
            name='Sync teams from registration site',
            replace_existing=True
        )

        # Synchronisation immédiate au démarrage (après 10 secondes)
        scheduler.add_job(
            func=sync_teams_from_registration_site,
            trigger='date',
            run_date=datetime.now(),
            id='sync_teams_startup',
            name='Initial team sync'
        )

        scheduler.start()
        logger.info("Scheduler de synchronisation démarré (toutes les minutes)")

    logger.info("Plugin registration_sync chargé avec succès")
