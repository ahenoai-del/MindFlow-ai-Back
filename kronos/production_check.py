import asyncio
import aiosqlite
import os
import sys

print("=" * 50)
print("MINDFLOW PRE-PRODUCTION CHECK")
print("=" * 50)

errors = []
warnings = []

# 1. Files
print("\n[1] CHECKING FILES...")
required_files = [
    'main.py', '.env', 'requirements.txt',
    'db/__init__.py', 'db/database.py', 'db/models.py', 'db/repo.py',
    'bot/__init__.py', 'bot/handlers/__init__.py',
    'bot/handlers/start.py', 'bot/handlers/tasks.py',
    'bot/handlers/payments.py', 'bot/handlers/webapp_handler.py',
    'bot/keyboards/kb.py',
    'core/__init__.py', 'core/config.py',
    'ai/parser.py', 'ai/scheduler.py',
    'scheduler/jobs.py',
    'webapp/index.html'
]

for f in required_files:
    if os.path.exists(f'C:/kronos/{f}'):
        print(f"  [OK] {f}")
    else:
        print(f"  [ERROR] {f} - MISSING")
        errors.append(f"Missing file: {f}")

# 2. Imports
print("\n[2] CHECKING IMPORTS...")
try:
    from aiogram import Bot, Dispatcher
    print("  [OK] aiogram")
except Exception as e:
    print(f"  [ERROR] aiogram: {e}")
    errors.append("aiogram import failed")

try:
    from db import TaskRepo, UserRepo, GamificationRepo, ReminderRepo
    print("  [OK] db modules")
except Exception as e:
    print(f"  [ERROR] db: {e}")
    errors.append("db import failed")

try:
    from core.config import settings
    print("  [OK] config")
except Exception as e:
    print(f"  [ERROR] config: {e}")
    errors.append("config import failed")

try:
    from bot.handlers import start, tasks, planning, webapp_handler, admin, payments
    print("  [OK] handlers")
except Exception as e:
    print(f"  [ERROR] handlers: {e}")
    errors.append("handlers import failed")

try:
    from ai.parser import parse_task_text
    print("  [OK] ai.parser")
except Exception as e:
    print(f"  [ERROR] ai.parser: {e}")
    errors.append("ai.parser import failed")

# 3. Config
print("\n[3] CHECKING CONFIG...")
try:
    from core.config import settings
    
    if settings.BOT_TOKEN and len(settings.BOT_TOKEN) > 20:
        print(f"  [OK] BOT_TOKEN set")
    else:
        print("  [ERROR] BOT_TOKEN invalid")
        errors.append("Invalid BOT_TOKEN")
    
    if settings.WEBAPP_URL:
        print(f"  [OK] WEBAPP_URL: {settings.WEBAPP_URL}")
    else:
        print("  [WARN] WEBAPP_URL not set")
        warnings.append("WEBAPP_URL not set")
    
    if settings.OPENAI_API_KEY:
        print(f"  [OK] OPENAI_API_KEY set")
    else:
        print("  [WARN] OPENAI_API_KEY not set")
        warnings.append("OPENAI_API_KEY not set")
        
    if settings.ADMIN_IDS:
        print(f"  [OK] ADMIN_IDS: {settings.ADMIN_IDS}")
    else:
        print("  [WARN] ADMIN_IDS not set")
        warnings.append("ADMIN_IDS not set")
except Exception as e:
    print(f"  [ERROR] Config: {e}")
    errors.append(f"Config error: {e}")

# 4. Database
print("\n[4] CHECKING DATABASE...")
async def check_db():
    async with aiosqlite.connect('mindflow.db') as db:
        db.row_factory = aiosqlite.Row
        
        tables = []
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as c:
            for row in await c.fetchall():
                tables.append(row['name'])
        
        required_tables = ['users', 'tasks', 'plans', 'stats', 'gamification', 'reminders']
        for t in required_tables:
            if t in tables:
                print(f"  [OK] Table: {t}")
            else:
                print(f"  [ERROR] Table: {t} - MISSING")
                errors.append(f"Missing table: {t}")
        
        try:
            task = await TaskRepo.create(
                user_id=8375524976,
                title='__TEST_TASK__',
                category='test'
            )
            print(f"  [OK] TaskRepo.create() id={task.id}")
            
            fetched = await TaskRepo.get(task.id)
            if fetched:
                print("  [OK] TaskRepo.get()")
            else:
                print("  [ERROR] TaskRepo.get()")
                errors.append("TaskRepo.get failed")
            
            await TaskRepo.delete(task.id)
            print("  [OK] TaskRepo.delete()")
            
        except Exception as e:
            print(f"  [ERROR] TaskRepo: {e}")
            errors.append(f"TaskRepo error: {e}")
        
        try:
            g = await GamificationRepo.get_or_create(8375524976)
            print(f"  [OK] GamificationRepo xp={g.xp}")
        except Exception as e:
            print(f"  [ERROR] GamificationRepo: {e}")
            errors.append(f"GamificationRepo error: {e}")

asyncio.run(check_db())

# 5. WebApp
print("\n[5] CHECKING WEBAPP...")
webapp_path = 'C:/kronos/webapp/index.html'
if os.path.exists(webapp_path):
    with open(webapp_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('tg.sendData', 'Telegram integration'),
        ('saveState()', 'State saving'),
        ('renderTasks()', 'Task rendering'),
        ('toggleTask', 'Task completion'),
        ('state.user.xp', 'XP system'),
        ('localStorage', 'Persistence'),
    ]
    
    for check, name in checks:
        if check in content:
            print(f"  [OK] {name}")
        else:
            print(f"  [WARN] {name} - may be missing")
            warnings.append(f"WebApp: {name} missing")
    
    print(f"  [OK] File size: {len(content)} bytes")
else:
    print("  [ERROR] index.html not found")
    errors.append("WebApp index.html missing")

# 6. Security
print("\n[6] CHECKING SECURITY...")
env_path = 'C:/kronos/.env'
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    if 'BOT_TOKEN=' in env_content and 'your_' not in env_content.lower():
        print("  [OK] BOT_TOKEN is set")
    else:
        print("  [WARN] BOT_TOKEN may be placeholder")
        warnings.append("BOT_TOKEN may be placeholder")
    
    main_path = 'C:/kronos/main.py'
    if os.path.exists(main_path):
        with open(main_path, 'r') as f:
            main_content = f.read()
        if 'AAE' in main_content and 'settings.BOT_TOKEN' not in main_content:
            print("  [ERROR] Token may be hardcoded!")
            errors.append("Token may be hardcoded")
        else:
            print("  [OK] Token not hardcoded")

# Summary
print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)

if errors:
    print(f"\n[ERRORS] {len(errors)}:")
    for e in errors:
        print(f"  - {e}")

if warnings:
    print(f"\n[WARNINGS] {len(warnings)}:")
    for w in warnings:
        print(f"  - {w}")

if not errors:
    print("\n>>> READY FOR PRODUCTION! <<<")
    print("\nNext steps:")
    print("  1. Update WebApp on Netlify")
    print("  2. Deploy bot to hosting")
    print("  3. Set up environment variables on hosting")
else:
    print("\n>>> NOT READY - Fix errors first! <<<")
