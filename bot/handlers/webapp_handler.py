import json
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import settings
from services.user_service import UserService
from services.payment_service import PaymentService
from db import TaskRepo, UserRepo
from bot.keyboards.kb import get_back_button

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "📱 Приложение")
async def open_webapp(message: Message):
    if not settings.WEBAPP_URL:
        await message.answer("⚠️ WebApp пока не настроен.\nДобавь WEBAPP_URL в .env файл")
        return

    is_premium = await UserService.is_premium(message.from_user.id)
    webapp_url = settings.WEBAPP_URL
    params: list[str] = []
    if is_premium:
        params.append("premium=1")
    if settings.API_URL:
        params.append(f"api_url={settings.API_URL}")
    if params:
        separator = "&" if "?" in webapp_url else "?"
        webapp_url += separator + "&".join(params)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть MindFlow App",
            web_app=WebAppInfo(url=webapp_url),
        )],
    ])
    await message.answer(
        "📱 <b>MindFlow WebApp</b>\n\nУдобный интерфейс для управления задачами",
        reply_markup=kb,
    )


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, TypeError):
        await message.answer("❌ Неверные данные")
        return

    action = data.get("action")

    if action == "buy_premium":
        await PaymentService.create_invoice(message, data.get("plan", "year"))
        return

    if action == "check_premium":
        status = await UserService.is_premium(message.from_user.id)
        if status:
            await message.answer("✅ Premium активен")
        else:
            await message.answer("❌ Premium не активен. Напиши /premium для покупки.")
        return

    if action == "add_task":
        task = await TaskRepo.create(
            user_id=message.from_user.id,
            title=data.get("title", ""),
            description=data.get("description"),
            category=data.get("category", data.get("tag", "general")),
            priority=data.get("priority", 2),
            deadline=data.get("deadline"),
            estimated_minutes=data.get("estimated_minutes"),
        )
        if task:
            await message.answer(f"✅ Задача создана: {task.title}")
        else:
            await message.answer("❌ Не удалось создать задачу")
        return

    if action == "complete_task":
        task_id = data.get("task_id")
        task = await TaskRepo.complete(task_id)
        if task:
            await message.answer(f"✅ Выполнено: {task.title}")
        else:
            await message.answer("❌ Задача не найдена")
        return

    if action == "delete_task":
        task_id = data.get("task_id")
        await TaskRepo.delete(task_id)
        await message.answer("🗑 Задача удалена")
        return

    if action == "update_task":
        filtered = {
            k: v for k, v in {
                "title": data.get("title"),
                "description": data.get("description"),
                "priority": data.get("priority"),
                "category": data.get("category"),
                "deadline": data.get("deadline"),
                "status": data.get("status"),
            }.items() if v is not None
        }
        task = await TaskRepo.update(data.get("task_id"), **filtered)
        if task:
            await message.answer(f"✏️ Задача обновлена: {task.title}")
        else:
            await message.answer("❌ Задача не найдена")
        return

    await message.answer("❓ Неизвестное действие")
