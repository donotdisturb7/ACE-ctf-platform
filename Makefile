.PHONY: help setup start stop restart logs build rebuild clean status shell test

# Variables
DOCKER_COMPOSE = docker compose

help: ## Afficher l'aide
	@echo "Commandes disponibles pour CTFd ACE 2025:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Créer le fichier .env depuis .env.example
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Fichier .env créé"; \
		echo "⚠ Éditez .env avec vos valeurs (JWT_SECRET, passwords, etc.)"; \
	else \
		echo "✓ .env existe déjà"; \
	fi

start: ## Démarrer tous les services
	@echo "Démarrage de CTFd..."
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "✓ CTFd démarré"
	@echo "  Interface: http://localhost:8000"
	@echo "  Traefik:   http://localhost:8082"
	@echo "  Challenge: http://test.challenges.local (ajoutez au /etc/hosts)"

stop: ## Arrêter tous les services
	$(DOCKER_COMPOSE) down
	@echo "✓ Services arrêtés"

restart: ## Redémarrer tous les services
	$(DOCKER_COMPOSE) restart
	@echo "✓ Services redémarrés"

logs: ## Afficher les logs CTFd
	$(DOCKER_COMPOSE) logs -f --tail=100 ctfd

logs-all: ## Afficher tous les logs
	$(DOCKER_COMPOSE) logs -f --tail=50

status: ## Afficher l'état des services
	@echo "État des services:"
	@$(DOCKER_COMPOSE) ps

build: ## Reconstruire l'image CTFd (après modification plugins)
	@echo "Reconstruction de l'image CTFd..."
	$(DOCKER_COMPOSE) build ctfd
	@echo "✓ Image reconstruite"

rebuild: ## Reconstruire et redémarrer CTFd
	@echo "Reconstruction et redémarrage..."
	$(DOCKER_COMPOSE) up -d --build ctfd
	@echo "✓ CTFd reconstruit et redémarré"

shell: ## Ouvrir un shell dans le conteneur CTFd
	$(DOCKER_COMPOSE) exec ctfd /bin/bash

test: ## Tester l'accès aux services
	@echo "Test des services..."
	@curl -s http://localhost:8000/healthcheck > /dev/null && echo "✓ CTFd accessible" || echo "✗ CTFd inaccessible"
	@curl -s http://localhost:8082/api/http/routers > /dev/null && echo "✓ Traefik accessible" || echo "✗ Traefik inaccessible"
	@echo ""
	@echo "Pour tester le challenge:"
	@echo "  1. Ajoutez '127.0.0.1 test.challenges.local' au /etc/hosts"
	@echo "  2. Ouvrez http://test.challenges.local"

clean: ## Supprimer tous les conteneurs et volumes (⚠ perte de données)
	@echo "⚠ ATTENTION: Suppression de toutes les données !"
	@read -p "Confirmer ? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		$(DOCKER_COMPOSE) down -v --remove-orphans; \
		echo "✓ Nettoyage terminé"; \
	else \
		echo "✗ Annulé"; \
	fi
