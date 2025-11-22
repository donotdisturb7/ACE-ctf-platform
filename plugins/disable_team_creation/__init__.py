from flask import request, abort, render_template_string


def load(app):
    @app.before_request
    def block_team_creation():
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.path in ['/api/v1/teams', '/teams']:
                abort(403)

            if '/api/v1/teams/' in request.path and request.path.endswith('/join'):
                abort(403)

        if request.path in ['/teams/new', '/teams/join']:
            message = "La création et le join d'équipes se font uniquement via le site d'inscription ACE 2025."
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Équipes désactivées</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: #050511;
                        color: white;
                    }}
                    .container {{
                        text-align: center;
                        padding: 2rem;
                        background: rgba(15, 14, 74, 0.6);
                        border-radius: 12px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                    }}
                    h1 {{ color: #fc10ca; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Équipes désactivées</h1>
                    <p>{message}</p>
                    <p><a href="/challenges" style="color: #09c7df;">Retour aux challenges</a></p>
                </div>
            </body>
            </html>
            """
            return render_template_string(html), 403

    print("✅ Plugin disable_team_creation chargé - Création d'équipes bloquée")
