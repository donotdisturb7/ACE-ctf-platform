"""
CTFd Plugin: Disable Team Editing
Prevents teams from editing their information in CTFd.
All team information should be managed through the registration site.
"""

from flask import abort, request, render_template, redirect, url_for, flash
from CTFd.plugins import register_plugin_assets_directory
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import is_admin


def load(app):
    """Plugin load function"""

    # Override team edit routes to prevent modifications
    @app.before_request
    def block_team_edits():
        """Block any team edit requests"""
        # Allow admins to do anything
        if is_admin():
            return

        # Block team settings/edit page
        if request.path.startswith('/teams/') and '/settings' in request.path:
            flash("Team editing is disabled. Please use the registration site to manage your team.", "warning")
            return redirect(url_for('teams.listing'))

        # Block API endpoints for team modifications
        if request.method in ['PATCH', 'PUT', 'DELETE']:
            if '/api/v1/teams/' in request.path:
                abort(403, description="Team editing is disabled. Please use the registration site to manage your team.")

        # Block team join/leave endpoints for non-admins
        if request.method == 'POST':
            blocked_paths = [
                '/teams/join',
                '/teams/new',
            ]
            for path in blocked_paths:
                if request.path.startswith(path):
                    abort(403, description="Team management is disabled. Teams are created through the registration site.")

    # Add a custom message template
    @app.context_processor
    def inject_team_edit_message():
        """Inject message about team editing"""
        registration_url = app.config.get('REGISTRATION_SITE_URL', 'http://localhost:3000')
        return {
            'team_edit_disabled': True,
            'team_edit_message': 'Team information is managed through the registration site.',
            'registration_site_url': registration_url
        }

    print("[Plugin] disable_team_editing loaded - Team editing restricted to admins only")
