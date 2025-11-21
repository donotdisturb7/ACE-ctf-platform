from flask import request, abort


def load(app):
    @app.before_request
    def block_setup_page():
        if request.path == '/setup' or request.path.startswith('/setup/'):
            abort(404)

    print("✅ Plugin disable_setup chargé - Route /setup désactivée")
