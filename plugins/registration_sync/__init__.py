import os
import requests
import logging
from flask import Blueprint, request
from apscheduler.schedulers.background import BackgroundScheduler
from CTFd.models import db, Teams, Users
from CTFd.utils.security.auth import generate_user_token
from CTFd.plugins import bypass_csrf_protection
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
                        # Équipe existe déjà, synchroniser les membres
                        # Récupérer la liste des emails des membres actuels
                        current_member_emails = set()
                        for member in team_data.get('members', []):
                            member_email = member.get('email')
                            if member_email:
                                current_member_emails.add(member_email)

                        # Retirer les utilisateurs qui ne sont plus dans l'équipe
                        team_users = Users.query.filter_by(team_id=existing_team.id).all()
                        for user in team_users:
                            if user.email not in current_member_emails:
                                user.team_id = None
                                logger.info(f"Utilisateur {user.email} retiré de l'équipe {existing_team.name}")

                        # Ajouter ou mettre à jour les membres
                        for member in team_data.get('members', []):
                            member_email = member.get('email')
                            if not member_email:
                                continue

                            # Vérifier si l'utilisateur existe dans CTFd
                            existing_user = Users.query.filter_by(email=member_email).first()

                            if not existing_user:
                                # Créer l'utilisateur s'il n'existe pas
                                from CTFd.utils.security.passwords import hash_password
                                import os

                                fake_password = hash_password(os.urandom(32).hex())
                                username = member_email.split('@')[0]

                                new_user = Users(
                                    name=username,
                                    email=member_email,
                                    password=fake_password,
                                    type='user',
                                    team_id=existing_team.id,
                                    verified=True,
                                    hidden=False,
                                    banned=False
                                )
                                db.session.add(new_user)
                                db.session.flush()
                                logger.info(f"Utilisateur créé: {member_email} pour équipe {existing_team.name}")
                            else:
                                # Mettre à jour l'équipe de l'utilisateur si nécessaire
                                if existing_user.team_id != existing_team.id:
                                    existing_user.team_id = existing_team.id
                                    logger.info(f"Utilisateur {member_email} assigné à l'équipe {existing_team.name}")

                        # Mettre à jour le capitaine
                        captain_email = None
                        for member in team_data.get('members', []):
                            if member.get('id') == team_data.get('captainId'):
                                captain_email = member.get('email')
                                break

                        if captain_email:
                            captain_user = Users.query.filter_by(email=captain_email).first()
                            if captain_user and existing_team.captain_id != captain_user.id:
                                existing_team.captain_id = captain_user.id
                                logger.info(f"Capitaine mis à jour pour {existing_team.name}: {captain_email}")

                        db.session.commit()
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

                    # Créer les comptes utilisateurs pour tous les membres
                    for member in team_data.get('members', []):
                        member_email = member.get('email')
                        if not member_email:
                            continue

                        # Vérifier si l'utilisateur existe déjà
                        existing_user = Users.query.filter_by(email=member_email).first()

                        if not existing_user:
                            from CTFd.utils.security.passwords import hash_password
                            import os

                            fake_password = hash_password(os.urandom(32).hex())
                            username = member_email.split('@')[0]

                            new_user = Users(
                                name=username,
                                email=member_email,
                                password=fake_password,
                                type='user',
                                team_id=new_team.id,
                                verified=True,
                                hidden=False,
                                banned=False
                            )
                            db.session.add(new_user)
                            logger.info(f"Utilisateur créé: {member_email} pour nouvelle équipe {new_team.name}")
                        else:
                            # Mettre à jour l'équipe de l'utilisateur
                            existing_user.team_id = new_team.id
                            logger.info(f"Utilisateur {member_email} assigné à la nouvelle équipe {new_team.name}")

                    # Assigner le capitaine
                    captain_email = None
                    for member in team_data.get('members', []):
                        if member.get('id') == team_data.get('captainId'):
                            captain_email = member.get('email')
                            break

                    if captain_email:
                        captain_user = Users.query.filter_by(email=captain_email).first()
                        if captain_user:
                            new_team.captain_id = captain_user.id
                            logger.info(f"Capitaine assigné pour {new_team.name}: {captain_email}")

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

    @blueprint.route('/webhook', methods=['POST'])
    @bypass_csrf_protection
    def webhook_sync():
        """Endpoint webhook pour synchronisation instantanée depuis le backend"""
        import hmac
        import hashlib

        WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'changeme_webhook_secret')

        signature = request.headers.get('X-Webhook-Signature')
        if not signature:
            return {'success': False, 'error': 'Missing signature'}, 401

        body = request.get_data()
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Webhook signature invalide")
            return {'success': False, 'error': 'Invalid signature'}, 401

        data = request.get_json()
        event_type = data.get('event')

        logger.info(f"Webhook reçu: {event_type}")

        if event_type in ['team.created', 'team.updated', 'team.member_added', 'team.member_removed']:
            sync_teams_from_registration_site()
            return {'success': True, 'message': 'Synchronisation déclenchée'}

        return {'success': False, 'error': 'Unknown event type'}, 400

    # Créer un blueprint séparé pour le webhook (public, pas sous /admin)
    webhook_blueprint = Blueprint(
        'registration_sync_webhook',
        __name__,
        url_prefix='/api/registration-sync'
    )

    @webhook_blueprint.route('/webhook', methods=['POST'])
    @bypass_csrf_protection
    def webhook_public():
        """Endpoint webhook public pour synchronisation instantanée depuis le backend"""
        import hmac
        import hashlib

        WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'changeme_webhook_secret')

        signature = request.headers.get('X-Webhook-Signature')
        if not signature:
            logger.warning("Webhook reçu sans signature")
            return {'success': False, 'error': 'Missing signature'}, 401

        body = request.get_data()
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Webhook signature invalide")
            return {'success': False, 'error': 'Invalid signature'}, 401

        data = request.get_json()
        event_type = data.get('event')
        event_data = data.get('data', {})

        logger.info(f"Webhook reçu: {event_type} - Data: {event_data}")

        if event_type == 'team.deleted':
            team_id_to_delete = data.get('data', {}).get('teamId')
            ctfd_team_id = data.get('data', {}).get('ctfdTeamId')
            team_name = data.get('data', {}).get('teamName')
            
            logger.info(f"Traitement team.deleted: teamId={team_id_to_delete}, ctfdTeamId={ctfd_team_id}, teamName={team_name}")
            
            if ctfd_team_id or team_id_to_delete or team_name:
                try:
                    teams_to_delete = []
                    
                    # Priorité 1: ID CTFd s'il est fourni
                    if ctfd_team_id:
                        team = Teams.query.filter_by(id=ctfd_team_id).first()
                        if team:
                            teams_to_delete.append(team)
                            logger.info(f"Équipe trouvée par ctfdTeamId: {team.name}")
                    
                    # Priorité 2: Nom exact de l'équipe
                    if not teams_to_delete and team_name:
                        team = Teams.query.filter_by(name=team_name).first()
                        if team:
                            teams_to_delete.append(team)
                            logger.info(f"Équipe trouvée par nom: {team.name}")
                    
                    # Priorité 3: Recherche par UUID partiel (fallback)
                    if not teams_to_delete and team_id_to_delete:
                        teams_to_delete = Teams.query.filter(
                            Teams.name.like(f'%{team_id_to_delete[-8:]}%')
                        ).all()
                        if teams_to_delete:
                            logger.info(f"Équipe(s) trouvée(s) par UUID partiel: {[t.name for t in teams_to_delete]}")

                    if not teams_to_delete:
                        logger.warning(f"Aucune équipe trouvée pour suppression (ctfdId={ctfd_team_id}, uuid={team_id_to_delete}, name={team_name})")
                        return {'success': False, 'message': 'Équipe non trouvée'}, 404

                    for team in teams_to_delete:
                        # Dissocier les utilisateurs avant de supprimer l'équipe
                        Users.query.filter_by(team_id=team.id).update({'team_id': None})
                        db.session.delete(team)
                        logger.info(f"Équipe supprimée via webhook: {team.name} (ID: {team.id})")

                    db.session.commit()
                    return {'success': True, 'message': 'Équipe supprimée'}
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression de l'équipe: {e}")
                    db.session.rollback()
                    return {'success': False, 'error': str(e)}, 500

        if event_type == 'team.member_removed':
            user_id = data.get('data', {}).get('userId')
            team_id = data.get('data', {}).get('teamId')
            
            logger.info(f"Traitement team.member_removed: userId={user_id}, teamId={team_id}")

            if user_id and team_id:
                try:
                    # S'assurer que le client est authentifié
                    if not api_client.token:
                        logger.info("Authentification nécessaire pour récupérer les infos utilisateur")
                        api_client.authenticate()
                    
                    # Récupérer les infos utilisateur du site d'inscription pour trouver l'email
                    response = requests.get(
                        f"{REGISTRATION_SITE_URL}/admin/users/{user_id}",
                        headers={"Authorization": f"Bearer {api_client.token}"},
                        timeout=10
                    )

                    if response.status_code == 200:
                        user_data = response.json().get('data', {}).get('user', {})
                        user_email = user_data.get('email')
                        
                        logger.info(f"Email utilisateur récupéré: {user_email}")

                        if user_email:
                            # Trouver l'utilisateur CTFd par email
                            ctfd_user = Users.query.filter_by(email=user_email).first()

                            if ctfd_user and ctfd_user.team_id:
                                old_team_id = ctfd_user.team_id
                                ctfd_user.team_id = None
                                db.session.commit()
                                logger.info(f"Utilisateur {user_email} retiré de l'équipe {old_team_id} via webhook")
                                return {'success': True, 'message': "Utilisateur retiré de l'équipe"}
                            else:
                                logger.warning(f"Utilisateur {user_email} non trouvé dans CTFd ou n'a pas d'équipe")
                    else:
                        logger.warning(f"Erreur lors de la récupération de l'utilisateur: {response.status_code}")

                    # Si on n'a pas pu retirer l'utilisateur directement, faire une sync complète
                    logger.info("Fallback: synchronisation complète")
                    sync_teams_from_registration_site()
                    return {'success': True, 'message': 'Synchronisation complète effectuée'}

                except Exception as e:
                    logger.error(f"Erreur lors du retrait du membre: {e}")
                    # Fallback: synchronisation complète
                    sync_teams_from_registration_site()
                    return {'success': True, 'message': 'Synchronisation de secours effectuée'}

        if event_type in ['team.created', 'team.updated', 'team.member_added']:
            sync_teams_from_registration_site()
            return {'success': True, 'message': 'Synchronisation déclenchée'}

        return {'success': False, 'error': 'Unknown event type'}, 400

    # Enregistrer les blueprints
    app.register_blueprint(blueprint)
    app.register_blueprint(webhook_blueprint)

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
