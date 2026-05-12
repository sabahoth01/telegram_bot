# Telegram-бот для локальных LLM-моделей Gemma и Qwen (small llm packet)

Данный проект представляет собой Telegram-бота для взаимодействия с локальными языковыми моделями (LLM) через Ollama.


- Gemma 2B
- Qwen 2.5 0.5B

Бот работает полностью локально и позволяет:

- общаться с локальными LLM через Telegram;
- переключаться между моделями прямо в чате;
- использовать локальный AI без облачных API.


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
Gemma 2B / Qwen 0.5B
```

В данной архитектуре:

- модели запускаются локально через Ollama;
- Docker содержит только Telegram-бота;
- снижается использование RAM;
- уменьшается размер Docker image;
- ускоряется запуск контейнеров;
- упрощается развертывание.


# Используемые модели

## Gemma 2B

- Разработчик: Google
- Размер: ~2B параметров

Команда загрузки:

```bash
ollama pull gemma:2b
```

---

## Qwen 2.5 0.5B

- Разработчик: Alibaba
- Размер: ~0.5B параметров
- Очень лёгкая и быстрая модель.

Команда загрузки:

```bash
ollama pull qwen2.5:0.5b
```


# Варианты запуска Ollama

## Вариант 1 — Ollama внутри Docker

### Плюсы

- Полная контейнеризация;
- Проще переносить проект между машинами.

### Минусы

- Большой Docker image;
- Более высокое использование RAM;
- Медленный запуск;
- Медленная сборка контейнеров.

---

## Вариант 2 — Ollama на хосте

### Плюсы

- Намного легче;
- Быстрее работает;
- Подходит для слабых ноутбуков;
- Docker используется только для Telegram-бота.

### Минусы

- Ollama необходимо запускать отдельно.

---

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

---

# Загрузка моделей

## Gemma

```bash
ollama pull gemma:2b
```

## Qwen

```bash
ollama pull qwen2.5:0.5b
```

## Проверка

```bash
ollama list
```

Пример:

```text
NAME              SIZE
gemma:2b          1.7 GB
qwen2.5:0.5b      397 MB
```


# Структура проекта

```text
telegram_bot/
│
├── bot.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Makefile
├── .env
└── README.md
```


# Регистрация Telegram-бота

Чтобы получить Telegram Token:

1. Найдите @BotFather в Telegram.
2. Выполните команду:

```text
/newbot
```

3. Укажите имя и username.
4. Скопируйте API Token.
5. Добавьте токен в `.env`.


# Настройка `.env`

## Без Proxy

```env
TELEGRAM_TOKEN=ваш_токен
OLLAMA_HOST=http://host.docker.internal:11434
GEMMA_MODEL=gemma:2b
QWEN_MODEL=qwen2.5:0.5b
DEFAULT_MODEL=gemma:2b
```

---

## С Proxy Webshare

```env
TELEGRAM_TOKEN=ваш_токен
OLLAMA_HOST=http://host.docker.internal:11434
GEMMA_MODEL=gemma:2b
QWEN_MODEL=qwen2.5:0.5b
DEFAULT_MODEL=gemma:2b
PROXY_URL=http://USERNAME:PASSWORD@IP:PORT
```

Пример:

```env
PROXY_URL=http://pbioafwr:u8nvo6quoift@31.59.20.176:6754
```


# requirements.txt

```txt
python-telegram-bot[socks]==20.7
requests==2.31.0
python-dotenv==1.0.0
```

# Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```


# docker-compose.yml

```yaml
services:

  bot:
    build: .
    container_name: gemma-bot
    restart: always

    env_file:
      - .env

    extra_hosts:
      - "host.docker.internal:host-gateway"
```


# Сборка проекта

## Сборка контейнера

```bash
docker compose build --no-cache
```

## Запуск

```bash
docker compose up -d
```

## Просмотр логов

```bash
docker compose logs -f
```


# Проверка Ollama

## На хосте

```bash
ollama list
```

## Проверка API

```bash
curl http://localhost:11434/api/tags
```


# Использование Telegram-бота

## Основные команды

### Запуск

```text
/start
```

### Очистка истории

```text
/clear
```

### Информация о модели

```text
/model
```

### Переключение на Gemma

```text
/setmodel gemma
```

### Переключение на Qwen

```text
/setmodel qwen
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

Telegram API может быть заблокирован провайдером или сетью.

---

## Решение через Proxy

В `.env`:

```env
PROXY_URL=http://USERNAME:PASSWORD@IP:PORT
```

---

## Проверка Proxy

```bash
curl -x http://USERNAME:PASSWORD@IP:PORT \
"https://api.telegram.org/botTOKEN/getUpdates"
```

---

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


# Полная очистка Docker

## Удаление контейнеров

```bash
docker compose down -v
```

## Полная очистка Docker

```bash
docker system prune -a --volumes
```

# Использование Makefile

Для упрощения управления проектом используется Makefile.

 Просмотр всех доступных команд

```bash
make help
```

## Основные команды

Сборка и запуск бота

```bash
make run
```

Команда:

- собирает Docker image;
- запускает Telegram-бота;
- автоматически использует настройки из `.env`.

Остановка контейнеров

```bash
make stop
```
Останавливает Telegram-бота.


Перезапуск бота

```bash
make restart
```

Полностью пересобирает и перезапускает контейнер бота.

# Техническая архитектура

- LLM: Gemma 2B / Qwen 2.5 0.5B
- Inference Engine: Ollama
- Telegram API: python-telegram-bot
- Containerization: Docker Compose
- Proxy Support: HTTP/SOCKS Proxy webshare
- Deployment: Local AI inference