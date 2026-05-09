.PHONY: run stop restart logs logs-bot logs-ollama build shell \
        test-ollama pull-model clean status ingest re-ingest \
        backup restore help

help:
	@echo ""
	@echo "  Gemma Telegram Bot — Commands"
	@echo ""
	@echo "  --- Setup ---"
	@echo "  make run          Build and start all containers"
	@echo "  make ingest       Load course docs into vector DB"
	@echo "  make re-ingest    Clear and reload all course docs"
	@echo ""
	@echo "  --- Dev ---"
	@echo "  make stop         Stop all containers"
	@echo "  make restart      Rebuild and restart bot only"
	@echo "  make logs         Live logs (all containers)"
	@echo "  make logs-bot     Live logs (bot only)"
	@echo "  make logs-ollama  Ollama runs on host, not in Docker"
	@echo "  make shell        Open shell in bot container"
	@echo "  make status       Show container status"
	@echo ""
	@echo "  --- Maintenance ---"
	@echo "  make build        Force rebuild bot image"
	@echo "  make pull-model   Pull Gemma model on host Ollama"
	@echo "  make test-ollama  Test Ollama is alive"
	@echo "  make clean        Remove containers and local ChromaDB"
	@echo "  make backup       Create backup of ChromaDB"
	@echo "  make restore      Restore selected ChromaDB backup"
	@echo ""

run:
	docker compose up -d --build

stop:
	docker compose stop

restart:
	docker compose up -d --build bot

logs:
	docker compose logs -f

logs-bot:
	docker compose logs -f bot

logs-ollama:
	@echo "Ollama is running on the host, not inside Docker."
	@echo "Check it with: ollama list"

build:
	docker compose build --no-cache bot

shell:
	docker exec -it gemma-bot sh

status:
	docker compose ps

test-ollama:
	curl -s http://host.docker.internal:11434/api/generate \
		-d '{"model":"gemma:2b","prompt":"Say hello","stream":false}' \
		| python3 -m json.tool

pull-model:
	ollama pull gemma:2b

ingest:
	docker exec -it gemma-bot python ingest.py

re-ingest:
	docker exec -it gemma-bot python -c "import shutil; shutil.rmtree('/app/chroma_db', ignore_errors=True)"
	docker exec -it gemma-bot python ingest.py

backup:
	@echo "Backing up ChromaDB..."
	tar -czvf chroma_db_backup_$$(date +%Y%m%d_%H%M%S).tar.gz ./chroma_db
	@echo "Saved."

restore:
	@echo "Available backups:"
	@ls *.tar.gz 2>/dev/null || echo "No backups found."
	@read -p "Enter complete backup file name: " backup_file; \
	if [ -f $$backup_file ]; then \
		echo "Restoring $$backup_file..."; \
		rm -rf ./chroma_db; \
		tar -xzvf $$backup_file; \
		echo "Restore done."; \
	else \
		echo "Error: file not found."; \
	fi

clean:
	docker compose down -v --remove-orphans
	rm -rf ./chroma_db