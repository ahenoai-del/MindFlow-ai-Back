from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import json
import aiosqlite
from db import TaskRepo, UserRepo
from db.database import DB_PATH
from core.config import settings
from ..keyboards.kb import get_back_button

router = Router()


@router.message(F.text == "📱 Приложение")
async def open_webapp(message: Message):
    if not settings.WEBAPP_URL:
        await message.answer(
            "⚠️ WebApp пока не настроен.\n"
            "Добавь WEBAPP_URL в .env файл"
        )
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT is_premium FROM users WHERE id = ?", (message.from_user.id,)
        ) as cursor:
            row = await cursor.fetchone()
            is_premium = row['is_premium'] if row else 0
    
    webapp_url = settings.WEBAPP_URL
    params = []
    
    if is_premium:
        params.append(f"premium=1")
    if settings.API_URL:
        params.append(f"api_url={settings.API_URL}")
    
    if params:
        separator = '&' if '?' in webapp_url else '?'
        webapp_url += separator + '&'.join(params)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть MindFlow App",
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
    
    await message.answer(
        "📱 <b>MindFlow WebApp</b>\n\n"
        "Удобный интерфейс для управления задачами",
        reply_markup=kb
    )


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    data = json.loads(message.web_app_data.data)
    action = data.get("action")
    
    if action == "buy_premium":
        from .payments import create_premium_invoice
        await create_premium_invoice(message, data.get("plan", "year"))
        return
    
    if action == "check_premium":
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT is_premium, premium_until FROM users WHERE id = ?", (message.from_user.id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row['is_premium']:
                    until = row['premium_until'] or "Бессрочно"
                    await message.answer(f"✅ Premium активен до: {until}")
                else:
                    await message.answer("❌ Premium не активен. Напиши /premium для покупки.")
        return
    
    if action == "add_task":
        task = await TaskRepo.create(
            user_id=message.from_user.id,
            title=data.get("title"),
            description=data.get("description"),
            category=data.get("category", data.get("tag", "general")),
            priority=data.get("priority", 2),
            deadline=data.get("deadline"),
            estimated_minutes=data.get("estimated_minutes")
        )
        await message.answer(f"✅ Задача создана: {task.title}")
    
    elif action == "complete_task":
        task_id = data.get("task_id")
        task = await TaskRepo.complete(task_id)
        if task:
            await message.answer(f"✅ Выполнено: {task.title}")
    
    elif action == "delete_task":
        task_id = data.get("task_id")
        await TaskRepo.delete(task_id)
        await message.answer("🗑 Задача удалена")
    
    elif action == "update_task":
        task = await TaskRepo.update(
            task_id=data.get("task_id"),
            title=data.get("title"),
            description=data.get("description"),
            priority=data.get("priority"),
            category=data.get("category"),
            deadline=data.get("deadline"),
            status=data.get("status")
        )
        await message.answer(f"✏️ Задача обновлена: {task.title}")


@router.callback_query(F.data == "settings_timezone")
async def change_timezone(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌍 Напиши название города для часового пояса:\n\n"
        "Примеры: Moscow, London, New York, Tokyo",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data == "settings_morning")
async def change_morning(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌅 Напиши время для утреннего плана (формат ЧЧ:ММ):\n\n"
        "Пример: 09:00",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data == "settings_evening")
async def change_evening(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌙 Напиши время для вечернего отчёта (формат ЧЧ:ММ):\n\n"
        "Пример: 21:00",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.message(F.text.regexp(r"^[A-Za-zА-Яа-я\s]+$"))
async def set_timezone(message: Message):
    from .start import get_timezone_by_city
    from aiogram.fsm.context import FSMContext
    
    timezone = get_timezone_by_city(message.text)
    await UserRepo.update_settings(message.from_user.id, timezone=timezone)
    
    await message.answer(f"✅ Часовой пояс изменен на: {timezone}")


@router.message(F.text.regexp(r"^\d{1,2}:\d{2}$"))
async def set_time(message: Message):
    time = message.text.strip()
    parts = time.split(":")
    h, m = int(parts[0]), int(parts[1])
    
    if not (0 <= h <= 23 and 0 <= m <= 59):
        await message.answer("❌ Неверный формат времени. Используй ЧЧ:ММ")
        return
    
    user = await UserRepo.get(message.from_user.id)
    
    morning = user.morning_time if user else "09:00"
    evening = user.evening_time if user else "21:00"
    
    current_hour = int(morning.split(":")[0])
    new_hour = h
    
    if new_hour < 12:
        await UserRepo.update_settings(message.from_user.id, morning_time=time)
        await message.answer(f"🌅 Утренний план установлен на {time}")
    elif new_hour >= 18:
        await UserRepo.update_settings(message.from_user.id, evening_time=time)
        await message.answer(f"🌙 Вечерний отчёт установлен на {time}")
    else:
        await UserRepo.update_settings(message.from_user.id, morning_time=time)
        await message.answer(f"⏰ Время напоминания установлено на {time}")
