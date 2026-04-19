import json
import logging
from datetime import datetime, date, timedelta
from typing import Any, List, Optional

import aiosqlite

from db.database import get_db
from db.models import User, Task, Plan, Stats, Gamification, Reminder

logger = logging.getLogger(__name__)


def _row_to_user(row: aiosqlite.Row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        timezone=row["timezone"],
        morning_time=row["morning_time"],
        evening_time=row["evening_time"],
        is_premium=row["is_premium"],
        premium_until=row["premium_until"],
        created_at=row["created_at"],
        last_activity=row["last_activity"],
    )


def _row_to_task(row: aiosqlite.Row) -> Task:
    return Task(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        description=row["description"],
        category=row["category"],
        priority=row["priority"],
        deadline=row["deadline"],
        estimated_minutes=row["estimated_minutes"],
        status=row["status"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


def _row_to_gamification(row: aiosqlite.Row) -> Gamification:
    return Gamification(
        user_id=row["user_id"],
        xp=row["xp"],
        level=row["level"],
        streak=row["streak"],
        max_streak=row["max_streak"],
        last_activity=row["last_activity"],
        total_completed=row["total_completed"],
        achievements=row["achievements"],
    )


class UserRepo:
    @staticmethod
    async def create(user_id: int, username: Optional[str] = None) -> tuple[Optional[User], bool]:
        db = get_db()
        try:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
                (user_id, username),
            )
            await db.commit()
            is_new = cursor.rowcount > 0
            return await UserRepo.get(user_id), is_new
        except Exception as e:
            logger.error("Failed to create user %s: %s", user_id, e)
            return None, False

    @staticmethod
    async def get(user_id: int) -> Optional[User]:
        db = get_db()
        try:
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user = _row_to_user(row)
                    if user.is_premium and user.premium_until:
                        try:
                            until_date = datetime.strptime(user.premium_until, "%Y-%m-%d").date()
                            if until_date < datetime.now().date():
                                await UserRepo.revoke_premium(user_id)
                                user.is_premium = 0
                        except (ValueError, TypeError):
                            pass
                    return user
        except Exception as e:
            logger.error("Failed to get user %s: %s", user_id, e)
        return None

    @staticmethod
    async def update_last_activity(user_id: int) -> None:
        db = get_db()
        try:
            now = datetime.now().isoformat()
            await db.execute(
                "UPDATE users SET last_activity = ? WHERE id = ?",
                (now, user_id),
            )
            await db.commit()
        except Exception as e:
            logger.error("Failed to update last_activity for %s: %s", user_id, e)

    @staticmethod
    async def update_settings(
        user_id: int,
        timezone: Optional[str] = None,
        morning_time: Optional[str] = None,
        evening_time: Optional[str] = None,
    ) -> None:
        db = get_db()
        updates: list[str] = []
        values: list[Any] = []
        if timezone is not None:
            updates.append("timezone = ?")
            values.append(timezone)
        if morning_time is not None:
            updates.append("morning_time = ?")
            values.append(morning_time)
        if evening_time is not None:
            updates.append("evening_time = ?")
            values.append(evening_time)
        if not updates:
            return
        values.append(user_id)
        await db.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?", values
        )
        await db.commit()

    @staticmethod
    async def set_premium(user_id: int, until: str) -> None:
        db = get_db()
        await db.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE id = ?",
            (until, user_id),
        )
        await db.commit()

    @staticmethod
    async def revoke_premium(user_id: int) -> None:
        db = get_db()
        await db.execute(
            "UPDATE users SET is_premium = 0, premium_until = NULL WHERE id = ?",
            (user_id,),
        )
        await db.commit()

    @staticmethod
    async def get_all() -> List[User]:
        db = get_db()
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [_row_to_user(row) for row in rows]

    @staticmethod
    async def count() -> int:
        db = get_db()
        async with db.execute("SELECT COUNT(*) as cnt FROM users") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    @staticmethod
    async def count_premium() -> int:
        db = get_db()
        async with db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_premium = 1") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    @staticmethod
    async def count_active_24h() -> int:
        db = get_db()
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE last_activity >= ?", (yesterday,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    @staticmethod
    async def count_new_since(since: str) -> int:
        db = get_db()
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE created_at >= ?", (since,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    @staticmethod
    async def get_all_ids() -> List[int]:
        db = get_db()
        async with db.execute("SELECT id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row["id"] for row in rows]


class TaskRepo:
    @staticmethod
    async def create(
        user_id: int,
        title: str,
        description: Optional[str] = None,
        category: str = "general",
        priority: int = 2,
        deadline: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
    ) -> Optional[Task]:
        db = get_db()
        if deadline == "":
            deadline = None
        try:
            cursor = await db.execute(
                """INSERT INTO tasks
                   (user_id, title, description, category, priority, deadline, estimated_minutes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, title, description, category, priority, deadline, estimated_minutes),
            )
            await db.commit()
            return await TaskRepo.get(cursor.lastrowid)
        except Exception as e:
            logger.error("Failed to create task: %s", e)
            return None

    @staticmethod
    async def get(task_id: int) -> Optional[Task]:
        db = get_db()
        async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            return _row_to_task(row) if row else None

    @staticmethod
    async def get_user_tasks(
        user_id: int,
        status: Optional[str] = None,
        include_completed: bool = False,
    ) -> List[Task]:
        db = get_db()
        query = "SELECT * FROM tasks WHERE user_id = ?"
        params: list[Any] = [user_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        elif not include_completed:
            query += " AND status != 'completed'"
        query += " ORDER BY priority ASC, deadline ASC"
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_task(row) for row in rows]

    @staticmethod
    async def update(task_id: int, **kwargs) -> Optional[Task]:
        db = get_db()
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if not filtered:
            return await TaskRepo.get(task_id)
        updates = [f"{k} = ?" for k in filtered.keys()]
        values = list(filtered.values())
        values.append(task_id)
        await db.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values
        )
        await db.commit()
        return await TaskRepo.get(task_id)

    @staticmethod
    async def complete(task_id: int) -> Optional[Task]:
        db = get_db()
        now = datetime.now().isoformat()
        await db.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        await db.commit()
        return await TaskRepo.get(task_id)

    @staticmethod
    async def uncomplete(task_id: int) -> Optional[Task]:
        db = get_db()
        await db.execute(
            "UPDATE tasks SET status = 'pending', completed_at = NULL WHERE id = ?",
            (task_id,),
        )
        await db.commit()
        return await TaskRepo.get(task_id)

    @staticmethod
    async def delete(task_id: int) -> None:
        db = get_db()
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()


class PlanRepo:
    @staticmethod
    async def create(user_id: int, date_str: str, schedule: str) -> Optional[Plan]:
        db = get_db()
        cursor = await db.execute(
            "INSERT OR REPLACE INTO plans (user_id, date, schedule) VALUES (?, ?, ?)",
            (user_id, date_str, schedule),
        )
        await db.commit()
        return await PlanRepo.get(user_id, date_str)

    @staticmethod
    async def get(user_id: int, date_str: str) -> Optional[Plan]:
        db = get_db()
        async with db.execute(
            "SELECT * FROM plans WHERE user_id = ? AND date = ?",
            (user_id, date_str),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Plan(
                    id=row["id"],
                    user_id=row["user_id"],
                    date=row["date"],
                    schedule=row["schedule"],
                    created_at=row["created_at"],
                )
        return None


class StatsRepo:
    @staticmethod
    async def create_or_update(
        user_id: int,
        date_str: str,
        tasks_completed: Optional[int] = None,
        tasks_total: Optional[int] = None,
        focus_score: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[Stats]:
        db = get_db()
        existing = await StatsRepo.get(user_id, date_str)
        if existing:
            updates: list[str] = []
            values: list[Any] = []
            if tasks_completed is not None:
                updates.append("tasks_completed = ?")
                values.append(tasks_completed)
            if tasks_total is not None:
                updates.append("tasks_total = ?")
                values.append(tasks_total)
            if focus_score is not None:
                updates.append("focus_score = ?")
                values.append(focus_score)
            if notes is not None:
                updates.append("notes = ?")
                values.append(notes)
            if updates:
                values.extend([user_id, date_str])
                await db.execute(
                    f"UPDATE stats SET {', '.join(updates)} WHERE user_id = ? AND date = ?",
                    values,
                )
                await db.commit()
        else:
            await db.execute(
                """INSERT INTO stats
                   (user_id, date, tasks_completed, tasks_total, focus_score, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, date_str, tasks_completed or 0, tasks_total or 0, focus_score, notes),
            )
            await db.commit()
        return await StatsRepo.get(user_id, date_str)

    @staticmethod
    async def get(user_id: int, date_str: str) -> Optional[Stats]:
        db = get_db()
        async with db.execute(
            "SELECT * FROM stats WHERE user_id = ? AND date = ?",
            (user_id, date_str),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Stats(
                    id=row["id"],
                    user_id=row["user_id"],
                    date=row["date"],
                    tasks_completed=row["tasks_completed"],
                    tasks_total=row["tasks_total"],
                    focus_score=row["focus_score"],
                    notes=row["notes"],
                )
        return None

    @staticmethod
    async def get_week_stats(user_id: int) -> List[Stats]:
        db = get_db()
        async with db.execute(
            """SELECT * FROM stats WHERE user_id = ?
               AND date >= date('now', '-7 days')
               ORDER BY date DESC""",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Stats(
                    id=row["id"],
                    user_id=row["user_id"],
                    date=row["date"],
                    tasks_completed=row["tasks_completed"],
                    tasks_total=row["tasks_total"],
                    focus_score=row["focus_score"],
                    notes=row["notes"],
                )
                for row in rows
            ]


class GamificationRepo:
    @staticmethod
    async def get_or_create(user_id: int) -> Gamification:
        db = get_db()
        await db.execute(
            "INSERT OR IGNORE INTO gamification (user_id) VALUES (?)",
            (user_id,),
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM gamification WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return _row_to_gamification(row)
        return Gamification(user_id=user_id)

    @staticmethod
    async def add_xp(user_id: int, xp: int) -> tuple[Gamification, int, bool]:
        from db.models import get_level

        db = get_db()
        await db.execute(
            "UPDATE gamification SET xp = xp + ? WHERE user_id = ?",
            (xp, user_id),
        )
        await db.commit()
        g = await GamificationRepo.get_or_create(user_id)
        new_level = get_level(g.xp)
        if new_level > g.level:
            await db.execute(
                "UPDATE gamification SET level = ? WHERE user_id = ?",
                (new_level, user_id),
            )
            await db.commit()
            g.level = new_level
            return g, new_level, True
        return g, g.level, False

    @staticmethod
    async def update_streak(user_id: int, completed: bool = True) -> int:
        db = get_db()
        g = await GamificationRepo.get_or_create(user_id)
        if not completed:
            return g.streak

        today = date.today().isoformat()
        if g.last_activity:
            try:
                last = datetime.fromisoformat(g.last_activity).date()
                yesterday = (date.today() - timedelta(days=1)).isoformat()
                if last.isoformat() == yesterday:
                    new_streak = g.streak + 1
                elif last.isoformat() == today:
                    new_streak = g.streak
                else:
                    new_streak = 1
            except (ValueError, TypeError):
                new_streak = 1
        else:
            new_streak = 1

        max_streak = max(g.max_streak, new_streak)
        now_iso = datetime.now().isoformat()
        await db.execute(
            """UPDATE gamification
               SET streak = ?, max_streak = ?, last_activity = ?, total_completed = total_completed + 1
               WHERE user_id = ?""",
            (new_streak, max_streak, now_iso, user_id),
        )
        await db.commit()
        return new_streak

    @staticmethod
    async def add_achievement(user_id: int, achievement_id: str) -> bool:
        db = get_db()
        g = await GamificationRepo.get_or_create(user_id)
        try:
            achievements = json.loads(g.achievements or "[]")
        except (json.JSONDecodeError, TypeError):
            achievements = []
        if achievement_id in achievements:
            return False
        achievements.append(achievement_id)
        await db.execute(
            "UPDATE gamification SET achievements = ? WHERE user_id = ?",
            (json.dumps(achievements), user_id),
        )
        await db.commit()
        return True

    @staticmethod
    async def get_achievements(user_id: int) -> list:
        g = await GamificationRepo.get_or_create(user_id)
        try:
            return json.loads(g.achievements or "[]")
        except (json.JSONDecodeError, TypeError):
            return []


class ReminderRepo:
    @staticmethod
    async def create(user_id: int, remind_at: str, task_id: Optional[int] = None) -> Optional[Reminder]:
        db = get_db()
        cursor = await db.execute(
            "INSERT INTO reminders (user_id, task_id, remind_at) VALUES (?, ?, ?)",
            (user_id, task_id, remind_at),
        )
        await db.commit()
        rid = cursor.lastrowid
        return await ReminderRepo.get(rid)

    @staticmethod
    async def get(reminder_id: int) -> Optional[Reminder]:
        db = get_db()
        async with db.execute(
            "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Reminder(
                    id=row["id"],
                    user_id=row["user_id"],
                    task_id=row["task_id"],
                    remind_at=row["remind_at"],
                    sent=row["sent"],
                    created_at=row["created_at"],
                )
        return None

    @staticmethod
    async def get_pending(user_id: Optional[int] = None) -> List[Reminder]:
        db = get_db()
        now = datetime.now().isoformat()
        query = "SELECT * FROM reminders WHERE sent = 0 AND remind_at <= ?"
        params: list[Any] = [now]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                Reminder(
                    id=row["id"],
                    user_id=row["user_id"],
                    task_id=row["task_id"],
                    remind_at=row["remind_at"],
                    sent=row["sent"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    @staticmethod
    async def get_user_reminders(user_id: int) -> List[Reminder]:
        db = get_db()
        async with db.execute(
            "SELECT * FROM reminders WHERE user_id = ? AND sent = 0 ORDER BY remind_at ASC",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Reminder(
                    id=row["id"],
                    user_id=row["user_id"],
                    task_id=row["task_id"],
                    remind_at=row["remind_at"],
                    sent=row["sent"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    @staticmethod
    async def mark_sent(reminder_id: int) -> None:
        db = get_db()
        await db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()

    @staticmethod
    async def delete(reminder_id: int) -> None:
        db = get_db()
        await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await db.commit()

    @staticmethod
    async def delete_for_task(task_id: int) -> None:
        db = get_db()
        await db.execute("DELETE FROM reminders WHERE task_id = ?", (task_id,))
        await db.commit()
