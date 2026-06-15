import sqlite3
import os
from datetime import datetime, timedelta

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "tracker.db")


def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '其他',
            purchase_date TEXT NOT NULL,
            shelf_life_days INTEGER NOT NULL,
            expire_date TEXT NOT NULL,
            is_notified INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def add_item(name, category, purchase_date, shelf_life_days):
    purchase = datetime.strptime(purchase_date, "%Y-%m-%d")
    expire = purchase + timedelta(days=shelf_life_days)
    expire_date = expire.strftime("%Y-%m-%d")

    conn = get_connection()
    conn.execute(
        "INSERT INTO items (name, category, purchase_date, shelf_life_days, expire_date) VALUES (?, ?, ?, ?, ?)",
        (name, category, purchase_date, shelf_life_days, expire_date),
    )
    conn.commit()
    conn.close()


def get_all_items():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM items ORDER BY expire_date ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expiring_soon_items(days=5):
    """获取即将在指定天数内过期的商品（未通知过的）"""
    today = datetime.today().strftime("%Y-%m-%d")
    deadline = (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")

    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM items WHERE expire_date BETWEEN ? AND ? AND is_notified = 0 ORDER BY expire_date ASC",
        (today, deadline),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expired_items():
    conn = get_connection()
    today = datetime.today().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM items WHERE expire_date < ? ORDER BY expire_date ASC",
        (today,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_notified(item_id):
    conn = get_connection()
    conn.execute("UPDATE items SET is_notified = 1 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def delete_item(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def get_shopping_suggestions():
    """获取购物建议：过期 + 3天内即将过期的商品，按分类汇总"""
    today = datetime.today().strftime("%Y-%m-%d")
    deadline = (datetime.today() + timedelta(days=3)).strftime("%Y-%m-%d")

    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM items WHERE expire_date <= ? ORDER BY category, expire_date ASC",
        (deadline,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]