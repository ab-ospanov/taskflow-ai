import asyncio
import httpx
from backend.config import settings


async def send_telegram(chat_id: str, text: str) -> bool:
    """Отправляет сообщение через Telegram Bot API."""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception:
        return False


def build_task_notification(task) -> str:
    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
    deadline_str = task.deadline.strftime("%d.%m.%Y %H:%M")
    text = (
        f"<b>📋 Новая задача: {task.title}</b>\n\n"
        f"{priority_emoji} Приоритет: {task.priority.upper()}\n"
        f"📅 Срок: {deadline_str}\n\n"
        f"<b>Описание:</b>\n{task.description}\n\n"
    )
    if task.ai_plan:
        text += f"<b>🤖 AI-план:</b>\n{task.ai_plan}\n\n"
    text += "Для обновления статуса напишите /status"
    return text


def build_alert(task, risk: dict) -> str:
    return (
        f"⚠️ <b>Алерт по задаче: {task.title}</b>\n\n"
        f"Риск: {risk['risk_level'].upper()}\n"
        f"Причина: {risk['reason']}\n"
        f"Рекомендация: {risk['action']}\n"
        f"Прогресс: {task.progress}%"
    )
