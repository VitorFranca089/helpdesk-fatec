# Shortcuts for docker compose. Run `make` alone to list the commands.
# Requires Linux or WSL (GNU make and a POSIX shell).
# Ports: frontend http://localhost:8700, backend http://localhost:8701 (see "Portas" in the README).

.DEFAULT_GOAL := help
.PHONY: help up ps logs test smoke shell db reset-db stop down clean

help: ## List the commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

up: ## Build the images and start everything (the first run downloads the model)
	docker compose up -d --build

ps: ## Show the containers and their health
	docker compose ps

logs: ## Follow the backend logs (Ctrl+C to quit)
	docker compose logs -f backend

test: ## Run the backend unit tests
	docker compose run --rm --no-deps backend pytest

smoke: ## Send the 4 sample tickets to the running API
	docker compose exec backend python scripts/smoke_test.py

shell: ## Open a shell in the backend
	docker compose exec backend bash

db: ## Open the SQLite shell
	docker compose exec backend python -m sqlite3 /data/triadesk.db

reset-db: ## Delete every ticket, keeping the containers up (asks for confirmation)
	@read -p "This deletes every ticket. Continue? [y/N] " r && [ "$$r" = y ]
	docker compose exec backend python -c "import app.models; from app.database import Base, engine; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"

stop: ## Stop the containers without removing them
	docker compose stop

down: ## Stop and remove the containers. Volumes are kept
	docker compose down

clean: ## Stop everything and delete the volumes, including the model cache (asks for confirmation)
	@read -p "This deletes the volumes and their data. Continue? [y/N] " r && [ "$$r" = y ]
	docker compose down -v
