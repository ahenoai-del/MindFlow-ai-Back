import asyncio
import aiosqlite
from db import TaskRepo, UserRepo, GamificationRepo

async def test_db():
    print("=== DATABASE TEST ===\n")
    
    async with aiosqlite.connect('mindflow.db') as db:
        db.row_factory = aiosqlite.Row
        
        tables = []
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as c:
            for row in await c.fetchall():
                tables.append(row['name'])
        print(f"Tables: {tables}\n")
        
        async with db.execute('SELECT id, username, is_premium FROM users') as c:
            users = await c.fetchall()
            print(f"Users: {len(users)}")
            for u in users:
                print(f"  - {u['id']}: @{u['username']} premium={u['is_premium']}")
        print()
        
        async with db.execute('SELECT COUNT(*) as cnt FROM tasks') as c:
            row = await c.fetchone()
            print(f"Tasks before: {row['cnt']}")
    
    print("\n=== CREATE TASK TEST ===\n")
    
    task = await TaskRepo.create(
        user_id=8375524976,
        title='Тестовая задача',
        category='work',
        priority=1
    )
    print(f"Created: ID={task.id}, title={task.title}")
    
    async with aiosqlite.connect('mindflow.db') as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT COUNT(*) as cnt FROM tasks') as c:
            row = await c.fetchone()
            print(f"Tasks after create: {row['cnt']}")
    
    print("\n=== GAMIFICATION TEST ===\n")
    
    g, level, level_up = await GamificationRepo.add_xp(8375524976, 50)
    print(f"XP added: xp={g.xp}, level={level}, level_up={level_up}")
    
    print("\n=== DELETE TEST TASK ===\n")
    
    await TaskRepo.delete(task.id)
    print("Deleted test task")
    
    async with aiosqlite.connect('mindflow.db') as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT COUNT(*) as cnt FROM tasks') as c:
            row = await c.fetchone()
            print(f"Tasks after delete: {row['cnt']}")
    
    print("\n=== ALL TESTS PASSED ===")

asyncio.run(test_db())
