# reporium-mcp $0 local-OSS dev substrate.
# Additive, local-only, no cloud, no credentials. Application code unchanged.

COMPOSE := docker compose -f docker-compose.yml

.PHONY: up down smoke seed logs ps rebuild

up: ## Build + start the stub API and mcp container, wait for healthy
	$(COMPOSE) up -d --build --wait

down: ## Stop and remove containers, networks, and volumes
	$(COMPOSE) down -v --remove-orphans

smoke: ## Full e2e: up -> assert health -> run MCP tools vs local stub -> down
	bash smoke/smoke.sh

seed: ## Show the seed data the local stub serves
	@echo "Seed file: seed/repos.json"
	@python -c "import json;d=json.load(open('seed/repos.json'));print('repos:',len(d['repos']));print('edges:',len(d['graph_edges']));print('gaps:',len(d['taxonomy_gaps']))"

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

rebuild: ## Rebuild images without cache
	$(COMPOSE) build --no-cache
