.PHONY: run stop restart logs logs-bot logs-ollama build shell \
        test-ollama pull-model clean status ingest re-ingest help

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
	@echo "  make logs-ollama  Live logs (Ollama only)"
	@echo "  make shell        Open shell in bot container"
	@echo "  make status       Show container status"
	@echo ""
	@echo "  --- Maintenance ---"
	@echo "  make build        Force rebuild bot image"
	@echo "  make pull-model   Re-pull Gemma model"
	@echo "  make test-ollama  Test Ollama is alive"
	@echo "  make clean        Remove all containers and volumes"
	@echo "  make backup       Create copy of the chromaDB"
	@echo "  make restore      Restore the selected DB archive"
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
	docker compose logs -f ollama

build:
	docker compose build --no-cache bot

shell:
	docker exec -it gemma-bot sh

status:
	docker compose ps

test-ollama:
	curl -s http://localhost:11434/api/generate \
		-d '{"model":"gemma:2b","prompt":"Say hello","stream":false}' \
		| python3 -m json.tool

pull-model:
	docker exec -it ollama ollama pull gemma:2b

ingest:
	docker exec -it gemma-bot python ingest.py

re-ingest:
	docker exec -it gemma-bot python -c "import shutil; shutil.rmtree('/app/chroma_db', ignore_errors=True)"
	docker exec -it gemma-bot python ingest.py

backup:
	@echo "Backup ChromaDB..."
	tar -czvf chroma_db_backup_$$(date +%Y%m%d_%H%M%S).tar.gz ./chroma_db
	@echo "Savec!"

restore:
	@echo "Available backups :"
	@ls *.tar.gz 2>/dev/null || echo "Aucune sauvegarde trouvée."
	@read -p "Enter complet na,e of the backup : " backup_file; \
	if [ -f $$backup_file ]; then \
		echo "Restauration of $$backup_file..."; \
		rm -rf ./chroma_db; \
		tar -xzvf $$backup_file; \
		echo "Restauration done."; \
	else \
		echo "Error : File not found."; \
	fi


clean:
	docker compose down -v --remove-orphans
	rm -rf ./chroma_db