import json
import re
import requests
from backend.config import settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

SYSTEM_PROMPT = (
    "Ты — AI-агент системы TaskFlow AI. Помогаешь руководителям управлять задачами "
    "и исполнителям их выполнять. Отвечай на русском языке. "
    "Будь конкретным, структурированным, используй маркированные списки."
)


def _chat(prompt: str, max_tokens: int = 1024) -> str:
    full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    resp = requests.post(
        GEMINI_URL,
        headers={"X-goog-api-key": settings.anthropic_api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _parse_json(text: str, fallback: dict) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    try:
        return json.loads(text)
    except Exception:
        return fallback


def analyze_task(title: str, description: str) -> dict:
    prompt = f"""Проанализируй задачу и верни JSON строго в таком формате (без markdown-блоков):
{{
  "task_type": "одно из: проектная|операционная|исследовательская|регуляторная",
  "methodology": "рекомендуемая методология",
  "plan": "пошаговый план выполнения (5-7 шагов с контрольными точками)",
  "milestones": ["milestone 1", "milestone 2", "milestone 3"],
  "recommendations": "конкретные рекомендации исполнителю"
}}

Задача: {title}
Описание: {description}"""

    text = _chat(prompt, max_tokens=1500)
    return _parse_json(text, {
        "task_type": "операционная",
        "methodology": "GTD",
        "plan": text,
        "milestones": [],
        "recommendations": "",
    })


def parse_status_update(raw_text: str, task_title: str) -> dict:
    prompt = f"""Исполнитель прислал обновление по задаче "{task_title}".
Верни JSON строго в таком формате (без markdown-блоков):
{{
  "progress": <число от 0 до 100>,
  "blockers": "описание блокеров или null",
  "next_steps": "следующие шаги"
}}

Текст обновления: {raw_text}"""

    text = _chat(prompt)
    return _parse_json(text, {"progress": 0, "blockers": None, "next_steps": raw_text})


def generate_correction_recommendations(task_title: str, comment: str, current_status: str) -> str:
    prompt = f"""Руководитель недоволен ходом задачи "{task_title}".
Текущий статус: {current_status}
Комментарий руководителя: {comment}

Сформулируй 3-5 конкретных корректирующих действий для исполнителя.
Что именно нужно сделать, в каком порядке, с какими сроками."""
    return _chat(prompt)


def assess_risk(task_title: str, deadline_str: str, progress: int, days_left: int) -> dict:
    prompt = f"""Задача: "{task_title}"
Дедлайн: {deadline_str}, осталось дней: {days_left}
Текущий прогресс: {progress}%

Оцени риск срыва. Верни JSON (без markdown-блоков):
{{
  "risk_level": "low|medium|high",
  "reason": "краткое объяснение",
  "action": "рекомендуемое действие"
}}"""

    text = _chat(prompt)
    return _parse_json(text, {"risk_level": "medium", "reason": text, "action": ""})
