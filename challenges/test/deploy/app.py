#!/usr/bin/env python3
"""
Challenge de test - ACE 2025
Un challenge simple pour tester l'infrastructure CTFd
"""

from flask import Flask, render_template_string

app = Flask(__name__)

# Le flag du challenge
FLAG = "ACE{bienvenue_sur_la_plateforme_ctf}"

# Template HTML simple
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Challenge Test - ACE 2025</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: slideIn 0.5s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        h1 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 2em;
            text-align: center;
        }

        .badge {
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-bottom: 20px;
        }

        p {
            color: #4b5563;
            line-height: 1.6;
            margin-bottom: 15px;
        }

        .flag-box {
            background: #f3f4f6;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }

        .flag {
            font-family: 'Courier New', monospace;
            font-size: 1.2em;
            color: #1f2937;
            font-weight: bold;
            word-break: break-all;
        }

        .hint {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin-top: 20px;
            border-radius: 5px;
        }

        .hint-title {
            color: #92400e;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .footer {
            text-align: center;
            margin-top: 30px;
            color: #9ca3af;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div style="text-align: center;">
            <span class="badge">FACILE</span>
        </div>

        <h1>🚩 Challenge de Test</h1>

        <p>
            Bienvenue sur la plateforme CTF ACE 2025 !
            Ce challenge de test vous permet de vérifier que tout fonctionne correctement.
        </p>

        <p>
            <strong>Objectif :</strong> Trouvez le flag caché sur cette page.
        </p>

        <div class="hint">
            <div class="hint-title">💡 Indice</div>
            <div>Le flag est directement visible sur cette page. Aucune manipulation n'est nécessaire !</div>
        </div>

        <div class="flag-box">
            <div style="margin-bottom: 10px; color: #6b7280; font-weight: bold;">🎯 FLAG</div>
            <div class="flag">{{ flag }}</div>
        </div>

        <p style="margin-top: 20px;">
            <strong>Comment soumettre :</strong><br>
            1. Copiez le flag ci-dessus<br>
            2. Retournez sur CTFd<br>
            3. Soumettez le flag dans le champ prévu<br>
            4. Profitez de vos points ! 🎉
        </p>

        <div class="footer">
            <div>Challenge créé pour ACE 2025</div>
            <div style="margin-top: 5px;">🔒 CTF Platform - Escape Game Edition</div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Page principale du challenge"""
    return render_template_string(HTML_TEMPLATE, flag=FLAG)

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
