import aiosqlite
from datetime import datetime
from typing import Optional


class Database:
    def __init__(self, db_path: str = "shop.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT,
                    full_name   TEXT,
                    is_banned   INTEGER DEFAULT 0,
                    joined_at   TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS gifts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    description TEXT,
                    price       INTEGER NOT NULL,
                    emoji       TEXT DEFAULT '🎁',
                    photo_id    TEXT,
                    stock       INTEGER DEFAULT -1,
                    is_active   INTEGER DEFAULT 1,
                    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER NOT NULL,
                    gift_id         INTEGER NOT NULL,
                    amount          INTEGER NOT NULL,
                    status          TEXT DEFAULT 'pending',
                    payment_id      TEXT,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at    TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id     INTEGER PRIMARY KEY,
                    added_by    INTEGER,
                    added_at    TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    # ─── USERS ────────────────────────────────────────────
    async def get_or_create_user(self, user_id: int, username: str, full_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
            if row is None:
                await db.execute(
                    "INSERT INTO users (user_id, username, full_name) VALUES (?,?,?)",
                    (user_id, username, full_name)
                )
                await db.commit()
            else:
                await db.execute(
                    "UPDATE users SET username=?, full_name=? WHERE user_id=?",
                    (username, full_name, user_id)
                )
                await db.commit()

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
                return await cur.fetchone()

    async def get_all_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE is_banned=0") as cur:
                return await cur.fetchall()

    async def ban_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
            await db.commit()

    async def unban_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
            await db.commit()

    async def is_banned(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                return bool(row[0]) if row else False

    # ─── GIFTS ────────────────────────────────────────────
    async def add_gift(self, name, description, price, emoji, photo_id=None, stock=-1):
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "INSERT INTO gifts (name, description, price, emoji, photo_id, stock) VALUES (?,?,?,?,?,?)",
                (name, description, price, emoji, photo_id, stock)
            )
            await db.commit()
            return cur.lastrowid

    async def get_gifts(self, only_active=True):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM gifts"
            if only_active:
                query += " WHERE is_active=1 AND (stock=-1 OR stock>0)"
            query += " ORDER BY id"
            async with db.execute(query) as cur:
                return await cur.fetchall()

    async def get_gift(self, gift_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM gifts WHERE id=?", (gift_id,)) as cur:
                return await cur.fetchone()

    async def update_gift(self, gift_id, **kwargs):
        async with aiosqlite.connect(self.db_path) as db:
            for key, val in kwargs.items():
                await db.execute(f"UPDATE gifts SET {key}=? WHERE id=?", (val, gift_id))
            await db.commit()

    async def delete_gift(self, gift_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM gifts WHERE id=?", (gift_id,))
            await db.commit()

    async def decrease_stock(self, gift_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE gifts SET stock=stock-1 WHERE id=? AND stock>0",
                (gift_id,)
            )
            await db.commit()

    # ─── ORDERS ───────────────────────────────────────────
    async def create_order(self, user_id, gift_id, amount):
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "INSERT INTO orders (user_id, gift_id, amount) VALUES (?,?,?)",
                (user_id, gift_id, amount)
            )
            await db.commit()
            return cur.lastrowid

    async def complete_order(self, order_id, payment_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE orders SET status='completed', payment_id=?, completed_at=CURRENT_TIMESTAMP WHERE id=?",
                (payment_id, order_id)
            )
            await db.commit()

    async def get_user_orders(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT o.*, g.name AS gift_name, g.emoji
                FROM orders o
                JOIN gifts g ON o.gift_id = g.id
                WHERE o.user_id=? AND o.status='completed'
                ORDER BY o.created_at DESC
            """, (user_id,)) as cur:
                return await cur.fetchall()

    async def get_all_orders(self, limit=50):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT o.*, g.name AS gift_name, g.emoji,
                       u.username, u.full_name
                FROM orders o
                JOIN gifts g ON o.gift_id = g.id
                JOIN users u ON o.user_id = u.user_id
                WHERE o.status='completed'
                ORDER BY o.created_at DESC LIMIT ?
            """, (limit,)) as cur:
                return await cur.fetchall()

    async def get_order(self, order_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM orders WHERE id=?", (order_id,)) as cur:
                return await cur.fetchone()

    # ─── STATS ────────────────────────────────────────────
    async def get_stats(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c:
                total_users = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned=1") as c:
                banned = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM orders WHERE status='completed'") as c:
                total_orders = (await c.fetchone())[0]
            async with db.execute("SELECT SUM(amount) FROM orders WHERE status='completed'") as c:
                total_revenue = (await c.fetchone())[0] or 0
            async with db.execute("SELECT COUNT(*) FROM gifts WHERE is_active=1") as c:
                active_gifts = (await c.fetchone())[0]
        return {
            "total_users": total_users,
            "banned": banned,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "active_gifts": active_gifts,
        }

    # ─── ADMINS ───────────────────────────────────────────
    async def add_admin(self, user_id: int, added_by: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?,?)",
                (user_id, added_by)
            )
            await db.commit()

    async def remove_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
            await db.commit()

    async def get_admins(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM admins") as cur:
                return await cur.fetchall()

    async def is_admin_db(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
                return (await cur.fetchone()) is not None
