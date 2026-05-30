"""
Telegram-бот для исполнителей.
Запускается отдельно: python -m bot.main
"""
import asyncio
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from backend.config import settings

API_BASE = settings.base_url + "/api"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я TaskFlow AI бот.\n\n"
        "Команды:\n"
        "/tasks — мои задачи\n"
        "/status <task_id> <текст> — обновить статус\n\n"
        "Или просто отправь голосовое/текстовое сообщение с обновлением статуса."
    )


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/tasks/")
    tasks = resp.json()
    my_tasks = [t for t in tasks if t.get("assignee_telegram") == chat_id]
    if not my_tasks:
        await update.message.reply_text("У вас нет активных задач.")
        return
    lines = []
    for t in my_tasks:
        status_emoji = {"new": "🆕", "in_progress": "⚙️", "at_risk": "⚠️", "done": "✅", "overdue": "🔴"}.get(t["status"], "⚪")
        lines.append(f"{status_emoji} <b>[{t['id']}] {t['title']}</b>\nПрогресс: {t['progress']}% | Срок: {t['deadline'][:10]}")
    await update.message.reply_html("\n\n".join(lines))


async def update_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Использование: /status <task_id> <текст обновления>")
        return
    task_id = args[0]
    text = " ".join(args[1:])
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/tasks/{task_id}/status", json={"raw_text": text})
    if resp.status_code == 200:
        data = resp.json()
        await update.message.reply_text(
            f"✅ Статус обновлён!\nПрогресс: {data['progress']}%\n"
            f"Блокеры: {data['blockers'] or 'нет'}\nСледующие шаги: {data['next_steps']}"
        )
    else:
        await update.message.reply_text("Ошибка при обновлении статуса.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Свободный текст — подсказываем формат."""
    await update.message.reply_text(
        "Для обновления статуса используй:\n/status <номер_задачи> <твой текст>\n\n"
        "Список задач: /tasks"
    )


def run_bot():
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("status", update_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()


if __name__ == "__main__":
    run_bot()
