import logging
import requests
import os
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
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma:2b")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation history per user (in-memory)
user_histories: dict[int, list[dict]] = {}


# def query_gemma(user_id: int, user_message: str) -> str:
#     """Send message to Gemma via Ollama and return response."""
#     if user_id not in user_histories:
#         user_histories[user_id] = []

#     user_histories[user_id].append({
#         "role": "user",
#         "content": user_message
#     })

#     # Keep last 10 messages to avoid context overflow
#     history = user_histories[user_id][-10:]

#     # Build prompt from history
#     prompt = ""
#     for msg in history:
#         if msg["role"] == "user":
#             prompt += f"User: {msg['content']}\n"
#         else:
#             prompt += f"Assistant: {msg['content']}\n"
#     prompt += "Assistant:"

#     try:
#         response = requests.post(
#             f"{OLLAMA_HOST}/api/generate",
#             json={
#                 "model": GEMMA_MODEL,
#                 "prompt": prompt,
#                 "stream": False,
#                 "options": {
#                     "temperature": 0.7,
#                     "num_predict": 512,
#                 }
#             },
#             timeout=120
#         )
#         response.raise_for_status()
#         reply = response.json().get("response", "").strip()

#         user_histories[user_id].append({
#             "role": "assistant",
#             "content": reply
#         })
#         return reply

#     except requests.exceptions.ConnectionError:
#         return "Cannot connect to Gemma. Make sure Ollama is running (`ollama serve`)."
#     except requests.exceptions.Timeout:
#         return "Gemma is thinking too long. Try a shorter question."
#     except Exception as e:
#         logger.error(f"Ollama error: {e}")
#         return f"Error: {str(e)}"

SYSTEM_PROMPT = """You are a helpful teaching assistant for a Big Data course.
You have access to course materials including lectures, tasks, and quizzes.
When answering, prioritize information from the course context provided.
If the question is not covered in the course materials, answer from general knowledge but say so.
Be concise and helpful. If you don't know something, say so honestly."""


def query_gemma(user_id: int, user_message: str) -> str:
    if user_id not in user_histories:
        user_histories[user_id] = []

    # 1. Retrieve relevant course context
    context = retrieve(user_message)

    # 2. Build prompt
    if context:
        rag_block = f"Relevant course materials:\n\n{context}\n\n---\n\n"
    else:
        rag_block = ""

    user_histories[user_id].append({
        "role": "user",
        "content": user_message
    })

    history = user_histories[user_id][-6:]  # last 6 messages
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
                "options": {"temperature": 0.3, "num_predict": 512}
                # lower temperature = more factual answers
            },
            timeout=120
        )
        response.raise_for_status()
        reply = response.json().get("response", "").strip()

        user_histories[user_id].append({"role": "assistant", "content": reply})
        return reply

    except Exception as e:
        return f"Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}!\n\n"
        f"I'm powered by **{GEMMA_MODEL}** running locally via Ollama.\n\n"
        "Just send me any message and I'll respond!\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/clear - Clear conversation history\n"
        "/model - Show current model",
        parse_mode="Markdown"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories.pop(user_id, None)
    await update.message.reply_text("🧹 Conversation history cleared!")


async def model_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Current model: `{GEMMA_MODEL}`\n"
        f"Ollama host: `{OLLAMA_HOST}`",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    logger.info(f"User {user_id}: {user_message}")
    reply = query_gemma(user_id, user_message)
    logger.info(f"Gemma: {reply[:100]}...")

    await update.message.reply_text(reply)


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set in .env file!")

    logger.info(f"Starting bot with model: {GEMMA_MODEL}")
    logger.info(f"Ollama host: {OLLAMA_HOST}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("model", model_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()