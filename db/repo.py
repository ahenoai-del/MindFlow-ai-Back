import aiosqlite
import json
from datetime import datetime, date, timedelta
from typing import List, Optional
from .database import get_db
from .models import User, Task, Plan, Stats, Gamification, Reminder


class UserRepo:
    @staticmethod
    async def create(user_id: int, username: str = None) -> tuple:
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
                (user_id, username)
            )
            await db.commit()
            
            is_new = cursor.rowcount > 0
            
            if is_new:
                until = datetime.now() + timedelta(days=3)
                await db.execute(
                    "UPDATE users SET is_premium = 1, premium_until = ? WHERE id = ?",
                    (until.strftime('%Y-%m-%d'), user_id)
                )
                await db.commit()
            
            user = await UserRepo.get(user_id)
            return user, is_new
    
    @staticmethod
    async def get(user_id: int) -> Optional[User]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    is_premium = row['is_premium']
                    premium_until = row['premium_until']
                    
                    if is_premium and premium_until:
                        from datetime import datetime
                        try:
                            until_date = datetime.strptime(premium_until, '%Y-%m-%d').date()
                            if until_date < datetime.now().date():
                                is_premium = 0
                                await db.execute(
                                    "UPDATE users SET is_premium = 0 WHERE id = ?",
                                    (user_id,)
                                )
                                await db.commit()
                        except:
                            pass
                    
                    return User(
                        id=row['id'],
                        username=row['username'],
                        timezone=row['timezone'],
                        morning_time=row['morning_time'],
                        evening_time=row['evening_time'],
                        is_premium=is_premium,
                        premium_until=premium_until,
                        created_at=row['created_at']
                    )
        return None
    
    @staticmethod
    async def update_settings(user_id: int, timezone: str = None, 
                              morning_time: str = None, evening_time: str = None):
        async with get_db() as db:
            updates = []
            values = []
            if timezone:
                updates.append("timezone = ?")
                values.append(timezone)
            if morning_time:
                updates.append("morning_time = ?")
                values.append(morning_time)
            if evening_time:
                updates.append("evening_time = ?")
                values.append(evening_time)
            values.append(user_id)
            await db.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await db.commit()
    
    @staticmethod
    async def get_all() -> List[User]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users") as cursor:
                rows = await cursor.fetchall()
                return [User(
                    id=row['id'],
                    username=row['username'],
                    timezone=row['timezone'],
                    morning_time=row['morning_time'],
                    evening_time=row['evening_time'],
                    is_premium=row['is_premium'],
                    premium_until=row['premium_until'],
                    created_at=row['created_at']
                ) for row in rows]


class TaskRepo:
    @staticmethod
    async def create(user_id: int, title: str, description: str = None,
                     category: str = "general", priority: int = 2,
                     deadline: str = None, estimated_minutes: int = None) -> Task:
        async with get_db() as db:
            if deadline == "":
                deadline = None
            cursor = await db.execute(
                """INSERT INTO tasks 
                   (user_id, title, description, category, priority, deadline, estimated_minutes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, title, description, category, priority, deadline, estimated_minutes)
            )
            await db.commit()
            return await TaskRepo.get(cursor.lastrowid)
    
    @staticmethod
    async def get(task_id: int) -> Optional[Task]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Task(
                        id=row['id'],
                        user_id=row['user_id'],
                        title=row['title'],
                        description=row['description'],
                        category=row['category'],
                        priority=row['priority'],
                        deadline=row['deadline'],
                        estimated_minutes=row['estimated_minutes'],
                        status=row['status'],
                        created_at=row['created_at'],
                        completed_at=row['completed_at']
                    )
        return None
    
    @staticmethod
    async def get_user_tasks(user_id: int, status: str = None, 
                             include_completed: bool = False) -> List[Task]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM tasks WHERE user_id = ?"
            params = [user_id]
            
            if status:
                query += " AND status = ?"
                params.append(status)
            elif not include_completed:
                query += " AND status != 'completed'"
            
            query += " ORDER BY priority ASC, deadline ASC"
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [Task(
                    id=row['id'],
                    user_id=row['user_id'],
                    title=row['title'],
                    description=row['description'],
                    category=row['category'],
                    priority=row['priority'],
                    deadline=row['deadline'],
                    estimated_minutes=row['estimated_minutes'],
                    status=row['status'],
                    created_at=row['created_at'],
                    completed_at=row['completed_at']
                ) for row in rows]
    
    @staticmethod
    async def update(task_id: int, **kwargs) -> Optional[Task]:
        async with get_db() as db:
            updates = [f"{k} = ?" for k in kwargs.keys()]
            values = list(kwargs.values())
            values.append(task_id)
            await db.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await db.commit()
            return await TaskRepo.get(task_id)
    
    @staticmethod
    async def complete(task_id: int) -> Optional[Task]:
        async with get_db() as db:
            now = datetime.now().isoformat()
            await db.execute(
                "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
                (now, task_id)
            )
            await db.commit()
            return await TaskRepo.get(task_id)
    
    @staticmethod
    async def uncomplete(task_id: int) -> Optional[Task]:
        async with get_db() as db:
            await db.execute(
                "UPDATE tasks SET status = 'pending', completed_at = NULL WHERE id = ?",
                (task_id,)
            )
            await db.commit()
            return await TaskRepo.get(task_id)
    
    @staticmethod
    async def delete(task_id: int):
        async with get_db() as db:
            await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()


class PlanRepo:
    @staticmethod
    async def create(user_id: int, date_str: str, schedule: str) -> Plan:
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT OR REPLACE INTO plans (user_id, date, schedule) VALUES (?, ?, ?)",
                (user_id, date_str, schedule)
            )
            await db.commit()
            return await PlanRepo.get(user_id, date_str)
    
    @staticmethod
    async def get(user_id: int, date_str: str) -> Optional[Plan]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM plans WHERE user_id = ? AND date = ?",
                (user_id, date_str)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Plan(
                        id=row['id'],
                        user_id=row['user_id'],
                        date=row['date'],
                        schedule=row['schedule'],
                        created_at=row['created_at']
                    )
        return None


class StatsRepo:
    @staticmethod
    async def create_or_update(user_id: int, date_str: str, 
                               tasks_completed: int = None, tasks_total: int = None,
                               focus_score: float = None, notes: str = None) -> Stats:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            existing = await StatsRepo.get(user_id, date_str)
            if existing:
                updates = []
                values = []
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
                values.extend([user_id, date_str])
                await db.execute(
                    f"UPDATE stats SET {', '.join(updates)} WHERE user_id = ? AND date = ?",
                    values
                )
            else:
                await db.execute(
                    """INSERT INTO stats 
                       (user_id, date, tasks_completed, tasks_total, focus_score, notes)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, date_str, tasks_completed or 0, tasks_total or 0, 
                     focus_score, notes)
                )
            await db.commit()
            return await StatsRepo.get(user_id, date_str)
    
    @staticmethod
    async def get(user_id: int, date_str: str) -> Optional[Stats]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM stats WHERE user_id = ? AND date = ?",
                (user_id, date_str)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Stats(
                        id=row['id'],
                        user_id=row['user_id'],
                        date=row['date'],
                        tasks_completed=row['tasks_completed'],
                        tasks_total=row['tasks_total'],
                        focus_score=row['focus_score'],
                        notes=row['notes']
                    )
        return None
    
    @staticmethod
    async def get_week_stats(user_id: int) -> List[Stats]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM stats WHERE user_id = ? 
                   AND date >= date('now', '-7 days') 
                   ORDER BY date DESC""",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Stats(
                    id=row['id'],
                    user_id=row['user_id'],
                    date=row['date'],
                    tasks_completed=row['tasks_completed'],
                    tasks_total=row['tasks_total'],
                    focus_score=row['focus_score'],
                    notes=row['notes']
                ) for row in rows]


class GamificationRepo:
    @staticmethod
    async def get_or_create(user_id: int) -> Gamification:
        async with get_db() as db:
            await db.execute(
                "INSERT OR IGNORE INTO gamification (user_id) VALUES (?)",
                (user_id,)
            )
            await db.commit()
            
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM gamification WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Gamification(
                        user_id=row['user_id'],
                        xp=row['xp'],
                        level=row['level'],
                        streak=row['streak'],
                        max_streak=row['max_streak'],
                        last_activity=row['last_activity'],
                        total_completed=row['total_completed'],
                        achievements=row['achievements']
                    )
        return Gamification(user_id=user_id)
    
    @staticmethod
    async def add_xp(user_id: int, xp: int) -> tuple:
        from .models import get_level, LEVEL_XP
        async with get_db() as db:
            await db.execute(
                "UPDATE gamification SET xp = xp + ? WHERE user_id = ?",
                (xp, user_id)
            )
            await db.commit()
            
            g = await GamificationRepo.get_or_create(user_id)
            new_level = get_level(g.xp)
            
            if new_level > g.level:
                await db.execute(
                    "UPDATE gamification SET level = ? WHERE user_id = ?",
                    (new_level, user_id)
                )
                await db.commit()
                return g, new_level, True
            return g, g.level, False
    
    @staticmethod
    async def update_streak(user_id: int, completed: bool = True) -> int:
        from datetime import datetime, timedelta
        async with get_db() as db:
            g = await GamificationRepo.get_or_create(user_id)
            today = date.today().isoformat()
            
            if completed:
                if g.last_activity:
                    last = datetime.fromisoformat(g.last_activity).date()
                    yesterday = (date.today() - timedelta(days=1)).isoformat()
                    
                    if last.isoformat() == yesterday:
                        new_streak = g.streak + 1
                    elif last.isoformat() == today:
                        new_streak = g.streak
                    else:
                        new_streak = 1
                else:
                    new_streak = 1
                
                max_streak = max(g.max_streak, new_streak)
                
                await db.execute(
                    """UPDATE gamification 
                       SET streak = ?, max_streak = ?, last_activity = ?, total_completed = total_completed + 1
                       WHERE user_id = ?""",
                    (new_streak, max_streak, datetime.now().isoformat(), user_id)
                )
                await db.commit()
                return new_streak
            return g.streak
    
    @staticmethod
    async def add_achievement(user_id: int, achievement_id: str) -> bool:
        async with get_db() as db:
            g = await GamificationRepo.get_or_create(user_id)
            achievements = json.loads(g.achievements or '[]')
            
            if achievement_id not in achievements:
                achievements.append(achievement_id)
                await db.execute(
                    "UPDATE gamification SET achievements = ? WHERE user_id = ?",
                    (json.dumps(achievements), user_id)
                )
                await db.commit()
                return True
            return False
    
    @staticmethod
    async def get_achievements(user_id: int) -> list:
        g = await GamificationRepo.get_or_create(user_id)
        return json.loads(g.achievements or '[]')


class ReminderRepo:
    @staticmethod
    async def create(user_id: int, remind_at: str, task_id: int = None) -> Reminder:
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT INTO reminders (user_id, task_id, remind_at) VALUES (?, ?, ?)",
                (user_id, task_id, remind_at)
            )
            await db.commit()
            return await ReminderRepo.get(cursor.lastrowid)
    
    @staticmethod
    async def get(reminder_id: int) -> Optional[Reminder]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Reminder(
                        id=row['id'],
                        user_id=row['user_id'],
                        task_id=row['task_id'],
                        remind_at=row['remind_at'],
                        sent=row['sent'],
                        created_at=row['created_at']
                    )
        return None
    
    @staticmethod
    async def get_pending(user_id: int = None) -> List[Reminder]:
        from datetime import datetime
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            now = datetime.now().isoformat()
            query = "SELECT * FROM reminders WHERE sent = 0 AND remind_at <= ?"
            params = [now]
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [Reminder(
                    id=row['id'],
                    user_id=row['user_id'],
                    task_id=row['task_id'],
                    remind_at=row['remind_at'],
                    sent=row['sent'],
                    created_at=row['created_at']
                ) for row in rows]
    
    @staticmethod
    async def get_user_reminders(user_id: int) -> List[Reminder]:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM reminders WHERE user_id = ? AND sent = 0 ORDER BY remind_at ASC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Reminder(
                    id=row['id'],
                    user_id=row['user_id'],
                    task_id=row['task_id'],
                    remind_at=row['remind_at'],
                    sent=row['sent'],
                    created_at=row['created_at']
                ) for row in rows]
    
    @staticmethod
    async def mark_sent(reminder_id: int):
        async with get_db() as db:
            await db.execute(
                "UPDATE reminders SET sent = 1 WHERE id = ?",
                (reminder_id,)
            )
            await db.commit()
    
    @staticmethod
    async def delete(reminder_id: int):
        async with get_db() as db:
            await db.execute(
                "DELETE FROM reminders WHERE id = ?",
                (reminder_id,)
            )
            await db.commit()
    
    @staticmethod
    async def delete_for_task(task_id: int):
        async with get_db() as db:
            await db.execute(
                "DELETE FROM reminders WHERE task_id = ?",
                (task_id,)
            )
            await db.commit()
