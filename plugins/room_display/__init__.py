"""
Plugin room_display - Placeholder pour affichage des salles
Ce plugin peut être étendu plus tard pour afficher les informations de salle
"""

import logging

logger = logging.getLogger(__name__)


def load(app):
    """Charger le plugin dans CTFd"""
    logger.info("Plugin room_display chargé (placeholder)")
    # Plugin vide pour l'instant, peut être étendu plus tard
    pass

