import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import httpx
from backend.config import settings


async def send_telegram(chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception:
        return False


def send_email_sync(to_email: str, subject: str, html_body: str) -> bool:
    if not settings.smtp_user or not settings.smtp_password:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"TaskFlow AI <{settings.smtp_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


async def send_email(to_email: str, subject: str, html_body: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_email_sync, to_email, subject, html_body)


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


def build_task_email_html(task) -> str:
    priority_label = {"high": "🔴 Высокий", "medium": "🟡 Средний", "low": "🟢 Низкий"}.get(task.priority, task.priority)
    deadline_str = task.deadline.strftime("%d.%m.%Y %H:%M")
    plan_html = task.ai_plan.replace("\n", "<br>") if task.ai_plan else "—"
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f8;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
    <div style="background:#0f172a;border-radius:8px;padding:16px 24px;margin-bottom:24px">
      <h1 style="color:#38bdf8;margin:0;font-size:22px">TaskFlow AI</h1>
    </div>
    <h2 style="color:#1e293b;margin-bottom:8px">📋 Вам назначена новая задача</h2>
    <h3 style="color:#0f172a;font-size:20px;margin-bottom:16px">{task.title}</h3>
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
      <tr>
        <td style="padding:8px 0;color:#64748b;width:140px">Исполнитель:</td>
        <td style="padding:8px 0;font-weight:600">{task.assignee_name}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:#64748b">Срок выполнения:</td>
        <td style="padding:8px 0;font-weight:600;color:#ef4444">{deadline_str}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:#64748b">Приоритет:</td>
        <td style="padding:8px 0">{priority_label}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:#64748b">Тип задачи:</td>
        <td style="padding:8px 0">{task.task_type or '—'}</td>
      </tr>
    </table>
    <div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:20px">
      <h4 style="color:#475569;margin:0 0 8px">Описание:</h4>
      <p style="color:#1e293b;margin:0;line-height:1.6">{task.description}</p>
    </div>
    <div style="background:#eff6ff;border-radius:8px;padding:16px;border-left:4px solid #38bdf8">
      <h4 style="color:#1e40af;margin:0 0 8px">🤖 AI-план выполнения:</h4>
      <div style="color:#1e293b;line-height:1.8">{plan_html}</div>
    </div>
    <p style="color:#94a3b8;font-size:13px;margin-top:24px;text-align:center">
      Обновляйте статус через Telegram-бот или на дашборде.<br>
      <a href="{settings.base_url}" style="color:#38bdf8">Открыть TaskFlow AI</a>
    </p>
  </div>
</body>
</html>
"""


def build_alert(task, risk: dict) -> str:
    return (
        f"⚠️ <b>Алерт по задаче: {task.title}</b>\n\n"
        f"Риск: {risk['risk_level'].upper()}\n"
        f"Причина: {risk['reason']}\n"
        f"Рекомендация: {risk['action']}\n"
        f"Прогресс: {task.progress}%"
    )
