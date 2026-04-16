from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import UserRepo
from core.config import settings
from ..keyboards.kb import get_main_menu, get_tasks_menu

router = Router()


class OnboardingStates(StatesGroup):
    waiting_timezone = State()
    waiting_morning = State()
    waiting_evening = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    try:
        result = await UserRepo.create(message.from_user.id, message.from_user.username)
        if result is None or (isinstance(result, tuple) and result[0] is None):
            await message.answer("❌ Ошибка создания пользователя. Попробуй позже.")
            return
        
        if isinstance(result, tuple):
            user, is_new = result
        else:
            user = result
            is_new = False
        
        if is_new:
            await message.answer(
                "🎉 <b>Добро пожаловать в MindFlow AI!</b>\n\n"
                "🎁 Тебе подарили <b>3 дня Premium</b>!\n\n"
                "Теперь доступны:\n"
                "🎨 Все темы оформления\n"
                "🏷 Безлимитные теги\n"
                "🤖 AI без ограничений\n\n"
                "Давай настроим твой часовой пояс. Напиши название города "
                "(например: Moscow, London, New York):"
            )
            await state.set_state(OnboardingStates.waiting_timezone)
        elif user.timezone == "UTC" and user.morning_time == "09:00":
            await message.answer(
                "👋 Привет! Я MindFlow AI — твой AI-ассистент для планирования.\n\n"
                "Давай настроим твой часовой пояс. Напиши название города "
                "(например: Moscow, London, New York):"
            )
            await state.set_state(OnboardingStates.waiting_timezone)
        else:
            await show_main_menu(message)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")


@router.message(OnboardingStates.waiting_timezone)
async def process_timezone(message: Message, state: FSMContext):
    city = message.text.strip()
    timezone = get_timezone_by_city(city)
    
    await UserRepo.update_settings(message.from_user.id, timezone=timezone)
    await state.update_data(timezone=timezone)
    
    await message.answer(
        f"✅ Часовой пояс: {timezone}\n\n"
        "Во сколько тебе удобно получать утренний план? (формат: ЧЧ:ММ)"
    )
    await state.set_state(OnboardingStates.waiting_morning)


@router.message(OnboardingStates.waiting_morning)
async def process_morning(message: Message, state: FSMContext):
    time = message.text.strip()
    if not is_valid_time(time):
        await message.answer("❌ Неверный формат. Напиши время как: 09:00")
        return
    
    await UserRepo.update_settings(message.from_user.id, morning_time=time)
    await state.update_data(morning_time=time)
    
    await message.answer(
        f"✅ Утренний план в {time}\n\n"
        "Во сколько отправлять вечерний отчёт? (формат: ЧЧ:ММ)"
    )
    await state.set_state(OnboardingStates.waiting_evening)


@router.message(OnboardingStates.waiting_evening)
async def process_evening(message: Message, state: FSMContext):
    time = message.text.strip()
    if not is_valid_time(time):
        await message.answer("❌ Неверный формат. Напиши время как: 21:00")
        return
    
    await UserRepo.update_settings(message.from_user.id, evening_time=time)
    await state.clear()
    
    await message.answer(
        f"✅ Вечерний отчёт в {time}\n\n"
        "🎉 Настройка завершена! Я готов помогать тебе планировать день."
    )
    await show_main_menu(message)


@router.message(F.text == "🔙 Главное меню")
@router.callback_query(F.data == "back_main")
async def back_to_main(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    await msg.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_menu()
    )


async def show_main_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))
        ],
        [
            InlineKeyboardButton(text="📋 Задачи", callback_data="task_list"),
            InlineKeyboardButton(text="📊 План", callback_data="plan_generate")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton(text="📈 Статистика", callback_data="stats")
        ]
    ])
    
    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выбери действие или открой приложение:",
        reply_markup=keyboard
    )


def get_timezone_by_city(city: str) -> str:
    tz_map = {
        "moscow": "Europe/Moscow",
        "london": "Europe/London",
        "new york": "America/New_York",
        "tokyo": "Asia/Tokyo",
        "paris": "Europe/Paris",
        "berlin": "Europe/Berlin",
        "kiev": "Europe/Kiev",
        "dubai": "Asia/Dubai",
        "singapore": "Asia/Singapore",
        "sydney": "Australia/Sydney",
        "los angeles": "America/Los_Angeles",
        "chicago": "America/Chicago",
    }
    return tz_map.get(city.lower(), "UTC")


def is_valid_time(time_str: str) -> bool:
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return False
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except:
        return False
