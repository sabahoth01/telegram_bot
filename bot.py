import logging
import requests
import os
import asyncio
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://host.docker.internal:11434"
)

GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma:2b")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen2.5:0.5b")

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", GEMMA_MODEL)

PROXY_URL = os.getenv("PROXY_URL")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

user_histories: dict[int, list[dict]] = {}
user_models: dict[int, str] = {}
pending_model_choice: set[int] = set()

available_models = {
    "gemma": GEMMA_MODEL,
    "qwen": QWEN_MODEL,
}

SYSTEM_PROMPT = """
You are a helpful AI assistant.

Rules:
- Be concise, clear, and natural.
- Answer in the same language as the user.
- Do not use Markdown formatting.
- Do not use bold text, headers, or code blocks unless explicitly requested.
- Write clean plain text suitable for Telegram.
"""


def get_user_model(user_id: int) -> str:
    return user_models.get(user_id, DEFAULT_MODEL)


def clean_reply(text: str) -> str:
    text = text.strip()

    for symbol in ["**", "```", "##", "#", "`"]:
        text = text.replace(symbol, "")

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def query_model(user_id: int, user_message: str) -> str:
    if user_id not in user_histories:
        user_histories[user_id] = []

    selected_model = get_user_model(user_id)

    user_histories[user_id].append({
        "role": "user",
        "content": user_message
    })

    history = user_histories[user_id][-6:]

    conversation = ""

    for msg in history:
        if msg["role"] == "user":
            conversation += f"User: {msg['content']}\n"
        else:
            conversation += f"Assistant: {msg['content']}\n"

    prompt = f"""
{SYSTEM_PROMPT}

The user's latest message is:
{user_message}

Answer strictly in the same language as the user's latest message.

{conversation}

Assistant:
"""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 200,
                    "num_ctx": 2048,
                    "num_thread": 2
                }
            },
            timeout=180
        )

        response.raise_for_status()

        reply = response.json().get("response", "").strip()
        reply = clean_reply(reply)

        if not reply:
            reply = "I received an empty response from Ollama."

        user_histories[user_id].append({
            "role": "assistant",
            "content": reply
        })

        return reply

    except requests.exceptions.ConnectionError:
        return (
            "Cannot connect to Ollama.\n\n"
            "Check that:\n"
            "1. Ollama is running\n"
            "2. OLLAMA_HOST is correct\n"
            "3. Docker can access host.docker.internal"
        )

    except requests.exceptions.Timeout:
        return "The model took too long to answer."

    except requests.exceptions.HTTPError as e:
        return f"Ollama HTTP error: {e.response.text}"

    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"Error: {str(e)}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    current_model = get_user_model(user.id)

    await update.message.reply_text(
        f"Hi {user.first_name}!\n\n"
        f"I'm powered by {current_model} running locally via Ollama.\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/clear - Clear conversation history\n"
        "/model - Show current model\n"
        "/setmodel gemma - Use Gemma\n"
        "/setmodel qwen - Use Qwen"
    )

    logger.info("START command received")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    user_histories.pop(user_id, None)

    await update.message.reply_text(
        "Conversation history cleared."
    )


async def model_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    current_model = get_user_model(user_id)

    await update.message.reply_text(
        f"Current model: {current_model}\n\n"
        "Available models:\n"
        f"gemma -> {GEMMA_MODEL}\n"
        f"qwen -> {QWEN_MODEL}"
    )


async def set_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        pending_model_choice.add(user_id)

        await update.message.reply_text(
            "Please choose a model:\n\n"
            "gemma\n"
            "qwen\n\n"
            "Or use directly:\n"
            "/setmodel gemma\n"
            "/setmodel qwen"
        )
        return

    choice = context.args[0].lower().strip()

    if choice not in available_models:
        await update.message.reply_text(
            "Unknown model.\n\n"
            "Available models:\n"
            "gemma\n"
            "qwen"
        )
        return

    selected_model = available_models[choice]

    user_models[user_id] = selected_model

    pending_model_choice.discard(user_id)

    await update.message.reply_text(
        f"Model selected successfully.\n\n"
        f"Current model: {selected_model}"
    )

    logger.info(f"User {user_id} selected model: {selected_model}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("MESSAGE RECEIVED")

        user_id = update.effective_user.id
        user_message = update.message.text.strip()

        logger.info(f"USER MESSAGE: {user_message}")

        if user_id in pending_model_choice:
            msg = user_message.lower()

            if msg in available_models:
                selected_model = available_models[msg]

                user_models[user_id] = selected_model

                pending_model_choice.discard(user_id)

                await update.message.reply_text(
                    f"Model selected successfully.\n\n"
                    f"Current model: {selected_model}"
                )

                logger.info(
                    f"User {user_id} selected model: {selected_model}"
                )

                return

            await update.message.reply_text(
                "Please choose only:\n"
                "gemma\n"
                "qwen"
            )

            return

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        logger.info(
            f"CALLING MODEL: {get_user_model(user_id)}"
        )

        reply = await asyncio.to_thread(
            query_model,
            user_id,
            user_message
        )

        logger.info(f"MODEL REPLY: {reply[:200]}")

        await update.message.reply_text(reply)

        logger.info("MESSAGE SENT SUCCESSFULLY")

    except Exception as e:
        logger.exception(f"HANDLE_MESSAGE ERROR: {e}")


async def error_handler(update: object,
                        context: ContextTypes.DEFAULT_TYPE):
    logger.exception(
        "Telegram error",
        exc_info=context.error
    )


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError(
            "TELEGRAM_TOKEN not set in .env file."
        )

    logger.info(
        f"Starting bot with default model: {DEFAULT_MODEL}"
    )

    logger.info(f"Ollama host: {OLLAMA_HOST}")

    logger.info(
        f"Proxy enabled: {bool(PROXY_URL)}"
    )

    builder = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .connect_timeout(60)
        .read_timeout(60)
        .write_timeout(60)
        .pool_timeout(60)
    )

    if PROXY_URL:
        builder = (
            builder
            .proxy(PROXY_URL)
            .get_updates_proxy(PROXY_URL)
        )

    app = builder.build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("clear", clear)
    )

    app.add_handler(
        CommandHandler("model", model_info)
    )

    app.add_handler(
        CommandHandler("setmodel", set_model)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.add_error_handler(error_handler)

    logger.info("Bot is running...")

    app.run_polling(
        poll_interval=2,
        timeout=60,
        drop_pending_updates=False,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()