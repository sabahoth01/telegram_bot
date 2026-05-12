.PHONY: run stop restart logs logs-bot logs-ollama build shell \
        test-ollama pull-models clean status help

help:
	@echo ""
	@echo "  Telegram Ollama Bot — Commands"
	@echo ""
	@echo "  --- Setup ---"
	@echo "  make run           Build and start the bot container"
	@echo "  make pull-models   Pull Gemma 2B and Qwen 0.5B on host Ollama"
	@echo "  make test-ollama   Test Ollama API from host"
	@echo ""
	@echo "  --- Dev ---"
	@echo "  make stop          Stop containers"
	@echo "  make restart       Rebuild and restart bot"
	@echo "  make logs          Live logs"
	@echo "  make logs-bot      Live bot logs"
	@echo "  make logs-ollama   Show Ollama status info"
	@echo "  make shell         Open shell in bot container"
	@echo "  make status        Show container status"
	@echo ""
	@echo "  --- Maintenance ---"
	@echo "  make build         Force rebuild bot image"
	@echo "  make clean         Remove containers and unused project resources"
	@echo ""

run:
	docker compose up -d --build

stop:
	docker compose stop

restart:
	docker compose up -d --build --force-recreate bot

logs:
	docker compose logs -f

logs-bot:
	docker compose logs -f bot

logs-ollama:
	@echo "Ollama is running on the host, not inside Docker."
	@echo "Installed models:"
	@ollama list
	@echo ""
	@echo "Running models:"
	@ollama ps

build:
	docker compose build --no-cache bot

shell:
	docker exec -it gemma-bot sh

status:
	docker compose ps

test-ollama:
	curl -s http://localhost:11434/api/generate \
		-d '{"model":"gemma:2b","prompt":"Say hello","stream":false}' \
		| python -m json.tool

pull-models:
	ollama pull gemma:2b
	ollama pull qwen2.5:0.5b

clean:
	docker compose down -v --remove-orphans