from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Задачи")
    builder.button(text="➕ Новая задача")
    builder.button(text="📊 План на сегодня")
    builder.button(text="📱 Приложение")
    builder.button(text="⚙️ Настройки")
    builder.button(text="📈 Статистика")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_tasks_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить задачу", callback_data="task_add")
    builder.button(text="📝 Список задач", callback_data="task_list")
    builder.button(text="✅ Выполненные", callback_data="task_completed")
    builder.button(text="🔙 Назад", callback_data="back_main")
    builder.adjust(2)
    return builder.as_markup()


def get_task_actions(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнить", callback_data=f"task_done_{task_id}")
    builder.button(text="✏️ Изменить", callback_data=f"task_edit_{task_id}")
    builder.button(text="🗑 Удалить", callback_data=f"task_del_{task_id}")
    builder.button(text="🔙 К списку", callback_data="task_list")
    builder.adjust(2)
    return builder.as_markup()


def get_priority_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔴 Высокий", callback_data="priority_1")
    builder.button(text="🟡 Средний", callback_data="priority_2")
    builder.button(text="🟢 Низкий", callback_data="priority_3")
    builder.adjust(3)
    return builder.as_markup()


def get_category_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    categories = [
        ("💼 Работа", "work"),
        ("🏠 Дом", "home"),
        ("📚 Учёба", "study"),
        ("💪 Спорт", "sport"),
        ("🎯 Прочее", "other")
    ]
    for text, cat in categories:
        builder.button(text=text, callback_data=f"category_{cat}")
    builder.adjust(3)
    return builder.as_markup()


def get_plan_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Сгенерировать план", callback_data="plan_generate")
    builder.button(text="📅 Изменить расписание", callback_data="plan_schedule")
    builder.button(text="🔙 Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def get_settings_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌍 Часовой пояс", callback_data="settings_timezone")
    builder.button(text="🌅 Утреннее время", callback_data="settings_morning")
    builder.button(text="🌙 Вечернее время", callback_data="settings_evening")
    builder.button(text="🔙 Назад", callback_data="back_main")
    builder.adjust(2)
    return builder.as_markup()


def get_back_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back_main")
    return builder.as_markup()


def get_webapp_button(webapp_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📱 Открыть приложение", web_app={"url": webapp_url})
    return builder.as_markup()
