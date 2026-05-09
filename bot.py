import logging
import requests
import os
import asyncio
from rag import retrieve
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
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma:2b")
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

SYSTEM_PROMPT = """You are a helpful teaching assistant for a Big Data course.
You have access to course materials including lectures, tasks, and quizzes.

When answering:
- prioritize information from the course context provided;
- if the question is not covered in the course materials, answer from general knowledge and clearly say so;
- be concise, clear, and helpful;
- if you do not know something, say so honestly;
- do not use Markdown formatting symbols;
- do not use **bold**, # headers, backticks, or Markdown lists;
- write clean plain text suitable for Telegram messages;
- always answer in the same language as the user's latest message.

Language rule:
If the user writes in English, answer in English.
If the user writes in Russian, answer in Russian.
If the user writes in French, answer in French.
Do not switch languages unless the user switches languages.
"""


def query_gemma(user_id: int, user_message: str) -> str:
    if user_id not in user_histories:
        user_histories[user_id] = []

    try:
        context = retrieve(user_message)
    except Exception as e:
        logger.warning(f"RAG retrieve error: {e}")
        context = ""

    rag_block = f"Relevant course materials:\n\n{context}\n\n---\n\n" if context else ""

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

    prompt = f"{SYSTEM_PROMPT}\n\n{rag_block}{conversation}Assistant:"

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": GEMMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 512
                }
            },
            timeout=180
        )

        response.raise_for_status()
        reply = response.json().get("response", "").strip()
        reply = (
            reply
            .replace("**", "")
            .replace("```", "")
            .replace("##", "")
            .replace("#", "")
        )

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
            "1. Ollama is running on the host: `ollama serve`\n"
            "2. OLLAMA_HOST is `http://host.docker.internal:11434`\n"
            "3. Your Docker container has access to `host.docker.internal`."
        )

    except requests.exceptions.Timeout:
        return "Gemma took too long to answer. Try a shorter question."

    except requests.exceptions.HTTPError as e:
        return f"Ollama HTTP error: {e.response.text}"

    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"Error: {str(e)}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}!\n\n"
        f"I'm powered by {GEMMA_MODEL} running locally via Ollama.\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/clear - Clear conversation history\n"
        "/model - Show current model"
    )
    logger.info("START command received")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories.pop(user_id, None)
    await update.message.reply_text("Conversation history cleared.")


async def model_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Current model: {GEMMA_MODEL}\n"
        f"Ollama host: {OLLAMA_HOST}"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("MESSAGE RECEIVED")
        user_id = update.effective_user.id
        user_message = update.message.text
        logger.info(f"USER MESSAGE: {user_message}")
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        logger.info("CALLING GEMMA...")
        reply = await asyncio.to_thread(
            query_gemma,
            user_id,
            user_message
        )
        logger.info(f"GEMMA REPLY: {reply[:200]}")
        logger.info("SENDING MESSAGE TO TELEGRAM...")
        await update.message.reply_text(reply)
        logger.info("MESSAGE SENT SUCCESSFULLY")

    except Exception as e:
        logger.exception(f"HANDLE_MESSAGE ERROR: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram error", exc_info=context.error)

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set in .env file.")

    logger.info(f"Starting bot with model: {GEMMA_MODEL}")
    logger.info(f"Ollama host: {OLLAMA_HOST}")
    logger.info(f"Proxy enabled: {bool(PROXY_URL)}")

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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("model", model_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
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