from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime, timedelta
import json
import aiosqlite
from db import UserRepo, TaskRepo, StatsRepo, GamificationRepo
from db.database import DB_PATH, get_db
from core.config import settings

router = Router()


def is_admin(user_id: int) -> bool:
    return settings.ADMIN_IDS and user_id in settings.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📋 Все задачи", callback_data="admin_tasks"),
            InlineKeyboardButton(text="📈 Аналитика", callback_data="admin_analytics")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="🏆 Топ пользователи", callback_data="admin_top"),
            InlineKeyboardButton(text="💎 Premium", callback_data="admin_premium")
        ]
    ])
    
    await message.answer(
        "🔐 <b>Админ-панель MindFlow AI</b>\n\n"
        "Выберите раздел:",
        reply_markup=kb
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute("SELECT COUNT(*) as cnt FROM users") as cursor:
            row = await cursor.fetchone()
            total_users = row['cnt']
        
        async with db.execute("SELECT COUNT(*) as cnt FROM tasks") as cursor:
            row = await cursor.fetchone()
            total_tasks = row['cnt']
        
        async with db.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = 'completed'") as cursor:
            row = await cursor.fetchone()
            completed_tasks = row['cnt']
        
        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) as cnt FROM tasks WHERE date(created_at) = date('now')"
        ) as cursor:
            row = await cursor.fetchone()
            active_today = row['cnt']
        
        async with db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_premium = 1") as cursor:
            row = await cursor.fetchone()
            premium_users = row['cnt']
    
    await callback.message.edit_text(
        f"📊 <b>Статистика MindFlow AI</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"📋 Всего задач: <b>{total_tasks}</b>\n"
        f"✅ Выполнено: <b>{completed_tasks}</b>\n"
        f"🔥 Активных сегодня: <b>{active_today}</b>\n"
        f"💎 Premium: <b>{premium_users}</b>\n\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, username, is_premium, created_at FROM users ORDER BY created_at DESC LIMIT 20"
        ) as cursor:
            users = await cursor.fetchall()
    
    text = "👥 <b>Последние пользователи:</b>\n\n"
    for u in users:
        username = f"@{u['username']}" if u['username'] else "No username"
        premium = "💎" if u['is_premium'] else ""
        text += f"• {username} {premium}\n  ID: {u['id']}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_tasks")
async def admin_tasks(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT t.id, t.title, t.status, t.priority, u.username FROM tasks t "
            "JOIN users u ON t.user_id = u.id "
            "ORDER BY t.created_at DESC LIMIT 30"
        ) as cursor:
            tasks = await cursor.fetchall()
    
    text = "📋 <b>Последние задачи:</b>\n\n"
    for t in tasks:
        status = "✅" if t['status'] == 'completed' else "⏳"
        priority_colors = {1: "🔴", 2: "🟡", 3: "🟢"}
        p = priority_colors.get(t['priority'], "⚪")
        text += f"{status} {p} {t['title'][:40]}\n  by @{t['username'] or 'user'}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_top")
async def admin_top(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT u.username, u.id, g.level, g.xp, g.streak, g.achievements "
            "FROM gamification g "
            "JOIN users u ON g.user_id = u.id "
            "ORDER BY g.xp DESC LIMIT 10"
        ) as cursor:
            top_users = await cursor.fetchall()
    
    text = "🏆 <b>Топ пользователи по XP:</b>\n\n"
    for i, u in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        username = f"@{u['username']}" if u['username'] else f"User {u['id']}"
        achievements = len(json.loads(u['achievements'] or '[]'))
        text += f"{medal} {username}\n"
        text += f"   ⭐ Ур. {u['level']} | {u['xp']} XP\n"
        text += f"   🔥 Серия: {u['streak']} | 🏅 {achievements}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Для рассылки отправьте команду в формате:\n"
        "<code>/broadcast Ваше сообщение</code>\n\n"
        "Сообщение будет отправлено всем пользователям бота.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


@router.message(Command("broadcast"))
async def broadcast_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("❌ Укажите текст рассылки: /broadcast Текст")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id FROM users") as cursor:
            users = await cursor.fetchall()
    
    success = 0
    failed = 0
    
    status_msg = await message.answer(f"📢 Рассылка начата... (0/{len(users)})")
    
    for u in users:
        try:
            await message.bot.send_message(u['id'], text, parse_mode="HTML")
            success += 1
        except:
            failed += 1
        
        if (success + failed) % 10 == 0:
            await status_msg.edit_text(f"📢 Рассылка... ({success + failed}/{len(users)})")
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Ошибок: {failed}"
    )


@router.callback_query(F.data == "admin_premium")
async def admin_premium(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, username, premium_until FROM users WHERE is_premium = 1"
        ) as cursor:
            premium_users = await cursor.fetchall()
    
    text = f"💎 <b>Premium пользователи ({len(premium_users)}):</b>\n\n"
    for u in premium_users:
        username = f"@{u['username']}" if u['username'] else f"ID: {u['id']}"
        until = u['premium_until'] or "Бессрочно"
        text += f"• {username}\n  До: {until}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить Premium", callback_data="admin_add_premium"),
                InlineKeyboardButton(text="➖ Удалить Premium", callback_data="admin_remove_premium")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_premium")
async def admin_add_premium(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "➕ <b>Добавить Premium</b>\n\n"
        "Отправьте команду:\n"
        "<code>/addpremium USER_ID MONTHS</code>\n\n"
        "Пример: <code>/addpremium 123456789 12</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_premium")]
        ])
    )
    await callback.answer()


@router.message(Command("addpremium"))
async def add_premium(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Формат: /addpremium USER_ID MONTHS")
        return
    
    try:
        user_id = int(args[1])
        months = int(args[2])
        
        until = datetime.now() + timedelta(days=months * 30)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET is_premium = 1, premium_until = ? WHERE id = ?",
                (until.strftime('%Y-%m-%d'), user_id)
            )
            await db.commit()
        
        await message.answer(f"✅ Premium добавлен для {user_id} на {months} мес.")
        
        try:
            await message.bot.send_message(
                user_id,
                f"🎉 <b>Premium активирован!</b>\n\n"
                f"Вы получили MindFlow Pro на {months} месяц(ев)!\n"
                f"Действует до: {until.strftime('%d.%m.%Y')}"
            )
        except:
            pass
            
    except ValueError:
        await message.answer("❌ Неверные аргументы")


@router.message(Command("removepremium"))
async def remove_premium(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Формат: /removepremium USER_ID")
        return
    
    try:
        user_id = int(args[1])
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET is_premium = 0, premium_until = NULL WHERE id = ?",
                (user_id,)
            )
            await db.commit()
        
        await message.answer(f"✅ Premium удалён для {user_id}")
    except ValueError:
        await message.answer("❌ Неверный USER_ID")


@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🤖 Bot Token: {'✅ Установлен' if settings.BOT_TOKEN else '❌ Не установлен'}\n"
        f"🧠 OpenAI Key: {'✅ Установлен' if settings.OPENAI_API_KEY else '❌ Не установлен'}\n"
        f"🌐 WebApp URL: {settings.WEBAPP_URL or '❌ Не установлен'}\n"
        f"👤 Admin IDs: {settings.ADMIN_IDS or '❌ Не установлены'}\n\n"
        "Команды админа:\n"
        "• /admin - Админ-панель\n"
        "• /broadcast - Рассылка\n"
        "• /addpremium USER_ID MONTHS - Выдать Premium\n"
        "• /removepremium USER_ID - Забрать Premium\n"
        "• /userinfo USER_ID - Инфо о пользователе\n"
        "• /userstats - Общая статистика",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_analytics")
async def admin_analytics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute(
            """SELECT date(created_at) as d, COUNT(*) as cnt 
               FROM tasks WHERE created_at >= date('now', '-30 days')
               GROUP BY d ORDER BY d"""
        ) as cursor:
            tasks_by_day = await cursor.fetchall()
        
        async with db.execute(
            """SELECT date(completed_at) as d, COUNT(*) as cnt 
               FROM tasks WHERE completed_at >= date('now', '-30 days') AND status = 'completed'
               GROUP BY d ORDER BY d"""
        ) as cursor:
            completed_by_day = await cursor.fetchall()
        
        async with db.execute(
            "SELECT category, COUNT(*) as cnt FROM tasks GROUP BY category ORDER BY cnt DESC LIMIT 5"
        ) as cursor:
            by_category = await cursor.fetchall()
        
        async with db.execute(
            "SELECT priority, COUNT(*) as cnt FROM tasks GROUP BY priority"
        ) as cursor:
            by_priority = await cursor.fetchall()
        
        async with db.execute(
            """SELECT u.username, COUNT(t.id) as cnt 
               FROM tasks t JOIN users u ON t.user_id = u.id 
               WHERE t.status = 'completed'
               GROUP BY t.user_id ORDER BY cnt DESC LIMIT 5"""
        ) as cursor:
            top_performers = await cursor.fetchall()
    
    text = "📈 <b>Аналитика за 30 дней</b>\n\n"
    
    if tasks_by_day:
        total_created = sum(r['cnt'] for r in tasks_by_day)
        text += f"📝 Создано задач: <b>{total_created}</b>\n"
    
    if completed_by_day:
        total_completed = sum(r['cnt'] for r in completed_by_day)
        text += f"✅ Выполнено задач: <b>{total_completed}</b>\n"
    
    text += "\n📊 <b>По категориям:</b>\n"
    for r in by_category:
        text += f"• {r['category']}: {r['cnt']}\n"
    
    text += "\n⚡ <b>По приоритету:</b>\n"
    priority_names = {1: "🔴 Высокий", 2: "🟡 Средний", 3: "🟢 Низкий"}
    for r in by_priority:
        name = priority_names.get(r['priority'], f"Приоритет {r['priority']}")
        text += f"• {name}: {r['cnt']}\n"
    
    text += "\n🏆 <b>Топ по выполнению:</b>\n"
    for i, r in enumerate(top_performers, 1):
        username = f"@{r['username']}" if r['username'] else f"User"
        text += f"{i}. {username} — {r['cnt']} задач\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_analytics")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📋 Все задачи", callback_data="admin_tasks"),
            InlineKeyboardButton(text="📈 Аналитика", callback_data="admin_analytics")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="🏆 Топ пользователи", callback_data="admin_top"),
            InlineKeyboardButton(text="💎 Premium", callback_data="admin_premium")
        ]
    ])
    
    await callback.message.edit_text(
        "🔐 <b>Админ-панель MindFlow AI</b>\n\n"
        "Выберите раздел:",
        reply_markup=kb
    )
    await callback.answer()


@router.message(Command("userinfo"))
async def userinfo(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Формат: /userinfo USER_ID")
        return
    
    try:
        user_id = int(args[1])
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                user = await cursor.fetchone()
            
            if not user:
                await message.answer("❌ Пользователь не найден")
                return
            
            async with db.execute(
                "SELECT * FROM gamification WHERE user_id = ?", (user_id,)
            ) as cursor:
                gamification = await cursor.fetchone()
            
            async with db.execute(
                "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                tasks_count = row['cnt']
            
            async with db.execute(
                "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND status = 'completed'", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                completed_count = row['cnt']
        
        text = f"👤 <b>Информация о пользователе</b>\n\n"
        text += f"🆔 ID: {user['id']}\n"
        text += f"👤 Username: @{user['username'] or 'не указан'}\n"
        text += f"💎 Premium: {'Да' if user['is_premium'] else 'Нет'}\n"
        text += f"🌍 Часовой пояс: {user['timezone']}\n"
        text += f"🌅 Утро: {user['morning_time']}\n"
        text += f"🌙 Вечер: {user['evening_time']}\n"
        text += f"📅 Создан: {user['created_at']}\n\n"
        
        if gamification:
            text += f"⭐ Уровень: {gamification['level']}\n"
            text += f"🔥 XP: {gamification['xp']}\n"
            text += f"📊 Серия: {gamification['streak']} дней\n"
        
        text += f"\n📋 Задач создано: {tasks_count}\n"
        text += f"✅ Выполнено: {completed_count}"
        
        await message.answer(text)
        
    except ValueError:
        await message.answer("❌ Неверный USER_ID")


@router.message(Command("userstats"))
async def userstats(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute("SELECT COUNT(*) as cnt FROM users") as cursor:
            row = await cursor.fetchone()
            total_users = row['cnt']
        
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE date(created_at) = date('now')"
        ) as cursor:
            row = await cursor.fetchone()
            today_users = row['cnt']
        
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE created_at >= date('now', '-7 days')"
        ) as cursor:
            row = await cursor.fetchone()
            week_users = row['cnt']
        
        async with db.execute("SELECT COUNT(*) as cnt FROM tasks") as cursor:
            row = await cursor.fetchone()
            total_tasks = row['cnt']
        
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE date(created_at) = date('now')"
        ) as cursor:
            row = await cursor.fetchone()
            today_tasks = row['cnt']
        
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE status = 'completed' AND date(completed_at) = date('now')"
        ) as cursor:
            row = await cursor.fetchone()
            completed_today = row['cnt']
    
    await message.answer(
        f"📊 <b>Статистика MindFlow AI</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: {total_users}\n"
        f"• Новых сегодня: {today_users}\n"
        f"• За неделю: {week_users}\n\n"
        f"📋 <b>Задачи:</b>\n"
        f"• Всего: {total_tasks}\n"
        f"• Создано сегодня: {today_tasks}\n"
        f"• Выполнено сегодня: {completed_today}"
    )
