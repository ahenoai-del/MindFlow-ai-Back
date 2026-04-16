from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import hmac
import hashlib
import json

from db import UserRepo, TaskRepo, GamificationRepo, ReminderRepo
from core.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_telegram_webapp(init_data: str) -> Optional[dict]:
    try:
        params = dict(pair.split('=') for pair in init_data.split('&'))
        hash_value = params.pop('hash', None)
        if not hash_value:
            return None
        
        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(params.items()))
        
        secret_key = hmac.new(
            b"WebAppData", 
            settings.BOT_TOKEN.encode(), 
            hashlib.sha256
        ).digest()
        
        computed_hash = hmac.new(
            secret_key, 
            data_check_string.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        if computed_hash == hash_value:
            user_data = params.get('user')
            if user_data:
                return json.loads(user_data)
        return None
    except:
        return None


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "general"
    priority: int = 2
    deadline: Optional[str] = None
    estimated_minutes: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    deadline: Optional[str] = None
    status: Optional[str] = None


class ReminderCreate(BaseModel):
    remind_at: str
    task_id: Optional[int] = None


@app.get("/api/user/{user_id}")
async def get_user(user_id: int):
    user = await UserRepo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    g = await GamificationRepo.get_or_create(user_id)
    
    return {
        "id": user.id,
        "username": user.username,
        "timezone": user.timezone,
        "morning_time": user.morning_time,
        "evening_time": user.evening_time,
        "is_premium": bool(user.is_premium),
        "premium_until": user.premium_until,
        "xp": g.xp,
        "level": g.level,
        "streak": g.streak,
        "total_completed": g.total_completed,
        "achievements": await GamificationRepo.get_achievements(user_id)
    }


@app.get("/api/tasks/{user_id}")
async def get_tasks(user_id: int, include_completed: bool = False):
    tasks = await TaskRepo.get_user_tasks(user_id, include_completed=include_completed)
    
    return [{
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "category": t.category,
        "priority": t.priority,
        "deadline": t.deadline,
        "estimated_minutes": t.estimated_minutes,
        "status": t.status,
        "created_at": t.created_at,
        "completed_at": t.completed_at
    } for t in tasks]


@app.post("/api/tasks/{user_id}")
async def create_task(user_id: int, task: TaskCreate):
    new_task = await TaskRepo.create(
        user_id=user_id,
        title=task.title,
        description=task.description,
        category=task.category,
        priority=task.priority,
        deadline=task.deadline,
        estimated_minutes=task.estimated_minutes
    )
    
    return {
        "id": new_task.id,
        "title": new_task.title,
        "status": "created"
    }


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: int, task: TaskUpdate):
    updates = {k: v for k, v in task.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    updated = await TaskRepo.update(task_id, **updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"id": updated.id, "status": "updated"}


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: int):
    task = await TaskRepo.complete(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"id": task.id, "status": "completed"}


@app.post("/api/tasks/{task_id}/uncomplete")
async def uncomplete_task(task_id: int):
    task = await TaskRepo.uncomplete(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"id": task.id, "status": "pending"}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    await TaskRepo.delete(task_id)
    return {"status": "deleted"}


@app.get("/api/reminders/{user_id}")
async def get_reminders(user_id: int):
    reminders = await ReminderRepo.get_user_reminders(user_id)
    
    return [{
        "id": r.id,
        "task_id": r.task_id,
        "remind_at": r.remind_at,
        "created_at": r.created_at
    } for r in reminders]


@app.post("/api/reminders/{user_id}")
async def create_reminder(user_id: int, reminder: ReminderCreate):
    new_reminder = await ReminderRepo.create(
        user_id=user_id,
        remind_at=reminder.remind_at,
        task_id=reminder.task_id
    )
    
    return {
        "id": new_reminder.id,
        "remind_at": new_reminder.remind_at,
        "status": "created"
    }


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int):
    await ReminderRepo.delete(reminder_id)
    return {"status": "deleted"}


@app.get("/api/stats/{user_id}")
async def get_stats(user_id: int):
    from db import StatsRepo
    stats = await StatsRepo.get_week_stats(user_id)
    
    return [{
        "date": s.date,
        "tasks_completed": s.tasks_completed,
        "tasks_total": s.tasks_total,
        "focus_score": s.focus_score
    } for s in stats]


@app.get("/api/verify")
async def verify_user(init_data: str = Query(...)):
    user_data = verify_telegram_webapp(init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram data")
    
    user_id = user_data.get('id')
    if user_id:
        await UserRepo.create(user_id, user_data.get('username'))
    
    return {"user_id": user_id, "user": user_data}
