from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class User:
    id: int
    username: Optional[str]
    timezone: str = "UTC"
    morning_time: str = "09:00"
    evening_time: str = "21:00"
    is_premium: int = 0
    premium_until: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Task:
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    category: str = "general"
    priority: int = 2
    deadline: Optional[str] = None
    estimated_minutes: Optional[int] = None
    status: str = "pending"
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Plan:
    id: int
    user_id: int
    date: str
    schedule: str
    created_at: Optional[datetime] = None


@dataclass
class Stats:
    id: int
    user_id: int
    date: str
    tasks_completed: int = 0
    tasks_total: int = 0
    focus_score: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class Gamification:
    user_id: int
    xp: int = 0
    level: int = 1
    streak: int = 0
    max_streak: int = 0
    last_activity: Optional[str] = None
    total_completed: int = 0
    achievements: Optional[str] = "[]"


@dataclass
class Reminder:
    id: int
    user_id: int
    task_id: Optional[int]
    remind_at: str
    sent: int = 0
    created_at: Optional[datetime] = None


ACHIEVEMENTS = {
    "first_task": {"name": "Начало пути", "description": "Создать первую задачу", "icon": "🎯", "xp": 10},
    "first_complete": {"name": "Первый шаг", "description": "Выполнить первую задачу", "icon": "✅", "xp": 15},
    "streak_3": {"name": "На волне", "description": "3 дня подряд", "icon": "🔥", "xp": 30},
    "streak_7": {"name": "Неделя силы", "description": "7 дней подряд", "icon": "⚡", "xp": 70},
    "streak_30": {"name": "Месяц мастерства", "description": "30 дней подряд", "icon": "🏆", "xp": 300},
    "tasks_10": {"name": "Десятка", "description": "10 выполненных задач", "icon": "🔟", "xp": 50},
    "tasks_50": {"name": "Пол сотни", "description": "50 выполненных задач", "icon": "💪", "xp": 200},
    "tasks_100": {"name": "Сотня", "description": "100 выполненных задач", "icon": "💯", "xp": 500},
    "early_bird": {"name": "Ранняя пташка", "description": "Выполнить задачу до 9 утра", "icon": "🌅", "xp": 20},
    "night_owl": {"name": "Ночная сова", "description": "Выполнить задачу после 23", "icon": "🦉", "xp": 20},
    "planner": {"name": "Планировщик", "description": "Создать план на день", "icon": "📅", "xp": 25},
    "ai_user": {"name": "AI-энтузиаст", "description": "Использовать AI для 10 задач", "icon": "🤖", "xp": 40},
}

LEVEL_XP = {
    1: 0,
    2: 100,
    3: 250,
    4: 500,
    5: 1000,
    6: 2000,
    7: 4000,
    8: 8000,
    9: 15000,
    10: 30000,
}


def get_level(xp: int) -> int:
    for level in reversed(range(1, 11)):
        if xp >= LEVEL_XP.get(level, 0):
            return level
    return 1


def xp_to_next_level(xp: int) -> int:
    current_level = get_level(xp)
    if current_level >= 10:
        return 0
    next_level_xp = LEVEL_XP.get(current_level + 1, 0)
    return next_level_xp - xp
