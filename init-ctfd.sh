#!/bin/bash
# Script d'initialisation automatique de CTFd
# Évite la page de setup (faille de sécurité)

set -e

echo "🔧 Initialisation de CTFd..."

# Attendre que la base de données soit prête
echo "⏳ Attente de la base de données..."
sleep 15

# Initialiser CTFd avec Python
python3 <<'PYTHON_EOF'
from CTFd import create_app
from CTFd.models import db, Configs, Users
from werkzeug.security import generate_password_hash
import os
import sys

try:
    app = create_app()

    with app.app_context():
        # Vérifier si CTFd est déjà configuré
        setup_complete = Configs.query.filter_by(key='setup').first()

        if not setup_complete or not setup_complete.value:
            print("⚠️  CTFd n'est pas configuré, initialisation automatique...")

            # Configuration CTF
            db.session.query(Configs).filter_by(key='ctf_name').delete()
            db.session.query(Configs).filter_by(key='ctf_description').delete()
            db.session.query(Configs).filter_by(key='user_mode').delete()
            db.session.query(Configs).filter_by(key='challenge_visibility').delete()
            db.session.query(Configs).filter_by(key='setup').delete()

            db.session.add(Configs(key='ctf_name', value=os.getenv('CTF_NAME', 'ACE Escape Game 2025')))
            db.session.add(Configs(key='ctf_description', value=os.getenv('CTF_DESCRIPTION', 'Plateforme CTF')))
            db.session.add(Configs(key='user_mode', value='teams'))
            db.session.add(Configs(key='challenge_visibility', value='public'))
            db.session.add(Configs(key='setup', value=True))  # Boolean True, not string!

            # Créer l'utilisateur admin
            admin_email = os.getenv('CTFD_ADMIN_EMAIL', 'admin@ctfd.local')
            admin_password = os.getenv('CTFD_ADMIN_PASSWORD', 'changeme')

            if not Users.query.filter_by(email=admin_email).first():
                admin = Users(
                    name='admin',
                    email=admin_email,
                    password=generate_password_hash(admin_password),
                    type='admin',
                    verified=True,
                    hidden=True
                )
                db.session.add(admin)

            db.session.commit()
            print("✅ CTFd initialisé automatiquement")
        else:
            print("✅ CTFd déjà configuré")

except Exception as e:
    print(f"❌ Erreur d'initialisation: {e}")
    sys.exit(1)
PYTHON_EOF

# Lancer CTFd
exec gunicorn 'CTFd:create_app()' \
    --bind '0.0.0.0:8000' \
    --workers ${WORKERS:-1} \
    --worker-tmp-dir /dev/shm \
    --worker-class 'gevent' \
    --access-logfile '/var/log/CTFd/access.log' \
    --error-logfile '/var/log/CTFd/error.log'
