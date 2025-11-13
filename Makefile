.PHONY: help install run stop restart logs clean build test deploy

help: ## Show this help message
	@echo "MCQ Application - Makefile Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (for local development without Docker)
	pip install -r requirements.txt

run: ## Start the application with Docker Compose
	@chmod +x run.sh
	./run.sh

up: run ## Alias for run

start: run ## Alias for run

stop: ## Stop the application
	docker compose down

down: stop ## Alias for stop

restart: ## Restart the application
	docker compose restart

logs: ## View application logs
	docker compose logs -f

build: ## Build the Docker image
	docker compose build

clean: ## Stop and remove containers, networks, and volumes
	docker compose down -v
	docker system prune -f

test: ## Run tests (placeholder for future tests)
	@echo "Tests not yet implemented"

shell: ## Open a shell in the running container
	docker compose exec mcq-app bash

status: ## Check application status
	docker compose ps

health: ## Check application health
	@curl -s http://localhost:5000/health | python -m json.tool || echo "Application is not responding"

deploy-railway: ## Deploy to Railway (requires Railway CLI)
	@echo "Deploying to Railway..."
	@echo "Make sure you have Railway CLI installed: npm i -g @railway/cli"
	railway up

deploy-render: ## Deploy to Render (manual deployment via Render dashboard)
	@echo "To deploy to Render:"
	@echo "1. Push code to GitHub"
	@echo "2. Connect repository in Render dashboard"
	@echo "3. Select 'Web Service'"
	@echo "4. Use the settings from render.yaml"

deploy-fly: ## Deploy to Fly.io (requires Fly CLI)
	@echo "Deploying to Fly.io..."
	@echo "Make sure you have Fly CLI installed: https://fly.io/docs/hands-on/install-flyctl/"
	flyctl deploy

