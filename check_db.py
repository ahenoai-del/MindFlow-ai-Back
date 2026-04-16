import aiosqlite
import asyncio

async def check():
    async with aiosqlite.connect('mindflow.db') as db:
        db.row_factory = aiosqlite.Row
        
        print("=== USERS ===")
        async with db.execute("SELECT * FROM users") as c:
            for row in await c.fetchall():
                print(dict(row))
        
        print("\n=== TASKS ===")
        async with db.execute("SELECT * FROM tasks") as c:
            for row in await c.fetchall():
                print(dict(row))
        
        print("\n=== GAMIFICATION ===")
        async with db.execute("SELECT * FROM gamification") as c:
            for row in await c.fetchall():
                print(dict(row))

asyncio.run(check())
