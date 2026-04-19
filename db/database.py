import aiosqlite
import logging
from typing import Optional
from contextlib import asynccontextmanager

from config.settings import settings

logger = logging.getLogger(__name__)

_db: Optional[aiosqlite.Connection] = None


async def init_db() -> None:
    global _db
    _db = await aiosqlite.connect(settings.DB_PATH)
    _db.row_factory = aiosqlite.Row

    await _db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            timezone TEXT DEFAULT 'UTC',
            morning_time TEXT DEFAULT '09:00',
            evening_time TEXT DEFAULT '21:00',
            is_premium INTEGER DEFAULT 0,
            premium_until TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'general',
            priority INTEGER DEFAULT 2,
            deadline TEXT,
            estimated_minutes INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            schedule TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            tasks_completed INTEGER DEFAULT 0,
            tasks_total INTEGER DEFAULT 0,
            focus_score REAL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS gamification (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            streak INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0,
            last_activity TEXT,
            total_completed INTEGER DEFAULT 0,
            achievements TEXT DEFAULT '[]',
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER,
            remind_at TEXT NOT NULL,
            sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_premium ON users(is_premium);
        CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);
        CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
        CREATE INDEX IF NOT EXISTS idx_reminders_pending ON reminders(sent, remind_at);
        CREATE INDEX IF NOT EXISTS idx_gamification_user ON gamification(user_id);
    """)
    await _db.commit()
    logger.info("Database initialized")


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


@asynccontextmanager
async def db_connection():
    conn = get_db()
    try:
        yield conn
    except Exception:
        await conn.rollback()
        raise
