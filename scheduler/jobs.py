from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import date, datetime
from aiogram import Bot
from db import UserRepo, TaskRepo, PlanRepo, ReminderRepo
from ai.scheduler import generate_day_plan, generate_evening_summary

scheduler = AsyncIOScheduler()


def setup_scheduler(bot: Bot):
    scheduler.add_job(
        send_scheduled_messages,
        IntervalTrigger(minutes=5),
        args=[bot],
        id="scheduled_messages"
    )
    
    scheduler.add_job(
        send_reminders,
        IntervalTrigger(minutes=1),
        args=[bot],
        id="send_reminders"
    )
    
    scheduler.start()


async def send_scheduled_messages(bot: Bot):
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today = date.today().isoformat()
    
    users = await UserRepo.get_all()
    
    for user in users:
        try:
            if user.morning_time == current_time:
                tasks = await TaskRepo.get_user_tasks(user.id)
                if tasks:
                    plan = await PlanRepo.get(user.id, today)
                    
                    if not plan:
                        plan_text = await generate_day_plan(tasks, user.timezone)
                        await PlanRepo.create(user.id, today, plan_text)
                    else:
                        plan_text = plan.schedule
                    
                    await bot.send_message(
                        user.id,
                        f"🌅 <b>Доброе утро!</b>\n\n"
                        f"📅 Вот твой план на сегодня:\n\n{plan_text}"
                    )
            
            if user.evening_time == current_time:
                tasks = await TaskRepo.get_user_tasks(user.id, include_completed=True)
                if tasks:
                    summary = await generate_evening_summary(tasks)
                    await bot.send_message(user.id, summary)
                    
        except Exception as e:
            print(f"Failed to send scheduled message to {user.id}: {e}")


async def send_morning_plan(bot: Bot):
    pass


async def send_evening_summary(bot: Bot):
    pass


async def send_reminders(bot: Bot):
    reminders = await ReminderRepo.get_pending()
    
    for reminder in reminders:
        try:
            task = None
            if reminder.task_id:
                task = await TaskRepo.get(reminder.task_id)
            
            if task:
                text = f"⏰ <b>Напоминание!</b>\n\n📋 {task.title}"
                if task.description:
                    text += f"\n📝 {task.description}"
            else:
                text = "⏰ <b>Напоминание!</b>"
            
            await bot.send_message(reminder.user_id, text)
            await ReminderRepo.mark_sent(reminder.id)
            
        except Exception as e:
            print(f"Failed to send reminder {reminder.id}: {e}")
