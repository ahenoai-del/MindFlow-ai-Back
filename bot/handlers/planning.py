from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date, datetime, timedelta
from db import TaskRepo, PlanRepo, StatsRepo, UserRepo, GamificationRepo, ACHIEVEMENTS, get_level, xp_to_next_level
from ..keyboards.kb import get_plan_menu, get_back_button, get_settings_menu
from ai.scheduler import generate_day_plan

router = Router()


class ScheduleStates(StatesGroup):
    waiting_time = State()


@router.message(F.text == "📊 План на сегодня")
@router.callback_query(F.data == "plan_generate")
async def show_today_plan(event: Message | CallbackQuery):
    user_id = event.from_user.id
    today = date.today().isoformat()
    
    existing_plan = await PlanRepo.get(user_id, today)
    
    if existing_plan:
        await show_plan(event, existing_plan.schedule)
        return
    
    tasks = await TaskRepo.get_user_tasks(user_id)
    user = await UserRepo.get(user_id)
    
    if not tasks:
        msg = event if isinstance(event, Message) else event.message
        text = "📭 Нет задач на сегодня. Добавь задачи, и я составлю план!"
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(text, reply_markup=get_plan_menu())
            except:
                await event.answer(text)
        else:
            await msg.answer(text, reply_markup=get_plan_menu())
        return
    
    plan_text = await generate_day_plan(tasks, user.timezone if user else "UTC")
    
    await PlanRepo.create(user_id, today, plan_text)
    
    added = await GamificationRepo.add_achievement(user_id, "planner")
    if added:
        await GamificationRepo.add_xp(user_id, ACHIEVEMENTS["planner"]["xp"])
    
    await show_plan(event, plan_text)


@router.callback_query(F.data == "plan_schedule")
async def plan_schedule_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📅 <b>Настройка расписания</b>\n\n"
        "Напиши время в формате ЧЧ:ММ для начала планирования:\n\n"
        "Например: <b>09:00</b>",
        reply_markup=get_back_button()
    )
    await state.set_state(ScheduleStates.waiting_time)
    await callback.answer()


@router.message(ScheduleStates.waiting_time)
async def process_schedule_time(message: Message, state: FSMContext):
    time = message.text.strip()
    parts = time.split(":")
    
    if len(parts) != 2:
        await message.answer("❌ Неверный формат. Напиши время как: 09:00")
        return
    
    try:
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError()
    except:
        await message.answer("❌ Неверный формат. Напиши время как: 09:00")
        return
    
    await UserRepo.update_settings(message.from_user.id, morning_time=time)
    await state.clear()
    
    await message.answer(f"✅ Планирование будет в {time} каждый день")
    user_id = event.from_user.id
    today = date.today().isoformat()
    
    existing_plan = await PlanRepo.get(user_id, today)
    
    if existing_plan:
        await show_plan(event, existing_plan.schedule)
        return
    
    tasks = await TaskRepo.get_user_tasks(user_id)
    user = await UserRepo.get(user_id)
    
    if not tasks:
        msg = event if isinstance(event, Message) else event.message
        text = "📭 Нет задач на сегодня. Добавь задачи, и я составлю план!"
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(text, reply_markup=get_plan_menu())
            except:
                await event.answer(text)
        else:
            await msg.answer(text, reply_markup=get_plan_menu())
        return
    
    plan_text = await generate_day_plan(tasks, user.timezone if user else "UTC")
    
    await PlanRepo.create(user_id, today, plan_text)
    
    added = await GamificationRepo.add_achievement(user_id, "planner")
    if added:
        await GamificationRepo.add_xp(user_id, ACHIEVEMENTS["planner"]["xp"])
    
    await show_plan(event, plan_text)


async def show_plan(event: Message | CallbackQuery, plan_text: str):
    msg = event if isinstance(event, Message) else event.message
    text = f"📅 <b>План на сегодня</b>\n\n{plan_text}"
    
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=get_plan_menu())
        except:
            await event.answer("План готов!")
    else:
        await msg.answer(text, reply_markup=get_plan_menu())


@router.callback_query(F.data == "stats")
@router.message(F.text == "📈 Статистика")
async def show_stats(event: Message | CallbackQuery):
    user_id = event.from_user.id
    msg = event if isinstance(event, Message) else event.message
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    tasks = await TaskRepo.get_user_tasks(user_id, include_completed=True)
    completed = [t for t in tasks if t.status == "completed"]
    
    today_tasks = [t for t in tasks if t.deadline == today.isoformat()]
    today_completed = [t for t in completed if t.completed_at and 
                       t.completed_at.startswith(today.isoformat())]
    
    g = await GamificationRepo.get_or_create(user_id)
    xp_next = xp_to_next_level(g.xp)
    
    text = f"""📊 <b>Твоя статистика</b>

🏆 <b>Уровень {g.level}</b>
💰 XP: {g.xp}
📈 До следующего: {xp_next} XP

🔥 Серия: {g.streak} дней
⚡ Лучшая серия: {g.max_streak} дней
✅ Всего выполнено: {g.total_completed}

📊 <b>Сегодня:</b>
• Выполнено: {len(today_completed)}/{len(today_tasks)} задач
• Продуктивность: {len(today_completed)/max(len(today_tasks),1)*100:.0f}%

📅 <b>За неделю:</b>
• Всего задач: {len([t for t in tasks if t.created_at])}
• Выполнено: {len(completed)}
"""
    
    categories = {}
    for t in completed:
        categories[t.category] = categories.get(t.category, 0) + 1
    
    if categories:
        text += "\n🏆 <b>Топ категории:</b>\n"
        top_cat = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
        for cat, count in top_cat:
            text += f"• {cat}: {count} задач\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏅 Достижения", callback_data="achievements")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=keyboard)
        except:
            await event.answer("Статистика")
    else:
        await msg.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "achievements")
async def show_achievements(callback: CallbackQuery):
    user_id = callback.from_user.id
    g = await GamificationRepo.get_or_create(user_id)
    unlocked = await GamificationRepo.get_achievements(user_id)
    
    text = "🏅 <b>Достижения</b>\n\n"
    
    unlocked_count = 0
    for ach_id, ach in ACHIEVEMENTS.items():
        if ach_id in unlocked:
            text += f"✅ {ach['icon']} {ach['name']}\n   <i>{ach['description']}</i>\n"
            unlocked_count += 1
        else:
            text += f"⬜ {ach['icon']} {ach['name']}\n   <i>{ach['description']}</i>\n"
    
    text += f"\n🔓 Разблокировано: {unlocked_count}/{len(ACHIEVEMENTS)}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="stats")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.answer("Достижения")


@router.message(F.text == "⚙️ Настройки")
@router.callback_query(F.data == "settings")
async def show_settings(event: Message | CallbackQuery):
    msg = event if isinstance(event, Message) else event.message
    user = await UserRepo.get(event.from_user.id)
    
    text = f"""⚙️ <b>Настройки</b>

🌍 Часовой пояс: {user.timezone if user else 'UTC'}
🌅 Утренний план: {user.morning_time if user else '09:00'}
🌙 Вечерний отчёт: {user.evening_time if user else '21:00'}
"""
    
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=get_settings_menu())
        except:
            await event.answer("Настройки")
    else:
        await msg.answer(text, reply_markup=get_settings_menu())
