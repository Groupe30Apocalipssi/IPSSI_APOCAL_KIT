# ============================================================================
# IPSSI_APOCAL_KIT — Makefile
# ----------------------------------------------------------------------------
# Raccourcis pour les opérations courantes. Tapez `make help` pour la liste.
# ============================================================================

DEFAULT_OLLAMA_MODEL := llama3.2:3b
OLLAMA_MODEL_FROM_ENV_FILE := $(shell sed -n 's/^[[:space:]]*OLLAMA_MODEL[[:space:]]*=[[:space:]]*//p' .env 2>/dev/null | head -n1)
OLLAMA_MODEL ?= $(if $(OLLAMA_MODEL_FROM_ENV_FILE),$(OLLAMA_MODEL_FROM_ENV_FILE),$(DEFAULT_OLLAMA_MODEL))

.PHONY: help dev down logs build test lint ci pull-model benchmark-llm seed reset-db backend-shell frontend-shell

help:  ## Affiche cette aide
	@echo "IPSSI_APOCAL_KIT — Cibles Makefile disponibles :"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# ---------- Cycle de vie Docker ----------

dev:  ## Lance tous les services en arrière-plan (postgres, ollama, backend, frontend)
	docker compose up -d
	@echo ""
	@echo "✅ Services démarrés."
	@echo "   Frontend  : http://localhost:3000"
	@echo "   API       : http://localhost:8000/api"
	@echo "   API docs  : http://localhost:8000/api/docs"
	@echo "   Ollama    : http://localhost:11434"
	@echo ""
	@echo "ℹ️  Premier lancement ? Pensez à : make pull-model"

down:  ## Arrête tous les services (conserve les volumes)
	docker compose down

logs:  ## Affiche les logs des services en temps réel
	docker compose logs -f

build:  ## Reconstruit les images Docker (après changement de Dockerfile / requirements)
	docker compose build --no-cache

# ---------- LLM ----------

pull-model:  ## Télécharge le modèle Ollama configuré (OLLAMA_MODEL, défaut llama3.2:3b)
	@OLLAMA_MODEL="$(OLLAMA_MODEL)" bash scripts/pull-model.sh

benchmark-llm:  ## Mesure la latence LLM et échoue si elle dépasse 60 s
	docker compose exec backend python manage.py benchmark_llm --threshold 60

# ---------- Qualité de code ----------

test:  ## Lance les tests backend (pytest) et frontend (vitest)
	docker compose exec backend pytest
	docker compose exec frontend npm test -- --run

lint:  ## Vérifie la qualité du code (black, ruff, eslint, prettier)
	docker compose exec backend black --check .
	docker compose exec backend ruff check .
	docker compose exec frontend npm run lint

ci:  ## Cible "CI complète" — lint + tests (utilisée par GitHub Actions)
	$(MAKE) lint
	$(MAKE) test

# ---------- Données ----------

seed:  ## Insère les données de test (1 user + 2 quizz exemples)
	docker compose exec backend python manage.py seed

reset-db:  ## ⚠️ DESTRUCTIF — supprime la DB Postgres et la recrée vide
	@echo "⚠️  Cette commande va supprimer toutes les données. Ctrl+C pour annuler."
	@sleep 3
	docker compose down -v
	docker compose up -d postgres
	@sleep 3
	docker compose up -d
	$(MAKE) seed

# ---------- Shells utiles ----------

backend-shell:  ## Shell Python dans le conteneur backend
	docker compose exec backend python manage.py shell

frontend-shell:  ## Shell sh dans le conteneur frontend
	docker compose exec frontend sh
