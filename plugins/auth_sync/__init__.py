"""
Plugin d'authentification unifiée avec le site d'inscription ACE 2025
Le site d'inscription authentifie les utilisateurs, puis crée une session CTFd via un token JWT
"""

import os
import requests
import logging
import jwt
from flask import Blueprint, request, jsonify, redirect, url_for
from CTFd.models import db, Users, Teams
from CTFd.utils.security.auth import login_user
from CTFd.plugins import bypass_csrf_protection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REGISTRATION_SITE_URL = os.getenv('REGISTRATION_SITE_URL', 'http://backend:5000/api')
JWT_SECRET = os.getenv('JWT_SECRET', 'changez-moi-en-production')
CTFD_PUBLIC_URL = os.getenv('CTFD_PUBLIC_URL', 'http://localhost:8000')


class RegistrationAuthAPI:
    """Client pour valider les credentials via l'API du site d'inscription"""

    def __init__(self):
        self.base_url = REGISTRATION_SITE_URL

    def validate_credentials(self, email, password):
        """Valider les credentials via l'API du site d'inscription"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={
                    "email": email,
                    "password": password
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Récupérer les informations de l'utilisateur depuis le token
                    token = data['data'].get('token')
                    user_data = data['data'].get('user', {})
                    return {
                        'valid': True,
                        'token': token,
                        'user': user_data
                    }
            
            return {'valid': False, 'error': 'Invalid credentials'}

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la validation des credentials: {e}")
            return {'valid': False, 'error': str(e)}

    def get_user_team(self, user_id, token):
        """Récupérer l'équipe de l'utilisateur"""
        try:
            # Récupérer toutes les équipes et trouver celle de l'utilisateur
            response = requests.get(
                f"{self.base_url}/admin/teams",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    teams = data['data'].get('teams', [])
                    for team in teams:
                        members = team.get('members', [])
                        for member in members:
                            if member.get('id') == user_id:
                                return team
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération de l'équipe: {e}")
            return None


# Instance globale de l'API
auth_api = RegistrationAuthAPI()


def load(app):
    """Charger le plugin d'authentification unifiée"""
    logger.info("Chargement du plugin auth_sync (SSO avec site d'inscription)")

    # Créer un blueprint pour les routes d'authentification
    blueprint = Blueprint(
        'auth_sync',
        __name__,
        url_prefix=''
    )

    @blueprint.route('/sso/authenticate', methods=['POST', 'OPTIONS'])
    @bypass_csrf_protection
    def sso_authenticate():
        """
        Endpoint pour créer une session CTFd depuis le site d'inscription
        Le site d'inscription envoie un token JWT après authentification réussie
        """
        # Gérer les requêtes OPTIONS (CORS preflight)
        if request.method == 'OPTIONS':
            return '', 200

        # Déterminer si c'est une requête browser ou API
        is_browser_request = False

        try:
            # Support à la fois JSON et form data
            if request.content_type and 'application/json' in request.content_type:
                data = request.get_json()
                is_browser_request = False
            else:
                # Requête depuis un formulaire HTML
                data = request.form.to_dict()
                is_browser_request = True

            token = data.get('token', '')  # Token JWT du site d'inscription
            email = data.get('email', '').strip()  # Email de l'utilisateur

            if not token or not email:
                if is_browser_request:
                    return '<html><body><h1>Erreur</h1><p>Token et email requis</p></body></html>', 400
                return jsonify({
                    'success': False,
                    'message': 'Token et email requis'
                }), 400

            # Décoder et valider le token JWT localement
            try:
                # Décoder le JWT avec la clé secrète partagée
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

                # Vérifier que l'email correspond
                if payload.get('email') != email:
                    if is_browser_request:
                        return '<html><body><h1>Erreur</h1><p>Email ne correspond pas au token</p></body></html>', 401
                    return jsonify({
                        'success': False,
                        'message': 'Email ne correspond pas au token'
                    }), 401

                # Extraire les informations utilisateur du token
                user_data = {
                    'id': payload.get('id'),
                    'email': payload.get('email'),
                    'firstName': '',  # Pas dans le JWT
                    'lastName': '',   # Pas dans le JWT
                    'isAdmin': payload.get('isAdmin', False),
                    'teamId': payload.get('teamId')
                }

                # Si on a besoin des infos complètes (nom, équipe), appeler l'API
                # Mais seulement si l'utilisateur est admin OU on utilise un endpoint non-admin
                team_data = None
                if user_data.get('teamId'):
                    # Essayer de récupérer l'équipe depuis CTFd si elle existe déjà
                    # Sinon on la créera si nécessaire via l'API admin (si token admin)
                    pass

            except jwt.ExpiredSignatureError:
                logger.error("Token JWT expiré")
                if is_browser_request:
                    return '<html><body><h1>Erreur</h1><p>Token expiré. Veuillez vous reconnecter.</p></body></html>', 401
                return jsonify({
                    'success': False,
                    'message': 'Token expiré'
                }), 401
            except jwt.InvalidTokenError as e:
                logger.error(f"Token JWT invalide: {e}")
                if is_browser_request:
                    return '<html><body><h1>Erreur</h1><p>Token invalide</p></body></html>', 401
                return jsonify({
                    'success': False,
                    'message': 'Token invalide'
                }), 401
            except Exception as e:
                logger.error(f"Erreur lors du décodage du token: {e}")
                if is_browser_request:
                    return '<html><body><h1>Erreur</h1><p>Erreur de validation du token</p></body></html>', 500
                return jsonify({
                    'success': False,
                    'message': 'Erreur de validation du token'
                }), 500

            # Trouver ou créer l'utilisateur dans CTFd
            user = Users.query.filter_by(email=email).first()

            if not user:
                # Créer l'utilisateur dans CTFd
                from CTFd.utils.security.passwords import hash_password
                fake_password = hash_password(os.urandom(32).hex())

                # Utiliser l'email comme nom d'utilisateur par défaut
                username = email.split('@')[0]

                user = Users(
                    name=username,
                    email=email,
                    password=fake_password,
                    team_id=None,  # L'équipe sera assignée plus tard si nécessaire
                    verified=True,
                    hidden=False,
                    banned=False
                )
                db.session.add(user)
                db.session.commit()
                logger.info(f"Utilisateur créé via SSO: {email}")

            # Connecter l'utilisateur dans CTFd
            login_user(user)

            # Si c'est une requête browser (formulaire), rediriger automatiquement
            if is_browser_request:
                return redirect(f"{CTFD_PUBLIC_URL}/challenges")

            # Sinon, retourner une réponse JSON pour les appels API
            return jsonify({
                'success': True,
                'message': 'Session CTFd créée',
                'data': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'redirect_url': f"{CTFD_PUBLIC_URL}/challenges"
                }
            })

        except Exception as e:
            logger.error(f"Erreur lors de l'authentification SSO: {e}")
            db.session.rollback()
            if is_browser_request:
                return '<html><body><h1>Erreur</h1><p>Erreur lors de l\'authentification. Veuillez réessayer.</p></body></html>', 500
            return jsonify({
                'success': False,
                'message': 'Erreur lors de l\'authentification'
            }), 500

    # Enregistrer le blueprint
    app.register_blueprint(blueprint)

    logger.info("Plugin auth_sync chargé avec succès - SSO activé")

