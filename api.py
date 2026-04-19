import hmac
import hashlib
import json
import logging
from typing import Optional
from urllib.parse import parse_qs, unquote

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from db import UserRepo, TaskRepo, GamificationRepo, ReminderRepo, StatsRepo, PushSubscriptionRepo
from config.settings import settings
from services.push_service import PushService
from services.reminder_service import ReminderService
from services.voice_service import VoiceService

logger = logging.getLogger(__name__)

app = FastAPI(title="MindFlow API")

# FIXED: allow_origins=["*"] несовместим с allow_credentials=True по спецификации CORS.
# Указываем конкретные домены. WEBAPP_URL берётся из настроек.
_allowed_origins = [settings.WEBAPP_URL.rstrip("/")]  if settings.WEBAPP_URL else []
if not _allowed_origins:
    _allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_telegram_webapp(init_data: str) -> Optional[dict]:
    """
    Верификация данных Telegram WebApp согласно официальной документации:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # FIXED: dict(pair.split("=") ...) падает на значениях содержащих "=" (base64 и др.)
        # Используем parse_qs который корректно обрабатывает URL-encoded строки
        parsed = parse_qs(init_data, keep_blank_values=True)
        params = {k: unquote(v[0]) for k, v in parsed.items()}

        hash_value = params.pop("hash", None)
        if not hash_value:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )

        # FIXED: порядок аргументов был перепутан.
        # Правильно по документации Telegram:
        #   secret_key = HMAC_SHA256(key=BOT_TOKEN, msg="WebAppData")
        #   hash = HMAC_SHA256(key=secret_key, msg=data_check_string)
        secret_key = hmac.new(
            settings.BOT_TOKEN.encode(),  # key = BOT_TOKEN
            b"WebAppData",               # msg = "WebAppData"
            hashlib.sha256,
        ).digest()

        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        # FIXED: используем hmac.compare_digest вместо == для защиты от timing attack
        if hmac.compare_digest(computed_hash, hash_value):
            user_data = params.get("user")
            if user_data:
                return json.loads(user_data)
        return None
    except Exception as e:
        logger.warning("WebApp verification failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Dependency: получить и проверить текущего пользователя из заголовка
# ---------------------------------------------------------------------------
tg_init_data_header = APIKeyHeader(name="X-Telegram-Init-Data", auto_error=False)


async def get_current_user_id(init_data: Optional[str] = Depends(tg_init_data_header)) -> Optional[int]:
    """
    Возвращает user_id из верифицированного Telegram init_data.
    Возвращает None если заголовок отсутствует (для обратной совместимости с query param).
    """
    if not init_data:
        return None
    user_data = verify_telegram_webapp(init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth data")
    return user_data.get("id")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

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
    text: Optional[str] = None
    repeat_interval: Optional[str] = None


class ReminderSnooze(BaseModel):
    minutes: int = 10


class PushSubscriptionCreate(BaseModel):
    subscription: str


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------

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
        "is_premium": user.is_premium_active,
        "premium_until": user.premium_until,
        "xp": g.xp,
        "level": g.level,
        "streak": g.streak,
        "total_completed": g.total_completed,
        "achievements": await GamificationRepo.get_achievements(user_id),
    }


@app.get("/api/user/{user_id}/premium")
async def check_premium(user_id: int):
    user = await UserRepo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"is_premium": user.is_premium_active, "premium_until": user.premium_until}


# ---------------------------------------------------------------------------
# Push endpoints
# ---------------------------------------------------------------------------

@app.get("/api/vapid-public-key")
async def get_vapid_public_key():
    if not PushService.is_configured():
        raise HTTPException(status_code=404, detail="Push not configured")
    return {"publicKey": settings.VAPID_PUBLIC_KEY}


@app.post("/api/push/{user_id}/subscribe")
async def push_subscribe(user_id: int, sub: PushSubscriptionCreate):
    ok = await PushService.register_subscription(user_id, sub.subscription)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid subscription")
    return {"status": "subscribed"}


@app.delete("/api/push/{user_id}/subscribe")
async def push_unsubscribe(user_id: int):
    await PushService.unregister_subscription(user_id)
    return {"status": "unsubscribed"}


# ---------------------------------------------------------------------------
# Task endpoints
# FIXED: добавлена проверка владельца задачи (ownership check).
# Без этого любой пользователь мог изменить/удалить чужую задачу по task_id.
# ---------------------------------------------------------------------------

@app.get("/api/tasks/{user_id}")
async def get_tasks(user_id: int, include_completed: bool = False):
    tasks = await TaskRepo.get_user_tasks(user_id, include_completed=include_completed)
    return [
        {
            "id": t.id, "title": t.title, "description": t.description,
            "category": t.category, "priority": t.priority, "deadline": t.deadline,
            "estimated_minutes": t.estimated_minutes, "status": t.status,
            "created_at": t.created_at, "completed_at": t.completed_at,
        }
        for t in tasks
    ]


@app.post("/api/tasks/{user_id}")
async def create_task(user_id: int, task: TaskCreate):
    new_task = await TaskRepo.create(
        user_id=user_id, title=task.title, description=task.description,
        category=task.category, priority=task.priority,
        deadline=task.deadline, estimated_minutes=task.estimated_minutes,
    )
    if not new_task:
        raise HTTPException(status_code=500, detail="Failed to create task")
    return {"id": new_task.id, "title": new_task.title, "status": "created"}


async def _get_task_or_403(task_id: int, user_id: int):
    """Возвращает задачу если она существует и принадлежит user_id, иначе кидает 403/404."""
    task = await TaskRepo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return task


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: int, task: TaskUpdate, user_id: int = Query(...)):
    await _get_task_or_403(task_id, user_id)
    updates = {k: v for k, v in task.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    updated = await TaskRepo.update(task_id, **updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": updated.id, "status": "updated"}


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: int, user_id: int = Query(...)):
    await _get_task_or_403(task_id, user_id)
    task = await TaskRepo.complete(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task.id, "status": "completed"}


@app.post("/api/tasks/{task_id}/uncomplete")
async def uncomplete_task(task_id: int, user_id: int = Query(...)):
    await _get_task_or_403(task_id, user_id)
    task = await TaskRepo.uncomplete(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task.id, "status": "pending"}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, user_id: int = Query(...)):
    await _get_task_or_403(task_id, user_id)
    await TaskRepo.delete(task_id)
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Reminder endpoints
# ---------------------------------------------------------------------------

@app.get("/api/reminders/{user_id}")
async def get_reminders(user_id: int):
    reminders = await ReminderService.get_user_reminders(user_id)
    return [
        {
            "id": r.id, "task_id": r.task_id, "text": r.text,
            "remind_at": r.remind_at, "status": r.status,
            "repeat_interval": r.repeat_interval, "created_at": r.created_at,
        }
        for r in reminders
    ]


@app.post("/api/reminders/{user_id}")
async def create_reminder(user_id: int, reminder: ReminderCreate):
    new_reminder = await ReminderService.create(
        user_id=user_id, remind_at=reminder.remind_at,
        task_id=reminder.task_id, text=reminder.text,
        repeat_interval=reminder.repeat_interval,
    )
    if not new_reminder:
        raise HTTPException(status_code=500, detail="Failed to create reminder")
    return {
        "id": new_reminder.id, "remind_at": new_reminder.remind_at,
        "status": "created",
    }


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int, user_id: int = Query(...)):
    ok = await ReminderService.delete(reminder_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "deleted"}


@app.post("/api/reminders/{reminder_id}/snooze")
async def snooze_reminder(reminder_id: int, body: ReminderSnooze, user_id: int = Query(...)):
    ok = await ReminderService.snooze(reminder_id, user_id, body.minutes)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "snoozed", "minutes": body.minutes}


# ---------------------------------------------------------------------------
# Voice endpoint
# ---------------------------------------------------------------------------

@app.post("/api/voice/{user_id}")
async def transcribe_voice(user_id: int, file: UploadFile = File(...)):
    if not VoiceService.is_configured():
        raise HTTPException(status_code=501, detail="Voice transcription not configured")
    audio_data = await file.read()
    if len(audio_data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25MB)")
    text = await VoiceService.transcribe(audio_data, filename=file.filename or "voice.ogg")
    if not text:
        raise HTTPException(status_code=422, detail="Could not transcribe audio")
    return {"text": text}


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------

@app.get("/api/stats/{user_id}")
async def get_stats(user_id: int):
    stats = await StatsRepo.get_week_stats(user_id)
    return [
        {
            "date": s.date, "tasks_completed": s.tasks_completed,
            "tasks_total": s.tasks_total, "focus_score": s.focus_score,
        }
        for s in stats
    ]


# ---------------------------------------------------------------------------
# Verify endpoint
# ---------------------------------------------------------------------------

@app.get("/api/verify")
async def verify_user(init_data: str = Query(...)):
    user_data = verify_telegram_webapp(init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram data")
    user_id = user_data.get("id")
    if user_id:
        await UserRepo.create(user_id, user_data.get("username"))
    return {"user_id": user_id, "user": user_data}


# ---------------------------------------------------------------------------
# Service worker
# ---------------------------------------------------------------------------

@app.get("/sw.js")
async def service_worker():
    return FileResponse(
        "webapp/sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )
