from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.database import get_db
from backend.models.task import Task, StatusUpdate, Comment, Priority, TaskStatus
from backend.services import ai_agent, notifier

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: str
    assignee_name: str
    assignee_email: str
    assignee_telegram: Optional[str] = None
    deadline: datetime
    priority: Priority = Priority.MEDIUM


class StatusUpdateCreate(BaseModel):
    raw_text: str


class CommentCreate(BaseModel):
    text: str


@router.post("/", status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    # AI analysis
    analysis = ai_agent.analyze_task(data.title, data.description)

    task = Task(
        title=data.title,
        description=data.description,
        assignee_name=data.assignee_name,
        assignee_email=data.assignee_email,
        assignee_telegram=data.assignee_telegram,
        deadline=data.deadline,
        priority=data.priority,
        task_type=analysis.get("task_type"),
        ai_plan=analysis.get("plan"),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Уведомление в Telegram
    if task.assignee_telegram:
        msg = notifier.build_task_notification(task)
        await notifier.send_telegram(task.assignee_telegram, msg)

    # Уведомление на email
    email_html = notifier.build_task_email_html(task)
    await notifier.send_email(
        to_email=task.assignee_email,
        subject=f"📋 Новая задача: {task.title}",
        html_body=email_html,
    )

    return _task_to_dict(task)


@router.get("/")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task).options(selectinload(Task.updates)).order_by(Task.created_at.desc())
    )
    tasks = result.scalars().all()
    return [_task_to_dict(t) for t in tasks]


@router.get("/{task_id}")
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await _get_or_404(task_id, db)
    return _task_to_dict(task)


@router.post("/{task_id}/status")
async def add_status_update(task_id: int, data: StatusUpdateCreate, db: AsyncSession = Depends(get_db)):
    task = await _get_or_404(task_id, db)
    parsed = ai_agent.parse_status_update(data.raw_text, task.title)

    update = StatusUpdate(
        task_id=task_id,
        raw_text=data.raw_text,
        progress=parsed.get("progress", 0),
        blockers=parsed.get("blockers"),
        next_steps=parsed.get("next_steps"),
    )
    db.add(update)

    task.progress = parsed.get("progress", task.progress)
    if task.progress >= 100:
        task.status = TaskStatus.DONE
    elif task.status == TaskStatus.NEW:
        task.status = TaskStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(update)
    return {"id": update.id, "progress": update.progress, "blockers": update.blockers, "next_steps": update.next_steps}


@router.post("/{task_id}/comments")
async def add_comment(task_id: int, data: CommentCreate, db: AsyncSession = Depends(get_db)):
    task = await _get_or_404(task_id, db)
    ai_rec = ai_agent.generate_correction_recommendations(task.title, data.text, task.status.value)

    comment = Comment(task_id=task_id, text=data.text, ai_recommendation=ai_rec)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    # Forward recommendation to assignee
    if task.assignee_telegram:
        msg = f"💬 <b>Комментарий руководителя по задаче «{task.title}»:</b>\n{data.text}\n\n🤖 <b>Рекомендации:</b>\n{ai_rec}"
        await notifier.send_telegram(task.assignee_telegram, msg)

    return {"id": comment.id, "ai_recommendation": ai_rec}


@router.get("/dashboard/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task))
    tasks = result.scalars().all()
    total = len(tasks)
    by_status = {}
    for t in tasks:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
    at_risk = [_task_to_dict(t) for t in tasks if t.status == TaskStatus.AT_RISK]
    overdue = [_task_to_dict(t) for t in tasks if t.deadline < datetime.utcnow() and t.status != TaskStatus.DONE]
    return {"total": total, "by_status": by_status, "at_risk": at_risk, "overdue": overdue}


async def _get_or_404(task_id: int, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id).options(
            selectinload(Task.updates), selectinload(Task.comments)
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "assignee_name": task.assignee_name,
        "assignee_email": task.assignee_email,
        "assignee_telegram": task.assignee_telegram,
        "deadline": task.deadline.isoformat(),
        "priority": task.priority.value,
        "status": task.status.value,
        "task_type": task.task_type,
        "ai_plan": task.ai_plan,
        "progress": task.progress,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }
