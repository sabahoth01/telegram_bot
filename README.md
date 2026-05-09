# Telegram RAG-бот для курса Big Data (Gemma 2B)

Этот проект представляет собой Telegram-бота, использующего модель Gemma 2B (через Ollama) для ответов на вопросы по курсу Big Data. Бот использует связку LangChain и ChromaDB для реализации технологии RAG (Retrieval-Augmented Generation — генерация с дополнением извлечёнными данными).

Бот способен:

- отвечать на вопросы пользователей;
- использовать контекст из учебных материалов;
- работать полностью локально;
- использовать Gemma 2B через Ollama;
- хранить векторную базу знаний;
- поддерживать Telegram через Proxy/VPN.


# Архитектура проекта

```text
Telegram
   ↓
Proxy / VPN
   ↓
Docker Container (bot)
   ↓
Ollama на хосте
   ↓
Gemma 2B
```

В данной архитектуре:

- Gemma запускается локально на хостовой системе;
- Docker содержит только Telegram-бота и RAG;
- снижается использование RAM;
- ускоряется запуск контейнеров;
- уменьшается размер Docker image.


# Варианты запуска Gemma

## Вариант 1 — Ollama внутри Docker

### Плюсы

- Полная контейнеризация;
- Проще переносить проект между машинами.

### Минусы

- Очень большой Docker image;
- Высокое потребление RAM;
- Медленная сборка;
- Медленный запуск;
- На ноутбуках с 8 ГБ RAM возможны зависания.

### docker-compose.yml

```yaml
services:

  ollama:
    image: ollama/ollama
    container_name: ollama
    restart: always
    volumes:
      - ollama_data:/root/.ollama

  ollama-init:
    image: ollama/ollama
    container_name: ollama-init
    depends_on:
      - ollama
    entrypoint: sh -c "sleep 5 && ollama pull gemma:2b"
    environment:
      - OLLAMA_HOST=http://ollama:11434
    restart: "no"

  bot:
    build: .
    container_name: gemma-bot
    restart: always
    depends_on:
      - ollama
    env_file:
      - .env
    environment:
      - OLLAMA_HOST=http://ollama:11434
```

## Вариант 2 — Ollama на хосте (рекомендуется)

### Плюсы

- Намного легче;
- Меньше использование RAM;
- Быстрее запуск;
- Подходит для слабых ноутбуков;
- Docker используется только для бота.

### Минусы

- Ollama необходимо запускать отдельно на хостовой системе.

### docker-compose.yml

```yaml
services:
  bot:
    build: .
    container_name: gemma-bot
    restart: always

    env_file:
      - .env

    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434
      - ANONYMIZED_TELEMETRY=False

    extra_hosts:
      - "host.docker.internal:host-gateway"

    volumes:
      - ./chroma_db:/app/chroma_db
      - ./course_docs:/app/course_docs
```

# Требования

## Основные зависимости

- Docker
- Docker Compose
- Ollama
- Telegram Bot Token
- Python 3.10+

# Установка Ollama

## Windows

Скачать Ollama:

```text
https://ollama.com/download
```

После установки:

```bash
ollama serve
```

Скачать модель:

```bash
ollama pull gemma:2b
```

Проверка:

```bash
ollama list
```

---

# Структура проекта

```text
telegram_bot/
│
├── bot.py
├── rag.py
├── ingest.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Makefile
├── .env
│
├── chroma_db/
│
└── course_docs/
```


# Регистрация Telegram-бота

Чтобы получить токен:

1. Найдите **@BotFather** в Telegram.
2. Выполните команду:

```text
/newbot
```

3. Укажите имя и username.
4. Скопируйте API Token.
5. Добавьте его в `.env`.


# Настройка `.env`

## Без Proxy

```env
TELEGRAM_TOKEN=ваш_токен

OLLAMA_HOST=http://host.docker.internal:11434
GEMMA_MODEL=gemma:2b
```

## С Proxy Webshare

```env
TELEGRAM_TOKEN=ваш_токен

OLLAMA_HOST=http://host.docker.internal:11434
GEMMA_MODEL=gemma:2b

PROXY_URL=http://USERNAME:PASSWORD@IP:PORT
```

Пример:

```env
PROXY_URL=http://pbioafwr:u8nvo6quoift@31.59.20.176:6754
```

# Установка зависимостей

## requirements.txt

```txt
--extra-index-url https://download.pytorch.org/whl/cpu

numpy<2

torch==2.2.2+cpu
sentence-transformers==2.7.0

python-telegram-bot[socks]==20.7

requests==2.31.0
python-dotenv==1.0.0

chromadb==0.4.22
langchain-text-splitters==0.2.2
pypdf==4.2.0
```

# Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

CMD ["python", "bot.py"]
```

# Запуск проекта

## Сборка контейнеров

```bash
docker compose build --no-cache
```

## Запуск

```bash
docker compose up -d
```

## Проверка логов

```bash
docker compose logs -f bot
```

# Проверка Ollama

## На хосте

```bash
ollama list
```

## Из Docker

```bash
docker exec -it gemma-bot sh
```

```bash
curl http://host.docker.internal:11434/api/tags
```

# Подготовка документов

Поместите материалы курса в:

```text
course_docs/
```

Поддерживаются:

- PDF
- TXT
- MD

# Индексация документов

```bash
make ingest
```

или:

```bash
docker exec -it gemma-bot python ingest.py
```

# Использование Makefile

## Управление контейнерами

```bash
make run
```

Сборка и запуск контейнеров.


```bash
make stop
```

Остановка контейнеров.

```bash
make restart
```

Перезапуск бота.

```bash
make status
```

Проверка статуса контейнеров.

```bash
make clean
```

Удаление контейнеров, volumes и базы данных.


# Работа с логами

```bash
make logs
```

Логи всех контейнеров.


```bash
make logs-bot
```

Логи Telegram-бота.


```bash
make logs-ollama
```

Логи Ollama.


# Работа с базой знаний

## Полная переиндексация

```bash
make re-ingest
```


## Backup базы данных

```bash
make backup
```

## Restore базы данных

```bash
make restore
```

# Решение проблем

# Telegram не отвечает

## Симптомы

```text
telegram.error.TimedOut
```

или:

```text
HTTPSConnectionPool(host='api.telegram.org')
```


## Причина

Telegram API заблокирован в сети.


## Решение через Proxy

### Webshare

В `.env`:

```env
PROXY_URL=http://USERNAME:PASSWORD@IP:PORT
```


## Настройка Proxy в bot.py

```python
if PROXY_URL:
    builder = (
        builder
        .proxy(PROXY_URL)
        .get_updates_proxy(PROXY_URL)
    )
```


## Проверка Telegram API

```bash
curl -x http://USERNAME:PASSWORD@IP:PORT \
"https://api.telegram.org/botTOKEN/getUpdates"
```


# Использование VPN

Можно использовать:

- Cloudflare WARP
- Amnezia VPN
- Outline VPN
- OpenVPN

После включения VPN:

```bash
docker compose restart
```


# Ошибка подключения к Ollama

## Ошибка

```text
Cannot connect to Ollama
```

## Проверить

```bash
ollama serve
```

и:

```env
OLLAMA_HOST=http://host.docker.internal:11434
```

# Ошибка NumPy

## Ошибка

```text
A module compiled using NumPy 1.x cannot run in NumPy 2.x
```

## Решение

```txt
numpy<2
```

# Полная очистка Docker

## Удаление всех volumes

```bash
docker volume rm $(docker volume ls -q)
```

## Полная очистка Docker

```bash
docker system prune -a --volumes
```

# Техническая архитектура

- **LLM**: Gemma 2B
- **Inference Engine**: Ollama
- **RAG**: LangChain + ChromaDB
- **Embeddings**: all-MiniLM-L6-v2
- **Vector Database**: ChromaDB
- **Containerization**: Docker Compose
- **Telegram API**: python-telegram-bot
- **Proxy Support**: HTTP/SOCKS Proxy
