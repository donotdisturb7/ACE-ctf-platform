import os
import sys
import logging
from CTFd.models import db, Users
from CTFd.utils.security.auth import generate_user_token
from CTFd.utils import set_config
from werkzeug.security import generate_password_hash
import CTFd.utils.config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load(app):
    if CTFd.utils.config.is_setup():
        logger.info("✅ CTFd déjà configuré - initial_setup ignoré")
        return

    logger.info("⚠️  CTFd n'est pas configuré - Initialisation automatique...")

    with app.app_context():
        try:
            CTF_NAME = os.getenv('CTF_NAME', 'ACE Escape Game 2025')
            CTF_DESCRIPTION = os.getenv('CTF_DESCRIPTION', 'Plateforme CTF pour ACE Escape Game Cybersécurité')
            ADMIN_NAME = os.getenv('CTFD_ADMIN_USER', 'admin')
            ADMIN_EMAIL = os.getenv('CTFD_ADMIN_EMAIL', 'admin@ctfd.local')
            ADMIN_PASSWORD = os.getenv('CTFD_ADMIN_PASSWORD')

            if not ADMIN_PASSWORD:
                logger.error("❌ CTFD_ADMIN_PASSWORD n'est pas défini!")
                sys.exit(1)

            set_config('ctf_name', CTF_NAME)
            set_config('ctf_description', CTF_DESCRIPTION)
            set_config('user_mode', 'teams')
            set_config('challenge_visibility', 'public')

            existing_admin = Users.query.filter_by(email=ADMIN_EMAIL).first()

            if not existing_admin:
                admin = Users(
                    name=ADMIN_NAME,
                    email=ADMIN_EMAIL,
                    password=generate_password_hash(ADMIN_PASSWORD),
                    type='admin',
                    verified=True,
                    hidden=True
                )
                db.session.add(admin)
                db.session.commit()
                logger.info(f"✅ Utilisateur admin créé: {ADMIN_EMAIL}")

                try:
                    admin_token = generate_user_token(admin)
                    logger.info(f"✅ Token admin généré: {admin_token[:20]}...")
                except Exception as e:
                    logger.warning(f"Impossible de générer le token admin: {e}")
            else:
                logger.info(f"✅ Admin déjà existant: {ADMIN_EMAIL}")

            set_config('setup', True)
            db.session.commit()
            logger.info("✅ CTFd initialisé automatiquement avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation automatique: {e}")
            db.session.rollback()
            sys.exit(1)
