from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from db import TaskRepo, GamificationRepo, ACHIEVEMENTS
from ..keyboards.kb import (
    get_tasks_menu, get_task_actions, get_priority_keyboard,
    get_category_keyboard, get_back_button
)
from ai.parser import parse_task_text

router = Router()


class TaskStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_deadline = State()
    waiting_priority = State()
    waiting_category = State()


@router.message(F.text == "📋 Задачи")
async def show_tasks_menu(message: Message):
    await message.answer("📋 Управление задачами", reply_markup=get_tasks_menu())


@router.message(F.text == "➕ Новая задача")
async def new_task_prompt(message: Message, state: FSMContext):
    await message.answer(
        "📝 Напиши задачу в свободной форме:\n\n"
        "Примеры:\n"
        "• <b>завтра встреча в 15:00</b> - поставит дедлайн\n"
        "• <b>срочно позвонить клиенту</b> - высокий приоритет\n"
        "• <b>купить продукты</b> - создаст сразу\n\n"
        "Или нажми /cancel для отмены",
        reply_markup=get_back_button()
    )
    await state.set_state(TaskStates.waiting_title)


@router.message(TaskStates.waiting_title)
async def process_task_title(message: Message, state: FSMContext):
    title = message.text.strip()
    
    if title.lower() in ['отмена', 'cancel', '/cancel']:
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=get_tasks_menu())
        return
    
    parsed = await parse_task_text(title)
    
    task = await TaskRepo.create(
        user_id=message.from_user.id,
        title=parsed.get('title', title),
        description=parsed.get('description'),
        category=parsed.get('category', 'general'),
        priority=parsed.get('priority', 2),
        deadline=parsed.get('deadline')
    )
    
    g, level, level_up = await GamificationRepo.add_xp(message.from_user.id, 10)
    
    text = f"✅ Задача создана: <b>{task.title}</b>\n"
    if task.deadline:
        text += f"📅 Дедлайн: {task.deadline}\n"
    if level_up:
        text += f"\n🎉 Уровень повышен! Теперь ты на уровне {level}!"
    
    await state.clear()
    await message.answer(text, reply_markup=get_tasks_menu())


@router.callback_query(F.data == "task_list")
async def show_task_list(callback: CallbackQuery):
    tasks = await TaskRepo.get_user_tasks(callback.from_user.id)
    
    if not tasks:
        try:
            await callback.message.edit_text(
                "📭 У тебя пока нет задач. Добавь первую!",
                reply_markup=get_tasks_menu()
            )
        except:
            pass
        return
    
    text = "📋 <b>Твои задачи:</b>\n\n"
    for task in tasks:
        priority_emoji = {1: "🔴", 2: "🟡", 3: "🟢"}.get(task.priority, "⚪")
        deadline = f" 📅 {task.deadline}" if task.deadline else ""
        text += f"{priority_emoji} <b>{task.title}</b>{deadline}\n"
        text += f"   📁 {task.category} | ID: {task.id}\n"
    
    try:
        await callback.message.edit_text(text, reply_markup=get_tasks_actions_list(tasks))
    except:
        await callback.answer("Список не изменился")


def get_tasks_actions_list(tasks) -> InlineKeyboardMarkup:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for task in tasks[:10]:
        buttons.append([
            InlineKeyboardButton(
                text=f"{task.title[:30]}",
                callback_data=f"task_view_{task.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("task_view_"))
async def view_task(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[-1])
    task = await TaskRepo.get(task_id)
    
    if not task:
        await callback.answer("Задача не найдена")
        return
    
    priority_names = {1: "Высокий", 2: "Средний", 3: "Низкий"}
    text = f"""📋 <b>{task.title}</b>

📝 Описание: {task.description or 'не указано'}
📁 Категория: {task.category}
⚡ Приоритет: {priority_names.get(task.priority, 'Средний')}
📅 Дедлайн: {task.deadline or 'не указан'}
⏱ Оценка: {f'{task.estimated_minutes} мин' if task.estimated_minutes else 'не указана'}
"""
    
    await callback.message.edit_text(text, reply_markup=get_task_actions(task_id))


@router.callback_query(F.data == "task_add")
async def add_task_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✍️ Напиши задачу в свободной форме.\n\n"
        "Примеры:\n"
        "• «Завтра в 15:00 встреча с клиентом»\n"
        "• «До пятницы подготовить отчёт по проекту»\n"
        "• «Позвонить маме вечером»\n\n"
        "AI автоматически определит дату и приоритет.\n\n"
        "Или /cancel для отмены.",
        reply_markup=get_back_button()
    )
    await state.set_state(TaskStates.waiting_title)


@router.callback_query(F.data.startswith("task_done_"))
async def complete_task(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[-1])
    task = await TaskRepo.complete(task_id)
    
    if task:
        user_id = callback.from_user.id
        
        xp_earned = 10
        if task.priority == 1:
            xp_earned = 20
        elif task.priority == 3:
            xp_earned = 5
        
        g, new_level, leveled_up = await GamificationRepo.add_xp(user_id, xp_earned)
        streak = await GamificationRepo.update_streak(user_id)
        
        achievements_msg = ""
        if g.total_completed == 0:
            await GamificationRepo.add_achievement(user_id, "first_complete")
            achievements_msg = f"\n🏆 Достижение: {ACHIEVEMENTS['first_complete']['name']}!"
        
        if streak >= 3 and streak % 3 == 0:
            ach_key = f"streak_{streak}" if streak <= 30 else "streak_7"
            if ach_key in ACHIEVEMENTS:
                added = await GamificationRepo.add_achievement(user_id, ach_key)
                if added:
                    achievements_msg += f"\n🔥 {streak} дней подряд! +{ACHIEVEMENTS[ach_key]['xp']} XP"
        
        if g.total_completed + 1 in [10, 50, 100]:
            ach_key = f"tasks_{g.total_completed + 1}"
            added = await GamificationRepo.add_achievement(user_id, ach_key)
            if added:
                achievements_msg += f"\n🏆 Достижение: {ACHIEVEMENTS[ach_key]['name']}!"
        
        hour = datetime.now().hour
        if hour < 9:
            added = await GamificationRepo.add_achievement(user_id, "early_bird")
            if added:
                achievements_msg += "\n🌅 Ранняя пташка!"
        elif hour >= 23:
            added = await GamificationRepo.add_achievement(user_id, "night_owl")
            if added:
                achievements_msg += "\n🦉 Ночная сова!"
        
        msg = f"✅ Задача выполнена!\n💰 +{xp_earned} XP"
        
        if leveled_up:
            msg += f"\n\n🎉 УРОВЕНЬ {new_level}!"
        
        if streak > 1:
            msg += f"\n🔥 Серия: {streak} дней"
        
        msg += achievements_msg
        
        await callback.answer(msg, show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("Задача не найдена")


@router.callback_query(F.data.startswith("task_del_"))
async def delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[-1])
    await TaskRepo.delete(task_id)
    await callback.answer("🗑 Задача удалена")
    await callback.message.delete()


class TaskEditStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_deadline = State()


@router.callback_query(F.data.startswith("task_edit_"))
async def edit_task_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[-1])
    task = await TaskRepo.get(task_id)
    
    if not task:
        await callback.answer("Задача не найдена")
        return
    
    await state.update_data(task_id=task_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Название", callback_data=f"edit_field_title_{task_id}")],
        [InlineKeyboardButton(text="📋 Описание", callback_data=f"edit_field_desc_{task_id}")],
        [InlineKeyboardButton(text="📅 Дедлайн", callback_data=f"edit_field_deadline_{task_id}")],
        [InlineKeyboardButton(text="⚡ Приоритет", callback_data=f"edit_field_priority_{task_id}")],
        [InlineKeyboardButton(text="📁 Категория", callback_data=f"edit_field_category_{task_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"task_view_{task_id}")]
    ])
    
    try:
        await callback.message.edit_text(
            f"✏️ <b>Редактирование задачи</b>\n\n"
            f"📋 {task.title}\n\n"
            f"Выберите что изменить:",
            reply_markup=keyboard
        )
    except:
        pass


@router.callback_query(F.data.startswith("edit_field_title_"))
async def edit_field_title(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[-1])
    await state.update_data(task_id=task_id, field="title")
    await state.set_state(TaskEditStates.waiting_title)
    
    task = await TaskRepo.get(task_id)
    await callback.message.edit_text(
        f"📝 <b>Изменение названия</b>\n\n"
        f"Текущее: {task.title}\n\n"
        f"Напиши новое название:",
        reply_markup=get_back_button()
    )


@router.callback_query(F.data.startswith("edit_field_desc_"))
async def edit_field_desc(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[-1])
    await state.update_data(task_id=task_id, field="description")
    await state.set_state(TaskEditStates.waiting_description)
    
    task = await TaskRepo.get(task_id)
    await callback.message.edit_text(
        f"📋 <b>Изменение описания</b>\n\n"
        f"Текущее: {task.description or 'не указано'}\n\n"
        f"Напиши новое описание или /clear чтобы очистить:",
        reply_markup=get_back_button()
    )


@router.callback_query(F.data.startswith("edit_field_deadline_"))
async def edit_field_deadline(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[-1])
    await state.update_data(task_id=task_id, field="deadline")
    await state.set_state(TaskEditStates.waiting_deadline)
    
    task = await TaskRepo.get(task_id)
    await callback.message.edit_text(
        f"📅 <b>Изменение дедлайна</b>\n\n"
        f"Текущий: {task.deadline or 'не указан'}\n\n"
        f"Напиши дату в формате ГГГГ-ММ-ДД или /clear чтобы убрать:",
        reply_markup=get_back_button()
    )


@router.callback_query(F.data.startswith("edit_field_priority_"))
async def edit_field_priority(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[-1])
    task = await TaskRepo.get(task_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Высокий", callback_data=f"set_priority_1_{task_id}")],
        [InlineKeyboardButton(text="🟡 Средний", callback_data=f"set_priority_2_{task_id}")],
        [InlineKeyboardButton(text="🟢 Низкий", callback_data=f"set_priority_3_{task_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"task_edit_{task_id}")]
    ])
    
    await callback.message.edit_text(
        f"⚡ <b>Изменение приоритета</b>\n\n"
        f"Текущий: {['', 'Высокий', 'Средний', 'Низкий'][task.priority]}\n\n"
        f"Выберите новый приоритет:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("set_priority_"))
async def set_priority(callback: CallbackQuery):
    parts = callback.data.split("_")
    priority = int(parts[2])
    task_id = int(parts[3])
    
    await TaskRepo.update(task_id, priority=priority)
    await callback.answer("✅ Приоритет изменен")
    
    task = await TaskRepo.get(task_id)
    await view_task_callback(callback, task_id)


@router.callback_query(F.data.startswith("edit_field_category_"))
async def edit_field_category(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[-1])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Работа", callback_data=f"set_category_work_{task_id}")],
        [InlineKeyboardButton(text="🏠 Дом", callback_data=f"set_category_home_{task_id}")],
        [InlineKeyboardButton(text="📚 Учёба", callback_data=f"set_category_study_{task_id}")],
        [InlineKeyboardButton(text="💪 Спорт", callback_data=f"set_category_sport_{task_id}")],
        [InlineKeyboardButton(text="🎯 Прочее", callback_data=f"set_category_other_{task_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"task_edit_{task_id}")]
    ])
    
    task = await TaskRepo.get(task_id)
    await callback.message.edit_text(
        f"📁 <b>Изменение категории</b>\n\n"
        f"Текущая: {task.category}\n\n"
        f"Выберите новую категорию:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("set_category_"))
async def set_category(callback: CallbackQuery):
    parts = callback.data.split("_")
    category = parts[2]
    task_id = int(parts[3])
    
    await TaskRepo.update(task_id, category=category)
    await callback.answer("✅ Категория изменена")
    
    await view_task_callback(callback, task_id)


@router.message(TaskEditStates.waiting_title)
async def process_edit_title(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["task_id"]
    
    await TaskRepo.update(task_id, title=message.text)
    await state.clear()
    
    await message.answer(f"✅ Название изменено на: {message.text}")
    await show_task_by_id(message, task_id)


@router.message(TaskEditStates.waiting_description)
async def process_edit_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["task_id"]
    
    new_desc = None if message.text == "/clear" else message.text
    await TaskRepo.update(task_id, description=new_desc)
    await state.clear()
    
    await message.answer("✅ Описание изменено")
    await show_task_by_id(message, task_id)


@router.message(TaskEditStates.waiting_deadline)
async def process_edit_deadline(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["task_id"]
    
    new_deadline = None if message.text == "/clear" else message.text
    await TaskRepo.update(task_id, deadline=new_deadline)
    await state.clear()
    
    await message.answer(f"✅ Дедлайн изменен на: {new_deadline or 'не указан'}")
    await show_task_by_id(message, task_id)


async def view_task_callback(callback: CallbackQuery, task_id: int):
    task = await TaskRepo.get(task_id)
    if not task:
        await callback.answer("Задача не найдена")
        return
    
    priority_names = {1: "Высокий", 2: "Средний", 3: "Низкий"}
    text = f"""📋 <b>{task.title}</b>

📝 Описание: {task.description or 'не указано'}
📁 Категория: {task.category}
⚡ Приоритет: {priority_names.get(task.priority, 'Средний')}
📅 Дедлайн: {task.deadline or 'не указан'}
⏱ Оценка: {f'{task.estimated_minutes} мин' if task.estimated_minutes else 'не указана'}
"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_task_actions(task_id))
    except:
        pass


async def show_task_by_id(message: Message, task_id: int):
    task = await TaskRepo.get(task_id)
    if not task:
        return
    
    priority_names = {1: "Высокий", 2: "Средний", 3: "Низкий"}
    text = f"""📋 <b>{task.title}</b>

📝 Описание: {task.description or 'не указано'}
📁 Категория: {task.category}
⚡ Приоритет: {priority_names.get(task.priority, 'Средний')}
📅 Дедлайн: {task.deadline or 'не указан'}
"""
    
    await message.answer(text, reply_markup=get_task_actions(task_id))


@router.callback_query(F.data == "task_completed")
async def show_completed_tasks(callback: CallbackQuery):
    tasks = await TaskRepo.get_user_tasks(callback.from_user.id, include_completed=True)
    tasks = [t for t in tasks if t.status == "completed"]
    
    if not tasks:
        await callback.answer("Нет выполненных задач")
        return
    
    text = "✅ <b>Выполненные задачи:</b>\n\n"
    for task in tasks[-10:]:
        text += f"✓ {task.title}\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_button())
